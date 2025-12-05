# 🔍 Отчет о проверке бэкенда Since Translator

**Дата проверки:** 2024  
**Версия:** 0.1.0  
**Статус:** ⚠️ Обнаружены критические проблемы безопасности

---

## 📋 Содержание

1. [Критические проблемы безопасности](#критические-проблемы-безопасности)
2. [Проблемы валидации](#проблемы-валидации)
3. [Проблемы производительности](#проблемы-производительности)
4. [Проблемы обработки ошибок](#проблемы-обработки-ошибок)
5. [Архитектурные проблемы](#архитектурные-проблемы)
6. [Рекомендации по улучшению](#рекомендации-по-улучшению)

---

## 🚨 Критические проблемы безопасности

### 1. Path Traversal уязвимость (КРИТИЧНО)

**Файл:** `backend/main.py:140`

**Проблема:**
```python
file_path = UPLOAD_DIR / file.filename  # ❌ ОПАСНО!
```

**Риск:** Злоумышленник может загрузить файл с именем `../../../etc/passwd` или `..\\..\\windows\\system32\\config\\sam`, что приведет к записи файла вне директории `uploads/`.

**Пример атаки:**
```
filename: "../../../etc/passwd"
Результат: файл будет записан в /etc/passwd (Linux) или C:\etc\passwd (Windows)
```

**Решение:**
```python
from werkzeug.utils import secure_filename
import uuid

# Безопасное имя файла
safe_filename = secure_filename(file.filename) or f"file_{uuid.uuid4().hex}"
# Или использовать только имя файла без пути
safe_filename = Path(file.filename).name
# Еще лучше - генерировать уникальное имя
safe_filename = f"{uuid.uuid4().hex}{Path(file.filename).suffix}"
file_path = UPLOAD_DIR / safe_filename
```

---

### 2. Path Traversal в download endpoint (КРИТИЧНО)

**Файл:** `backend/main.py:234`

**Проблема:**
```python
file_path = OUTPUT_DIR / filename  # ❌ ОПАСНО!
```

**Риск:** Злоумышленник может скачать любой файл с сервера, используя путь типа `../../../.env` или `../../config.py`.

**Пример атаки:**
```
GET /api/download/../../../.env
Результат: получение секретных ключей из .env файла
```

**Решение:**
```python
from pathlib import Path
import os

# Проверяем, что путь находится внутри OUTPUT_DIR
file_path = OUTPUT_DIR / filename
try:
    # Проверяем, что файл действительно внутри OUTPUT_DIR
    file_path.resolve().relative_to(OUTPUT_DIR.resolve())
except ValueError:
    raise HTTPException(status_code=403, detail="Invalid file path")

# Дополнительно: проверяем, что нет символов .. в имени
if ".." in filename or "/" in filename or "\\" in filename:
    raise HTTPException(status_code=403, detail="Invalid filename")
```

---

### 3. Отсутствие лимитов на размер файлов (ВЫСОКИЙ)

**Файл:** `backend/main.py:143`

**Проблема:**
```python
content = await file.read()  # ❌ Нет ограничения размера
```

**Риск:**
- DoS атака через загрузку огромных файлов (несколько GB)
- Исчерпание памяти сервера
- Замедление работы сервера

**Решение:**
```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

content = await file.read()
if len(content) > MAX_FILE_SIZE:
    raise HTTPException(
        status_code=413, 
        detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024} MB"
    )
```

**Или использовать FastAPI File с ограничением:**
```python
from fastapi import File, UploadFile

@app.post("/api/translate-file")
async def translate_file(
    file: UploadFile = File(..., max_length=50 * 1024 * 1024),  # 50 MB
    ...
):
```

---

### 4. Отсутствие валидации реального содержимого файлов (ВЫСОКИЙ)

**Файл:** `backend/main.py:120-137`

**Проблема:**
Проверяется только расширение и `content-type`, но не реальное содержимое файла.

**Риск:**
- Загрузка вредоносных файлов (например, `.pdf` с макросами)
- Загрузка файлов с неправильным расширением (например, `.txt` файл, который на самом деле `.exe`)

**Решение:**
```python
import magic  # python-magic или python-magic-bin

def validate_file_content(file_content: bytes, expected_ext: str) -> bool:
    """Проверяет реальное содержимое файла"""
    file_type = magic.from_buffer(file_content, mime=True)
    
    type_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain"
    }
    
    expected_mime = type_map.get(expected_ext)
    return file_type == expected_mime

# Использование:
if not validate_file_content(content, file_ext):
    raise HTTPException(status_code=400, detail="File content does not match extension")
```

---

### 5. Слишком открытые CORS настройки (СРЕДНИЙ)

**Файл:** `backend/main.py:26-32`

**Проблема:**
```python
allow_origins=["http://localhost:5173", ..., "http://89.110.95.15:5173"],  # Хардкод IP
allow_methods=["*"],  # Разрешены все методы
allow_headers=["*"],  # Разрешены все заголовки
```

**Риск:**
- Хардкод IP адреса в коде (плохая практика)
- Слишком открытые настройки могут позволить CSRF атаки

**Решение:**
```python
import os

# Использовать переменные окружения
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Только нужные методы
    allow_headers=["Content-Type", "Authorization"],  # Только нужные заголовки
)
```

---

## ⚠️ Проблемы валидации

### 6. Отсутствие валидации длины текста (СРЕДНИЙ)

**Файл:** `backend/main.py:72`

**Проблема:**
```python
if not request.text.strip():  # Проверяется только пустота
    raise HTTPException(status_code=400, detail="Текст не может быть пустым")
```

**Риск:**
- DoS через отправку огромных текстов
- Превышение лимитов токенов OpenAI

**Решение:**
```python
MAX_TEXT_LENGTH = 1_000_000  # 1M символов

if len(request.text) > MAX_TEXT_LENGTH:
    raise HTTPException(
        status_code=400, 
        detail=f"Text too long. Maximum length: {MAX_TEXT_LENGTH} characters"
    )
```

---

### 7. Отсутствие rate limiting (СРЕДНИЙ)

**Проблема:**
Нет ограничений на количество запросов от одного клиента.

**Риск:**
- DoS атака
- Исчерпание квоты OpenAI API
- Высокие затраты на API

**Решение:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/translate")
@limiter.limit("10/minute")  # 10 запросов в минуту
async def translate_text(request: Request, ...):
    ...
```

---

## 🐌 Проблемы производительности

### 8. Синхронная инициализация сервисов (НИЗКИЙ)

**Файл:** `backend/main.py:35-36`

**Проблема:**
```python
translator_service = TranslationService()  # Синхронная инициализация
docx_generator = DocxGenerator()
```

**Риск:**
- Блокировка при старте приложения
- Медленная загрузка глоссариев

**Решение:**
```python
# Использовать startup event
@app.on_event("startup")
async def startup_event():
    global translator_service, docx_generator
    translator_service = TranslationService()
    docx_generator = DocxGenerator()
```

---

### 9. Отсутствие кэширования (НИЗКИЙ)

**Проблема:**
Глоссарии загружаются каждый раз при инициализации, переводы не кэшируются.

**Решение:**
```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def get_cached_translation(text_hash: str, source_lang: str, model: str) -> str:
    # Кэширование переводов
    ...

def translate_with_cache(text: str, ...):
    text_hash = hashlib.md5(text.encode()).hexdigest()
    return get_cached_translation(text_hash, source_lang, model)
```

---

## 🔧 Проблемы обработки ошибок

### 10. Слишком общие исключения (СРЕДНИЙ)

**Файл:** `backend/main.py:99`

**Проблема:**
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Ошибка при переводе: {str(e)}")
```

**Риск:**
- Утечка внутренней информации (стек трейсы, пути к файлам)
- Сложность отладки

**Решение:**
```python
except HTTPException:
    raise
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
except FileNotFoundError as e:
    raise HTTPException(status_code=404, detail="File not found")
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    raise HTTPException(
        status_code=500, 
        detail="Internal server error. Please try again later."
    )
```

---

### 11. Отсутствие валидации ответов OpenAI (НИЗКИЙ)

**Файл:** `backend/services/translator.py:259`

**Проблема:**
```python
translated_text = response.choices[0].message.content.strip()
```

**Риск:**
- `IndexError` если `choices` пустой
- `AttributeError` если структура ответа неожиданная

**Решение:**
```python
if not response.choices or not response.choices[0].message.content:
    raise ValueError("Empty response from OpenAI API")
translated_text = response.choices[0].message.content.strip()
```

---

## 🏗️ Архитектурные проблемы

### 12. Хардкод путей и конфигурации (НИЗКИЙ)

**Проблема:**
Много хардкода в коде (пути к Tesseract, Poppler, размеры лимитов).

**Решение:**
Использовать конфигурационный файл или переменные окружения:
```python
# config.py
import os
from pathlib import Path

class Config:
    UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
    OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs"))
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))
    TESSERACT_PATH = os.getenv("TESSERACT_PATH")
    POPPLER_PATH = os.getenv("POPPLER_PATH")
```

---

### 13. Отсутствие мониторинга и метрик (НИЗКИЙ)

**Проблема:**
Нет сбора метрик (время обработки, количество запросов, ошибки).

**Решение:**
```python
from prometheus_client import Counter, Histogram
import time

request_count = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    request_duration.observe(time.time() - start_time)
    request_count.inc()
    return response
```

---

## ✅ Положительные моменты

1. ✅ Хорошая структура проекта (разделение на сервисы)
2. ✅ Использование типизации (Pydantic, Literal)
3. ✅ Логирование ошибок
4. ✅ Обработка различных форматов файлов
5. ✅ Интеграция с OCR и Mathpix
6. ✅ Защита формул от перевода

---

## 📝 Рекомендации по приоритетам

### Критично (исправить немедленно):
1. ✅ Path Traversal в upload endpoint
2. ✅ Path Traversal в download endpoint
3. ✅ Добавить лимиты на размер файлов

### Высокий приоритет:
4. ✅ Валидация реального содержимого файлов
5. ✅ Валидация длины текста
6. ✅ Rate limiting

### Средний приоритет:
7. ✅ Улучшить обработку ошибок
8. ✅ Настроить CORS через переменные окружения
9. ✅ Добавить мониторинг

### Низкий приоритет:
10. ✅ Кэширование
11. ✅ Асинхронная инициализация
12. ✅ Конфигурационный файл

---

## 🔒 Чек-лист безопасности

- [ ] Path Traversal защита
- [ ] Валидация размера файлов
- [ ] Валидация содержимого файлов
- [ ] Rate limiting
- [ ] CORS настройки
- [ ] Обработка ошибок без утечки информации
- [ ] Логирование безопасности
- [ ] Валидация входных данных
- [ ] Защита от DoS
- [ ] Мониторинг и алерты

---

## 📚 Полезные ресурсы

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)

---

**Вывод:** Бэкенд имеет хорошую архитектуру, но содержит критические уязвимости безопасности, которые необходимо исправить перед продакшеном.

