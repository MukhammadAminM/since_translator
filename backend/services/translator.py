from typing import Literal, Optional
import asyncio
import os
import re
import json
from pathlib import Path

# OpenAI для перевода
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Глоссарий
from services.glossary_manager import GlossaryManager

# Mathpix для распознавания формул
try:
    from services.mathpix_service import MathpixService
    MATHPIX_AVAILABLE = True
except ImportError:
    MATHPIX_AVAILABLE = False

# Для извлечения текста из файлов
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class TranslationService:
    """
    Сервис для перевода текстов с использованием LLM моделей
    """
    
    def __init__(self):
        # Модели OpenAI для разных типов перевода
        self.models = {
            "general": "gpt-4o-mini",      # Быстрая и экономичная модель
            "engineering": "gpt-4o",       # Более мощная модель для технических текстов
            "academic": "gpt-4o",          # Для академических текстов
            "scientific": "gpt-4o"         # Для научных текстов
        }
        
        # Инициализация OpenAI клиента
        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY не найден в переменных окружения. "
                    "Установите его через .env файл или переменные окружения."
                )
            self.client = AsyncOpenAI(api_key=api_key)
        else:
            self.client = None
            print("⚠️  OpenAI библиотека не установлена. Установите: pip install openai")
        
        # Загружаем словарь химических элементов
        self.chemical_data = self._load_chemical_data()
        
        # Инициализация менеджера глоссария
        try:
            self.glossary_manager = GlossaryManager()
        except Exception as e:
            print(f"⚠️  Не удалось загрузить глоссарий: {str(e)}")
            self.glossary_manager = None
        
        # Инициализация Mathpix для распознавания формул
        if MATHPIX_AVAILABLE:
            try:
                self.mathpix = MathpixService()
            except Exception as e:
                print(f"⚠️  Не удалось инициализировать Mathpix: {str(e)}")
                self.mathpix = None
        else:
            self.mathpix = None
    
    async def translate(
        self,
        text: str,
        source_lang: Literal["ru", "ar", "zh"],
        target_lang: str = "en",
        model: Literal["general", "engineering", "academic", "scientific"] = "general"
    ) -> str:
        """
        Переводит текст с исходного языка на целевой используя выбранную модель OpenAI
        """
        
        if not OPENAI_AVAILABLE or not self.client:
            raise RuntimeError(
                "OpenAI не настроен. Установите библиотеку: pip install openai "
                "и установите OPENAI_API_KEY в переменных окружения."
            )
        
        if not text.strip():
            raise ValueError("Текст для перевода не может быть пустым")
        
        import time
        start_time = time.time()
        print(f"   🔄 Начинаем защиту формул... (длина текста: {len(text)} символов)")
        # Защищаем формулы и технические обозначения от перевода
        text, protected_items = self._protect_formulas_and_notations(text)
        elapsed_time = time.time() - start_time
        print(f"   ✅ Защита формул завершена (защищено элементов: {len(protected_items)}, время: {elapsed_time:.2f} сек)")
        
        # Названия языков для промпта
        lang_names = {
            "ru": "Russian",
            "ar": "Arabic",
            "zh": "Chinese"
        }
        
        # Специальные инструкции для разных типов перевода
        model_instructions = {
            "general": "Translate naturally and accurately, maintaining the original tone and style.",
            "engineering": (
                "Translate technical and engineering terminology precisely. Maintain technical accuracy and use appropriate engineering terminology. "
                "CRITICAL: Do NOT translate mathematical formulas, equations, variable names (Isp, g0, m0, mf, Δv, etc.), "
                "technical abbreviations (LEO, GTO, TLI, TMI, GSO, IMU, RCS, etc.), "
                "fuel combinations (RP-1/LOX, LH2/LOX, CH4/LOX, etc.), "
                "or numerical values with units (9.3-9.5 km/s, 285-300 s, etc.). "
                "Keep all formulas, equations, and technical notation exactly as they appear in the original text."
            ),
            "academic": (
                "Translate academic texts with precision. Maintain formal academic style, preserve citations and references if present. "
                "CRITICAL: Do NOT translate mathematical formulas, equations, variable names, or technical notation. "
                "Keep all formulas and equations exactly as they appear in the original text."
            ),
            "scientific": (
                "Translate scientific texts with utmost precision. Maintain scientific terminology, preserve formulas and technical notation exactly. "
                "CRITICAL: NEVER translate mathematical formulas, equations, variable names (like Δv, Isp, g0, m0, mf), "
                "mathematical symbols, technical abbreviations, or numerical values with units. "
                "Keep all formulas, equations, and technical notation exactly as they appear in the original text."
            )
        }
        
        # Добавляем глоссарий в промпт, если он доступен
        # Используем умный поиск релевантных терминов из текста
        # Ограничиваем размер глоссария, чтобы не превысить лимит токенов
        glossary_text = ""
        if self.glossary_manager:
            # Начинаем с меньшего количества терминов, чтобы не превысить лимит
            max_terms = 50  # Уменьшено с 200 до 50
            glossary_summary = self.glossary_manager.get_glossary_summary(
                source_lang, 
                text=text,  # Передаем текст для поиска релевантных терминов
                max_terms=max_terms
            )
            if glossary_summary:
                glossary_text = f"\n\n{glossary_summary}"
        
        # Добавляем специальные инструкции для защищенных элементов (оптимизированная версия)
        protection_instructions = (
            f"\n\n⚠️ CRITICAL: {len(protected_items)} protected placeholders (__PROTECTED_0__ to __PROTECTED_{len(protected_items)-1}__) "
            f"MUST be preserved EXACTLY. NEVER translate or modify them. All {len(protected_items)} must appear in translation.\n"
        ) if protected_items else ""
        
        system_prompt = (
            f"You are a professional translator specializing in {model} translation. "
            f"Translate the following text from {lang_names[source_lang]} to {target_lang.upper()}. "
            f"{model_instructions[model]} "
            f"Maintain the original formatting, paragraph structure, and line breaks. "
            f"Do not add any explanations, comments, or notes - provide only the translation."
            f"{protection_instructions}"
            f"{glossary_text}"
        )
        
        # Функция для оценки размера запроса (приблизительно)
        def estimate_tokens(text: str) -> int:
            # Приблизительная оценка: 1 токен ≈ 4 символа для английского, меньше для других языков
            return len(text) // 3
        
        # Проверяем размер запроса и уменьшаем при необходимости
        total_estimated_tokens = estimate_tokens(system_prompt) + estimate_tokens(text)
        max_allowed_tokens = 25000  # Оставляем запас от лимита 30000
        
        if total_estimated_tokens > max_allowed_tokens:
            print(f"   ⚠️  Запрос слишком большой (~{total_estimated_tokens} токенов), уменьшаем размер...")
            # Уменьшаем размер глоссария
            if glossary_text:
                # Пробуем уменьшить глоссарий
                if self.glossary_manager:
                    glossary_summary = self.glossary_manager.get_glossary_summary(
                        source_lang, 
                        text=text,
                        max_terms=30  # Еще меньше
                    )
                    if glossary_summary:
                        glossary_text = f"\n\n{glossary_summary}"
                    else:
                        glossary_text = ""
                system_prompt = (
                    f"You are a professional translator specializing in {model} translation. "
                    f"Translate the following text from {lang_names[source_lang]} to {target_lang.upper()}. "
                    f"{model_instructions[model]} "
                    f"Maintain the original formatting, paragraph structure, and line breaks. "
                    f"Do not add any explanations, comments, or notes - provide only the translation."
                    f"{protection_instructions}"
                    f"{glossary_text}"
                )
            
            # Если все еще слишком большой, разбиваем текст на части
            if estimate_tokens(system_prompt) + estimate_tokens(text) > max_allowed_tokens:
                print(f"   ⚠️  Текст слишком большой, разбиваем на части...")
                # Разбиваем текст на части по параграфам
                paragraphs = text.split('\n\n')
                translated_parts = []
                current_chunk = []
                current_size = estimate_tokens(system_prompt)
                
                for para in paragraphs:
                    para_size = estimate_tokens(para)
                    if current_size + para_size > max_allowed_tokens and current_chunk:
                        # Переводим текущий chunk
                        chunk_text = '\n\n'.join(current_chunk)
                        translated = await self._translate_chunk(
                            chunk_text, system_prompt, model, protected_items
                        )
                        translated_parts.append(translated)
                        current_chunk = [para]
                        current_size = estimate_tokens(system_prompt) + para_size
                    else:
                        current_chunk.append(para)
                        current_size += para_size
                
                # Переводим последний chunk
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    translated = await self._translate_chunk(
                        chunk_text, system_prompt, model, protected_items
                    )
                    translated_parts.append(translated)
                
                translated_text = '\n\n'.join(translated_parts)
                # Восстанавливаем формулы
                translated_text = self._restore_formulas_and_notations(translated_text, protected_items)
                return translated_text
        
        print(f"   🔄 Отправляем запрос в OpenAI... (длина текста: {len(text)} символов, модель: {model})")
        try:
            response = await self.client.chat.completions.create(
                model=self.models[model],
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.3,  # Низкая температура для более точного перевода
                max_tokens=4000   # Максимальная длина ответа
            )
            print(f"   ✅ Получен ответ от OpenAI")
            
            translated_text = response.choices[0].message.content.strip()
            
            # Проверяем, что плейсхолдеры сохранились
            if protected_items:
                preserved_count = sum(1 for placeholder in protected_items.keys() if placeholder in translated_text)
                total_count = len(protected_items)
                if preserved_count < total_count:
                    missing = set(protected_items.keys()) - {p for p in protected_items.keys() if p in translated_text}
                    print(f"   ⚠️  Потеряно плейсхолдеров: {len(missing)}/{total_count}")
                    # Пытаемся найти похожие строки, которые могли быть переведены
                    for placeholder in list(missing)[:5]:
                        original = protected_items[placeholder]
                        print(f"      ❌ {placeholder} -> '{original[:50]}...'")
                    
                    # КРИТИЧЕСКАЯ ОШИБКА: если потеряно слишком много плейсхолдеров, пробуем повторить перевод
                    if preserved_count == 0:
                        print(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: Все плейсхолдеры потеряны!")
                        print(f"   🔄 Пробуем повторить перевод с более строгими инструкциями...")
                        # Повторяем запрос с еще более строгими инструкциями
                        strict_prompt = system_prompt + "\n\n" + "="*80 + "\n" + \
                            "⚠️ ПРЕДЫДУЩАЯ ПОПЫТКА ПЕРЕВОДА ПРОВАЛИЛАСЬ - ВСЕ ПЛЕЙСХОЛДЕРЫ БЫЛИ ПОТЕРЯНЫ!\n" + \
                            "В ЭТОМ ПЕРЕВОДЕ ВЫ ОБЯЗАНЫ СОХРАНИТЬ ВСЕ ПЛЕЙСХОЛДЕРЫ БЕЗ ИСКЛЮЧЕНИЯ!\n" + \
                            "="*80
                        
                        response = await self.client.chat.completions.create(
                            model=self.models[model],
                            messages=[
                                {"role": "system", "content": strict_prompt},
                                {"role": "user", "content": text}
                            ],
                            temperature=0.1,  # Еще более низкая температура
                            max_tokens=4000
                        )
                        translated_text = response.choices[0].message.content.strip()
                        
                        # Проверяем снова
                        preserved_count = sum(1 for placeholder in protected_items.keys() if placeholder in translated_text)
                        if preserved_count > 0:
                            print(f"   ✅ После повторной попытки сохранено: {preserved_count}/{total_count}")
                        else:
                            print(f"   ❌ Повторная попытка также не сохранила плейсхолдеры")
                else:
                    print(f"   ✅ Все плейсхолдеры сохранены: {preserved_count}/{total_count}")
            
            # Восстанавливаем защищенные формулы и обозначения
            translated_text = self._restore_formulas_and_notations(translated_text, protected_items)
            
            if not translated_text:
                raise ValueError("OpenAI вернул пустой ответ")
            
            return translated_text
            
        except Exception as e:
            error_str = str(e)
            # Обрабатываем ошибку 429 (превышение лимита токенов)
            if "429" in error_str or "rate_limit" in error_str.lower() or "tokens per min" in error_str.lower() or "TPM" in error_str:
                print(f"   ⚠️  Превышен лимит токенов (429), пробуем уменьшить размер запроса...")
                # Уменьшаем размер глоссария и упрощаем промпт
                if self.glossary_manager:
                    glossary_summary = self.glossary_manager.get_glossary_summary(
                        source_lang, 
                        text=text,
                        max_terms=20  # Минимальное количество
                    )
                    if glossary_summary:
                        glossary_text = f"\n\n{glossary_summary}"
                    else:
                        glossary_text = ""
                else:
                    glossary_text = ""
                
                # Упрощаем protection_instructions
                protection_instructions = (
                    f"\n\n⚠️ Preserve {len(protected_items)} placeholders (__PROTECTED_0__ to __PROTECTED_{len(protected_items)-1}__) exactly.\n"
                ) if protected_items else ""
                
                # Упрощаем системный промпт
                system_prompt = (
                    f"Translate from {lang_names[source_lang]} to {target_lang.upper()}. "
                    f"{model_instructions[model]} "
                    f"Maintain formatting.{protection_instructions}{glossary_text}"
                )
                
                # Пробуем еще раз с уменьшенным промптом
                try:
                    response = await self.client.chat.completions.create(
                        model=self.models[model],
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text}
                        ],
                        temperature=0.3,
                        max_tokens=4000
                    )
                    translated_text = response.choices[0].message.content.strip()
                    translated_text = self._restore_formulas_and_notations(translated_text, protected_items)
                    return translated_text
                except Exception as e2:
                    error_msg = f"Ошибка при переводе через OpenAI (после уменьшения размера): {str(e2)}"
                    print(f"❌ {error_msg}")
                    raise RuntimeError(error_msg) from e2
            
            error_msg = f"Ошибка при переводе через OpenAI: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg) from e
    
    async def _translate_chunk(
        self, 
        chunk_text: str, 
        system_prompt: str, 
        model: str,
        protected_items: dict
    ) -> str:
        """Переводит часть текста (для больших текстов)"""
        try:
            response = await self.client.chat.completions.create(
                model=self.models[model],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": chunk_text}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"   ⚠️  Ошибка при переводе части текста: {str(e)}")
            return chunk_text  # Возвращаем оригинал в случае ошибки
    
    def _load_chemical_data(self) -> dict:
        """Загружает словарь химических элементов из JSON файла"""
        try:
            # Путь к файлу с химическими элементами
            chemical_file = Path(__file__).parent.parent / "data" / "chemical_elements.json"
            if chemical_file.exists():
                with open(chemical_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"✅ Загружен словарь химических элементов: {len(data.get('elements', {}))} элементов, {len(data.get('common_compounds', {}))} соединений")
                    return data
            else:
                print(f"⚠️  Файл с химическими элементами не найден: {chemical_file}")
                # Возвращаем базовую структуру для работы
                return {
                    'elements': {'H': 'Hydrogen', 'C': 'Carbon', 'N': 'Nitrogen', 'O': 'Oxygen'},
                    'common_compounds': {'H2O': 'Water', 'CO2': 'Carbon dioxide', 'CH4': 'Methane', 'N2O4': 'Dinitrogen tetroxide'},
                    'rocket_fuels': {'RP-1': 'Rocket Propellant-1', 'LOX': 'Liquid Oxygen', 'LH2': 'Liquid Hydrogen', 'CH4': 'Methane', 'MMH': 'Monomethylhydrazine', 'N2O4': 'Dinitrogen tetroxide'},
                    'fuel_combinations': {}
                }
        except Exception as e:
            print(f"⚠️  Ошибка при загрузке словаря химических элементов: {str(e)}")
            # Возвращаем базовую структуру для работы
            return {
                'elements': {'H': 'Hydrogen', 'C': 'Carbon', 'N': 'Nitrogen', 'O': 'Oxygen'},
                'common_compounds': {'H2O': 'Water', 'CO2': 'Carbon dioxide', 'CH4': 'Methane', 'N2O4': 'Dinitrogen tetroxide'},
                'rocket_fuels': {'RP-1': 'Rocket Propellant-1', 'LOX': 'Liquid Oxygen', 'LH2': 'Liquid Hydrogen', 'CH4': 'Methane', 'MMH': 'Monomethylhydrazine', 'N2O4': 'Dinitrogen tetroxide'},
                'fuel_combinations': {}
            }
    
    def _fix_ocr_errors_in_formulas(self, text: str) -> str:
        """
        Исправляет типичные ошибки OCR в химических формулах
        Например: CH,/LOX -> CH4/LOX, LH,/LOX -> LH2/LOX
        Также исправляет ошибки OCR в математических формулах для русского языка
        Например: Ук -> V_k, М0 -> m_0, лв -> лв (исправление русских букв в формулах)
        
        Args:
            text: Исходный текст
        
        Returns:
            Текст с исправленными формулами
        """
        fixed_count = 0
        fixed_formulas = []
        
        # Карта исправления типичных ошибок OCR в формулах для русского языка
        # Русские буквы, которые часто путаются с латинскими в формулах
        russian_to_latin_in_formulas = {
            # Заглавные буквы
            'У': 'V', 'К': 'K', 'М': 'M', 'Н': 'H', 'В': 'B', 'А': 'A',
            'Р': 'P', 'С': 'C', 'Т': 'T', 'О': 'O', 'Е': 'E', 'Х': 'X',
            'Г': 'G', 'Д': 'D', 'Л': 'L', 'П': 'P', 'И': 'I', 'З': 'Z',
            'Я': 'R', 'Б': 'B', 'Ю': 'Y', 'Э': 'E', 'Ф': 'F', 'Ж': 'J',
            # Строчные буквы (в формулах обычно используются заглавные, но на всякий случай)
            'у': 'v', 'к': 'k', 'м': 'm', 'н': 'h', 'в': 'b', 'а': 'a',
            'р': 'p', 'с': 'c', 'т': 't', 'о': 'o', 'е': 'e', 'х': 'x',
            'г': 'g', 'д': 'd', 'л': 'l', 'п': 'p', 'и': 'i', 'з': 'z',
        }
        
        # Исправляем типичные ошибки OCR в математических формулах
        # Ищем строки, которые выглядят как формулы (содержат =, +, -, *, /, цифры и русские буквы)
        formula_line_pattern = r'^[^а-яА-Я]*[УКМНВАРСТОЕХГДЛПИЗЯБЮЭФЖукмнварстоехгдлпизябюэфж][^а-яА-Я]*(?:[=+\-*/]|\(|\)|\d)[^а-яА-Я]*$'
        
        lines = text.split('\n')
        fixed_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            # Проверяем, является ли строка формулой с ошибками OCR
            if (len(line_stripped) < 150 and  # Короткая строка
                len(line_stripped) > 3 and
                any(op in line_stripped for op in ['=', '+', '-', '*', '/', '(', ')']) and
                any(rus_char in line_stripped for rus_char in russian_to_latin_in_formulas.keys()) and
                any(char.isdigit() for char in line_stripped)):
                
                # Исправляем русские буквы в формулах на латинские
                fixed_line = line
                original_line = line
                
                # Сначала исправляем типичные ошибки OCR в переменных (более специфичные паттерны)
                common_fixes = {
                    r'\bУк\b': 'V_k',
                    r'\bУ\b': 'V',  # Если просто У в формуле
                    r'\bМ0\b': 'm_0',
                    r'\bМк\b': 'm_k',
                    r'\bМо\b': 'm_0',
                    r'\bМ\b': 'M',  # Если просто М в формуле
                    r'\bАv\b': 'Δv',
                    r'\bAv\b': 'Δv',
                    r'\bДУк\b': 'ΔV_k',
                    r'\bДУ\b': 'ΔV',
                    r'\bД\b': 'Δ',  # Если просто Д в формуле
                    r'\bлв\b': 'лв',  # Это не переменная, оставляем
                    r'\bГуд\b': 'I_{sp}',  # Типичная ошибка OCR
                    r'\bГ\b': 'I',  # Если просто Г в формуле
                }
                
                for pattern, replacement in common_fixes.items():
                    if re.search(pattern, fixed_line):
                        fixed_line = re.sub(pattern, replacement, fixed_line)
                
                # Затем исправляем остальные русские буквы в контексте формул
                # Используем простой подход без look-behind для избежания ошибок
                # Заменяем русские буквы, которые находятся рядом с математическими символами
                for rus_char, lat_char in russian_to_latin_in_formulas.items():
                    # Используем простые паттерны с фиксированной шириной look-behind (один символ)
                    # Избегаем \s и других переменной ширины в look-behind
                    
                    # Паттерн 1: русская буква между операторами (фиксированная ширина - один символ)
                    pattern1 = r'(?<=[=+\-*/\(\)\d])' + re.escape(rus_char) + r'(?=[=+\-*/\(\)\d])'
                    # Паттерн 2: русская буква после оператора, перед пробелом (простая замена без look-ahead)
                    pattern2 = r'([=+\-*/\(\)\d])' + re.escape(rus_char) + r' '
                    # Паттерн 3: русская буква после пробела, перед оператором (простая замена)
                    pattern3 = r' ' + re.escape(rus_char) + r'([=+\-*/\(\)\d])'
                    # Паттерн 4: русская буква в начале строки, перед оператором
                    pattern4 = r'^' + re.escape(rus_char) + r'(?=[=+\-*/\(\)\d])'
                    # Паттерн 5: русская буква после цифры, перед оператором
                    pattern5 = r'(?<=\d)' + re.escape(rus_char) + r'(?=[=+\-*/\(\)\d])'
                    # Паттерн 6: русская буква после оператора, перед цифрой
                    pattern6 = r'(?<=[=+\-*/\(\)])' + re.escape(rus_char) + r'(?=\d)'
                    # Обрабатываем паттерны по отдельности, чтобы избежать ошибок
                    # Паттерны с фиксированной шириной look-behind/look-ahead
                    safe_patterns = [pattern1, pattern4, pattern5, pattern6]
                    for pattern in safe_patterns:
                        try:
                            if re.search(pattern, fixed_line):
                                fixed_line = re.sub(pattern, lat_char, fixed_line)
                                if fixed_line != original_line and fixed_count < 20:
                                    fixed_count += 1
                                    if fixed_count <= 10:
                                        fixed_formulas.append(f"{rus_char} -> {lat_char} в формуле")
                                break
                        except re.error:
                            continue
                    
                    # Обрабатываем паттерны с пробелами отдельно (используем группы захвата вместо look-behind/look-ahead)
                    try:
                        if re.search(pattern2, fixed_line):
                            fixed_line = re.sub(pattern2, r'\1' + lat_char + r' ', fixed_line)
                            if fixed_line != original_line and fixed_count < 20:
                                fixed_count += 1
                                if fixed_count <= 10:
                                    fixed_formulas.append(f"{rus_char} -> {lat_char} в формуле")
                    except re.error:
                        pass
                    
                    try:
                        if re.search(pattern3, fixed_line):
                            fixed_line = re.sub(pattern3, r' ' + lat_char + r'\1', fixed_line)
                            if fixed_line != original_line and fixed_count < 20:
                                fixed_count += 1
                                if fixed_count <= 10:
                                    fixed_formulas.append(f"{rus_char} -> {lat_char} в формуле")
                    except re.error:
                        pass
                
                if fixed_line != line:
                    fixed_lines.append(fixed_line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        text = '\n'.join(fixed_lines)
        
        if fixed_count > 0:
            print(f"   🔧 Исправлено ошибок OCR в формулах: {fixed_count}")
            for formula in fixed_formulas[:10]:
                print(f"      - {formula}")
        
        # Получаем известные соединения и топлива из словаря
        compounds = self.chemical_data.get('common_compounds', {})
        fuels = self.chemical_data.get('rocket_fuels', {})
        elements = self.chemical_data.get('elements', {})
        
        # Создаем список известных формул
        known_formulas = set(compounds.keys()) | set(fuels.keys())
        
        # 1. Исправляем запятые вместо цифр в комбинациях топлива
        # Паттерн: буква(ы) + запятая + /LOX (с возможными пробелами)
        fuel_comma_pattern = r'([A-Z][A-Z]?)\s*,\s*/LOX'
        def fix_fuel_comma(match):
            nonlocal fixed_count
            formula_part = match.group(1)  # CH или LH
            # Пробуем найти правильную цифру на основе известных формул
            # CH4/LOX, LH2/LOX - самые распространенные
            if formula_part == 'CH':
                fixed = 'CH4/LOX'
            elif formula_part == 'LH':
                fixed = 'LH2/LOX'
            else:
                # Для других случаев пробуем найти в словаре
                for known in known_formulas:
                    if known.startswith(formula_part) and '/LOX' in known:
                        fixed = known
                        break
                else:
                    # Если не нашли, оставляем как есть
                    return match.group(0)
            
            original = match.group(0)
            if fixed != original:
                fixed_count += 1
                fixed_formulas.append(f"{original} -> {fixed}")
            return fixed
        
        text = re.sub(fuel_comma_pattern, fix_fuel_comma, text)
        
        # 1.1. Также исправляем случаи типа "CH,/LOX" без пробелов
        fuel_comma_pattern2 = r'([A-Z][A-Z]?),/LOX'
        text = re.sub(fuel_comma_pattern2, fix_fuel_comma, text)
        
        # 2. Исправляем запятые вместо цифр в отдельных формулах
        # Паттерн: буква(ы) + запятая (в конце слова или перед пробелом/знаком препинания)
        formula_comma_pattern = r'\b([A-Z][A-Z]?),(?=\s|$|/|\(|:|\s*\(|,|\.)'
        def fix_formula_comma(match):
            nonlocal fixed_count
            formula_part = match.group(1)  # CH, LH, H2, N2 и т.д.
            original = match.group(0)
            
            # Пробуем найти правильную формулу в словаре
            for known in known_formulas:
                if known.startswith(formula_part):
                    # Проверяем, что это действительно формула (содержит цифру)
                    if re.search(r'\d', known):
                        fixed = known
                        if fixed != original:
                            fixed_count += 1
                            fixed_formulas.append(f"{original} -> {fixed}")
                        return fixed
            
            # Если не нашли в словаре, пробуем исправить на основе паттернов
            # CH, -> CH4 (метан), LH, -> LH2 (жидкий водород)
            if formula_part == 'CH':
                fixed = 'CH4'
            elif formula_part == 'LH':
                fixed = 'LH2'
            elif formula_part == 'H':
                fixed = 'H2'
            elif formula_part == 'N':
                fixed = 'N2'
            else:
                # Если не знаем, оставляем как есть
                return original
            
            if fixed != original:
                fixed_count += 1
                fixed_formulas.append(f"{original} -> {fixed}")
            return fixed
        
        text = re.sub(formula_comma_pattern, fix_formula_comma, text)
        
        if fixed_count > 0:
            print(f"   🔧 Исправлено ошибок OCR в формулах: {fixed_count}")
            for formula in fixed_formulas[:10]:
                print(f"      - {formula}")
        
        return text
    
    def _normalize_chemical_formulas(self, text: str) -> str:
        """
        Нормализует химические формулы сразу после OCR/извлечения текста
        Использует словарь химических элементов для правильной конвертации
        Конвертирует формулы типа CH4, LH2 в формат с подстрочными индексами CH_{4}, LH_{2}
        Это нужно делать ДО защиты формул, чтобы они правильно обрабатывались
        
        Args:
            text: Исходный текст
        
        Returns:
            Текст с нормализованными химическими формулами
        """
        # Сначала исправляем ошибки OCR (запятые вместо цифр и русские буквы в формулах)
        text = self._fix_ocr_errors_in_formulas(text)
        
        normalized_count = 0
        normalized_formulas = []
        
        # Получаем известные соединения и комбинации топлива из словаря
        compounds = self.chemical_data.get('common_compounds', {})
        fuels = self.chemical_data.get('rocket_fuels', {})
        fuel_combinations = self.chemical_data.get('fuel_combinations', {})
        elements = self.chemical_data.get('elements', {})
        
        # Создаем список известных формул для проверки
        known_formulas = set(compounds.keys()) | set(fuels.keys())
        
        def is_chemical_formula(formula: str) -> bool:
            """Проверяет, является ли строка химической формулой"""
            # Убираем пробелы
            formula = formula.replace(' ', '')
            # Проверяем, является ли это известной формулой
            if formula in known_formulas:
                return True
            # Проверяем паттерн: начинается с заглавной буквы, содержит цифры
            if re.match(r'^[A-Z][a-z]?\d+', formula):
                # Проверяем, начинается ли с известного элемента
                for element in elements.keys():
                    if formula.startswith(element):
                        return True
            return False
        
        # Карта для конвертации цифр в Unicode подстрочные индексы
        unicode_subscript_map = {
            '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
            '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'
        }
        
        def normalize_formula(formula: str, use_unicode: bool = True) -> str:
            """
            Нормализует химическую формулу, конвертируя цифры в подстрочные индексы
            Для простых формул использует Unicode подстрочные индексы (H₂O)
            Для сложных формул использует LaTeX формат (H_{2}O)
            """
            # Убираем пробелы
            formula = formula.replace(' ', '')
            
            if use_unicode:
                # Конвертируем цифры в Unicode подстрочные индексы для простых формул
                # Это будет отображаться как обычный текст, не как изображение
                def replace_digit(match):
                    digit = match.group(2)
                    return match.group(1) + unicode_subscript_map.get(digit, digit)
                normalized = re.sub(r'([A-Z][a-z]?)(\d+)', replace_digit, formula)
            else:
                # Конвертируем цифры в LaTeX подстрочные индексы для сложных формул
                normalized = re.sub(r'([A-Z][a-z]?)(\d+)', r'\1_{\2}', formula)
            
            return normalized
        
        # 1. Нормализуем комбинации топлива: CH4/LOX, LH2/LOX и т.д.
        # Используем Unicode подстрочные индексы для простых формул
        # Паттерн ищет формулы в любом контексте (включая середину предложения)
        fuel_pattern = r'(?<![A-Za-z0-9₀₁₂₃₄₅₆₇₈₉])([A-Z][A-Z]?\s*\d+)/LOX(?=\s|$|\(|\)|,|\.|;|!|\?|，|。|！|？|；|，)'
        def normalize_fuel(match):
            nonlocal normalized_count
            formula_part = match.group(1)  # CH4 или LH2 (возможно с пробелом)
            original = match.group(0)
            # Убираем пробелы
            formula_part = formula_part.replace(' ', '')
            # Пропускаем RP-1, так как он не требует нормализации
            if formula_part.startswith('RP'):
                return original
            # Пропускаем, если формула уже содержит Unicode подстрочные индексы
            if any(char in formula_part for char in '₀₁₂₃₄₅₆₇₈₉'):
                return original
            # Нормализуем формулу с Unicode подстрочными индексами
            normalized_part = normalize_formula(formula_part, use_unicode=True)
            result = f"{normalized_part}/LOX"
            if result != original:
                normalized_count += 1
                normalized_formulas.append(f"{original} -> {result}")
            return result
        
        # Применяем паттерн несколько раз, чтобы найти все варианты
        prev_text = ""
        iterations = 0
        while text != prev_text and iterations < 5:
            prev_text = text
            text = re.sub(fuel_pattern, normalize_fuel, text)
            iterations += 1
        
        # 2. Нормализуем известные соединения и формулы топлива
        # Используем Unicode подстрочные индексы для простых формул
        # Сортируем по длине (от длинных к коротким), чтобы не конфликтовать
        sorted_formulas = sorted(known_formulas, key=len, reverse=True)
        for formula in sorted_formulas:
            # Пропускаем, если формула уже содержит Unicode подстрочные индексы
            if any(char in formula for char in '₀₁₂₃₄₅₆₇₈₉'):
                continue  # Уже нормализована
            # Пропускаем, если формула не содержит цифр (не требует нормализации)
            if not re.search(r'\d', formula):
                continue
            # Ищем формулу в тексте (с границами слов, чтобы не трогать части других слов)
            pattern = r'\b' + re.escape(formula) + r'(?=\s|$|/|\(|:|\s*\(|,|\.)'
            def replace_known_formula(match):
                nonlocal normalized_count
                original = match.group(0)
                # Используем Unicode подстрочные индексы для простых формул
                normalized = normalize_formula(formula, use_unicode=True)
                if normalized != original:
                    normalized_count += 1
                    normalized_formulas.append(f"{original} -> {normalized}")
                return normalized
            text = re.sub(pattern, replace_known_formula, text)
        
        # 3. Нормализуем другие химические формулы (не из словаря, но похожие на формулы)
        # Ищем формулы типа CH4, LH2, H2O, N2O4 и т.д.
        # Улучшенный паттерн для поиска формул в тексте на разных языках
        # Паттерн ищет: буква(ы) + цифра(ы), возможно с пробелами между элементами
        # Более агрессивный поиск - ищем формулы в любом контексте
        standalone_pattern = r'(?<![A-Za-z0-9₀₁₂₃₄₅₆₇₈₉])([A-Z][a-z]?\s*\d+(?:[A-Z][a-z]?\s*\d+)*)(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،|，|。|！|？|؛|،|\s|$)'
        def normalize_standalone(match):
            formula = match.group(1)
            # Убираем пробелы из формулы
            formula_clean = formula.replace(' ', '')
            # Пропускаем известные аббревиатуры и исключения
            if formula_clean in ['RP1', 'LOX', 'MMH', 'IMU', 'RCS', 'GTO', 'TLI', 'TMI', 'LEO', 'GSO']:
                return formula
            # Пропускаем, если это число
            if formula_clean.isdigit():
                return formula
            # Пропускаем, если формула уже содержит Unicode подстрочные индексы
            if any(char in formula for char in '₀₁₂₃₄₅₆₇₈₉'):
                return formula
            # Пропускаем, если формула уже в LaTeX формате
            if '_{' in formula or '\\[' in formula:
                return formula
            # Проверяем, является ли это химической формулой
            if is_chemical_formula(formula_clean):
                # Используем Unicode подстрочные индексы для простых формул
                normalized = normalize_formula(formula_clean, use_unicode=True)
                if normalized != formula_clean:
                    nonlocal normalized_count
                    normalized_count += 1
                    normalized_formulas.append(f"{formula} -> {normalized}")
                return normalized
            return formula
        
        # Применяем паттерн несколько раз для надежности
        # Также применяем к каждой строке отдельно для лучшего покрытия
        lines = text.split('\n')
        normalized_lines = []
        for line in lines:
            prev_line = ""
            iterations = 0
            while line != prev_line and iterations < 5:
                prev_line = line
                line = re.sub(standalone_pattern, normalize_standalone, line)
                iterations += 1
            normalized_lines.append(line)
        text = '\n'.join(normalized_lines)
        
        # Дополнительный проход по всему тексту
        prev_text = ""
        iterations = 0
        while text != prev_text and iterations < 3:
            prev_text = text
            text = re.sub(standalone_pattern, normalize_standalone, text)
            iterations += 1
        
        # 4. Дополнительный проход для поиска формул, которые могли быть пропущены
        # Ищем формулы в любом контексте, включая середину слов (для случаев типа "CH4/LOX")
        # Более гибкий паттерн для поиска формул
        flexible_pattern = r'([A-Z][a-z]?)\s*(\d+)(?=[A-Za-z\s/\(\):,\\.;!?，。！？؛،]|$)'
        def normalize_flexible(match):
            element = match.group(1)
            digits = match.group(2)
            # Проверяем, не является ли это частью уже обработанной формулы
            full_match = match.group(0)
            # Пропускаем, если уже в Unicode формате
            if any(char in full_match for char in '₀₁₂₃₄₅₆₇₈₉'):
                return full_match
            # Пропускаем известные аббревиатуры
            if element + digits in ['RP1', 'LOX', 'MMH']:
                return full_match
            # Конвертируем в Unicode
            unicode_digits = ''.join(unicode_subscript_map.get(d, d) for d in digits)
            normalized = element + unicode_digits
            if normalized != full_match:
                nonlocal normalized_count
                normalized_count += 1
                normalized_formulas.append(f"{full_match} -> {normalized}")
            return normalized
        
        # Применяем гибкий паттерн построчно
        lines = text.split('\n')
        flexible_lines = []
        for line in lines:
            # Пропускаем строки, которые уже содержат защищенные элементы
            if '__PROTECTED_' in line:
                flexible_lines.append(line)
                continue
            processed_line = re.sub(flexible_pattern, normalize_flexible, line)
            flexible_lines.append(processed_line)
        text = '\n'.join(flexible_lines)
        
        if normalized_count > 0:
            print(f"   🔬 Нормализовано химических формул: {normalized_count}")
            for formula in normalized_formulas[:10]:
                print(f"      - {formula}")
        
        return text
    
    def _protect_formulas_and_notations(self, text: str) -> tuple[str, dict[str, str]]:
        """
        Защищает математические формулы, технические обозначения и аббревиатуры от перевода
        
        Returns:
            Кортеж (текст с плейсхолдерами, словарь плейсхолдер -> оригинальный текст)
        """
        print(f"   🔒 Защита формул: начало (длина текста: {len(text)} символов)")
        protected_items = {}
        placeholder_counter = 0
        
        def create_placeholder(original: str) -> str:
            nonlocal placeholder_counter
            placeholder = f"__PROTECTED_{placeholder_counter}__"
            protected_items[placeholder] = original
            placeholder_counter += 1
            return placeholder
        
        def protect_latex(match):
            return create_placeholder(match.group(0))
        
        # Функция для защиты химических формул с Unicode подстрочными индексами
        # Эти формулы НЕ оборачиваются в LaTeX, они остаются как обычный текст
        def protect_chemical_formula_unicode(match):
            """Защищает химическую формулу с Unicode подстрочными индексами (H₂O, CH₄)"""
            formula = match.group(0)
            # Просто защищаем формулу как есть (она уже в правильном формате с Unicode индексами)
            return create_placeholder(formula)
        
        # 1. Защищаем LaTeX формулы: \[ ... \] и \( ... \)
        # Сначала защищаем display формулы (более длинные)
        # ВАЖНО: Формулы из Mathpix уже в формате \[...\], их нужно защитить сразу
        latex_display_pattern = r'\\\[[^\]]*?\\\]'
        text = re.sub(latex_display_pattern, protect_latex, text, flags=re.DOTALL)
        
        # Затем inline формулы
        latex_inline_pattern = r'\\\([^)]*?\\\)'
        text = re.sub(latex_inline_pattern, protect_latex, text, flags=re.DOTALL)
        
        print(f"   ✅ LaTeX формулы защищены (длина текста: {len(text)})")
        
        # 1.1. Защищаем отдельные LaTeX переменные (I_{sp}, \Delta v, g_0, m_0, m_f)
        latex_vars_pattern = r'\\(?:Delta|alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|omicron|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega)\s*[_\s]*\{[^}]+\}'
        text = re.sub(latex_vars_pattern, protect_latex, text)
        
        # 1.2. Защищаем переменные с подстрочными индексами в LaTeX (I_{sp}, g_0, m_0, m_f)
        latex_subscript_pattern = r'\b(I|g|m|f|v|sp|0|Delta)[_\s]*\{[^}]+\}'
        text = re.sub(latex_subscript_pattern, protect_latex, text)
        
        # 2. Защищаем математические уравнения БОЛЕЕ АГРЕССИВНО
        # Добавляем поддержку греческих букв и индексов (μ, Δ, ν, μ_κ₁, Δν_κ₁, и т.д.)
        
        # Паттерн 1: Уравнения с = и математическими переменными (включая греческие буквы)
        # Примеры: "Δv = Isp · g0 · ln(m0/mf)", "μ_κ = e^(-Δν / I_уд)", "μ_κ₁ = μ_κ₂"
        # Ограничиваем длину для производительности: максимум 150 символов с каждой стороны от =
        math_equation_pattern1 = r'(?:Δv|Isp|g0|m0|mf|Δ|C3|ln|log|exp|sin|cos|tan|ε|Ae|At|μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|μ_κ|Δν|μ_π|γ_д|a_т|n_0|I_уд|μ_κ₁|μ_κ₂|Δν_κ₁|Δν_κ₂|m_0|m_к|v_к|μ_п|μ_пр)[^。，。！？\n]{0,150}?[=≈~]\s*[^。，。！？\n]{0,150}?(?:Δv|Isp|g0|m0|mf|Δ|C3|ln|log|exp|sin|cos|tan|ε|Ae|At|μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|μ_κ|Δν|μ_π|γ_д|a_т|n_0|I_уд|μ_κ₁|μ_κ₂|Δν_κ₁|Δν_κ₂|m_0|m_к|v_к|μ_п|μ_пр|\(|\)|/|\d+|\*|\+|\-|·|×|÷|km/s|m/s|s|°|e\^|Π|∑|√|sqrt)[^。，。！？\n]{0,150}?'
        
        # Паттерн 2: Формулы с числовыми значениями и единицами (включая греческие буквы)
        # Примеры: "Δv ≈ 9.3-9.5 km/s", "Isp = 285-300 s", "μ_κ = 0.5"
        math_equation_pattern2 = r'(?:Δv|Isp|g0|m0|mf|Δ|C3|ε|Ae|At|μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|μ_κ|Δν|μ_π|γ_д|a_т|n_0|I_уд|μ_κ₁|μ_κ₂|Δν_κ₁|Δν_κ₂|m_0|m_к|v_к|μ_п|μ_пр)[_\s]*(?:=|≈|~|<|≤|>|≥)\s*\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s*(?:km/s|m/s²|m/s|s|°|meters?|degrees?)?'
        
        # Паттерн 3: Формулы с операторами (+, -, *, /, ·, ×, ÷) и греческими буквами
        # Примеры: "Δv_total = Δv1 + Δv2 + Δv3", "μ_κ₁ = μ_κ₂ = ... = μ_κN"
        math_equation_pattern3 = r'(?:Δv|Isp|g0|m0|mf|Δ|C3|ε|Ae|At|μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|μ_κ|Δν|μ_π|γ_д|a_т|n_0|I_уд|μ_κ₁|μ_κ₂|Δν_κ₁|Δν_κ₂|m_0|m_к|v_к|μ_п|μ_пр)[_\w]*(?:=|≈|~)\s*(?:Δv|Isp|g0|m0|mf|Δ|C3|ε|Ae|At|μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|μ_κ|Δν|μ_π|γ_д|a_т|n_0|I_уд|μ_κ₁|μ_κ₂|Δν_κ₁|Δν_κ₂|m_0|m_к|v_к|μ_п|μ_пр|\d+)[_\w\s]*[+\-*/·×÷][_\w\s]*(?:Δv|Isp|g0|m0|mf|Δ|C3|ε|Ae|At|μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|μ_κ|Δν|μ_π|γ_д|a_т|n_0|I_уд|μ_κ₁|μ_κ₂|Δν_κ₁|Δν_κ₂|m_0|m_к|v_к|μ_п|μ_пр|\d+)[_\w\s]*(?:[+\-*/·×÷][_\w\s]*(?:Δv|Isp|g0|m0|mf|Δ|C3|ε|Ae|At|μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|μ_κ|Δν|μ_π|γ_д|a_т|n_0|I_уд|μ_κ₁|μ_κ₂|Δν_κ₁|Δν_κ₂|m_0|m_к|v_к|μ_п|μ_пр|\d+))?'
        
        # Паттерн 4: Формулы с греческими буквами и индексами (μ_κ₁, Δν_κ₁, μ_π_г, и т.д.)
        # Примеры: "μ_κ₁ = μ_κ₂ = ... = μ_κN", "μ_π_г = 1 - (1 - e^(-v_k/I_уд))"
        # Ограничиваем длину для производительности: максимум 150 символов
        greek_formula_pattern = r'(?:μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|Δ)[_\s]*(?:[κπγδθλσφωа-яА-Яa-zA-Z0-9₁₂₃₄₅₆₇₈₉]+[_\s]*)*[=≈~]\s*(?:[^。，。！？\n]{0,150}?)(?:μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|Δ|e\^|ln|log|exp|sin|cos|tan|Π|∑|√|sqrt|\(|\)|/|\d+|\*|\+|\-|·|×|÷)[^。，。！？\n]{0,150}?'
        
        # Паттерн 5: Формулы с произведениями и суммами (Π_{i=1}^{N}, ∑, и т.д.)
        # Примеры: "μ_п.г = Π_{i=1}^{N} μ₀(i+1)"
        # Ограничиваем длину для производительности: максимум 100 символов
        product_sum_pattern = r'(?:Π|∑|∏|∫)[_\s]*\{[^}]{0,50}\}[_\s]*\^?\{?[^}]{0,50}\}?[=≈~]\s*[^。，。！？\n]{0,100}?'
        
        # Паттерн 6: Формулы с экспонентами и степенями (e^(-v_k/I_уд), e^(-Δν/I_уд), и т.д.)
        # Примеры: "μ_κ = e^(-Δν / I_уд)", "μ_π_г = 1 - (1 - e^(-v_k/I_уд))"
        # Упрощенный паттерн для избежания катастрофического backtracking
        # Ищем e^ с последующими скобками и содержимым до 30 символов (нежадный поиск)
        exponential_pattern = r'e\^\([^)]{1,30}?\)|e\^\[[^\]]{1,30}?\]'
        
        # Паттерн 7: Формулы с дробями (v_k/I_уд, Δν/I_уд, и т.д.)
        # Примеры: "v_k/I_уд", "Δν / I_уд", "ν_κ / N"
        # Упрощенный паттерн для избежания зависания - ограничиваем длину частей дроби
        fraction_pattern = r'(?:μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|Δ|v|m|I|a|n|g)[_\s]*(?:[κπγδθλσφωа-яА-Яa-zA-Z0-9₁₂₃₄₅₆₇₈₉]{0,20}[_\s]*){0,3}\s*/\s*(?:μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|Δ|v|m|I|a|n|g|N|\d+)[_\s]*(?:[κπγδθλσφωа-яА-Яa-zA-Z0-9₁₂₃₄₅₆₇₈₉]{0,20}[_\s]*){0,3}'
        
        # Паттерн 8: Формулы с многоточием (μ_κ₁ = μ_κ₂ = ... = μ_κN, и т.д.)
        # Примеры: "μ_κ₁ = μ_κ₂ = ... = μ_κN", "Δν_κ₁ = Δν_κ₂ = ... = Δν_κN"
        # Упрощенный паттерн для избежания зависания - ограничиваем длину частей
        ellipsis_formula_pattern = r'(?:μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|Δ|v|m|I|a|n|g)[_\s]*(?:[κπγδθλσφωа-яА-Яa-zA-Z0-9₁₂₃₄₅₆₇₈₉]{0,15}[_\s]*){0,2}\s*=\s*(?:μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|Δ|v|m|I|a|n|g)[_\s]*(?:[κπγδθλσφωа-яА-Яa-zA-Z0-9₁₂₃₄₅₆₇₈₉]{0,15}[_\s]*){0,2}\s*=\s*\.\.\.\s*=\s*(?:μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|Δ|v|m|I|a|n|g)[_\s]*(?:[κπγδθλσφωа-яА-Яa-zA-Z0-9₁₂₃₄₅₆₇₈₉]{0,15}[_\s]*){0,2}'
        
        # Паттерн 9: Формулы с скобками и сложными выражениями
        # Примеры: "1 - (1 - e^(-v_k/I_уд)) (1 + a_т.о)", "[1 - (1 - e^(-v_k/(2I_уд))) (1 + a_т.о)]^2"
        # Ограничиваем длину для производительности: максимум 150 символов
        complex_formula_pattern = r'(?:1\s*[-–]\s*)?\([^\)]{0,100}\)\s*(?:[=≈~]|[-–+*/·×÷]|\^|\*)\s*[^。，。！？\n]{0,150}?'
        
        # Паттерн 10: Формулы с уравнениями (13.1), (13.2) и т.д. в конце
        # Примеры: "μ_π_г = 1 - (1 - e^(-v_k/I_уд)) (1 + a_т.о) - γ_д_в_n_0_g_0. (13.1)"
        # Включаем поддержку русских букв в формулах (v_к, I_уд, μ_п.г)
        # Ограничиваем длину для производительности: максимум 200 символов
        numbered_formula_pattern = r'(?:[μνκπγαβδθλσφωΔmvIaа-яА-Я]|Isp|g0|m0|mf|Δv|C3|ln|log|exp|sin|cos|tan|ε|Ae|At)[^。，。！？\n]{0,200}?\(13\.\d+\)'
        
        # Паттерн 11: Формулы с многострочными выражениями (с переносами строк)
        # Примеры: формулы с несколькими строками
        multiline_formula_pattern = r'(?:[μνκπγαβδθλσφωΔmvIa]|Isp|g0|m0|mf|Δv)[^。，。！？]{0,200}?[=≈~]\s*[^。，。！？]{0,200}?\n\s*[^。，。！？]{0,200}?[=≈~]?\s*[^。，。！？]{0,200}?'
        
        # Определяем карту для конвертации Unicode подстрочных индексов в LaTeX
        # Должно быть определено ПЕРЕД использованием в protect_math_equation
        subscript_map = {
            '₂': '_2', '₃': '_3', '₄': '_4', '₅': '_5', '₆': '_6',
            '₇': '_7', '₈': '_8', '₉': '_9', '₀': '_0', '₁': '_1'
        }
        
        def protect_math_equation(match):
            eq = match.group(0).strip()
            # Быстрая проверка: пропускаем слишком короткие или слишком длинные строки
            if len(eq) <= 3 or len(eq) > 300:  # Уменьшили максимум с 500 до 300
                return match.group(0)
            
            # Быстрая проверка: если уже защищено, пропускаем
            if '__PROTECTED_' in eq:
                return match.group(0)
            
            # Оптимизированные проверки: используем более быстрые методы
            # Комбинируем несколько проверок в одну для скорости
            # Включаем поддержку русских букв в формулах (v_к, I_уд, μ_п.г и т.д.)
            has_math_elements = (
                '=' in eq or '≈' in eq or '~' in eq or  # Операторы равенства
                any(c in eq for c in 'μνκπγαβδθλσφωΔ') or  # Греческие буквы
                any(c in eq for c in '₁₂₃₄₅₆₇₈₉') or  # Unicode индексы
                '_' in eq or  # Подстрочные индексы
                any(op in eq for op in '+-*/·×÷') or  # Математические операторы
                # Проверка на русские буквы в контексте формул (v_к, I_уд, μ_п.г)
                (re.search(r'[а-яА-Я]', eq) and ('_' in eq or '=' in eq or any(op in eq for op in '+-*/·×÷')))
            )
            
            if not has_math_elements:
                return match.group(0)
            
            # Более детальная проверка только если первая прошла
            has_operators = bool(re.search(r'[+\-*/·×÷=≈~<>≤≥]', eq))
            has_numbers = bool(re.search(r'\d+', eq))
            
            # Это формула, если содержит операторы или числа
            # Также проверяем наличие русских букв в контексте формул
            has_russian_in_formula = bool(re.search(r'[а-яА-Я]', eq)) and ('_' in eq or '=' in eq)
            
            if has_operators or has_numbers or has_russian_in_formula:
                # Конвертируем формулу в LaTeX формат для правильного рендеринга
                # Заменяем Unicode индексы на LaTeX индексы
                eq_latex = eq
                for unicode_sub, latex_sub in subscript_map.items():
                    eq_latex = eq_latex.replace(unicode_sub, latex_sub)
                
                # Обрабатываем русские буквы в индексах: v_к -> v_{к}, I_уд -> I_{уд}
                # Находим паттерны типа: буква_русская_буква или буква_русская_буква.русская_буква
                eq_latex = re.sub(r'([a-zA-ZμνκπγαβδθλσφωΔ])_([а-яА-Я]+)(?=[\s=+\-*/·×÷\)\]\.,;!?]|$)', r'\1_{\2}', eq_latex)
                # Обрабатываем множественные индексы: μ_п.г -> μ_{п.г}
                eq_latex = re.sub(r'([a-zA-ZμνκπγαβδθλσφωΔ])_([а-яА-Я]+)\.([а-яА-Я]+)', r'\1_{\2.\3}', eq_latex)
                
                # Оборачиваем в LaTeX окружение
                eq_latex = f"\\[{eq_latex}\\]"
                return create_placeholder(eq_latex)
            return match.group(0)
        
        # Применяем все паттерны для уравнений
        # Пропускаем уже защищенные элементы для производительности
        # Также пропускаем, если в тексте много защищенных формул (из Mathpix) - они уже обработаны
        protected_count = text.count('__PROTECTED_')
        
        # Если много защищенных формул и текст большой, значит формулы уже из Mathpix
        # Пропускаем агрессивные паттерны для больших текстов с формулами из изображений
        if protected_count > 5 and len(text) > 5000:
            print(f"   ⏭️  Пропускаем паттерны 1-5 (найдено {protected_count} защищенных формул, текст большой)")
            print(f"   💡 Формулы из изображений уже обработаны через Mathpix, не требуется дополнительная обработка")
        elif '__PROTECTED_' not in text or protected_count < len(text) / 10:
            print(f"   🔒 Применяем паттерны для защиты формул...")
            initial_text_length = len(text)
            print(f"   📏 Начальная длина текста: {initial_text_length} символов")
            
            text = re.sub(math_equation_pattern1, protect_math_equation, text)
            print(f"   ✅ Паттерн 1 применен (длина: {len(text)})")
            
            text = re.sub(math_equation_pattern2, protect_math_equation, text)
            print(f"   ✅ Паттерн 2 применен (длина: {len(text)})")
            
            text = re.sub(math_equation_pattern3, protect_math_equation, text)
            print(f"   ✅ Паттерн 3 применен (длина: {len(text)})")
            
            text = re.sub(greek_formula_pattern, protect_math_equation, text)
            print(f"   ✅ Паттерн 4 (греческие) применен (длина: {len(text)})")
            
            text = re.sub(product_sum_pattern, protect_math_equation, text)
            print(f"   ✅ Паттерн 5 применен (длина: {len(text)})")
            # Паттерн 6 может быть медленным, для больших текстов пропускаем его полностью
            # Экспоненты будут обработаны другими паттернами (например, паттерн 1 или 4)
            # ВАЖНО: Полностью отключаем паттерн 6 для текстов больше 5000 символов
            if initial_text_length > 5000:
                print(f"   ⏭️  Паттерн 6 пропущен (текст слишком большой: {initial_text_length} символов)")
            else:
                print(f"   🔒 Применяем паттерн 6 (экспоненты)... (длина текста: {len(text)})")
                try:
                    text = re.sub(exponential_pattern, protect_math_equation, text)
                    print(f"   ✅ Паттерн 6 применен успешно")
                except Exception as e:
                    print(f"   ⚠️  Ошибка при применении паттерна 6: {e}, пропускаем")
            print(f"   ✅ Паттерн 6 обработан (длина текста: {len(text)})")
            # Паттерн 7 может быть медленным для больших текстов
            if initial_text_length > 10000:
                print(f"   ⏭️  Паттерн 7 пропущен (текст слишком большой: {initial_text_length} символов)")
            else:
                print(f"   🔒 Применяем паттерн 7 (дроби)...")
                try:
                    text = re.sub(fraction_pattern, protect_math_equation, text)
                except Exception as e:
                    print(f"   ⚠️  Ошибка при применении паттерна 7: {e}, пропускаем")
            print(f"   ✅ Паттерн 7 применен (длина: {len(text)})")
            
            # Паттерны 8-11 могут быть медленными для больших текстов
            if initial_text_length > 10000:
                print(f"   ⏭️  Паттерны 8-11 пропущены (текст слишком большой: {initial_text_length} символов)")
            else:
                print(f"   🔒 Применяем паттерн 8 (многоточие)...")
                try:
                    text = re.sub(ellipsis_formula_pattern, protect_math_equation, text)
                    print(f"   ✅ Паттерн 8 применен")
                except Exception as e:
                    print(f"   ⚠️  Ошибка при применении паттерна 8: {e}, пропускаем")
                
                print(f"   🔒 Применяем паттерн 9 (сложные формулы)...")
                try:
                    text = re.sub(complex_formula_pattern, protect_math_equation, text)
                    print(f"   ✅ Паттерн 9 применен")
                except Exception as e:
                    print(f"   ⚠️  Ошибка при применении паттерна 9: {e}, пропускаем")
                
                print(f"   🔒 Применяем паттерн 10 (нумерованные формулы)...")
                try:
                    text = re.sub(numbered_formula_pattern, protect_math_equation, text)
                    print(f"   ✅ Паттерн 10 применен")
                except Exception as e:
                    print(f"   ⚠️  Ошибка при применении паттерна 10: {e}, пропускаем")
                
                # Паттерн 11: Специальный паттерн для русских формул с индексами
                # Примеры: "v_к = ...", "I_уд = ...", "μ_п.г = ...", "a_т.о = ..."
                print(f"   🔒 Применяем паттерн 11 (русские формулы с индексами)...")
                russian_formula_pattern = r'(?:[mvIaμνκπγαβδθλσφωΔ]|Isp|g0|m0|mf|Δv)[_\s]*(?:[а-яА-Я]+[_\s\.]*)+[=≈~]\s*[^。，。！？\n]{0,150}?'
                try:
                    text = re.sub(russian_formula_pattern, protect_math_equation, text)
                    print(f"   ✅ Паттерн 11 применен")
                except Exception as e:
                    print(f"   ⚠️  Ошибка при применении паттерна 11: {e}, пропускаем")
        # Многострочные формулы обрабатываем отдельно (только если текст не слишком большой)
        # Ограничиваем обработку для производительности: пропускаем если текст очень длинный
        print(f"   🔒 Обработка многострочных формул... (длина текста: {len(text)})")
        if len(text) < 50000:  # Обрабатываем многострочные формулы только для небольших текстов
            lines = text.split('\n')
            processed_lines = []
            for i, line in enumerate(lines):
                # Пропускаем уже защищенные строки
                if '__PROTECTED_' in line:
                    processed_lines.append(line)
                    continue
                # Проверяем, является ли строка частью многострочной формулы
                if i > 0 and i < len(lines) - 1:
                    prev_line = lines[i-1].strip()
                    next_line = lines[i+1].strip()
                    # Если предыдущая и следующая строки похожи на формулы, текущая строка тоже может быть частью формулы
                    if (re.search(r'[=≈~]', prev_line) and re.search(r'[μνκπγαβδθλσφωΔ]', prev_line) and
                        re.search(r'[=≈~]', next_line) and re.search(r'[μνκπγαβδθλσφωΔ]', next_line)):
                        # Текущая строка - часть многострочной формулы
                        processed_line = re.sub(multiline_formula_pattern, protect_math_equation, line)
                        processed_lines.append(processed_line)
                    else:
                        processed_lines.append(line)
                else:
                    processed_lines.append(line)
            text = '\n'.join(processed_lines)
            print(f"   ✅ Многострочные формулы обработаны")
        
        # 3. Защищаем технические аббревиатуры (должны быть в верхнем регистре)
        abbreviations = [
            r'\bLEO\b', r'\bGTO\b', r'\bTLI\b', r'\bTMI\b', r'\bGSO\b',
            r'\bIMU\b', r'\bRCS\b', r'\bLRE\b', r'\bOKPA\b', r'\bS2\b', r'\bS3\b'
        ]
        for abbr_pattern in abbreviations:
            text = re.sub(abbr_pattern, protect_latex, text)
        
        # Функция для защиты химических формул с Unicode подстрочными индексами
        # Эти формулы НЕ оборачиваются в LaTeX, они остаются как обычный текст
        def protect_chemical_formula_unicode(match):
            """Защищает химическую формулу с Unicode подстрочными индексами (H₂O, CH₄)"""
            formula = match.group(0)
            # Просто защищаем формулу как есть (она уже в правильном формате с Unicode индексами)
            return create_placeholder(formula)
        
        # Функция для конвертации химических формул в LaTeX с подстрочными индексами
        # Используется только для сложных формул, которые нужно рендерить как изображения
        def convert_chemical_to_latex(match):
            """Конвертирует химическую формулу с обычными цифрами в LaTeX с подстрочными индексами"""
            formula = match.group(0)
            # Конвертируем Unicode подстрочные индексы в LaTeX (если есть)
            for unicode_sub, latex_sub in subscript_map.items():
                formula = formula.replace(unicode_sub, latex_sub)
            
            # Конвертируем обычные цифры после букв в подстрочные индексы
            # Паттерн: буква(ы) + цифра(ы) -> буква(ы) + _{цифра(ы)}
            # Примеры: CH4 -> CH_{4}, LH2 -> LH_{2}, N2O4 -> N_{2}O_{4}
            def replace_digits_with_subscript(text):
                # Ищем паттерны типа: буква + цифра (например, CH4, LH2, N2O4)
                # Но не трогаем уже обработанные формулы с _
                if '_' in text and '{' in text:
                    return text  # Уже в LaTeX формате
                
                # Конвертируем: буква(ы) + цифра(ы) -> буква(ы) + _{цифра(ы)}
                # Используем более точный паттерн для химических формул
                pattern = r'([A-Z][a-z]?)(\d+)'
                def replacer(m):
                    element = m.group(1)  # Элемент (C, H, N, O, и т.д.)
                    number = m.group(2)   # Цифра(ы)
                    return f"{element}_{{{number}}}"  # LaTeX формат с фигурными скобками
                
                result = re.sub(pattern, replacer, text)
                return result
            
            formula = replace_digits_with_subscript(formula)
            # Если формула содержит подстрочные индексы (_{), оборачиваем в LaTeX окружение для правильного рендеринга
            if '_{' in formula:
                formula = f"\\[{formula}\\]"
            return create_placeholder(formula)
        
        # 4. Защищаем комбинации топлива
        # Формулы уже нормализованы с Unicode подстрочными индексами (CH₄/LOX, LH₂/LOX)
        # Защищаем их как обычный текст, не оборачивая в LaTeX
        found_fuels = []
        
        # Паттерн для формул с Unicode подстрочными индексами (CH₄/LOX, LH₂/LOX)
        unicode_fuel_pattern = r'([A-Z][A-Z]?[₀₁₂₃₄₅₆₇₈₉]+)/LOX(?=\s|$|\(|:)'
        def replace_unicode_fuel(match):
            full_match = match.group(0)
            if '__PROTECTED_' in full_match:
                return full_match
            found_fuels.append(full_match)
            # Защищаем как обычный текст (не LaTeX)
            return protect_chemical_formula_unicode(match)
        
        # Паттерн для формул без подстрочных индексов (CH4/LOX, LH2/LOX) - если они не были нормализованы
        plain_fuel_pattern = r'([A-Z][A-Z]?\s*\d+)/LOX(?=\s|$|\(|:)'
        def replace_plain_fuel(match):
            full_match = match.group(0)
            if '__PROTECTED_' in full_match:
                return full_match
            formula_part = match.group(1).replace(' ', '')
            if formula_part in ['RP', 'LOX', 'MMH'] or formula_part.isdigit():
                return full_match
            if full_match.startswith('RP') and '1' in full_match:
                return full_match
            full_formula = f"{formula_part}/LOX"
            found_fuels.append(full_formula)
            # Конвертируем в LaTeX только если это не простая формула
            class Match:
                def __init__(self, text):
                    self._text = text
                def group(self, n):
                    return self._text if n == 0 else None
            temp_match = Match(full_formula)
            return convert_chemical_to_latex(temp_match)
        
        # Сначала применяем паттерн для формул с Unicode индексами
        text = re.sub(unicode_fuel_pattern, replace_unicode_fuel, text)
        # Затем применяем паттерн для формул без индексов
        text = re.sub(plain_fuel_pattern, replace_plain_fuel, text)
        
        # Отладочный вывод
        if found_fuels:
            print(f"   🔍 Найдено формул общим паттерном: {len(found_fuels)}")
            for fuel in found_fuels[:5]:
                print(f"      - {fuel}")
        
        # Затем применяем специфичные паттерны для RP-1/LOX и других вариантов
        fuel_patterns = [
            r'RP-1/LOX(?=\s|$|\(|:)',
            r'RP-1/LOX\s*\([^)]+\)(?=\s|$|:)',  # С контекстом типа "(sea level)"
            # Остальные паттерны для уже обработанных формул (если они не были найдены общим паттерном)
            r'LH₂/LOX(?=\s|$|\(|:)',  # С подстрочным индексом Unicode
            r'LH_2/LOX(?=\s|$|\(|:)',  # LaTeX формат
            r'CH₄/LOX(?=\s|$|\(|:)',  # С подстрочным индексом Unicode
            r'CH_4/LOX(?=\s|$|\(|:)',  # LaTeX формат
            r'LH₂/LOX\s*\([^)]+\)(?=\s|$|:)',
            r'LH_2/LOX\s*\([^)]+\)(?=\s|$|:)',
            r'CH₄/LOX\s*\([^)]+\)(?=\s|$|:)',
            r'CH_4/LOX\s*\([^)]+\)(?=\s|$|:)'
        ]
        for fuel_pattern in fuel_patterns:
            # Используем convert_chemical_to_latex для конвертации цифр в подстрочные индексы
            # Создаем временный match объект для convert_chemical_to_latex
            class Match:
                def __init__(self, text):
                    self._text = text
                def group(self, n):
                    return self._text if n == 0 else None
            
            def replace_fuel(match):
                formula = match.group(0)
                # Убираем пробелы из формулы
                formula = formula.replace(' ', '')
                temp_match = Match(formula)
                return convert_chemical_to_latex(temp_match)
            
            text = re.sub(fuel_pattern, replace_fuel, text)
        
        # 4.1. Защищаем отдельные химические формулы с Unicode подстрочными индексами
        # Эти формулы остаются как обычный текст, не оборачиваются в LaTeX
        # Сначала защищаем формулы с Unicode индексами (они уже нормализованы)
        # Улучшенный паттерн для поиска формул с Unicode индексами
        unicode_formula_pattern = r'(?<![A-Za-z0-9₀₁₂₃₄₅₆₇₈₉])([A-Z][a-z]?[₀₁₂₃₄₅₆₇₈₉]+[A-Za-z₀₁₂₃₄₅₆₇₈₉]*)(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)'
        def protect_any_unicode_formula(match):
            formula = match.group(1)
            # Пропускаем, если это уже защищено
            if '__PROTECTED_' in formula:
                return formula
            # Пропускаем известные аббревиатуры
            if formula in ['LOX', 'MMH', 'IMU', 'RCS', 'GTO', 'TLI', 'TMI', 'LEO', 'GSO']:
                return formula
            # Защищаем как обычный текст (Unicode, не LaTeX)
            return protect_chemical_formula_unicode(match)
        
        text = re.sub(unicode_formula_pattern, protect_any_unicode_formula, text)
        
        # 4.1.0. Защищаем простые химические формулы БЕЗ индексов (CH4, H2O, N2O4)
        # Конвертируем их в Unicode формат (CH₄, H₂O, N₂O₄) и защищаем
        # Это нужно делать ПОСЛЕ защиты формул с Unicode, но ДО конвертации в LaTeX
        simple_chemical_pattern = r'(?<![A-Za-z0-9])([A-Z][a-z]?\d+(?:[A-Z][a-z]?\d+)*)(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)'
        def protect_simple_chemical(match):
            formula = match.group(1)
            # Пропускаем, если это уже защищено
            if '__PROTECTED_' in formula:
                return formula
            # Пропускаем известные аббревиатуры
            if formula in ['RP1', 'LOX', 'MMH', 'IMU', 'RCS', 'GTO', 'TLI', 'TMI', 'LEO', 'GSO']:
                return formula
            # Пропускаем, если это число
            if formula.isdigit():
                return formula
            # Пропускаем, если уже в Unicode формате
            if any(char in formula for char in '₀₁₂₃₄₅₆₇₈₉'):
                return formula
            # Пропускаем, если уже в LaTeX формате
            if '_{' in formula or '\\[' in formula:
                return formula
            # Проверяем, является ли это простой химической формулой (максимум 10 символов)
            if len(formula) <= 10 and re.match(r'^[A-Z][a-z]?\d+([A-Z][a-z]?\d+)*$', formula):
                # Конвертируем в Unicode формат
                unicode_subscript_map = {
                    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
                    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'
                }
                def replace_digit(m):
                    element = m.group(1)
                    digits = m.group(2)
                    unicode_digits = ''.join(unicode_subscript_map.get(d, d) for d in digits)
                    return element + unicode_digits
                normalized = re.sub(r'([A-Z][a-z]?)(\d+)', replace_digit, formula)
                # Защищаем как Unicode формулу (не LaTeX)
                class Match:
                    def __init__(self, text):
                        self._text = text
                    def group(self, n):
                        return self._text if n == 0 else None
                temp_match = Match(normalized)
                return protect_chemical_formula_unicode(temp_match)
            return formula
        
        text = re.sub(simple_chemical_pattern, protect_simple_chemical, text)
        
        # 4.1.1. Защищаем химические формулы с LaTeX подстрочными индексами (для сложных случаев)
        # subscript_map уже определен выше
        
        def convert_subscript_to_latex(match):
            formula = match.group(0)
            # Конвертируем Unicode подстрочные индексы в LaTeX
            for unicode_sub, latex_sub in subscript_map.items():
                formula = formula.replace(unicode_sub, latex_sub)
            return create_placeholder(formula)
        
        def convert_chemical_formula_to_latex(match):
            """Конвертирует химическую формулу с обычными цифрами в LaTeX с подстрочными индексами"""
            formula = match.group(0)
            # Конвертируем Unicode подстрочные индексы в LaTeX (если есть)
            for unicode_sub, latex_sub in subscript_map.items():
                formula = formula.replace(unicode_sub, latex_sub)
            
            # Конвертируем обычные цифры после букв в подстрочные индексы
            # Паттерн: буква(ы) + цифра(ы) -> буква(ы) + _цифра(ы)
            # Примеры: CH4 -> CH_4, LH2 -> LH_2, N2O4 -> N_2O_4
            def replace_digits_with_subscript(text):
                # Ищем паттерны типа: буква + цифра (например, CH4, LH2, N2O4)
                # Но не трогаем уже обработанные формулы с _ и фигурными скобками
                if '_' in text and '{' in text:
                    return text  # Уже в LaTeX формате
                
                # Конвертируем: буква(ы) + цифра(ы) -> буква(ы) + _цифра(ы)
                # Используем более точный паттерн для химических формул
                pattern = r'([A-Z][a-z]?)(\d+)'
                def replacer(m):
                    element = m.group(1)  # Элемент (C, H, N, O, и т.д.)
                    number = m.group(2)   # Цифра(ы)
                    return f"{element}_{{{number}}}"  # LaTeX формат с фигурными скобками
                
                result = re.sub(pattern, replacer, text)
                return result
            
            formula = replace_digits_with_subscript(formula)
            # Если формула содержит подстрочные индексы (_{), оборачиваем в LaTeX окружение для правильного рендеринга
            if '_{' in formula:
                formula = f"\\[{formula}\\]"
            return create_placeholder(formula)
        
        # Защищаем химические формулы (включая конвертацию цифр в подстрочные индексы)
        # ВАЖНО: Простые формулы (CH4, H2O) должны оставаться в Unicode, а не конвертироваться в LaTeX
        # LaTeX используется только для сложных математических формул
        
        # Список простых химических формул, которые должны оставаться в Unicode
        simple_chemical_formulas_unicode = [
            r'(?<![A-Za-z0-9])LH₂(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)',
            r'(?<![A-Za-z0-9])CH₄(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)',
            r'(?<![A-Za-z0-9])H₂O(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)',
            r'(?<![A-Za-z0-9])N₂O₄(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)',
        ]
        # Защищаем простые формулы как Unicode (не LaTeX)
        for formula_pattern in simple_chemical_formulas_unicode:
            text = re.sub(formula_pattern, protect_chemical_formula_unicode, text)
        
        # Список формул, которые могут быть в LaTeX формате (если они уже в LaTeX)
        latex_chemical_formulas = [
            r'(?<![A-Za-z0-9])LH_2(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)',
            r'(?<![A-Za-z0-9])CH_4(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)',
            r'(?<![A-Za-z0-9])H_2O(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)',
            r'(?<![A-Za-z0-9])N_2O_4(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)',
        ]
        # Защищаем LaTeX формулы
        for formula_pattern in latex_chemical_formulas:
            text = re.sub(formula_pattern, protect_latex, text)
        
        # Формулы без индексов (CH4, H2O, LH2, N2O4) - конвертируем в Unicode и защищаем
        plain_chemical_formulas = [
            r'(?<![A-Za-z0-9])LH2(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)',
            r'(?<![A-Za-z0-9])CH4(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)',
            r'(?<![A-Za-z0-9])H2O(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)',
            r'(?<![A-Za-z0-9])N2O4(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،)',
        ]
        def convert_to_unicode_and_protect(match):
            formula = match.group(0)
            # Конвертируем в Unicode
            unicode_subscript_map = {
                '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
                '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'
            }
            def replace_digit(m):
                element = m.group(1)
                digits = m.group(2)
                unicode_digits = ''.join(unicode_subscript_map.get(d, d) for d in digits)
                return element + unicode_digits
            normalized = re.sub(r'([A-Z][a-z]?)(\d+)', replace_digit, formula)
            # Защищаем как Unicode формулу
            class Match:
                def __init__(self, text):
                    self._text = text
                def group(self, n):
                    return self._text if n == 0 else None
            temp_match = Match(normalized)
            return protect_chemical_formula_unicode(temp_match)
        
        for formula_pattern in plain_chemical_formulas:
            text = re.sub(formula_pattern, convert_to_unicode_and_protect, text)
        
        # 4.2. Дополнительно обрабатываем химические формулы в любом контексте
        # Ищем паттерны типа: буква(ы) + цифра(ы), которые могут быть пропущены
        # ВАЖНО: Простые формулы конвертируем в Unicode, а не в LaTeX
        # LaTeX используется только для сложных математических формул
        
        def process_standalone_chemical(match):
            formula = match.group(0)
            # Пропускаем уже обработанные формулы (содержат плейсхолдеры или уже в LaTeX/Unicode)
            if '__PROTECTED_' in formula or ('_' in formula and '{' in formula):
                return formula
            # Пропускаем, если уже в Unicode формате
            if any(char in formula for char in '₀₁₂₃₄₅₆₇₈₉'):
                return formula
            # Пропускаем исключения (не химические формулы)
            if formula in ['RP-1', 'LOX', 'MMH', 'IMU', 'RCS', 'GTO', 'TLI', 'TMI', 'LEO', 'GSO']:
                return formula
            # Пропускаем если это число (например, "285", "300")
            if formula.isdigit():
                return formula
            # Проверяем, является ли это простой химической формулой (максимум 10 символов)
            if len(formula) <= 10 and re.match(r'^[A-Z][a-z]?\d+([A-Z][a-z]?\d+)*$', formula):
                # Конвертируем в Unicode формат (не LaTeX для простых формул)
                unicode_subscript_map = {
                    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
                    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'
                }
                def replace_digit(m):
                    element = m.group(1)
                    digits = m.group(2)
                    unicode_digits = ''.join(unicode_subscript_map.get(d, d) for d in digits)
                    return element + unicode_digits
                converted = re.sub(r'([A-Z][a-z]?)(\d+)', replace_digit, formula)
                # Защищаем как Unicode формулу (не LaTeX)
                class Match:
                    def __init__(self, text):
                        self._text = text
                    def group(self, n):
                        return self._text if n == 0 else None
                temp_match = Match(converted)
                return protect_chemical_formula_unicode(temp_match)
            # Для сложных формул (длиннее 10 символов или содержат математические операторы)
            # используем LaTeX только если это действительно математическая формула
            elif len(formula) > 10 or any(op in formula for op in ['=', '+', '-', '*', '/', '(', ')']):
                # Это сложная формула, конвертируем в LaTeX
                converted = re.sub(r'([A-Z][a-z]?)(\d+)', r'\1_{\2}', formula)
                if '_{' in converted:
                    converted = f"\\[{converted}\\]"
                return create_placeholder(converted)
            return formula
        
        # Ищем химические формулы: буква(ы) + цифра(ы) в любом контексте
        # Улучшенный паттерн для поиска формул на разных языках
        # Более агрессивный поиск - ищем формулы в любом месте текста
        standalone_chemical_pattern = r'(?<![A-Za-z0-9₀₁₂₃₄₅₆₇₈₉])([A-Z][a-z]?\d+(?:[A-Z][a-z]?\d+)*)(?=\s|$|/|\(|:|\s*\(|,|\.|\)|;|!|\?|，|。|！|？|؛|،|\s|$)'
        def replace_standalone_chemical(match):
            formula = match.group(1)
            # Пропускаем уже обработанные формулы
            if '__PROTECTED_' in formula or ('_' in formula and '{' in formula):
                return formula
            # Пропускаем, если уже в Unicode формате
            if any(char in formula for char in '₀₁₂₃₄₅₆₇₈₉'):
                return formula
            # Пропускаем исключения
            if formula in ['RP-1', 'LOX', 'MMH', 'IMU', 'RCS', 'GTO', 'TLI', 'TMI', 'LEO', 'GSO']:
                return formula
            # Пропускаем если это число
            if formula.isdigit():
                return formula
            # Обрабатываем формулу
            class Match:
                def __init__(self, text):
                    self._text = text
                def group(self, n):
                    return self._text if n == 0 else None
            temp_match = Match(formula)
            converted = process_standalone_chemical(temp_match)
            return converted
        
        # Применяем поиск формул построчно для лучшего покрытия
        lines = text.split('\n')
        processed_lines = []
        for line in lines:
            processed_line = re.sub(standalone_chemical_pattern, replace_standalone_chemical, line)
            processed_lines.append(processed_line)
        text = '\n'.join(processed_lines)
        
        # Дополнительный проход по всему тексту
        text = re.sub(standalone_chemical_pattern, replace_standalone_chemical, text)
        
        # 5. Защищаем числовые значения с единицами измерения
        # Паттерн: число(ы) + единица измерения (km/s, s, m/s², и т.д.)
        units_pattern = r'\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s*(?:km/s|m/s²|m/s|s|°|meters?|degrees?)'
        text = re.sub(units_pattern, protect_latex, text)
        
        # 6. Защищаем технические переменные (Isp, g0, m0, mf, Δv, C3) и переменные с греческими буквами
        # Защищаем всегда, так как это технические обозначения
        variable_pattern = r'\b(Isp|g0|m0|mf|Δv|C3|ε|Ae|At|I_уд|μ_κ|Δν|μ_π|γ_д|a_т|n_0|μ_κ₁|μ_κ₂|Δν_κ₁|Δν_κ₂|m_0|m_к|v_к|μ_п|μ_пр|μ_π_г|μ_п\.г)\b'
        text = re.sub(variable_pattern, protect_latex, text)
        
        # 6.1. Защищаем переменные с индексами (μ_κ₁, Δν_κ₁, μ_π_г, и т.д.)
        # Паттерн для переменных с подстрочными индексами (Unicode и обычные)
        # Более точный паттерн: греческая буква + подстрочный индекс(ы)
        subscript_variable_patterns = [
            # Паттерн 1: μ_κ₁, μ_κ₂, Δν_κ₁ (с Unicode индексами)
            r'(?:μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|Δ)[_\s]*(?:[κπγδθλσφωа-яА-Яa-zA-Z]+)[_\s]*[₁₂₃₄₅₆₇₈₉]+',
            # Паттерн 2: μ_κ₁, μ_κ₂ (с обычными индексами после Unicode)
            r'(?:μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|Δ)[_\s]*(?:[κπγδθλσφωа-яА-Яa-zA-Z]+)[_\s]*\d+',
            # Паттерн 3: μ_π_г, γ_д_в, μ_п.г (множественные индексы, включая точки)
            r'(?:μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|Δ)[_\s]*(?:[κπγδθλσφωа-яА-Яa-zA-Z]+)[_\s]*(?:[_\s\.]*[κπγδθλσφωа-яА-Яa-zA-Z]+)+',
            # Паттерн 4: m_0, v_к, I_уд (латинские буквы с индексами)
            r'\b[mvIa]g?[_\s]*(?:[κπγδθλσφωа-яА-Яa-zA-Z0-9₁₂₃₄₅₆₇₈₉]+)',
            # Паттерн 5: μ_п.г, a_т.о (с точками в индексах)
            r'(?:μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|Δ|a|n|g)[_\s]*(?:[κπγδθλσφωа-яА-Яa-zA-Z]+)\.(?:[κπγδθλσφωа-яА-Яa-zA-Z]+)',
        ]
        
        def protect_subscript_variable(match):
            var = match.group(0)
            # Проверяем, что это действительно переменная в формуле (не обычный текст)
            # Должна быть рядом с операторами, цифрами или в начале/конце строки
            if len(var) <= 30:  # Переменные обычно короткие (увеличено до 30 для длинных индексов)
                # Конвертируем Unicode индексы в LaTeX формат для правильного рендеринга
                var_latex = var
                for unicode_sub, latex_sub in subscript_map.items():
                    var_latex = var_latex.replace(unicode_sub, latex_sub)
                # Конвертируем точки в индексах в подстрочные индексы LaTeX
                # Например: μ_п.г -> μ_{п.г} или μ_{пг}
                if '.' in var_latex and '_' in var_latex:
                    # Заменяем точки в индексах на подстрочные индексы
                    var_latex = re.sub(r'_([^_]+)\.([^_\s]+)', r'_{\1.\2}', var_latex)
                # Если есть индексы, оборачиваем в LaTeX
                if '_' in var_latex or '{' in var_latex:
                    var_latex = f"\\[{var_latex}\\]"
                return create_placeholder(var_latex)
            return var
        
        # Применяем паттерны для переменных с индексами
        for pattern in subscript_variable_patterns:
            text = re.sub(pattern, protect_subscript_variable, text)
        
        # Логируем статистику
        if protected_items:
            print(f"   📐 Защищено элементов: {len(protected_items)}")
            # Показываем примеры защищенных формул
            formula_examples = [v for v in list(protected_items.values())[:3] if any(c in v for c in ['=', 'Δ', 'Isp', 'g0'])]
            if formula_examples:
                print(f"   📋 Примеры формул: {len(formula_examples)}")
                for i, example in enumerate(formula_examples[:2], 1):
                    print(f"      {i}. {example[:60]}...")
            # Показываем примеры защищенных формул топлива
            fuel_examples = [v for v in protected_items.values() if '/LOX' in v or ('_{' in v and ('CH' in v or 'LH' in v))]
            if fuel_examples:
                print(f"   ⛽ Защищено формул топлива: {len(fuel_examples)}")
                for i, example in enumerate(fuel_examples[:3], 1):
                    print(f"      {i}. {example[:60]}...")
        
        return text, protected_items
    
    def _restore_formulas_and_notations(self, text: str, protected_items: dict[str, str]) -> str:
        """
        Восстанавливает защищенные формулы и обозначения после перевода
        
        Args:
            text: Переведенный текст с плейсхолдерами
            protected_items: Словарь плейсхолдер -> оригинальный текст
        
        Returns:
            Текст с восстановленными формулами и обозначениями
        """
        if not protected_items:
            return text
        
        # Восстанавливаем в обратном порядке (от больших номеров к меньшим)
        # чтобы избежать конфликтов при замене (например, __PROTECTED_10__ не должен конфликтовать с __PROTECTED_1__)
        sorted_items = sorted(
            protected_items.items(),
            key=lambda x: int(x[0].split('_')[1]) if len(x[0].split('_')) > 1 and x[0].split('_')[1].isdigit() else 0,
            reverse=True
        )
        
        restored_count = 0
        lost_placeholders = []
        for placeholder, original in sorted_items:
            if placeholder in text:
                text = text.replace(placeholder, original)
                restored_count += 1
            else:
                lost_placeholders.append((placeholder, original))
        
        if restored_count < len(protected_items):
            missing = len(protected_items) - restored_count
            print(f"   ⚠️  Не восстановлено элементов: {missing}/{len(protected_items)}")
            # Показываем примеры потерянных элементов
            if lost_placeholders:
                for placeholder, original in lost_placeholders[:3]:
                    # Проверяем, является ли это формулой топлива
                    if '/LOX' in original or '_{' in original:
                        print(f"      ❌ {placeholder} -> '{original[:50]}...' (формула топлива)")
        else:
            print(f"   ✅ Восстановлено элементов: {restored_count}/{len(protected_items)}")
        
        # Нормализуем химические формулы после восстановления
        # Это нужно, чтобы нормализовать формулы, которые могли быть изменены LLM
        # или добавлены в процессе перевода (например, "CH4/LOX" -> "CH₄/LOX")
        text = self._normalize_chemical_formulas(text)
        
        return text
    
    async def extract_text_from_file(
        self, 
        file_path: str, 
        source_lang: Optional[Literal["ru", "ar", "zh"]] = None
    ) -> str:
        """
        Извлекает текст из различных типов файлов (PDF, DOCX, DOC, TXT)
        
        Args:
            file_path: Путь к файлу
            source_lang: Исходный язык (для OCR, если PDF содержит изображения)
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension == ".txt":
            text = ""
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            # Нормализуем химические формулы
            text = self._normalize_chemical_formulas(text)
            return text
        
        elif extension == ".pdf":
            if not PDF_AVAILABLE:
                raise ImportError("PyPDF2 не установлен. Установите: pip install PyPDF2")
            
            # Пробуем извлечь текст напрямую
            text = ""
            try:
                with open(file_path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e:
                print(f"⚠️  Ошибка при извлечении текста из PDF: {str(e)}")
            
            # Проверяем наличие испорченных формул в извлеченном тексте
            # (даже если текст достаточно длинный, формулы могут быть испорчены)
            has_corrupted_formulas = False
            if text and len(text.strip()) >= 50:
                # Ищем признаки испорченных формул
                lines = text.split('\n')
                corrupted_lines = []
                for line in lines:
                    line_stripped = line.strip()
                    # Проверяем, является ли строка испорченной формулой
                    is_corrupted = (
                        len(line_stripped) < 100 and  # Короткая строка
                        len(line_stripped) > 3 and
                        ('=' in line_stripped or '+' in line_stripped or '-' in line_stripped or '*' in line_stripped) and
                        (re.search(r'\b(Isp|g0|m0|mf|Av|Δv|C3|ln|log)\b', line_stripped, re.IGNORECASE) or
                         re.search(r'[Δαβγδεζηθικλμνξοπρστυφχψω]', line_stripped) or
                         'go' in line_stripped.lower() or '-1n' in line_stripped.lower() or
                         'Ig,' in line_stripped or 'In |' in line_stripped or 'ln.r' in line_stripped or
                         'ln г' in line_stripped or 'М0' in line_stripped or 'cons' in line_stripped.lower())
                    )
                    if is_corrupted:
                        has_corrupted_formulas = True
                        corrupted_lines.append(line_stripped[:50])
                        if len(corrupted_lines) <= 3:  # Показываем только первые 3
                            print(f"   🔍 Найдена испорченная формула в текстовом слое: {line_stripped[:50]}...")
            
            # Если текст слишком короткий (вероятно, PDF с изображениями), пробуем OCR
            # ИЛИ если найдены испорченные формулы (особенно для русского языка), используем OCR для их исправления
            if not text or len(text.strip()) < 50:
                print(f"⚠️  Текст из PDF слишком короткий ({len(text)} символов), пробуем OCR...")
                ocr_result = self._extract_text_with_ocr(Path(file_path), source_lang)
                if ocr_result:
                    ocr_text, page_images = ocr_result if isinstance(ocr_result, tuple) else (ocr_result, {})
                    if ocr_text and len(ocr_text.strip()) > len(text.strip()):
                        text = ocr_text
                        print(f"✅ OCR извлек {len(text)} символов")
                        # Сохраняем информацию об изображениях для последующей вставки в Word
                        if page_images:
                            self._page_images = page_images
            elif has_corrupted_formulas:
                # Для русского языка особенно важно использовать OCR, так как формулы часто испорчены
                print(f"⚠️  Найдены испорченные формулы в текстовом слое ({len(corrupted_lines)} шт.), используем OCR для исправления...")
                ocr_result = self._extract_text_with_ocr(Path(file_path), source_lang)
                if ocr_result:
                    ocr_text, page_images = ocr_result if isinstance(ocr_result, tuple) else (ocr_result, {})
                    if ocr_text:
                        # Используем OCR текст, так как он содержит исправленные формулы через Mathpix
                        text = ocr_text
                        print(f"✅ OCR извлек {len(text)} символов с исправленными формулами")
                        # Сохраняем информацию об изображениях для последующей вставки в Word
                        if page_images:
                            self._page_images = page_images
                else:
                    print(f"⚠️  OCR не удался, используем оригинальный текст")
            
            if not text or not text.strip():
                raise ValueError(
                    "Не удалось извлечь текст из PDF. "
                    "Возможно, файл содержит только изображения. "
                    "Убедитесь, что установлены Tesseract OCR и Poppler для обработки сканированных PDF."
                )
            
            # Нормализуем химические формулы сразу после извлечения текста
            text = self._normalize_chemical_formulas(text)
            
            return text
        
        elif extension in [".docx", ".doc"]:
            if not DOCX_AVAILABLE:
                raise ImportError("python-docx не установлен. Установите: pip install python-docx")
            
            if extension == ".docx":
                doc = Document(file_path)
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                # Нормализуем химические формулы
                text = self._normalize_chemical_formulas(text)
                return text
            else:
                # .doc файлы требуют дополнительных библиотек (python-docx не поддерживает .doc)
                # Можно использовать antiword или docx2txt
                raise NotImplementedError(
                    "Формат .doc требует дополнительных библиотек. "
                    "Рекомендуется конвертировать в .docx или использовать библиотеку python-docx2txt"
                )
        
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {extension}")
    
    def _extract_text_with_ocr(
        self, 
        file_path: Path, 
        source_lang: Optional[Literal["ru", "ar", "zh"]] = None
    ) -> tuple[str, dict[int, str]]:
        """
        Извлекает текст из PDF используя OCR и сохраняет изображения страниц
        
        Returns:
            Кортеж (текст, словарь {номер_страницы: путь_к_изображению})
        """
        """
        Извлекает текст из PDF используя OCR (распознавание текста из изображений)
        Требует установленный Tesseract OCR и poppler
        
        Args:
            file_path: Путь к PDF файлу
            source_lang: Исходный язык для выбора языков OCR
        """
        try:
            import pytesseract
            from PIL import Image
            from pdf2image import convert_from_path
            
            # Настройка пути к Tesseract для Windows (если нужно)
            if os.name == 'nt':  # Windows
                tesseract_paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                ]
                for path in tesseract_paths:
                    if Path(path).exists():
                        pytesseract.pytesseract.tesseract_cmd = path
                        print(f"   ✅ Tesseract найден: {path}")
                        break
                else:
                    print("   ⚠️  Tesseract не найден в стандартных путях")
                    # Пробуем найти через PATH
                    import shutil
                    tesseract_cmd = shutil.which('tesseract')
                    if tesseract_cmd:
                        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                        print(f"   ✅ Tesseract найден в PATH: {tesseract_cmd}")
                    else:
                        print("   ❌ Tesseract не найден. Установите Tesseract OCR")
                        print("   См. инструкции: backend/INSTALL_OCR.md")
                        return "", {}
                    
        except ImportError:
            print("⚠️  OCR библиотеки не установлены. Установите: pip install pytesseract pdf2image Pillow")
            return ""
        
        try:
            # Конвертируем PDF в изображения
            print(f"   Конвертация PDF в изображения...")
            
            # Пробуем найти poppler в стандартных местах
            poppler_path = None
            if os.name == 'nt':  # Windows
                poppler_paths = [
                    r'C:\poppler\Library\bin',
                    r'C:\poppler\bin',
                    r'C:\Program Files\poppler\bin',
                ]
                for path in poppler_paths:
                    if Path(path).exists():
                        poppler_path = path
                        break
            
            # Конвертируем PDF в изображения
            if poppler_path:
                images = convert_from_path(str(file_path), dpi=300, poppler_path=poppler_path)
            else:
                images = convert_from_path(str(file_path), dpi=300)
            
            # Создаем временную папку для сохранения изображений страниц
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "pdf_images"
            temp_dir.mkdir(exist_ok=True)
            
            # Сохраняем изображения страниц
            page_images = {}
            for i, image in enumerate(images, 1):
                image_path = temp_dir / f"page_{i}.png"
                image.save(str(image_path), "PNG")
                page_images[i] = str(image_path)
            
            text = ""
            print(f"   Распознавание текста из {len(images)} страниц...")
            print(f"   📷 Сохранено {len(page_images)} изображений страниц")
            
            # Определяем язык для OCR на основе исходного языка
            lang_map = {
                "ru": "rus+eng",
                "ar": "ara+eng",
                "zh": "chi_sim+eng"  # Китайский упрощенный + английский
            }
            ocr_lang = lang_map.get(source_lang, "eng")  # По умолчанию английский
            
            print(f"   Используется язык OCR: {ocr_lang}")
            
            # Проверяем доступность языков Tesseract
            try:
                import pytesseract
                available_langs = pytesseract.get_languages()
                print(f"   Доступные языки Tesseract: {', '.join(available_langs)}")
                if "chi_sim" not in available_langs and source_lang == "zh":
                    print("   ⚠️  Китайский язык (chi_sim) не установлен в Tesseract")
                    print("   💡 Установите: tesseract-ocr-chi-sim или используйте английский OCR")
            except Exception:
                pass
            
            for i, image in enumerate(images, 1):
                print(f"   Страница {i}/{len(images)}...", end="\r")
                try:
                    # Сначала пробуем извлечь текст обычным OCR
                    page_text = pytesseract.image_to_string(
                        image, 
                        lang=ocr_lang,
                        config='--psm 6'
                    )
                    
                    # Если Mathpix доступен, используем его для улучшения распознавания формул
                    if self.mathpix and self.mathpix.available:
                        # Ищем строки с испорченными формулами (короткие строки с математическими символами)
                        lines = page_text.split('\n')
                        improved_lines = []
                        formulas_corrected = 0
                        images_inserted = 0
                        
                        # Обрабатываем каждую строку
                        for line_idx, line in enumerate(lines):
                            line_stripped = line.strip()
                            
                            # Проверяем, является ли строка испорченной формулой
                            # Испорченные формулы обычно короткие, содержат =, +, -, *, / и математические переменные
                            # Также проверяем на наличие номеров формул типа (13.7), (13.8), (13.9), (13.10), (13.11)
                            is_corrupted_formula = (
                                len(line_stripped) < 200 and  # Увеличено до 200 для многострочных формул
                                len(line_stripped) > 3 and
                                ('=' in line_stripped or '+' in line_stripped or '-' in line_stripped or 
                                 '/' in line_stripped or '*' in line_stripped or '^' in line_stripped or
                                 'where' in line_stripped.lower() or 'we obtain' in line_stripped.lower()) and
                                (re.search(r'\b(Isp|g0|m0|mf|Av|Δv|C3|ln|log|e\^|exp|μ|ν|κ|π|γ|α|β|δ|θ|λ|σ|φ|ω|Δ|Mo|Mar|Hoga|ик|V_k|I_уд|a_т|n_0|g_0|m_0)\b', line_stripped, re.IGNORECASE) or
                                 re.search(r'[Δαβγδεζηθικλμνξοπρστυφχψω]', line_stripped) or
                                 re.search(r'\(\d+\.\d+\)', line_stripped) or  # Номера формул типа (13.7)
                                 'go' in line_stripped.lower() or '-1n' in line_stripped.lower() or
                                 re.search(r'[a-zA-Z]\s*=\s*[a-zA-Z]', line_stripped))  # Паттерн типа "x = y"
                            )
                            
                            if is_corrupted_formula:
                                # Пробуем распознать формулу через Mathpix
                                print(f"\n   🔍 Найдена испорченная формула ({line_idx+1}): {line_stripped[:50]}...")
                                print(f"   📤 Отправка в Mathpix для распознавания...")
                                mathpix_result = self.mathpix.recognize_formula_from_image(image)
                                
                                if mathpix_result:
                                    # Очищаем результат от лишних пробелов и переносов строк
                                    mathpix_clean = mathpix_result.strip()
                                    # Убираем лишние пробелы между символами в индексах (например, I_{s p} -> I_{sp})
                                    mathpix_clean = re.sub(r'\{([^}]+)\s+([^}]+)\}', r'{\1\2}', mathpix_clean)
                                    # Убираем лишние пробелы вокруг операторов
                                    mathpix_clean = re.sub(r'\s*=\s*', '=', mathpix_clean)
                                    mathpix_clean = re.sub(r'\s*\+\s*', '+', mathpix_clean)
                                    mathpix_clean = re.sub(r'\s*-\s*', '-', mathpix_clean)
                                    # Убираем переносы строк внутри формулы
                                    mathpix_clean = re.sub(r'\s+', ' ', mathpix_clean)
                                    
                                    # Извлекаем только математическую часть из результата
                                    # Ищем LaTeX формулы в результате
                                    latex_match = re.search(r'\\\[(.*?)\\\]|\\\((.*?)\\\)|\$(.*?)\$', mathpix_clean, re.DOTALL)
                                    if latex_match:
                                        formula = latex_match.group(1) or latex_match.group(2) or latex_match.group(3)
                                        # Очищаем формулу от лишних пробелов
                                        formula = re.sub(r'\s+', ' ', formula.strip())
                                        improved_lines.append(f"\\[{formula}\\]")
                                        print(f"   ✅ Формула распознана: {formula[:60]}...")
                                        formulas_corrected += 1
                                    else:
                                        # Если не нашли LaTeX маркеры, но результат похож на формулу
                                        if len(mathpix_clean) < 300 and ('=' in mathpix_clean or '\\' in mathpix_clean):
                                            # Очищаем от лишних пробелов
                                            mathpix_clean = re.sub(r'\s+', ' ', mathpix_clean.strip())
                                            # Убираем уже существующие маркеры, если есть
                                            mathpix_clean = mathpix_clean.strip('$\\[\\]()')
                                            improved_lines.append(f"\\[{mathpix_clean}\\]")
                                            print(f"   ✅ Формула распознана: {mathpix_clean[:60]}...")
                                            formulas_corrected += 1
                                        else:
                                            # Если Mathpix вернул слишком длинный текст, это может быть график или сложная формула
                                            # Вставляем плейсхолдер для изображения страницы
                                            image_placeholder = f"__IMAGE_PAGE_{i}__"
                                            improved_lines.append(image_placeholder)
                                            images_inserted += 1
                                            print(f"   📷 Mathpix вернул слишком длинный результат ({len(mathpix_clean)} символов), будет вставлено изображение страницы {i}")
                                else:
                                    # Если Mathpix не сработал, это может быть график или сложная формула
                                    # Вставляем плейсхолдер для изображения страницы
                                    image_placeholder = f"__IMAGE_PAGE_{i}__"
                                    improved_lines.append(image_placeholder)
                                    images_inserted += 1
                                    print(f"   📷 Mathpix не распознал формулу (возможно график), будет вставлено изображение страницы {i}")
                            else:
                                improved_lines.append(line)
                        
                        if formulas_corrected > 0 or images_inserted > 0:
                            page_text = '\n'.join(improved_lines)
                            if formulas_corrected > 0:
                                print(f"   ✅ Исправлено формул через Mathpix: {formulas_corrected}")
                            if images_inserted > 0:
                                print(f"   📷 Вставлено изображений для нераспознанных формул: {images_inserted}")
                    
                except Exception as ocr_err:
                    # Если язык не установлен, пробуем только английский
                    if "chi_sim" in ocr_lang or "ara" in ocr_lang or "rus" in ocr_lang:
                        print(f"   ⚠️  Язык {ocr_lang} не найден, пробуем английский...")
                        page_text = pytesseract.image_to_string(
                            image, 
                            lang='eng',
                            config='--psm 6'
                        )
                    else:
                        raise ocr_err
                text += page_text + "\n\n"
            
            print(f"   ✅ Распознано {len(text)} символов")
            
            # Нормализуем химические формулы после OCR
            text = self._normalize_chemical_formulas(text)
            
            return text, page_images
            
        except Exception as e:
            print(f"   ❌ Ошибка OCR: {str(e)}")
            print("   Убедитесь, что Tesseract OCR установлен и доступен в PATH")
            return ""

