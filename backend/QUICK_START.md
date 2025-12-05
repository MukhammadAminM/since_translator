# 🚀 Быстрый старт нового пайплайна

## Шаг 1: Установка зависимостей

Убедитесь, что установлены все необходимые библиотеки:

```bash
cd backend
pip install -r requirements.txt

# Дополнительные зависимости для нового пайплайна:
pip install PyMuPDF pdfplumber lxml
```

## Шаг 2: Проверка переменных окружения

Убедитесь, что файл `.env` содержит:

```env
OPENAI_API_KEY=your_openai_api_key
MATHPIX_APP_ID=your_mathpix_app_id  # Опционально
MATHPIX_APP_KEY=your_mathpix_app_key  # Опционально
```

## Шаг 3: Запуск сервера

### Вариант 1: Запуск нового пайплайна (рекомендуется)

```bash
cd backend
python run_new.py
```

Сервер запустится на `http://localhost:8000`

### Вариант 2: Запуск через uvicorn напрямую

```bash
cd backend
uvicorn main_new:app --host 0.0.0.0 --port 8000 --reload
```

### Вариант 3: Запуск старого пайплайна (для обратной совместимости)

```bash
cd backend
python run.py
```

## Шаг 4: Проверка работы

Откройте в браузере:
- API документация: http://localhost:8000/docs
- Корневой endpoint: http://localhost:8000

## 📝 Использование API

### Перевод файла через новый пайплайн

**Endpoint:** `POST /api/translate-file`

**Параметры:**
- `file`: PDF файл
- `sourceLang`: `ru`, `ar`, или `zh`
- `model`: `general`, `engineering`, `academic`, или `scientific`
- `formulaMode`: `png` (по умолчанию) или `omml`
- `useOCR`: `true` или `false` (по умолчанию `false`)
- `useMathpix`: `true` или `false` (по умолчанию `true`)

**Пример через curl:**

```bash
curl -X POST "http://localhost:8000/api/translate-file" \
  -F "file=@document.pdf" \
  -F "sourceLang=ru" \
  -F "model=engineering" \
  -F "formulaMode=png" \
  -F "useOCR=false" \
  -F "useMathpix=true"
```

**Пример через Python:**

```python
import requests

url = "http://localhost:8000/api/translate-file"
files = {"file": open("document.pdf", "rb")}
data = {
    "sourceLang": "ru",
    "model": "engineering",
    "formulaMode": "png",
    "useOCR": "false",
    "useMathpix": "true"
}

response = requests.post(url, files=files, data=data)
result = response.json()
print(f"Скачать файл: http://localhost:8000{result['downloadUrl']}")
```

## 🔍 Проверка логов

При запуске вы увидите логи в консоли:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

При обработке файла:

```
INFO: Начало обработки PDF: document.pdf
INFO: Этап 1: Извлечение текста и изображений из PDF
INFO: Извлечено: 5000 символов, 10 страниц
INFO: Этап 2: Выделение формул
INFO: Найдено формул: 15
INFO: Этап 3: Распознавание формул через Mathpix
INFO: Распознано формул: 12
INFO: Этап 4: Перевод текста
INFO: Перевод завершен
INFO: Этап 6: Сборка DOCX документа
INFO: DOCX файл создан: document_translated_20240101_120000_abc123.docx
```

## ⚠️ Возможные проблемы

### 1. Ошибка импорта модулей

Если видите ошибку типа `ModuleNotFoundError`:

```bash
# Убедитесь, что вы в директории backend
cd backend

# Проверьте, что все модули на месте
ls services/
# Должны быть: pdf_extractor.py, formula_extractor.py, formula_recognizer.py, 
#              text_translator.py, document_builder.py, pipeline.py
```

### 2. Ошибка с PyMuPDF

Если PyMuPDF не установлен:

```bash
pip install PyMuPDF
```

### 3. Ошибка с Mathpix

Если Mathpix не настроен, пайплайн все равно будет работать, но без распознавания формул через Mathpix.

### 4. Порт занят

Если порт 8000 занят, измените в `run_new.py`:

```python
port=8001  # или другой свободный порт
```

## 🧪 Тестирование без сервера

Можно протестировать пайплайн напрямую:

```bash
cd backend
python example_usage.py
```

## 📚 Дополнительная документация

- Полная документация: `PIPELINE_README.md`
- Примеры использования: `example_usage.py`

