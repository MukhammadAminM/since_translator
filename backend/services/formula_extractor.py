"""
Модуль для автоматического выделения формул из текста
Заменяет формулы на маркеры формата <<<FORMULA_N>>>
"""
import re
import logging
from typing import List, Dict, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FormulaMarker:
    """Маркер формулы"""
    index: int
    original: str
    position: Tuple[int, int]  # (start, end) в исходном тексте


class FormulaExtractor:
    """
    Класс для автоматического выделения формул из текста
    
    Находит формулы при помощи регулярных выражений:
    - LaTeX выражения: $...$, $$...$$, \\(...\\), \\[...\\]
    - Строки с математическими символами: =, +, -, *, /, ^, _, {}, ()
    - Индексы и степени: x_1, y^2, A_{ij}
    """
    
    def __init__(self):
        """Инициализация с набором паттернов для поиска формул"""
        self.patterns = self._build_patterns()
        logger.info("FormulaExtractor инициализирован")
    
    def _build_patterns(self) -> List[Tuple[str, re.Pattern]]:
        """
        Строит список паттернов для поиска формул
        
        Returns:
            Список кортежей (название, regex_pattern)
        """
        patterns = []
        
        # 1. LaTeX display формулы: \[...\]
        patterns.append((
            "latex_display",
            re.compile(r'\\\[(.*?)\\\]', re.DOTALL)
        ))
        
        # 2. LaTeX inline формулы: \(...\)
        patterns.append((
            "latex_inline",
            re.compile(r'\\\((.*?)\\\)', re.DOTALL)
        ))
        
        # 3. Dollar формулы: $...$ и $$...$$
        patterns.append((
            "dollar_formula",
            re.compile(r'\$\$?(.*?)\$\$?', re.DOTALL)
        ))
        
        # 4. Строки с математическими выражениями (содержат =, +, -, *, /, ^, _)
        # Имеют ограничение по длине, чтобы не захватывать обычный текст
        patterns.append((
            "math_expression",
            re.compile(
                r'(?:^|\n)([^\n]{1,200}?[=+\-*/^_]\s*[^\n]{1,200}?)(?=\n|$)',
                re.MULTILINE
            )
        ))
        
        # 5. Индексы и степени: x_1, y^2, A_{ij}, B^{n+1}
        patterns.append((
            "subscript_superscript",
            re.compile(
                r'\b[a-zA-Zα-ωΑ-ΩΔ][_^]\{?[a-zA-Z0-9α-ωΑ-ΩΔ+\-]+\}?|'
                r'\b[a-zA-Zα-ωΑ-ΩΔ]\{?[a-zA-Z0-9α-ωΑ-ΩΔ+\-]+\}?[_^]\{?[a-zA-Z0-9α-ωΑ-ΩΔ+\-]+\}?',
                re.UNICODE
            )
        ))
        
        # 6. Греческие буквы в математическом контексте
        patterns.append((
            "greek_letters",
            re.compile(
                r'\b[αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ]\s*[=+\-*/^_]\s*[^\n]{1,100}',
                re.UNICODE
            )
        ))
        
        # 7. Дроби: a/b, (x+y)/(z-w)
        patterns.append((
            "fractions",
            re.compile(
                r'\([^)]{1,50}\)\s*/\s*\([^)]{1,50}\)|'
                r'[a-zA-Z0-9α-ωΑ-ΩΔ]+\s*/\s*[a-zA-Z0-9α-ωΑ-ΩΔ]+',
                re.UNICODE
            )
        ))
        
        # 8. Нумерованные формулы: (13.7), (13.8) и т.д.
        patterns.append((
            "numbered_formula",
            re.compile(
                r'\([0-9]+\.[0-9]+\)\s*[^\n]{1,200}?[=+\-*/^_]',
                re.MULTILINE
            )
        ))
        
        return patterns
    
    def extract(self, text: str) -> Tuple[str, Dict[int, str]]:
        """
        Извлекает формулы из текста и заменяет их на маркеры
        
        Args:
            text: Исходный текст
        
        Returns:
            Кортеж (текст_с_маркерами, словарь_формул)
            где словарь_формул: {индекс: оригинальная_формула}
        """
        formulas = {}
        formula_index = 0
        result_text = text
        
        logger.info("Начало извлечения формул из текста")
        
        # Собираем все найденные формулы с их позициями
        all_matches = []
        
        for pattern_name, pattern in self.patterns:
            for match in pattern.finditer(result_text):
                formula_text = match.group(0)
                start, end = match.span()
                
                # Проверяем, не является ли это частью уже найденной формулы
                is_overlap = any(
                    start < existing_end and end > existing_start
                    for existing_start, existing_end, _ in all_matches
                )
                
                if not is_overlap:
                    all_matches.append((start, end, formula_text))
                    logger.debug(f"Найдена формула ({pattern_name}): {formula_text[:50]}...")
        
        # Сортируем по позиции (с конца, чтобы не сбить индексы)
        all_matches.sort(key=lambda x: x[0], reverse=True)
        
        # Заменяем формулы на маркеры
        for start, end, formula_text in all_matches:
            # Проверяем, что формула не слишком короткая (не обычное слово)
            if len(formula_text.strip()) < 3:
                continue
            
            # Проверяем, что это действительно формула, а не обычный текст
            if not self._is_likely_formula(formula_text):
                continue
            
            marker = f"<<<FORMULA_{formula_index}>>>"
            formulas[formula_index] = formula_text
            result_text = result_text[:start] + marker + result_text[end:]
            formula_index += 1
        
        logger.info(f"Извлечено формул: {len(formulas)}")
        
        return result_text, formulas
    
    def _is_likely_formula(self, text: str) -> bool:
        """
        Проверяет, является ли текст формулой
        
        Args:
            text: Текст для проверки
        
        Returns:
            True если текст похож на формулу
        """
        text = text.strip()
        
        # Слишком короткий текст - не формула
        if len(text) < 3:
            return False
        
        # Если содержит LaTeX маркеры - точно формула
        if re.search(r'\\[\[\(]|\\[\]\)]|\$\$?', text):
            return True
        
        # Если содержит математические операторы и переменные
        has_math_ops = bool(re.search(r'[=+\-*/^_]', text))
        has_vars = bool(re.search(r'[a-zA-Zα-ωΑ-ΩΔ]', text))
        has_numbers = bool(re.search(r'\d', text))
        
        # Формула должна содержать хотя бы оператор и переменную/число
        if has_math_ops and (has_vars or has_numbers):
            # Но не должна быть слишком длинной (вероятно обычный текст)
            if len(text) > 300:
                return False
            return True
        
        # Индексы и степени - формула
        if re.search(r'[_^]\{?[a-zA-Z0-9]+\}?', text):
            return True
        
        return False
    
    def restore(self, text_with_markers: str, formulas: Dict[int, str]) -> str:
        """
        Восстанавливает формулы в текст по маркерам
        
        Args:
            text_with_markers: Текст с маркерами <<<FORMULA_N>>>
            formulas: Словарь формул {индекс: формула}
        
        Returns:
            Текст с восстановленными формулами
        """
        result = text_with_markers
        
        for index, formula in formulas.items():
            marker = f"<<<FORMULA_{index}>>>"
            result = result.replace(marker, formula)
        
        logger.debug(f"Восстановлено формул: {len(formulas)}")
        
        return result

