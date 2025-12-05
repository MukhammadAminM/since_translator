#!/bin/bash
# Скрипт для запуска нового пайплайна на Linux/Mac

echo "========================================"
echo "Запуск нового модульного пайплайна"
echo "========================================"
echo ""

cd "$(dirname "$0")"

echo "Проверка зависимостей..."
python3 -c "import fastapi, uvicorn, pymupdf, pdfplumber" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Ошибка: Не все зависимости установлены"
    echo "Установите: pip install -r requirements.txt"
    exit 1
fi

echo "Зависимости установлены!"
echo ""
echo "Запуск сервера на http://localhost:8000"
echo "Для остановки нажмите Ctrl+C"
echo ""

python3 run_new.py

