"""
Отладочный скрипт для проверки арабских PDF
"""
from pathlib import Path
from services.glossary_parser import GlossaryParser

def debug_arabic_pdf():
    parser = GlossaryParser()
    pdf_file = Path("glossary/arabic/Rocket arabic.pdf")
    
    if not pdf_file.exists():
        print(f"❌ Файл {pdf_file} не найден")
        return
    
    print(f"🔍 Анализ файла: {pdf_file.name}")
    print("=" * 60)
    
    # Проверяем извлечение текста
    try:
        # Пробуем извлечь текст напрямую
        import PyPDF2
        with open(pdf_file, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            print(f"📄 Количество страниц: {len(pdf_reader.pages)}")
            
            text = ""
            for i, page in enumerate(pdf_reader.pages[:3], 1):  # Первые 3 страницы
                page_text = page.extract_text()
                text += page_text + "\n"
                print(f"\nСтраница {i}:")
                print(f"  Длина текста: {len(page_text)} символов")
                if page_text:
                    print(f"  Первые 200 символов:")
                    print(f"  {repr(page_text[:200])}")
        
        print(f"\n📊 Общая длина текста: {len(text)} символов")
        
        if not text.strip() or len(text.strip()) < 50:
            print("\n⚠️  Текст не извлечен или слишком короткий - нужен OCR")
            print("   Пробуем OCR...")
            
            # Пробуем OCR
            ocr_text = parser._extract_text_with_ocr(pdf_file)
            if ocr_text:
                print(f"✅ OCR распознал {len(ocr_text)} символов")
                print(f"   Первые 500 символов:")
                print(f"   {ocr_text[:500]}")
            else:
                print("❌ OCR не смог распознать текст")
        else:
            print("\n✅ Текст извлечен, проверяем парсинг...")
            # Пробуем парсить
            terms = parser.parse_pdf_file(pdf_file)
            print(f"📝 Извлечено терминов: {len(terms)}")
            if terms:
                print("\nПримеры:")
                for i, (source, target) in enumerate(terms[:5], 1):
                    print(f"  {i}. {source} → {target}")
            else:
                print("\n⚠️  Термины не найдены. Возможные причины:")
                print("   - Неправильный формат разделителей")
                print("   - RTL текст требует специальной обработки")
                print("   - Текст не в формате 'термин – перевод'")
                
                # Показываем примеры строк
                print("\nПримеры строк из текста:")
                for line in text.split("\n")[:10]:
                    if line.strip():
                        print(f"  {repr(line[:100])}")
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_arabic_pdf()


