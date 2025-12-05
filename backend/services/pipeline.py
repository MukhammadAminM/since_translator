"""
Главный пайплайн для обработки PDF документов с формулами
Оркестрирует все модули: извлечение → выделение формул → распознавание → перевод → сборка
"""
import logging
from pathlib import Path
from typing import Literal, Optional, Dict
from dataclasses import dataclass

from services.pdf_extractor import PDFExtractor, ExtractedContent
from services.formula_extractor import FormulaExtractor
from services.formula_recognizer import FormulaRecognizer, RecognizedFormula
from services.text_translator import TextTranslator, TranslationConfig
from services.document_builder import DocumentBuilder, FormulaMode

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Конфигурация пайплайна"""
    source_lang: Literal["ru", "ar", "zh"]
    target_lang: str = "en"
    model: Literal["general", "engineering", "academic", "scientific"] = "general"
    formula_mode: FormulaMode = FormulaMode.PNG
    use_ocr: bool = False
    ocr_lang: Optional[str] = None
    use_mathpix: bool = True
    include_mathml: bool = True


@dataclass
class PipelineResult:
    """Результат работы пайплайна"""
    output_file: Path
    extracted_content: ExtractedContent
    formulas_count: int
    recognized_formulas_count: int
    success: bool
    error: Optional[str] = None


class TranslationPipeline:
    """
    Главный пайплайн для обработки PDF документов
    
    Этапы:
    1. Извлечение текста и изображений из PDF
    2. Выделение формул и замена на маркеры
    3. Распознавание формул через Mathpix (опционально)
    4. Перевод текста без формул
    5. Восстановление формул в переведенном тексте
    6. Сборка DOCX документа
    """
    
    def __init__(self, output_dir: str = "outputs"):
        """
        Args:
            output_dir: Директория для сохранения результатов
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Инициализация модулей
        logger.info("Инициализация модулей пайплайна...")
        
        self.pdf_extractor = PDFExtractor()
        self.formula_extractor = FormulaExtractor()
        # FormulaRecognizer и DocumentBuilder инициализируются в process() с правильной конфигурацией
        self.text_translator = TextTranslator()
        
        logger.info("Пайплайн инициализирован")
    
    async def process(
        self,
        pdf_path: Path,
        config: PipelineConfig
    ) -> PipelineResult:
        """
        Обрабатывает PDF документ через весь пайплайн
        
        Args:
            pdf_path: Путь к PDF файлу
            config: Конфигурация пайплайна
        
        Returns:
            PipelineResult с результатами обработки
        """
        try:
            logger.info(f"Начало обработки PDF: {pdf_path.name}")
            
            # Этап 1: Извлечение текста и изображений
            logger.info("Этап 1: Извлечение текста и изображений из PDF")
            extracted_content = self.pdf_extractor.extract(
                pdf_path,
                use_ocr=config.use_ocr,
                ocr_lang=config.ocr_lang
            )
            logger.info(f"Извлечено: {len(extracted_content.text)} символов, {extracted_content.page_count} страниц")
            
            # Этап 2: Выделение формул
            logger.info("Этап 2: Выделение формул")
            text_with_markers, formulas = self.formula_extractor.extract(extracted_content.text)
            logger.info(f"Найдено формул: {len(formulas)}")
            
            # Инициализация FormulaRecognizer и DocumentBuilder с правильной конфигурацией
            if config.use_mathpix:
                self.formula_recognizer = FormulaRecognizer()
            
            document_builder = DocumentBuilder(
                output_dir=str(self.output_dir),
                formula_mode=config.formula_mode
            )
            
            # Этап 3: Распознавание формул через Mathpix (опционально)
            recognized_formulas = {}
            if config.use_mathpix and self.formula_recognizer and self.formula_recognizer.available:
                logger.info("Этап 3: Распознавание формул через Mathpix")
                recognized_formulas = await self._recognize_formulas(
                    formulas,
                    extracted_content.page_images,
                    config.include_mathml
                )
                logger.info(f"Распознано формул: {len(recognized_formulas)}")
            else:
                logger.info("Этап 3: Пропущен (Mathpix недоступен или отключен)")
            
            # Этап 4: Перевод текста
            logger.info("Этап 4: Перевод текста")
            translation_config = TranslationConfig(
                source_lang=config.source_lang,
                target_lang=config.target_lang,
                model=config.model,
                use_glossary=True
            )
            translated_text = await self.text_translator.translate(
                text_with_markers,
                translation_config
            )
            logger.info("Перевод завершен")
            
            # Этап 5: Восстановление формул (не нужно - маркеры уже в тексте)
            # Формулы остаются в виде маркеров, DocumentBuilder их обработает
            
            # Этап 6: Сборка DOCX
            logger.info("Этап 6: Сборка DOCX документа")
            output_file = document_builder.build(
                translated_text=translated_text,
                formulas=formulas,
                recognized_formulas=recognized_formulas if recognized_formulas else None,
                source_lang=config.source_lang,
                model=config.model,
                original_filename=pdf_path.name,
                page_images=extracted_content.page_images
            )
            logger.info(f"DOCX файл создан: {output_file}")
            
            return PipelineResult(
                output_file=output_file,
                extracted_content=extracted_content,
                formulas_count=len(formulas),
                recognized_formulas_count=len(recognized_formulas),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Ошибка в пайплайне: {e}", exc_info=True)
            return PipelineResult(
                output_file=Path(),
                extracted_content=ExtractedContent("", {}, 0, {}),
                formulas_count=0,
                recognized_formulas_count=0,
                success=False,
                error=str(e)
            )
    
    async def _recognize_formulas(
        self,
        formulas: Dict[int, str],
        page_images: Dict[int, Path],
        include_mathml: bool
    ) -> Dict[int, RecognizedFormula]:
        """
        Распознает формулы через Mathpix
        
        Args:
            formulas: Словарь формул {индекс: формула}
            page_images: Изображения страниц
            include_mathml: Включать ли MathML
        
        Returns:
            Словарь распознанных формул {индекс: RecognizedFormula}
        """
        recognized = {}
        
        # Для каждой формулы пытаемся найти соответствующее изображение
        # Пока используем изображения страниц (в будущем можно улучшить)
        for formula_index, formula_text in formulas.items():
            # Пробуем найти страницу с формулой
            # Упрощенная версия: используем первую доступную страницу
            # В реальности нужно определять, на какой странице находится формула
            if page_images:
                # Используем первую страницу как пример
                first_page = list(page_images.values())[0]
                result = self.formula_recognizer.recognize_from_file(
                    first_page,
                    include_mathml=include_mathml
                )
                if result:
                    recognized[formula_index] = result
        
        return recognized

