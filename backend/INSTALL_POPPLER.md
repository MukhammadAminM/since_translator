# Установка Poppler для Windows

## Проблема

Ошибка: `Unable to get page count. Is poppler installed and in PATH?`

Poppler требуется для конвертации PDF в изображения (для OCR).

## Решение

### Вариант 1: Установка через установщик (рекомендуется)

1. **Скачайте poppler**:
   - **Прямая ссылка**: https://github.com/oschwartz10612/poppler-windows/releases/download/v23.11.0-0/Release-23.11.0-0.zip
   - Или перейдите на: https://github.com/oschwartz10612/poppler-windows/releases
   - Скачайте последний релиз (например, `Release-23.11.0-0.zip`)

2. **Распакуйте архив**:
   - Распакуйте в `C:\poppler` (или другое место)
   - Внутри должна быть папка `Library\bin`

3. **Добавьте в PATH**:
   - Нажмите `Win + R`, введите `sysdm.cpl`, Enter
   - Вкладка "Дополнительно" → "Переменные среды"
   - В "Системные переменные" найдите `Path` → "Изменить"
   - "Создать" → добавьте: `C:\poppler\Library\bin`
   - OK → OK → OK

4. **Перезапустите терминал** и проверьте:
   ```bash
   pdftoppm -h
   ```

### Вариант 2: Указать путь в коде (быстрое решение)

Если не хотите добавлять в PATH, можно указать путь в коде.

Откройте `backend/services/glossary_parser.py` и добавьте после импортов:

```python
import os
os.environ['PATH'] += r';C:\poppler\Library\bin'
```

Или измените путь на ваш.

### Вариант 3: Использовать conda (если установлен)

```bash
conda install -c conda-forge poppler
```

## Проверка установки

После установки перезапустите терминал и проверьте:

```bash
pdftoppm -h
```

Если команда работает, poppler установлен правильно.

## После установки

Пересоберите глоссарий:

```bash
python build_glossary.py
```

Теперь "Часть 3.pdf" и другие PDF с изображениями будут обработаны через OCR!

