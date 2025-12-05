"""
FastAPI приложение с новым модульным пайплайном
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Literal
import os
import tempfile
import traceback
import logging
from pathlib import Path
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Импортируем новый пайплайн
from services.pipeline import TranslationPipeline, PipelineConfig, FormulaMode

app = FastAPI(title="Since Translator API", version="2.0.0")

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://89.110.95.15:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация пайплайна
pipeline = TranslationPipeline(output_dir="outputs")

# Временные директории
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
    """Корневой endpoint"""
    return {
        "message": "Since Translator API v2.0",
        "status": "running",
        "endpoints": {
            "/api/translate": "Перевод текста",
            "/api/translate-file": "Перевод файла (PDF)",
            "/api/download/{filename}": "Скачать переведенный файл"
        }
    }


@app.post("/api/translate", response_model=TranslateResponse)
async def translate_text(request: TranslateRequest):
    """
    Переводит текст на английский
    """
    try:
        logger.info(f"Получен запрос на перевод текста: язык={request.sourceLang}, модель={request.model}")
        
        # Используем старый сервис для простого перевода текста
        # (можно оставить для обратной совместимости)
        from services.text_translator import TextTranslator, TranslationConfig
        
        translator = TextTranslator()
        config = TranslationConfig(
            source_lang=request.sourceLang,
            target_lang="en",
            model=request.model
        )
        
        translated_text = await translator.translate(request.text, config)
        
        # Сохраняем в временный файл
        import uuid
        from datetime import datetime
        from services.document_builder import DocumentBuilder
        
        builder = DocumentBuilder(output_dir=str(OUTPUT_DIR))
        temp_file = OUTPUT_DIR / f"translated_{uuid.uuid4().hex[:8]}.txt"
        temp_file.write_text(translated_text, encoding='utf-8')
        
        filename = temp_file.name
        download_url = f"/api/download/{filename}"
        
        return TranslateResponse(
            downloadUrl=download_url,
            message="Текст успешно переведен"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при переводе: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при переводе: {str(e)}")


@app.post("/api/translate-file", response_model=TranslateResponse)
async def translate_file(
    file: UploadFile = File(...),
    sourceLang: Literal["ru", "ar", "zh"] = Form(...),
    model: Literal["general", "engineering", "academic", "scientific"] = Form(...),
    formulaMode: Literal["png", "omml"] = Form("png"),
    useOCR: bool = Form(False),
    useMathpix: bool = Form(True)
):
    """
    Переводит PDF файл через новый модульный пайплайн
    
    Args:
        file: Загруженный PDF файл
        sourceLang: Исходный язык
        model: Модель перевода
        formulaMode: Режим отображения формул (png или omml)
        useOCR: Использовать OCR для извлечения текста
        useMathpix: Использовать Mathpix для распознавания формул
    """
    try:
        logger.info(f"Получен запрос на перевод файла: {file.filename}, язык: {sourceLang}, модель: {model}")
        
        # Проверка типа файла
        if not file.filename:
            raise HTTPException(status_code=400, detail="Имя файла не указано")
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext != ".pdf":
            raise HTTPException(
                status_code=400,
                detail=f"Поддерживаются только PDF файлы. Получен: {file_ext}"
            )
        
        # Сохраняем файл
        file_path = UPLOAD_DIR / file.filename
        try:
            with open(file_path, "wb") as f:
                content = await file.read()
                if not content:
                    raise HTTPException(status_code=400, detail="Файл пустой")
                f.write(content)
            logger.info(f"Файл сохранен: {file_path}, размер: {len(content)} байт")
        except Exception as e:
            logger.error(f"Ошибка при сохранении файла: {e}")
            raise HTTPException(status_code=400, detail=f"Ошибка при сохранении файла: {str(e)}")
        
        # Определяем язык OCR
        ocr_lang_map = {
            "ru": "rus+eng",
            "ar": "ara+eng",
            "zh": "chi_sim+eng"
        }
        ocr_lang = ocr_lang_map.get(sourceLang) if useOCR else None
        
        # Определяем режим формул
        formula_mode = FormulaMode.PNG if formulaMode == "png" else FormulaMode.OMML
        
        # Создаем конфигурацию пайплайна
        config = PipelineConfig(
            source_lang=sourceLang,
            target_lang="en",
            model=model,
            formula_mode=formula_mode,
            use_ocr=useOCR,
            ocr_lang=ocr_lang,
            use_mathpix=useMathpix,
            include_mathml=(formula_mode == FormulaMode.OMML)
        )
        
        # Запускаем пайплайн
        logger.info("Запуск пайплайна обработки...")
        result = await pipeline.process(file_path, config)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=f"Ошибка в пайплайне: {result.error}")
        
        # Генерируем URL для скачивания
        filename = result.output_file.name
        download_url = f"/api/download/{filename}"
        
        logger.info(f"Обработка завершена успешно: {filename}")
        logger.info(f"Статистика: формул найдено={result.formulas_count}, распознано={result.recognized_formulas_count}")
        
        # Удаляем временный загруженный файл
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass
        
        return TranslateResponse(
            downloadUrl=download_url,
            message=f"Файл успешно обработан. Найдено формул: {result.formulas_count}, распознано: {result.recognized_formulas_count}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обработке файла: {e}", exc_info=True)
        if 'file_path' in locals() and file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке файла: {str(e)}")


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """
    Скачивает переведенный файл
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

