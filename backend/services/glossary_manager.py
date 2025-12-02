"""
Менеджер для работы с глоссарием в процессе перевода
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Literal


class GlossaryManager:
    """
    Управляет загрузкой и использованием глоссария при переводе
    """
    
    def __init__(self, glossary_dir: Optional[str] = None):
        # Определяем путь к глоссарию относительно текущего файла
        if glossary_dir is None:
            # Путь относительно backend/services/glossary_manager.py -> backend/glossary/
            current_file = Path(__file__)
            backend_dir = current_file.parent.parent
            self.glossary_dir = backend_dir / "glossary"
        else:
            self.glossary_dir = Path(glossary_dir)
        self.glossaries: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._load_all_glossaries()
    
    def _load_all_glossaries(self):
        """
        Загружает все доступные глоссарии
        """
        lang_map = {
            "ru": "russian",
            "ar": "arabic",
            "zh": "chinise"
        }
        
        for lang_code, lang_name in lang_map.items():
            json_path = self.glossary_dir / f"glossary_{lang_name}_to_en.json"
            
            if json_path.exists():
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        self.glossaries[lang_code] = json.load(f)
                    print(f"✅ Загружен глоссарий для {lang_code}: {len(self.glossaries[lang_code])} терминов")
                except Exception as e:
                    print(f"❌ Ошибка при загрузке глоссария для {lang_code}: {str(e)}")
            else:
                print(f"⚠️  Глоссарий для {lang_code} не найден: {json_path}")
    
    def get_glossary_for_lang(
        self, 
        source_lang: Literal["ru", "ar", "zh"]
    ) -> Dict[str, Dict[str, str]]:
        """
        Возвращает глоссарий для указанного языка
        """
        return self.glossaries.get(source_lang, {})
    
    def format_glossary_for_prompt(
        self, 
        source_lang: Literal["ru", "ar", "zh"],
        max_terms: int = 100
    ) -> str:
        """
        Форматирует глоссарий для использования в промпте AI
        
        Args:
            source_lang: Исходный язык
            max_terms: Максимальное количество терминов для включения в промпт
        
        Returns:
            Отформатированная строка с терминами глоссария
        """
        glossary = self.get_glossary_for_lang(source_lang)
        
        if not glossary:
            return ""
        
        # Ограничиваем количество терминов для промпта
        terms_list = list(glossary.items())[:max_terms]
        
        lines = ["GLOSSARY (use these exact translations):"]
        lines.append("-" * 50)
        
        for key, term_data in terms_list:
            source = term_data.get("source", "")
            target = term_data.get("target", "")
            source_abbr = term_data.get("source_abbr")
            target_abbr = term_data.get("target_abbr")
            
            line = f"{source} → {target}"
            
            if source_abbr and target_abbr:
                line += f" ({source_abbr} → {target_abbr})"
            elif source_abbr:
                line += f" (abbr: {source_abbr})"
            
            lines.append(line)
        
        if len(glossary) > max_terms:
            lines.append(f"\n... and {len(glossary) - max_terms} more terms")
        
        return "\n".join(lines)
    
    def find_term_in_text(
        self,
        text: str,
        source_lang: Literal["ru", "ar", "zh"]
    ) -> List[Dict[str, str]]:
        """
        Находит термины из глоссария в тексте
        
        Returns:
            Список найденных терминов с их переводами
        """
        glossary = self.get_glossary_for_lang(source_lang)
        found_terms = []
        
        text_lower = text.lower()
        
        for key, term_data in glossary.items():
            source_term = term_data.get("source", "")
            source_lower = source_term.lower()
            
            # Ищем точное совпадение или как часть слова
            if source_lower in text_lower:
                found_terms.append({
                    "source": source_term,
                    "target": term_data.get("target", ""),
                    "source_abbr": term_data.get("source_abbr"),
                    "target_abbr": term_data.get("target_abbr")
                })
        
        return found_terms
    
    def get_glossary_summary(
        self, 
        source_lang: Literal["ru", "ar", "zh"],
        text: Optional[str] = None,
        max_terms: int = 200
    ) -> str:
        """
        Возвращает краткую сводку глоссария для промпта
        
        Args:
            source_lang: Исходный язык
            text: Текст для перевода (если указан, будут выбраны релевантные термины)
            max_terms: Максимальное количество терминов для включения
        """
        glossary = self.get_glossary_for_lang(source_lang)
        
        if not glossary:
            return ""
        
        # Если указан текст, находим релевантные термины
        if text:
            relevant_terms = self._find_relevant_terms(text, source_lang, max_terms)
            if relevant_terms:
                summary = f"IMPORTANT: Use these exact translations from the glossary when these terms appear in the text:\n\n"
                for term_data in relevant_terms:
                    source = term_data.get("source", "").strip()
                    target = term_data.get("target", "").strip()
                    
                    # Пропускаем пустые термины
                    if not source or not target:
                        continue
                    
                    source_abbr = term_data.get("source_abbr")
                    target_abbr = term_data.get("target_abbr")
                    
                    if source_abbr:
                        summary += f"- {source} ({source_abbr}) = {target}"
                        if target_abbr:
                            summary += f" ({target_abbr})"
                        summary += "\n"
                    else:
                        summary += f"- {source} = {target}\n"
                
                # Добавляем информацию о полном глоссарии
                if len(glossary) > len(relevant_terms):
                    summary += f"\nNote: The full glossary contains {len(glossary)} terms. "
                    summary += "Always use exact translations from the glossary for any matching terms."
                
                return summary
        
        # Если текст не указан, берем первые термины как примеры
        sample_terms = list(glossary.items())[:max_terms]
        
        summary = f"GLOSSARY ({len(glossary)} terms total). "
        summary += "When translating, use these EXACT translations:\n\n"
        
        for key, term_data in sample_terms:
            source = term_data.get("source", "")
            target = term_data.get("target", "")
            source_abbr = term_data.get("source_abbr")
            target_abbr = term_data.get("target_abbr")
            
            if source_abbr:
                summary += f"- {source} ({source_abbr}) = {target}"
                if target_abbr:
                    summary += f" ({target_abbr})"
                summary += "\n"
            else:
                summary += f"- {source} = {target}\n"
        
        if len(glossary) > max_terms:
            summary += f"\n... and {len(glossary) - max_terms} more terms. "
            summary += "Always use exact translations from the glossary when terms appear in the text."
        
        return summary
    
    def _find_relevant_terms(
        self,
        text: str,
        source_lang: Literal["ru", "ar", "zh"],
        max_terms: int = 200
    ) -> List[Dict[str, str]]:
        """
        Находит релевантные термины из глоссария, которые встречаются в тексте
        """
        glossary = self.get_glossary_for_lang(source_lang)
        if not glossary:
            return []
        
        text_lower = text.lower()
        found_terms = []
        
        # Ищем термины в тексте
        for key, term_data in glossary.items():
            source_term = term_data.get("source", "")
            source_abbr = term_data.get("source_abbr")
            
            if not source_term:
                continue
            
            source_lower = source_term.lower()
            
            # Пропускаем пустые термины
            if not source_term.strip():
                continue
            
            # Проверяем точное совпадение или как отдельное слово
            # Используем word boundaries для более точного поиска
            import re
            pattern = r'\b' + re.escape(source_lower) + r'\b'
            if re.search(pattern, text_lower):
                # Проверяем, что термин еще не добавлен (избегаем дубликатов)
                if not any(t.get("source") == source_term for t in found_terms):
                    found_terms.append(term_data)
            # Также проверяем аббревиатуру
            elif source_abbr and source_abbr.strip():
                abbr_lower = source_abbr.lower()
                if abbr_lower in text_lower:
                    # Проверяем, что термин еще не добавлен
                    if not any(t.get("source") == source_term for t in found_terms):
                        found_terms.append(term_data)
            
            # Ограничиваем количество найденных терминов
            if len(found_terms) >= max_terms:
                break
        
        return found_terms


