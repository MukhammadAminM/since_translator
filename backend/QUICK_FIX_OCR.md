# Быстрое решение проблемы OCR

## Проблема
```
❌ Ошибка OCR: tesseract is not installed or it's not in your PATH
```

## Решение

### Вариант 1: Tesseract установлен, но не в PATH

1. Найдите, где установлен Tesseract (обычно `C:\Program Files\Tesseract-OCR\`)
2. Добавьте путь к `tesseract.exe` в переменную окружения PATH:
   - Откройте "Переменные среды" в Windows
   - Добавьте `C:\Program Files\Tesseract-OCR\` в PATH
   - Перезапустите сервер

### Вариант 2: Tesseract не установлен

1. Скачайте Tesseract OCR:
   - Прямая ссылка: https://github.com/UB-Mannheim/tesseract/wiki
   - Или используйте: `winget install UB-Mannheim.TesseractOCR`

2. Установите языковые пакеты:
   - При установке выберите: Chinese (Simplified), Russian, Arabic, English
   - Или установите отдельно через установщик

3. Перезапустите сервер

### Проверка установки

Запустите в PowerShell:
```powershell
python backend/check_tesseract.py
```

Если Tesseract найден, вы увидите:
```
✅ Tesseract OCR готов к использованию!
```

## Что делает система автоматически

Система автоматически ищет Tesseract в:
- `C:\Program Files\Tesseract-OCR\tesseract.exe`
- `C:\Program Files (x86)\Tesseract-OCR\tesseract.exe`
- PATH (через `shutil.which('tesseract')`)

Если Tesseract найден, он будет использован автоматически.


