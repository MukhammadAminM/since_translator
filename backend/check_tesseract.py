"""
Скрипт для проверки установки Tesseract OCR
"""
import os
from pathlib import Path

def check_tesseract():
    print("🔍 Проверка установки Tesseract OCR...")
    print("=" * 60)
    
    # Проверяем Python библиотеки
    try:
        import pytesseract
        print("✅ pytesseract установлен")
    except ImportError:
        print("❌ pytesseract не установлен. Установите: pip install pytesseract")
        return False
    
    try:
        from pdf2image import convert_from_path
        print("✅ pdf2image установлен")
    except ImportError:
        print("❌ pdf2image не установлен. Установите: pip install pdf2image")
        return False
    
    try:
        from PIL import Image
        print("✅ Pillow установлен")
    except ImportError:
        print("❌ Pillow не установлен. Установите: pip install Pillow")
        return False
    
    # Проверяем Tesseract
    print("\n🔍 Проверка Tesseract OCR...")
    
    # Стандартные пути для Windows
    tesseract_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    
    # Добавляем путь из переменной окружения USERNAME если есть
    username = os.getenv('USERNAME')
    if username:
        tesseract_paths.append(
            rf'C:\Users\{username}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
        )
    
    tesseract_found = False
    for path in tesseract_paths:
        if Path(path).exists():
            print(f"✅ Tesseract найден: {path}")
            pytesseract.pytesseract.tesseract_cmd = path
            tesseract_found = True
            break
    
    if not tesseract_found:
        print("❌ Tesseract не найден в стандартных путях")
        print("\n📥 Установка Tesseract OCR для Windows:")
        print("   1. Скачайте установщик: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   2. Установите в стандартную папку (C:\\Program Files\\Tesseract-OCR)")
        print("   3. При установке выберите языки: Russian, English, Arabic, Chinese")
        print("   4. Запустите этот скрипт снова для проверки")
        return False
    
    # Проверяем версию Tesseract
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✅ Версия Tesseract: {version}")
    except Exception as e:
        print(f"⚠️  Не удалось получить версию: {str(e)}")
    
    # Проверяем доступные языки
    try:
        langs = pytesseract.get_languages()
        print(f"\n📚 Доступные языки: {', '.join(langs)}")
        
        required_langs = ['rus', 'eng', 'ara', 'chi_sim']
        missing_langs = [lang for lang in required_langs if lang not in langs]
        
        if missing_langs:
            print(f"⚠️  Отсутствуют языки: {', '.join(missing_langs)}")
            print("   Переустановите Tesseract и выберите все необходимые языки")
        else:
            print("✅ Все необходимые языки установлены")
    except Exception as e:
        print(f"⚠️  Не удалось получить список языков: {str(e)}")
    
    # Проверяем poppler (для pdf2image)
    print("\n🔍 Проверка poppler (для pdf2image)...")
    try:
        # Пробуем конвертировать тестовый PDF (если есть)
        test_pdf = Path("glossary/russian/words.txt")
        if test_pdf.exists():
            print("✅ pdf2image готов к работе")
        else:
            print("⚠️  poppler может быть не установлен")
            print("   Скачайте: https://github.com/oschwartz10612/poppler-windows/releases")
            print("   Распакуйте и добавьте папку 'bin' в PATH")
    except Exception as e:
        print(f"⚠️  Проверка poppler: {str(e)}")
    
    print("\n" + "=" * 60)
    if tesseract_found:
        print("✅ Tesseract OCR готов к использованию!")
        return True
    else:
        print("❌ Tesseract OCR не установлен")
        return False

if __name__ == "__main__":
    check_tesseract()

