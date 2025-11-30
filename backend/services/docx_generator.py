from pathlib import Path
from datetime import datetime
from typing import Literal, Optional
import uuid

try:
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class DocxGenerator:
    """
    Сервис для генерации .docx файлов с переведенным текстом
    """
    
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def create_docx(
        self,
        translated_text: str,
        source_lang: Literal["ru", "ar", "zh"],
        model: Literal["general", "engineering", "academic", "scientific"],
        original_filename: Optional[str] = None
    ) -> str:
        """
        Создает .docx файл с переведенным текстом
        
        Returns:
            Имя созданного файла
        """
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx не установлен. Установите: pip install python-docx")
        
        # Создаем новый документ
        doc = Document()
        
        # Настройка стилей
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Calibri'
        font.size = Pt(11)
        
        # Заголовок
        title = doc.add_heading('Translation Result', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Метаинформация
        meta_para = doc.add_paragraph()
        meta_para.add_run(f"Source Language: {source_lang.upper()}").bold = True
        meta_para.add_run(f"\nTarget Language: EN")
        meta_para.add_run(f"\nTranslation Model: {model.upper()}")
        meta_para.add_run(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if original_filename:
            meta_para.add_run(f"\nOriginal File: {original_filename}")
        
        # Разделитель
        doc.add_paragraph("─" * 50)
        
        # Основной текст перевода
        doc.add_heading('Translated Text', level=1)
        translated_para = doc.add_paragraph(translated_text)
        
        # Сохраняем файл
        filename = self._generate_filename(source_lang, model, original_filename)
        filepath = self.output_dir / filename
        doc.save(str(filepath))
        
        return filename
    
    def _generate_filename(
        self,
        source_lang: str,
        model: str,
        original_filename: Optional[str] = None
    ) -> str:
        """
        Генерирует уникальное имя файла
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        
        if original_filename:
            base_name = Path(original_filename).stem
            return f"{base_name}_translated_{timestamp}_{unique_id}.docx"
        else:
            return f"translation_{source_lang}_to_en_{model}_{timestamp}_{unique_id}.docx"

