"""
Тестовый скрипт для проверки извлечения текста из арабских PDF
"""
from pathlib import Path
from services.glossary_parser import GlossaryParser

def test_arabic_pdf():
    parser = GlossaryParser()
    arabic_dir = Path("glossary/arabic")
    
    if not arabic_dir.exists():
        print(f"❌ Папка {arabic_dir} не найдена")
        return
    
    print("🔍 Тестирование извлечения текста из арабских PDF...")
    print("=" * 60)
    
    for pdf_file in arabic_dir.glob("*.pdf"):
        print(f"\n📄 Файл: {pdf_file.name}")
        print("-" * 60)
        
        try:
            terms = parser.parse_pdf_file(pdf_file)
            print(f"✅ Извлечено терминов: {len(terms)}")
            
            if terms:
                print("\nПримеры терминов:")
                for i, (source, target) in enumerate(terms[:5], 1):
                    print(f"  {i}. {source[:50]} → {target[:50]}")
        except Exception as e:
            print(f"❌ Ошибка: {str(e)}")

if __name__ == "__main__":
    test_arabic_pdf()



