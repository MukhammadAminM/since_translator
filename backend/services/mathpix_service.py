"""
Сервис для распознавания математических формул из изображений с помощью Mathpix API
"""
import os
import base64
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
import io


class MathpixService:
    """
    Сервис для работы с Mathpix API для распознавания математических формул
    """
    
    def __init__(self):
        self.app_id = os.getenv("MATHPIX_APP_ID")
        self.app_key = os.getenv("MATHPIX_APP_KEY")
        self.api_url = "https://api.mathpix.com/v3/text"
        self.available = self.app_id and self.app_key
        
        if not self.available:
            print("⚠️  Mathpix API не настроен. Установите MATHPIX_APP_ID и MATHPIX_APP_KEY в .env")
        else:
            print("✅ Mathpix API настроен")
    
    def recognize_formula_from_image(self, image: Image.Image) -> Optional[str]:
        """
        Распознает математическую формулу из изображения
        
        Args:
            image: PIL Image объект
        
        Returns:
            LaTeX строка с формулой или None в случае ошибки
        """
        if not self.available:
            return None
        
        try:
            # Конвертируем изображение в base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Подготавливаем запрос
            headers = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "Content-type": "application/json"
            }
            
            data = {
                "src": f"data:image/png;base64,{image_base64}",
                "formats": ["latex_styled", "latex"],  # Пробуем оба формата
                "ocr": ["math"]  # Распознавать только математику
            }
            
            # Отправляем запрос
            response = requests.post(self.api_url, json=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                # Пробуем получить LaTeX формулу
                latex = result.get("latex_styled") or result.get("latex") or result.get("text", "")
                if latex:
                    latex = latex.strip()
                    # Если результат начинается с LaTeX маркеров, возвращаем как есть
                    if latex.startswith('$') or latex.startswith('\\[') or latex.startswith('\\('):
                        return latex
                    # Если результат содержит LaTeX формулы, извлекаем их
                    import re
                    math_patterns = [
                        r'\\\[.*?\\\]',  # Display формулы \[...\]
                        r'\\\(.*?\\\)',  # Inline формулы \(...\)
                        r'\$.*?\$',      # Dollar формулы $...$
                    ]
                    for pattern in math_patterns:
                        matches = re.findall(pattern, latex, re.DOTALL)
                        if matches:
                            # Возвращаем первую найденную формулу
                            formula = matches[0]
                            # Если формула уже в правильном формате, возвращаем как есть
                            if formula.startswith('\\[') or formula.startswith('\\(') or formula.startswith('$'):
                                return formula
                            # Иначе оборачиваем в \[...\]
                            return f"\\[{formula.strip('$\\[\\]()')}\\]"
                    
                    # Если не нашли LaTeX маркеры, но текст короткий и похож на формулу
                    if len(latex) < 300:
                        # Проверяем, содержит ли математические элементы
                        if re.search(r'[=+\-*/\\Δαβγδεζηθικλμνξοπρστυφχψω]', latex) or \
                           re.search(r'\b(Isp|g0|m0|mf|Δv|ln|log|exp)\b', latex, re.IGNORECASE):
                            # Очищаем от лишних пробелов
                            latex = re.sub(r'\s+', ' ', latex.strip())
                            # Убираем уже существующие маркеры, если есть
                            latex = latex.strip('$\\[\\]()')
                            # Оборачиваем в LaTeX display формат
                            return f"\\[{latex}\\]"
                    
                    # Если результат слишком длинный, вероятно это весь текст страницы
                    if len(latex) > 500:
                        print(f"   ⚠️  Mathpix вернул слишком длинный результат ({len(latex)} символов), вероятно весь текст")
                        return None
                    
                    # Очищаем от лишних пробелов перед возвратом
                    latex = re.sub(r'\s+', ' ', latex.strip())
                    return latex
                else:
                    print(f"   ⚠️  Mathpix вернул пустой результат: {result}")
                    return None
            else:
                error_msg = f"Mathpix API ошибка {response.status_code}: {response.text}"
                print(f"   ❌ {error_msg}")
                return None
                
        except requests.exceptions.Timeout:
            print("   ⚠️  Mathpix API timeout")
            return None
        except Exception as e:
            print(f"   ❌ Ошибка Mathpix API: {str(e)}")
            return None
    
    def recognize_formula_from_file(self, image_path: Path) -> Optional[str]:
        """
        Распознает математическую формулу из файла изображения
        
        Args:
            image_path: Путь к файлу изображения
        
        Returns:
            LaTeX строка с формулой или None в случае ошибки
        """
        try:
            image = Image.open(image_path)
            return self.recognize_formula_from_image(image)
        except Exception as e:
            print(f"   ❌ Ошибка при открытии изображения {image_path}: {str(e)}")
            return None
    
    def detect_formula_regions(self, image: Image.Image) -> list[tuple[int, int, int, int]]:
        """
        Обнаруживает области с формулами на изображении
        Использует простую эвристику: ищем области с высокой плотностью математических символов
        
        Args:
            image: PIL Image объект
        
        Returns:
            Список координат (x, y, width, height) областей с формулами
        """
        # Это упрощенная версия - в реальности можно использовать более сложные алгоритмы
        # или API Mathpix для обнаружения формул
        # Пока возвращаем весь изображение как одну область
        return [(0, 0, image.width, image.height)]

