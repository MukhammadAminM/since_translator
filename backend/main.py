from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Literal
import os
import tempfile
import traceback
import logging
from pathlib import Path
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env файла
load_dotenv()

from services.translator import TranslationService
from services.docx_generator import DocxGenerator

app = FastAPI(title="Since Translator API", version="0.1.0")

# CORS настройки для работы с frontend
# Добавляем все возможные origins для разработки
cors_origins = [
    "http://localhost:5173", 
    "http://localhost:3000", 
    "http://127.0.0.1:5173", 
    "http://89.110.95.15:5173",
    "http://89.110.95.15:5174",  # Добавлен порт 5174
    "https://89.110.95.15:5174",  # HTTPS вариант
]

# Middleware для обработки CORS (включая ngrok)
# Этот middleware должен быть ПЕРЕД CORSMiddleware
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    """
    Обрабатывает CORS заголовки, включая поддержку ngrok и любых origins
    """
    # Обрабатываем preflight запросы (OPTIONS)
    if request.method == "OPTIONS":
        origin = request.headers.get("origin")
        response = Response()
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "3600"
        return response
    
    # Обрабатываем обычные запросы
    response = await call_next(request)
    
    # Добавляем CORS заголовки к ответу
    origin = request.headers.get("origin")
    if origin:
        # Разрешаем все origins для разработки (можно ограничить в продакшене)
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Expose-Headers"] = "*"
    
    return response

# Дополнительный CORSMiddleware для совместимости
# В режиме разработки разрешаем все origins
allow_all_origins = os.getenv("ALLOW_ALL_CORS", "true").lower() == "true"  # По умолчанию true для разработки

if allow_all_origins:
    logger.info("⚠️  CORS: Разрешены все origins через middleware (режим разработки)")
    # Не добавляем CORSMiddleware, так как используем кастомный middleware выше
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

# Инициализация сервисов
translator_service = TranslationService()
docx_generator = DocxGenerator()

# Временная директория для файлов
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


class TranslateRequest(BaseModel):
    sourceLang: Literal["ru", "ar", "zh"]
    text: str
    model: Literal["general", "engineering", "academic", "scientific"]


class TranslateResponse(BaseModel):
    downloadUrl: str
    message: str


@app.get("/")
async def root():
    return {"message": "Since Translator API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/translate", response_model=TranslateResponse)
async def translate_text(request: TranslateRequest):
    """
    Переводит текст на английский и возвращает ссылку на .docx файл
    """
    try:
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Текст не может быть пустым")

        # Переводим текст через сервис перевода
        translated_text = await translator_service.translate(
            text=request.text,
            source_lang=request.sourceLang,
            target_lang="en",
            model=request.model
        )

        # Генерируем .docx файл
        output_filename = docx_generator.create_docx(
            translated_text=translated_text,
            source_lang=request.sourceLang,
            model=request.model,
            original_text=request.text  # Передаем оригинальный текст для сохранения структуры
        )

        # Возвращаем URL для скачивания
        download_url = f"/api/download/{output_filename}"
        
        return TranslateResponse(
            downloadUrl=download_url,
            message=f"Перевод выполнен успешно. Модель: {request.model}"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при переводе: {str(e)}")


@app.post("/api/translate-file", response_model=TranslateResponse)
async def translate_file(
    file: UploadFile = File(...),
    sourceLang: Literal["ru", "ar", "zh"] = Form(...),
    model: Literal["general", "engineering", "academic", "scientific"] = Form(...)
):
    """
    Переводит содержимое файла на английский и возвращает ссылку на .docx файл
    """
    try:
        logger.info(f"Получен запрос на перевод файла: {file.filename}, тип: {file.content_type}, язык: {sourceLang}, модель: {model}")
        
        # Проверяем наличие имени файла
        if not file.filename:
            logger.warning("Файл без имени")
            raise HTTPException(status_code=400, detail="Имя файла не указано")
        
        # Проверяем тип файла
        allowed_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain"
        ]
        
        # Также проверяем расширение файла, если content_type не определен
        file_ext = Path(file.filename).suffix.lower()
        allowed_extensions = [".pdf", ".doc", ".docx", ".txt"]
        
        if file.content_type not in allowed_types and file_ext not in allowed_extensions:
            logger.warning(f"Неподдерживаемый тип файла: {file.content_type}, расширение: {file_ext}")
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый тип файла. Разрешены: PDF, DOC, DOCX, TXT. Получен: {file.content_type or file_ext}"
            )

        # Сохраняем загруженный файл
        file_path = UPLOAD_DIR / file.filename
        try:
            with open(file_path, "wb") as f:
                content = await file.read()
                if not content:
                    raise HTTPException(status_code=400, detail="Файл пустой")
                f.write(content)
            logger.info(f"Файл сохранен: {file_path}, размер: {len(content)} байт")
        except Exception as e:
            logger.error(f"Ошибка при сохранении файла: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Ошибка при сохранении файла: {str(e)}")

        # Извлекаем текст из файла
        try:
            extracted_text = await translator_service.extract_text_from_file(
                str(file_path),
                source_lang=sourceLang  # Передаем язык для OCR
            )
            logger.info(f"Текст извлечен, длина: {len(extracted_text)} символов")
        except Exception as e:
            logger.error(f"Ошибка при извлечении текста: {str(e)}")
            logger.error(traceback.format_exc())
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=400, detail=f"Не удалось извлечь текст из файла: {str(e)}")
        
        if not extracted_text or not extracted_text.strip():
            logger.warning("Извлеченный текст пустой")
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=400, detail="Не удалось извлечь текст из файла (текст пустой)")

        # Переводим текст
        try:
            translated_text = await translator_service.translate(
                text=extracted_text,
                source_lang=sourceLang,
                target_lang="en",
                model=model
            )
            logger.info(f"Текст переведен, длина: {len(translated_text)} символов")
        except Exception as e:
            logger.error(f"Ошибка при переводе: {str(e)}")
            logger.error(traceback.format_exc())
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Ошибка при переводе: {str(e)}")

        # Генерируем .docx файл
        try:
            # Получаем информацию об изображениях страниц (если есть)
            page_images = getattr(translator_service, '_page_images', {})
            logger.info(f"Получены изображения страниц: {len(page_images)} шт.")
            
            output_filename = docx_generator.create_docx(
                translated_text=translated_text,
                source_lang=sourceLang,
                model=model,
                original_filename=file.filename,
                original_text=extracted_text,  # Передаем оригинальный текст для сохранения структуры
                page_images=page_images  # Передаем изображения страниц для вставки
            )
            logger.info(f"DOCX файл создан: {output_filename}")
        except Exception as e:
            logger.error(f"Ошибка при создании DOCX: {str(e)}")
            logger.error(traceback.format_exc())
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Ошибка при создании DOCX файла: {str(e)}")

        # Удаляем временный загруженный файл
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Временный файл удален: {file_path}")
        except Exception as e:
            logger.warning(f"Не удалось удалить временный файл: {str(e)}")

        # Возвращаем URL для скачивания
        download_url = f"/api/download/{output_filename}"
        
        logger.info(f"Возвращаем ответ: downloadUrl={download_url}, message=Файл переведен успешно")
        
        response = TranslateResponse(
            downloadUrl=download_url,
            message=f"Файл переведен успешно. Модель: {model}"
        )
        
        logger.info(f"Ответ сформирован, возвращаем клиенту")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка при переводе файла: {str(e)}")


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """
    Скачивание сгенерированного .docx файла
    """
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

