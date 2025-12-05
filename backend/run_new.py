"""
Скрипт для запуска FastAPI сервера с новым модульным пайплайном
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main_new:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Автоперезагрузка при изменении кода
        log_level="info"
    )

