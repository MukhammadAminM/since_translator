# Since Translator API

FastAPI backend для сервиса перевода текстов и файлов.

## Установка

1. Создайте виртуальное окружение:
```bash
python -m venv venv
```

2. Активируйте виртуальное окружение:
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте API ключ OpenAI:
   - Файл `.env` уже создан с вашим API ключом
   - Или установите переменную окружения:
     - Windows: `set OPENAI_API_KEY=your-key-here`
     - Linux/Mac: `export OPENAI_API_KEY=your-key-here`

## Запуск

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API будет доступен по адресу: http://localhost:8000

Документация API (Swagger): http://localhost:8000/docs

## API Endpoints

### POST `/api/translate`
Переводит текст на английский и возвращает ссылку на .docx файл.

**Request Body:**
```json
{
  "sourceLang": "ru",
  "text": "Текст для перевода",
  "model": "general"
}
```

**Response:**
```json
{
  "downloadUrl": "/api/download/filename.docx",
  "message": "Перевод выполнен успешно. Модель: general"
}
```

### POST `/api/translate-file`
Переводит содержимое файла на английский и возвращает ссылку на .docx файл.

**Form Data:**
- `file`: файл (PDF, DOC, DOCX, TXT)
- `sourceLang`: "ru" | "ar" | "zh"
- `model`: "general" | "engineering" | "academic" | "scientific"

### GET `/api/download/{filename}`
Скачивание сгенерированного .docx файла.

## Интеграция с LLM

✅ **OpenAI уже подключен!**

Перевод работает через OpenAI API. Используются следующие модели:
- **general**: `gpt-4o-mini` - быстрая и экономичная модель
- **engineering**: `gpt-4o` - для технических текстов
- **academic**: `gpt-4o` - для академических текстов  
- **scientific**: `gpt-4o` - для научных текстов

API ключ настроен в файле `.env`. При необходимости вы можете изменить его или использовать переменные окружения.

## Структура проекта

```
backend/
├── main.py                 # Основное FastAPI приложение
├── services/
│   ├── translator.py       # Сервис перевода
│   └── docx_generator.py   # Генератор .docx файлов
├── uploads/                # Временные загруженные файлы
├── outputs/                # Сгенерированные .docx файлы
└── requirements.txt        # Зависимости
```

