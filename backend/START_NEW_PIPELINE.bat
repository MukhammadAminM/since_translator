@echo off
REM Скрипт для запуска нового пайплайна на Windows
echo ========================================
echo Запуск нового модульного пайплайна
echo ========================================
echo.

cd /d %~dp0

echo Проверка зависимостей...
python -c "import fastapi, uvicorn, pymupdf, pdfplumber" 2>nul
if errorlevel 1 (
    echo Ошибка: Не все зависимости установлены
    echo Установите: pip install -r requirements.txt
    pause
    exit /b 1
)

echo Зависимости установлены!
echo.
echo Запуск сервера на http://localhost:8000
echo Для остановки нажмите Ctrl+C
echo.

python run_new.py

pause

