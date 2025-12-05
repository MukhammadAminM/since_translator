"""
Сервис для рендеринга LaTeX формул в изображения для вставки в DOCX
"""
import os
import io
from pathlib import Path
from typing import Optional
import re

try:
    import matplotlib
    matplotlib.use('Agg')  # Используем backend без GUI
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class LaTeXRenderer:
    """
    Рендерит LaTeX формулы в изображения для вставки в DOCX
    """
    
    def __init__(self):
        self.available = MATPLOTLIB_AVAILABLE
        if not self.available:
            print("⚠️  matplotlib не установлен. Установите: pip install matplotlib")
        else:
            # Настраиваем LaTeX рендеринг
            plt.rcParams['text.usetex'] = False  # Используем mathtext вместо LaTeX (быстрее)
            plt.rcParams['mathtext.fontset'] = 'cm'  # Computer Modern для математики
            plt.rcParams['font.size'] = 14
            print("✅ LaTeXRenderer инициализирован")
    
    def render_latex_to_image(self, latex_formula: str, dpi: int = 150) -> Optional[io.BytesIO]:
        """
        Рендерит LaTeX формулу в изображение
        
        Args:
            latex_formula: LaTeX формула (без \[ и \])
            dpi: Разрешение изображения
        
        Returns:
            BytesIO объект с PNG изображением или None в случае ошибки
        """
        if not self.available:
            return None
        
        try:
            # Очищаем формулу от \[ и \]
            formula = latex_formula.strip()
            if formula.startswith('\\[') and formula.endswith('\\]'):
                formula = formula[2:-2].strip()
            elif formula.startswith('\\(') and formula.endswith('\\)'):
                formula = formula[2:-2].strip()
            
            # Проверяем, содержит ли формула сложные LaTeX команды, которые не поддерживаются mathtext
            # mathtext не поддерживает: \begin, \end, \array, \matrix, \cases, \align, \split и т.д.
            unsupported_commands = [
                r'\\begin\{', r'\\end\{', r'\\array', r'\\matrix', r'\\cases',
                r'\\align', r'\\split', r'\\eqnarray', r'\\gather', r'\\multline',
                r'\\flalign', r'\\alignat', r'\\xrightarrow', r'\\xleftarrow'
            ]
            
            has_unsupported = any(re.search(cmd, formula) for cmd in unsupported_commands)
            
            if has_unsupported:
                # Пытаемся упростить формулу для mathtext
                # Удаляем \begin{array}...\end{array} и оставляем только содержимое
                simplified = self._simplify_complex_latex(formula)
                if simplified and simplified != formula:
                    formula = simplified
                else:
                    # Если не удалось упростить, возвращаем None - формула будет показана как текст
                    print(f"   ⚠️  Формула содержит неподдерживаемые команды, пропускаем рендеринг")
                    return None
            
            # Создаем фигуру
            fig, ax = plt.subplots(figsize=(10, 2))
            ax.axis('off')
            
            # Рендерим формулу
            ax.text(0.5, 0.5, f'${formula}$', 
                   fontsize=16, 
                   ha='center', 
                   va='center',
                   transform=ax.transAxes)
            
            # Сохраняем в BytesIO
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', 
                       pad_inches=0.2, transparent=True)
            buf.seek(0)
            
            plt.close(fig)
            
            return buf
            
        except Exception as e:
            print(f"   ❌ Ошибка при рендеринге LaTeX '{latex_formula[:50]}...': {str(e)}")
            plt.close('all')
            return None
    
    def _simplify_complex_latex(self, formula: str) -> str:
        """
        Упрощает сложные LaTeX формулы для mathtext
        Пытается извлечь основное содержимое из \begin{array}...\end{array} и подобных структур
        """
        try:
            # Упрощаем \begin{array}...\end{array}
            # Извлекаем содержимое между \begin{array} и \end{array}
            array_pattern = r'\\begin\{array\}[^}]*\}(.*?)\\end\{array\}'
            match = re.search(array_pattern, formula, re.DOTALL)
            if match:
                content = match.group(1)
                # Убираем & и \\, заменяем на пробелы и запятые
                content = re.sub(r'&', ', ', content)
                content = re.sub(r'\\\\', '; ', content)
                # Убираем лишние пробелы
                content = re.sub(r'\s+', ' ', content).strip()
                return content
            
            # Упрощаем другие структуры
            # Удаляем \begin{...} и \end{...}
            formula = re.sub(r'\\begin\{[^}]+\}', '', formula)
            formula = re.sub(r'\\end\{[^}]+\}', '', formula)
            
            # Заменяем & на запятые
            formula = re.sub(r'&', ', ', formula)
            # Заменяем \\ на точки с запятой
            formula = re.sub(r'\\\\', '; ', formula)
            
            # Убираем лишние пробелы
            formula = re.sub(r'\s+', ' ', formula).strip()
            
            return formula
            
        except Exception as e:
            print(f"   ⚠️  Ошибка при упрощении LaTeX: {str(e)}")
            return formula
    
    def render_latex_to_file(self, latex_formula: str, output_path: Path, dpi: int = 150) -> bool:
        """
        Рендерит LaTeX формулу в файл изображения
        
        Args:
            latex_formula: LaTeX формула
            output_path: Путь для сохранения изображения
            dpi: Разрешение изображения
        
        Returns:
            True если успешно, False в случае ошибки
        """
        buf = self.render_latex_to_image(latex_formula, dpi)
        if buf is None:
            return False
        
        try:
            with open(output_path, 'wb') as f:
                f.write(buf.read())
            return True
        except Exception as e:
            print(f"   ❌ Ошибка при сохранении изображения: {str(e)}")
            return False

