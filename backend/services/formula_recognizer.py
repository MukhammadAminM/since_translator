"""
Модуль для распознавания формул через Mathpix API
Поддерживает retry/backoff, MathML и обработку ошибок
"""
import os
import base64
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

import requests
from PIL import Image
import io

logger = logging.getLogger(__name__)


class FormulaFormat(Enum):
    """Форматы формул"""
    LATEX = "latex"
    LATEX_SIMPLIFIED = "latex_simplified"
    MATHML = "mathml"
    TEXT = "text"


@dataclass
class RecognizedFormula:
    """Распознанная формула"""
    latex: Optional[str] = None
    latex_simplified: Optional[str] = None
    mathml: Optional[str] = None
    text: Optional[str] = None
    confidence: Optional[float] = None
    is_graph: bool = False  # Является ли это графиком/диаграммой


class FormulaRecognizer:
    """
    Класс для распознавания формул через Mathpix API
    
    Особенности:
    - Retry с exponential backoff
    - Поддержка LaTeX и MathML
    - Обработка графиков и диаграмм
    - Кэширование результатов
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        timeout: int = 30
    ):
        """
        Args:
            max_retries: Максимальное количество попыток
            backoff_factor: Множитель для exponential backoff
            timeout: Таймаут запроса в секундах
        """
        self.app_id = os.getenv("MATHPIX_APP_ID")
        self.app_key = os.getenv("MATHPIX_APP_KEY")
        self.api_url = "https://api.mathpix.com/v3/text"
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        
        self.available = bool(self.app_id and self.app_key)
        
        if not self.available:
            logger.warning("Mathpix API не настроен. Установите MATHPIX_APP_ID и MATHPIX_APP_KEY в .env")
        else:
            logger.info("FormulaRecognizer инициализирован")
    
    def recognize(
        self,
        image: Image.Image,
        include_mathml: bool = True,
        include_text: bool = True
    ) -> Optional[RecognizedFormula]:
        """
        Распознает формулу из изображения
        
        Args:
            image: PIL Image объект
            include_mathml: Включать ли MathML в ответ
            include_text: Включать ли текстовое представление
        
        Returns:
            RecognizedFormula или None в случае ошибки
        """
        if not self.available:
            logger.warning("Mathpix API недоступен")
            return None
        
        # Конвертируем изображение в base64
        try:
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            logger.error(f"Ошибка при конвертации изображения: {e}")
            return None
        
        # Подготавливаем запрос
        headers = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "Content-type": "application/json"
        }
        
        formats = ["latex_simplified", "latex"]
        if include_mathml:
            formats.append("mathml")
        if include_text:
            formats.append("text")
        
        data = {
            "src": f"data:image/png;base64,{image_base64}",
            "formats": formats,
            "ocr": ["math"],  # Распознавать только математику
            "data_options": {
                "include_asciimath": False,
                "include_latex": True
            }
        }
        
        # Выполняем запрос с retry
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    json=data,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return self._parse_response(response.json())
                elif response.status_code == 429:  # Rate limit
                    retry_after = int(response.headers.get("Retry-After", self.backoff_factor * (2 ** attempt)))
                    logger.warning(f"Rate limit. Повтор через {retry_after} секунд")
                    time.sleep(retry_after)
                    continue
                else:
                    error_msg = f"Mathpix API ошибка {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    if attempt < self.max_retries - 1:
                        wait_time = self.backoff_factor * (2 ** attempt)
                        logger.info(f"Повтор через {wait_time} секунд...")
                        time.sleep(wait_time)
                    else:
                        return None
                        
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout при запросе к Mathpix (попытка {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_factor * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    return None
            except Exception as e:
                logger.error(f"Ошибка при запросе к Mathpix: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_factor * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    return None
        
        return None
    
    def _parse_response(self, response_data: Dict[str, Any]) -> RecognizedFormula:
        """
        Парсит ответ от Mathpix API
        
        Args:
            response_data: JSON ответ от API
        
        Returns:
            RecognizedFormula объект
        """
        latex = response_data.get("latex") or response_data.get("latex_styled")
        latex_simplified = response_data.get("latex_simplified")
        mathml = response_data.get("mathml")
        text = response_data.get("text", "")
        
        # Обрабатываем confidence - может быть словарем или числом
        confidence = None
        confidence_data = response_data.get("confidence")
        if isinstance(confidence_data, dict):
            confidence = confidence_data.get("overall")
        elif isinstance(confidence_data, (int, float)):
            confidence = confidence_data
        
        # Проверяем, является ли это графиком
        # Если текст длинный и содержит много слов - вероятно график
        is_graph = len(text) > 100 and text.count(" ") > 10
        
        # Очищаем LaTeX от маркеров, если есть
        if latex:
            latex = self._clean_latex(latex)
        if latex_simplified:
            latex_simplified = self._clean_latex(latex_simplified)
        
        return RecognizedFormula(
            latex=latex,
            latex_simplified=latex_simplified,
            mathml=mathml,
            text=text,
            confidence=confidence,
            is_graph=is_graph
        )
    
    def _clean_latex(self, latex: str) -> str:
        """
        Очищает LaTeX от лишних маркеров и форматирования
        
        Args:
            latex: LaTeX строка
        
        Returns:
            Очищенная LaTeX строка
        """
        import re
        
        latex = latex.strip()
        
        # Убираем лишние пробелы
        latex = re.sub(r'\s+', ' ', latex)
        
        # Если уже в правильном формате, возвращаем как есть
        if latex.startswith('\\[') and latex.endswith('\\]'):
            return latex
        if latex.startswith('\\(') and latex.endswith('\\)'):
            return latex
        if latex.startswith('$') and latex.endswith('$'):
            # Конвертируем $...$ в \[...\]
            latex = latex.strip('$')
            return f"\\[{latex}\\]"
        
        # Если нет маркеров, добавляем \[...\]
        if not (latex.startswith('\\[') or latex.startswith('\\(') or latex.startswith('$')):
            return f"\\[{latex}\\]"
        
        return latex
    
    def recognize_from_file(self, image_path: Path, **kwargs) -> Optional[RecognizedFormula]:
        """
        Распознает формулу из файла изображения
        
        Args:
            image_path: Путь к файлу изображения
            **kwargs: Дополнительные аргументы для recognize()
        
        Returns:
            RecognizedFormula или None
        """
        try:
            image = Image.open(image_path)
            return self.recognize(image, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка при открытии изображения {image_path}: {e}")
            return None
    
    def recognize_batch(
        self,
        images: List[Image.Image],
        include_mathml: bool = True,
        include_text: bool = True
    ) -> List[Optional[RecognizedFormula]]:
        """
        Распознает формулы из списка изображений
        
        Args:
            images: Список PIL Image объектов
            include_mathml: Включать ли MathML
            include_text: Включать ли текстовое представление
        
        Returns:
            Список RecognizedFormula или None
        """
        results = []
        for i, image in enumerate(images):
            logger.debug(f"Распознавание формулы {i + 1}/{len(images)}")
            result = self.recognize(image, include_mathml, include_text)
            results.append(result)
            # Небольшая задержка между запросами, чтобы не превысить rate limit
            if i < len(images) - 1:
                time.sleep(0.5)
        return results

