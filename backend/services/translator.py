from typing import Literal
import asyncio
import os
from pathlib import Path

# OpenAI для перевода
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Глоссарий
from services.glossary_manager import GlossaryManager

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
        
        # Инициализация менеджера глоссария
        try:
            self.glossary_manager = GlossaryManager()
        except Exception as e:
            print(f"⚠️  Не удалось загрузить глоссарий: {str(e)}")
            self.glossary_manager = None
    
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
        
        # Названия языков для промпта
        lang_names = {
            "ru": "Russian",
            "ar": "Arabic",
            "zh": "Chinese"
        }
        
        # Специальные инструкции для разных типов перевода
        model_instructions = {
            "general": "Translate naturally and accurately, maintaining the original tone and style.",
            "engineering": "Translate technical and engineering terminology precisely. Maintain technical accuracy and use appropriate engineering terminology.",
            "academic": "Translate academic texts with precision. Maintain formal academic style, preserve citations and references if present.",
            "scientific": "Translate scientific texts with utmost precision. Maintain scientific terminology, preserve formulas and technical notation exactly."
        }
        
        # Добавляем глоссарий в промпт, если он доступен
        # Используем умный поиск релевантных терминов из текста
        glossary_text = ""
        if self.glossary_manager:
            glossary_summary = self.glossary_manager.get_glossary_summary(
                source_lang, 
                text=text,  # Передаем текст для поиска релевантных терминов
                max_terms=200
            )
            if glossary_summary:
                glossary_text = f"\n\n{glossary_summary}"
        
        system_prompt = (
            f"You are a professional translator specializing in {model} translation. "
            f"Translate the following text from {lang_names[source_lang]} to {target_lang.upper()}. "
            f"{model_instructions[model]} "
            f"Maintain the original formatting, paragraph structure, and line breaks. "
            f"Do not add any explanations, comments, or notes - provide only the translation."
            f"{glossary_text}"
        )
        
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
            
            translated_text = response.choices[0].message.content.strip()
            
            if not translated_text:
                raise ValueError("OpenAI вернул пустой ответ")
            
            return translated_text
            
        except Exception as e:
            error_msg = f"Ошибка при переводе через OpenAI: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg) from e
    
    async def extract_text_from_file(self, file_path: str) -> str:
        """
        Извлекает текст из различных типов файлов (PDF, DOCX, DOC, TXT)
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        
        elif extension == ".pdf":
            if not PDF_AVAILABLE:
                raise ImportError("PyPDF2 не установлен. Установите: pip install PyPDF2")
            
            text = ""
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        
        elif extension in [".docx", ".doc"]:
            if not DOCX_AVAILABLE:
                raise ImportError("python-docx не установлен. Установите: pip install python-docx")
            
            if extension == ".docx":
                doc = Document(file_path)
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
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

