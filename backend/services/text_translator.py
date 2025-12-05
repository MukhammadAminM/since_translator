"""
Модуль для безопасного перевода текста без формул
Использует OpenAI API для перевода
"""
import os
import logging
from typing import Literal, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI библиотека не установлена. Установите: pip install openai")

from services.glossary_manager import GlossaryManager


@dataclass
class TranslationConfig:
    """Конфигурация для перевода"""
    source_lang: Literal["ru", "ar", "zh"]
    target_lang: str = "en"
    model: Literal["general", "engineering", "academic", "scientific"] = "general"
    use_glossary: bool = True
    temperature: float = 0.3  # Низкая температура для более точного перевода


class TextTranslator:
    """
    Класс для безопасного перевода текста
    
    Особенности:
    - Переводчик получает только текст без формул
    - Интеграция с глоссарием
    - Поддержка разных моделей OpenAI
    - Обработка ошибок и retry
    """
    
    def __init__(self):
        """Инициализация переводчика"""
        if not OPENAI_AVAILABLE:
            raise RuntimeError("OpenAI библиотека не установлена")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY не найден в переменных окружения. "
                "Установите его через .env файл или переменные окружения."
            )
        
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Модели для разных типов перевода
        self.models = {
            "general": "gpt-4o-mini",
            "engineering": "gpt-4o",
            "academic": "gpt-4o",
            "scientific": "gpt-4o"
        }
        
        # Инициализация менеджера глоссария
        try:
            self.glossary_manager = GlossaryManager()
            logger.info("Глоссарий загружен")
        except Exception as e:
            logger.warning(f"Не удалось загрузить глоссарий: {e}")
            self.glossary_manager = None
    
    async def translate(
        self,
        text: str,
        config: TranslationConfig
    ) -> str:
        """
        Переводит текст
        
        Args:
            text: Текст для перевода (уже без формул, с маркерами)
            config: Конфигурация перевода
        
        Returns:
            Переведенный текст (с теми же маркерами формул)
        """
        if not text.strip():
            return text
        
        logger.info(f"Начало перевода (язык: {config.source_lang} -> {config.target_lang}, модель: {config.model})")
        
        # Получаем модель
        model_name = self.models.get(config.model, self.models["general"])
        
        # Формируем промпт
        prompt = self._build_prompt(text, config)
        
        # Выполняем перевод
        try:
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": self._get_system_message(config)},
                    {"role": "user", "content": prompt}
                ],
                temperature=config.temperature,
                max_tokens=4000
            )
            
            translated_text = response.choices[0].message.content.strip()
            logger.info("Перевод завершен успешно")
            
            return translated_text
            
        except Exception as e:
            logger.error(f"Ошибка при переводе: {e}")
            raise
    
    def _build_prompt(self, text: str, config: TranslationConfig) -> str:
        """
        Формирует промпт для перевода
        
        Args:
            text: Текст для перевода
            config: Конфигурация перевода
        
        Returns:
            Промпт для OpenAI API
        """
        # Получаем релевантные термины из глоссария
        glossary_terms = ""
        if config.use_glossary and self.glossary_manager:
            try:
                relevant_terms = self.glossary_manager.find_relevant_terms(
                    text,
                    source_lang=config.source_lang,
                    max_terms=200
                )
                if relevant_terms:
                    glossary_terms = f"\n\nВажно: Используй следующие термины из глоссария:\n{relevant_terms}"
            except Exception as e:
                logger.warning(f"Ошибка при получении терминов из глоссария: {e}")
        
        # Языковые пары
        lang_names = {
            "ru": "русский",
            "ar": "арабский",
            "zh": "китайский",
            "en": "английский"
        }
        
        source_name = lang_names.get(config.source_lang, config.source_lang)
        target_name = lang_names.get(config.target_lang, config.target_lang)
        
        # Инструкции по переводу
        instructions = {
            "general": "Переведи текст точно и естественно.",
            "engineering": "Переведи текст, сохраняя техническую терминологию и точность.",
            "academic": "Переведи текст в академическом стиле, сохраняя формальность.",
            "scientific": "Переведи текст, сохраняя научную точность и терминологию."
        }
        
        instruction = instructions.get(config.model, instructions["general"])
        
        prompt = f"""Переведи следующий текст с {source_name} на {target_name}.

{instruction}

ВАЖНО:
- НЕ изменяй маркеры формул вида <<<FORMULA_N>>> - оставь их как есть
- Сохрани структуру текста (абзацы, переносы строк)
- Сохрани все числа, даты, названия в оригинальном формате
{glossary_terms}

Текст для перевода:

{text}"""
        
        return prompt
    
    def _get_system_message(self, config: TranslationConfig) -> str:
        """
        Получает системное сообщение для OpenAI API
        
        Args:
            config: Конфигурация перевода
        
        Returns:
            Системное сообщение
        """
        return """Ты профессиональный переводчик технических и научных текстов.
Твоя задача - точно переводить текст, сохраняя:
- Техническую терминологию
- Структуру документа
- Маркеры формул (<<<FORMULA_N>>>)
- Форматирование

НЕ изменяй маркеры формул и не переводи их содержимое."""

