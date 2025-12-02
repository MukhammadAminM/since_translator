"""Найти термины, которые могут быть одинаковыми, но записаны по-разному"""
import json
import re
from collections import defaultdict

# Загружаем глоссарий
with open('glossary/glossary_russian_to_en.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Нормализуем source для поиска похожих
def normalize_term(term):
    """Нормализует термин для сравнения"""
    if not term:
        return ""
    # Убираем знаки препинания, пробелы, приводим к нижнему регистру
    normalized = re.sub(r'[=:;,\s]+', '', term.lower())
    return normalized

# Группируем по нормализованному source
normalized_groups = defaultdict(list)
for key, value in data.items():
    source = value.get('source', '').strip()
    if source:
        norm = normalize_term(source)
        if norm:  # Пропускаем пустые
            normalized_groups[norm].append((key, source, value.get('target', '')))

# Находим группы с несколькими вариантами
similar_groups = {k: v for k, v in normalized_groups.items() if len(v) > 1}

print(f"Найдено групп похожих терминов: {len(similar_groups)}")
print("\nГруппы похожих терминов (возможные дубликаты или варианты написания):\n")

for norm, entries in sorted(similar_groups.items(), key=lambda x: len(x[1]), reverse=True):
    if len(entries) > 1:
        # Проверяем, есть ли разные переводы
        targets = [entry[2] for entry in entries]
        unique_targets = set(targets)
        
        if len(unique_targets) > 1:
            print(f"⚠️  '{norm}' ({len(entries)} варианта) - РАЗНЫЕ ПЕРЕВОДЫ:")
            for key, source, target in entries:
                print(f"     '{source}' -> '{target}' (ключ: '{key}')")
            print()
        else:
            print(f"ℹ️  '{norm}' ({len(entries)} варианта) - одинаковый перевод:")
            for key, source, target in entries[:3]:  # Показываем первые 3
                print(f"     '{source}' -> '{target}' (ключ: '{key}')")
            if len(entries) > 3:
                print(f"     ... и еще {len(entries) - 3} варианта")
            print()

