"""
Тестовый скрипт для проверки отображения LaTeX формул в DOCX
"""
import sys
from pathlib import Path

# Добавляем путь к backend
sys.path.insert(0, str(Path(__file__).parent))

from services.docx_generator import DocxGenerator
from services.latex_renderer import LaTeXRenderer


def test_latex_formula():
    """Тестирует отображение LaTeX формулы в DOCX"""
    
    print("🧪 Тест отображения LaTeX формулы в DOCX\n")
    
    # Тестовая формула
    test_formula = r"\[\Delta v = I_{sp} \cdot g_0 \cdot \ln\left(\frac{m_0}{m_f}\right)\]"
    
    print(f"Формула для теста: {test_formula}\n")
    
    # 1. Проверяем рендерер LaTeX
    print("1️⃣ Проверка LaTeX рендерера...")
    renderer = LaTeXRenderer()
    
    if renderer.available:
        print("   ✅ LaTeXRenderer доступен")
        
        # Пробуем отрендерить формулу
        image_buf = renderer.render_latex_to_image(test_formula)
        if image_buf:
            print("   ✅ Формула успешно отрендерена в изображение")
            print(f"   📊 Размер изображения: {len(image_buf.read())} байт")
            image_buf.seek(0)
        else:
            print("   ❌ Не удалось отрендерить формулу")
            return False
    else:
        print("   ⚠️  LaTeXRenderer недоступен (matplotlib не установлен)")
        print("   Установите: pip install matplotlib")
        return False
    
    # 2. Создаем тестовый DOCX с формулой
    print("\n2️⃣ Создание тестового DOCX файла...")
    
    test_text = f"""
This is a test document with a mathematical formula.

The Tsiolkovsky rocket equation is:

{test_formula}

Where:
- Δv is the change in velocity
- I_sp is the specific impulse
- g_0 is the standard gravity
- m_0 is the initial mass
- m_f is the final mass

This formula is essential for rocket propulsion calculations.
"""
    
    generator = DocxGenerator(output_dir="outputs")
    
    try:
        filename = generator.create_docx(
            translated_text=test_text,
            source_lang="zh",
            model="engineering",
            original_filename="test_formula.pdf"
        )
        
        print(f"   ✅ DOCX файл создан: {filename}")
        print(f"   📁 Путь: outputs/{filename}")
        print("\n3️⃣ Откройте файл в Microsoft Word или LibreOffice Writer")
        print("   и проверьте, что формула отображается правильно!")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка при создании DOCX: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_latex_formula()
    if success:
        print("\n✅ Тест завершен успешно!")
    else:
        print("\n❌ Тест завершен с ошибками")
        sys.exit(1)

