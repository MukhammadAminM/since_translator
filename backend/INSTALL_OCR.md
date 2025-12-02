# Установка OCR для распознавания текста из изображений в PDF

## Проблема

Некоторые PDF файлы содержат текст в виде изображений (отсканированные страницы), поэтому обычное извлечение текста не работает. Для таких файлов требуется OCR (Optical Character Recognition).

## Решение

### Шаг 1: Установите Tesseract OCR

#### Windows (РЕКОМЕНДУЕТСЯ):
1. **Скачайте установщик**: https://github.com/UB-Mannheim/tesseract/wiki
   - Выберите последнюю версию (например, `tesseract-ocr-w64-setup-5.x.x.exe`)
   - Это готовый установщик для Windows со всеми языками
2. **Запустите установщик**:
   - Установите в стандартную папку: `C:\Program Files\Tesseract-OCR`
   - **ВАЖНО**: При установке выберите компоненты:
     - ✅ Russian (русский)
     - ✅ English (английский)
     - ✅ Arabic (арабский)
     - ✅ Chinese Simplified (китайский упрощенный)
3. Установщик автоматически добавит Tesseract в PATH

#### Linux:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-rus  # Русский язык
sudo apt-get install tesseract-ocr-ara  # Арабский язык
sudo apt-get install tesseract-ocr-chi-sim  # Китайский язык
```

#### macOS:
```bash
brew install tesseract
brew install tesseract-lang  # Все языки
```

### Шаг 2: Установите Python библиотеки

```bash
cd backend
pip install pytesseract pdf2image Pillow
```

### Шаг 3: Установите poppler (для pdf2image)

#### Windows:
1. Скачайте: https://github.com/oschwartz10612/poppler-windows/releases
2. Распакуйте и добавьте `bin` в PATH

#### Linux:
```bash
sudo apt-get install poppler-utils
```

#### macOS:
```bash
brew install poppler
```

### Шаг 4: Проверьте установку

Запустите скрипт проверки:

```bash
python check_tesseract.py
```

Или вручную:

```bash
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

Скрипт `check_tesseract.py` покажет:
- ✅ Установленные библиотеки
- ✅ Путь к Tesseract
- ✅ Версию Tesseract
- ✅ Доступные языки
- ⚠️  Отсутствующие компоненты

### Шаг 5: Пересоберите глоссарий

```bash
python build_glossary.py
```

## Настройка пути к Tesseract (если нужно)

Если Tesseract не найден автоматически, укажите путь в коде:

```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

Или добавьте в `glossary_parser.py` после импорта:

```python
if os.name == 'nt':  # Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

## Поддерживаемые языки

- Русский: `rus`
- Арабский: `ara`
- Китайский: `chi_sim` или `chi_tra`

Для установки языковых пакетов смотрите инструкции выше.

## Производительность

OCR работает медленнее обычного извлечения текста:
- ~5-10 секунд на страницу
- Зависит от качества изображения и размера текста

## Альтернатива

Если OCR не работает или слишком медленно:
1. Конвертируйте PDF в изображения вручную
2. Используйте онлайн OCR сервисы
3. Сохраните результат в TXT файл
4. Поместите в папку `glossary/{language}/`
5. Пересоберите глоссарий

