"""
Модуль для извлечения текста и изображений из PDF документов
Поддерживает PyMuPDF (fitz) и pdfplumber
"""
import logging
from pathlib import Path
from typing import Tuple, Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Попытка импорта PyMuPDF
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF не установлен. Установите: pip install PyMuPDF")

# Попытка импорта pdfplumber
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber не установлен. Установите: pip install pdfplumber")

# Для OCR (если нужно)
try:
    from pdf2image import convert_from_path
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR библиотеки не установлены. Установите: pip install pdf2image pytesseract Pillow")


@dataclass
class ExtractedContent:
    """Структура для хранения извлеченного контента"""
    text: str
    page_images: Dict[int, Path]  # номер страницы -> путь к изображению
    page_count: int
    metadata: Dict[str, any]


class PDFExtractor:
    """
    Класс для извлечения текста и изображений из PDF документов
    
    Поддерживает:
    - PyMuPDF (fitz) - быстрый и точный
    - pdfplumber - для сложных PDF с таблицами
    - OCR через Tesseract - для сканированных документов
    """
    
    def __init__(self, prefer_pymupdf: bool = True):
        """
        Args:
            prefer_pymupdf: Если True, использует PyMuPDF, иначе pdfplumber
        """
        self.prefer_pymupdf = prefer_pymupdf
        self.use_pymupdf = PYMUPDF_AVAILABLE and prefer_pymupdf
        self.use_pdfplumber = PDFPLUMBER_AVAILABLE and not prefer_pymupdf
        
        if not self.use_pymupdf and not self.use_pdfplumber:
            logger.warning("Ни PyMuPDF, ни pdfplumber не доступны. Будет использован OCR.")
    
    def extract(self, pdf_path: Path, use_ocr: bool = False, ocr_lang: Optional[str] = None) -> ExtractedContent:
        """
        Извлекает текст и изображения из PDF
        
        Args:
            pdf_path: Путь к PDF файлу
            use_ocr: Использовать OCR для извлечения текста
            ocr_lang: Язык для OCR (например, 'rus+eng', 'ara+eng', 'chi_sim+eng')
        
        Returns:
            ExtractedContent с текстом, изображениями страниц и метаданными
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")
        
        logger.info(f"Извлечение контента из PDF: {pdf_path.name}")
        
        # Пробуем сначала обычное извлечение
        if not use_ocr:
            if self.use_pymupdf:
                return self._extract_with_pymupdf(pdf_path)
            elif self.use_pdfplumber:
                return self._extract_with_pdfplumber(pdf_path)
        
        # Если нужно OCR или обычное извлечение не сработало
        if OCR_AVAILABLE and use_ocr:
            return self._extract_with_ocr(pdf_path, ocr_lang)
        else:
            # Fallback на PyMuPDF даже если OCR недоступен
            if PYMUPDF_AVAILABLE:
                return self._extract_with_pymupdf(pdf_path)
            else:
                raise RuntimeError("Нет доступных методов для извлечения текста из PDF")
    
    def _extract_with_pymupdf(self, pdf_path: Path) -> ExtractedContent:
        """Извлечение через PyMuPDF"""
        import tempfile
        
        doc = fitz.open(pdf_path)
        text_parts = []
        page_images = {}
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Извлекаем текст
                page_text = page.get_text()
                text_parts.append(page_text)
                
                # Сохраняем изображение страницы для возможного использования
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom для лучшего качества
                image_path = temp_dir / f"page_{page_num + 1}.png"
                pix.save(str(image_path))
                page_images[page_num + 1] = image_path
                
                logger.debug(f"Страница {page_num + 1}: извлечено {len(page_text)} символов")
            
            full_text = "\n\n".join(text_parts)
            metadata = {
                "method": "pymupdf",
                "page_count": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
            }
            
            return ExtractedContent(
                text=full_text,
                page_images=page_images,
                page_count=len(doc),
                metadata=metadata
            )
        finally:
            doc.close()
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> ExtractedContent:
        """Извлечение через pdfplumber"""
        import tempfile
        
        text_parts = []
        page_images = {}
        temp_dir = Path(tempfile.mkdtemp())
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Извлекаем текст
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
                
                # Сохраняем изображение страницы
                # pdfplumber не имеет прямого метода для получения изображения страницы
                # Используем PyMuPDF для этого, если доступен
                if PYMUPDF_AVAILABLE:
                    doc = fitz.open(pdf_path)
                    pix = doc[page_num - 1].get_pixmap(matrix=fitz.Matrix(2, 2))
                    image_path = temp_dir / f"page_{page_num}.png"
                    pix.save(str(image_path))
                    page_images[page_num] = image_path
                    doc.close()
                
                logger.debug(f"Страница {page_num}: извлечено {len(page_text)} символов")
        
        full_text = "\n\n".join(text_parts)
        metadata = {
            "method": "pdfplumber",
            "page_count": len(text_parts),
        }
        
        return ExtractedContent(
            text=full_text,
            page_images=page_images,
            page_count=len(text_parts),
            metadata=metadata
        )
    
    def _extract_with_ocr(self, pdf_path: Path, ocr_lang: Optional[str] = None) -> ExtractedContent:
        """Извлечение через OCR (Tesseract)"""
        import tempfile
        
        if not OCR_AVAILABLE:
            raise RuntimeError("OCR библиотеки не установлены")
        
        logger.info("Использование OCR для извлечения текста")
        
        # Определяем язык OCR
        if not ocr_lang:
            ocr_lang = "eng"  # По умолчанию английский
        
        # Конвертируем PDF в изображения
        temp_dir = Path(tempfile.mkdtemp())
        poppler_path = self._find_poppler_path()
        
        try:
            if poppler_path:
                images = convert_from_path(str(pdf_path), dpi=300, poppler_path=poppler_path)
            else:
                images = convert_from_path(str(pdf_path), dpi=300)
        except Exception as e:
            logger.error(f"Ошибка при конвертации PDF в изображения: {e}")
            raise
        
        text_parts = []
        page_images = {}
        
        for i, image in enumerate(images, 1):
            # Сохраняем изображение страницы
            image_path = temp_dir / f"page_{i}.png"
            image.save(str(image_path))
            page_images[i] = image_path
            
            # Извлекаем текст через OCR
            try:
                page_text = pytesseract.image_to_string(image, lang=ocr_lang, config='--psm 6')
                text_parts.append(page_text)
                logger.debug(f"Страница {i}: извлечено {len(page_text)} символов через OCR")
            except Exception as e:
                logger.warning(f"Ошибка OCR на странице {i}: {e}")
                text_parts.append("")
        
        full_text = "\n\n".join(text_parts)
        metadata = {
            "method": "ocr",
            "ocr_lang": ocr_lang,
            "page_count": len(images),
        }
        
        return ExtractedContent(
            text=full_text,
            page_images=page_images,
            page_count=len(images),
            metadata=metadata
        )
    
    def _find_poppler_path(self) -> Optional[str]:
        """Находит путь к poppler (для Windows)"""
        import os
        if os.name == 'nt':  # Windows
            poppler_paths = [
                r'C:\poppler\Library\bin',
                r'C:\poppler\bin',
                r'C:\Program Files\poppler\bin',
            ]
            for path in poppler_paths:
                if Path(path).exists():
                    return path
        return None

