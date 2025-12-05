# Прямая ссылка на скачивание Poppler для Windows

## 🚀 Быстрое скачивание

### Прямая ссылка (последняя версия):
```
https://github.com/oschwartz10612/poppler-windows/releases/download/v23.11.0-0/Release-23.11.0-0.zip
```

### Альтернативная версия:
```
https://github.com/oschwartz10612/poppler-windows/releases/download/v23.08.0-0/Release-23.08.0-0.zip
```

## 📥 Установка через PowerShell

Скопируйте и выполните в PowerShell:

```powershell
# Скачать poppler
Invoke-WebRequest -Uri "https://github.com/oschwartz10612/poppler-windows/releases/download/v23.11.0-0/Release-23.11.0-0.zip" -OutFile "$env:TEMP\poppler.zip"

# Распаковать в C:\poppler
Expand-Archive -Path "$env:TEMP\poppler.zip" -DestinationPath "C:\" -Force

# Добавить в PATH (требует прав администратора)
$popplerPath = "C:\poppler\Library\bin"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -notlike "*$popplerPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$popplerPath", "Machine")
}

# Удалить архив
Remove-Item "$env:TEMP\poppler.zip"

Write-Host "✅ Poppler установлен в C:\poppler\Library\bin"
Write-Host "⚠️  Перезапустите терминал для применения изменений PATH"
```

## ✅ После установки

1. **Перезапустите терминал** (чтобы PATH обновился)

2. **Проверьте установку**:
   ```bash
   pdftoppm -h
   ```

3. **Пересоберите глоссарий**:
   ```bash
   python build_glossary.py
   ```

## 🔧 Альтернатива: Указать путь в коде

Если не хотите добавлять в PATH, можно указать путь в коде.

Парсер автоматически ищет poppler в:
- `C:\poppler\Library\bin`
- `C:\poppler\bin`
- `C:\Program Files\poppler\bin`

Если poppler в другом месте, измените пути в `backend/services/glossary_parser.py` в методе `_extract_text_with_ocr`.

## 📝 Ручная установка

1. Скачайте архив по ссылке выше
2. Распакуйте в `C:\poppler`
3. Добавьте `C:\poppler\Library\bin` в PATH:
   - `Win + R` → `sysdm.cpl` → Enter
   - "Дополнительно" → "Переменные среды"
   - В "Системные переменные" найдите `Path` → "Изменить"
   - "Создать" → `C:\poppler\Library\bin`
   - OK → OK → OK
4. Перезапустите терминал

## 🔗 Все версии

Все доступные версии: https://github.com/oschwartz10612/poppler-windows/releases



