from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Literal
import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

from services.translator import TranslationService
from services.docx_generator import DocxGenerator

app = FastAPI(title="Since Translator API", version="0.1.0")

# CORS настройки для работы с frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://89.110.95.15:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        # Проверяем тип файла
        allowed_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain"
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Неподдерживаемый тип файла. Разрешены: PDF, DOC, DOCX, TXT"
            )

        # Сохраняем загруженный файл
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Извлекаем текст из файла
        extracted_text = await translator_service.extract_text_from_file(str(file_path))
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Не удалось извлечь текст из файла")

        # Переводим текст
        translated_text = await translator_service.translate(
            text=extracted_text,
            source_lang=sourceLang,
            target_lang="en",
            model=model
        )

        # Генерируем .docx файл
        output_filename = docx_generator.create_docx(
            translated_text=translated_text,
            source_lang=sourceLang,
            model=model,
            original_filename=file.filename,
            original_text=extracted_text  # Передаем оригинальный текст для сохранения структуры
        )

        # Удаляем временный загруженный файл
        file_path.unlink()

        # Возвращаем URL для скачивания
        download_url = f"/api/download/{output_filename}"
        
        return TranslateResponse(
            downloadUrl=download_url,
            message=f"Файл переведен успешно. Модель: {model}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
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

