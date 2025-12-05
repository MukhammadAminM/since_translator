"""
Пример использования нового модульного пайплайна
"""
import asyncio
import logging
from pathlib import Path
from services.pipeline import TranslationPipeline, PipelineConfig, FormulaMode

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Основная функция примера"""
    
    # Путь к PDF файлу
    pdf_path = Path("example.pdf")
    
    if not pdf_path.exists():
        logger.error(f"Файл не найден: {pdf_path}")
        logger.info("Поместите PDF файл в текущую директорию и назовите его 'example.pdf'")
        return
    
    # Инициализация пайплайна
    logger.info("Инициализация пайплайна...")
    pipeline = TranslationPipeline(output_dir="outputs")
    
    # Конфигурация для русского языка
    config_ru = PipelineConfig(
        source_lang="ru",
        target_lang="en",
        model="engineering",
        formula_mode=FormulaMode.PNG,  # Используем PNG режим
        use_ocr=False,  # Не используем OCR (обычное извлечение)
        use_mathpix=True,  # Используем Mathpix для распознавания формул
        include_mathml=False  # Не нужен MathML для PNG режима
    )
    
    # Обработка PDF
    logger.info(f"Начало обработки: {pdf_path.name}")
    result = await pipeline.process(pdf_path, config_ru)
    
    # Результаты
    if result.success:
        logger.info("✅ Обработка завершена успешно!")
        logger.info(f"📄 Файл создан: {result.output_file}")
        logger.info(f"📊 Статистика:")
        logger.info(f"   - Найдено формул: {result.formulas_count}")
        logger.info(f"   - Распознано формул: {result.recognized_formulas_count}")
        logger.info(f"   - Страниц: {result.extracted_content.page_count}")
        logger.info(f"   - Символов: {len(result.extracted_content.text)}")
    else:
        logger.error(f"❌ Ошибка обработки: {result.error}")


async def example_with_ocr():
    """Пример с использованием OCR"""
    
    pdf_path = Path("scanned_document.pdf")
    
    if not pdf_path.exists():
        logger.warning(f"Файл не найден: {pdf_path}")
        return
    
    pipeline = TranslationPipeline(output_dir="outputs")
    
    # Конфигурация с OCR
    config = PipelineConfig(
        source_lang="ru",
        target_lang="en",
        model="academic",
        formula_mode=FormulaMode.PNG,
        use_ocr=True,  # Используем OCR
        ocr_lang="rus+eng",  # Русский + английский
        use_mathpix=True,
        include_mathml=False
    )
    
    result = await pipeline.process(pdf_path, config)
    
    if result.success:
        logger.info(f"✅ OCR обработка завершена: {result.output_file}")
    else:
        logger.error(f"❌ Ошибка: {result.error}")


async def example_omml_mode():
    """Пример с OMML режимом (нативные формулы Word)"""
    
    pdf_path = Path("formulas.pdf")
    
    if not pdf_path.exists():
        logger.warning(f"Файл не найден: {pdf_path}")
        return
    
    pipeline = TranslationPipeline(output_dir="outputs")
    
    # Конфигурация с OMML
    config = PipelineConfig(
        source_lang="ru",
        target_lang="en",
        model="scientific",
        formula_mode=FormulaMode.OMML,  # Используем OMML режим
        use_ocr=False,
        use_mathpix=True,
        include_mathml=True  # Нужен MathML для OMML
    )
    
    result = await pipeline.process(pdf_path, config)
    
    if result.success:
        logger.info(f"✅ OMML обработка завершена: {result.output_file}")
        logger.info("⚠️  Примечание: OMML режим требует дополнительной реализации конвертации MathML → OMML")
    else:
        logger.error(f"❌ Ошибка: {result.error}")


if __name__ == "__main__":
    # Запуск основного примера
    asyncio.run(main())
    
    # Раскомментируйте для других примеров:
    # asyncio.run(example_with_ocr())
    # asyncio.run(example_omml_mode())

