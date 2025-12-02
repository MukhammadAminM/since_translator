"""Проверка глоссария на неточности, дубликаты и несоответствия"""
import json
from collections import defaultdict

# Загружаем глоссарий
with open('glossary/glossary_russian_to_en.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 60)
print("Анализ глоссария на неточности")
print("=" * 60)

# 1. Проверка дубликатов по source (одинаковые термины с разными переводами)
source_to_entries = defaultdict(list)
for key, value in data.items():
    source = value.get('source', '').strip()
    if source:
        source_to_entries[source].append((key, value))

duplicates = {k: v for k, v in source_to_entries.items() if len(v) > 1}

print(f"\n1. Дубликаты терминов (одинаковый source, разные записи): {len(duplicates)}")
if duplicates:
    print("\nПримеры дубликатов:")
    for i, (source, entries) in enumerate(list(duplicates.items())[:10], 1):
        print(f"\n  {i}. '{source}' встречается {len(entries)} раз:")
        for key, value in entries:
            target = value.get('target', '')
            print(f"     - ключ: '{key}' -> '{target}'")

# 2. Проверка одинаковых source с разными переводами
conflicts = []
for source, entries in source_to_entries.items():
    if len(entries) > 1:
        targets = [entry[1].get('target', '').strip() for entry in entries]
        # Проверяем, есть ли разные переводы
        unique_targets = set(targets)
        if len(unique_targets) > 1:
            conflicts.append((source, entries))

print(f"\n2. Конфликты (одинаковый source, разные переводы): {len(conflicts)}")
if conflicts:
    print("\nПримеры конфликтов:")
    for i, (source, entries) in enumerate(conflicts[:10], 1):
        print(f"\n  {i}. '{source}':")
        for key, value in entries:
            target = value.get('target', '')
            print(f"     - '{target}' (ключ: '{key}')")

# 3. Проверка на пустые или подозрительные переводы
empty_targets = []
suspicious = []
for key, value in data.items():
    target = value.get('target', '').strip()
    source = value.get('source', '').strip()
    
    if not target:
        empty_targets.append((key, source))
    elif len(target) < 2:  # Слишком короткий перевод
        suspicious.append((key, source, target))
    elif target.lower() == source.lower():  # Перевод совпадает с исходным
        suspicious.append((key, source, target))

print(f"\n3. Пустые переводы: {len(empty_targets)}")
if empty_targets:
    print("Примеры:")
    for i, (key, source) in enumerate(empty_targets[:10], 1):
        print(f"  {i}. '{source}' (ключ: '{key}')")

print(f"\n4. Подозрительные переводы: {len(suspicious)}")
if suspicious:
    print("Примеры:")
    for i, (key, source, target) in enumerate(suspicious[:10], 1):
        print(f"  {i}. '{source}' -> '{target}' (ключ: '{key}')")

# 4. Проверка на похожие ключи (возможные опечатки)
key_variations = defaultdict(list)
for key in data.keys():
    # Нормализуем ключ (убираем пробелы, приводим к нижнему регистру)
    normalized = key.lower().strip().replace(' ', '').replace('=', '').replace(':', '')
    key_variations[normalized].append(key)

similar_keys = {k: v for k, v in key_variations.items() if len(v) > 1}

print(f"\n5. Похожие ключи (возможные опечатки): {len(similar_keys)}")
if similar_keys:
    print("Примеры:")
    for i, (norm, keys) in enumerate(list(similar_keys.items())[:10], 1):
        if len(set(keys)) > 1:  # Только если действительно разные ключи
            print(f"  {i}. Варианты ключей: {keys}")

# 5. Статистика
print(f"\n" + "=" * 60)
print("Статистика:")
print(f"  Всего терминов: {len(data)}")
print(f"  Уникальных source: {len(source_to_entries)}")
print(f"  Дубликатов: {len(duplicates)}")
print(f"  Конфликтов переводов: {len(conflicts)}")
print(f"  Пустых переводов: {len(empty_targets)}")
print(f"  Подозрительных: {len(suspicious)}")
print(f"  Похожих ключей: {len([k for k, v in similar_keys.items() if len(set(v)) > 1])}")

# Сохраняем отчет
report = {
    "duplicates": {k: [(entry[0], entry[1].get('target')) for entry in v] for k, v in duplicates.items()},
    "conflicts": {k: [(entry[0], entry[1].get('target')) for entry in v] for k, v in conflicts},
    "empty_targets": [{"key": k, "source": s} for k, s in empty_targets],
    "suspicious": [{"key": k, "source": s, "target": t} for k, s, t in suspicious]
}

with open('glossary_issues_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n✅ Полный отчет сохранен в glossary_issues_report.json")

