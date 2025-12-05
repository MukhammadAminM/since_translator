# Прямые ссылки на скачивание Tesseract OCR для Windows

## 🚀 Рекомендуемая версия (последняя стабильная)

### 64-bit Windows (рекомендуется):
```
https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.4.0.20240605.exe
```

### 32-bit Windows:
```
https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w32-setup-5.4.0.20240605.exe
```

## 📦 Альтернативные версии

Если ссылка выше не работает, попробуйте:

### Версия 5.3.3 (стабильная):
```
https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe
```

### Версия 5.3.0:
```
https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.0.20221214.exe
```

## 🔍 Как найти актуальную версию вручную

1. Перейдите на: https://github.com/UB-Mannheim/tesseract/wiki
2. Найдите раздел "Current version"
3. Скачайте файл с названием `tesseract-ocr-w64-setup-X.X.X.exe`

## ⚡ Быстрая установка через PowerShell

Скопируйте и выполните в PowerShell (от имени администратора):

```powershell
# Скачать установщик
Invoke-WebRequest -Uri "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.4.0.20240605.exe" -OutFile "$env:TEMP\tesseract-installer.exe"

# Запустить установщик
Start-Process "$env:TEMP\tesseract-installer.exe" -Wait

# Удалить установщик
Remove-Item "$env:TEMP\tesseract-installer.exe"
```

## ✅ После установки

1. **Проверьте установку**:
   ```bash
   python check_tesseract.py
   ```

2. **Если Tesseract не найден**, перезапустите терминал (PATH обновится)

3. **Если все еще не работает**, укажите путь вручную в `glossary_parser.py`

## 📝 Важные моменты при установке

- ✅ Установите в стандартную папку: `C:\Program Files\Tesseract-OCR`
- ✅ При выборе компонентов отметьте:
  - Russian (rus)
  - English (eng)
  - Arabic (ara)
  - Chinese Simplified (chi_sim)
- ✅ Установщик автоматически добавит Tesseract в PATH

## 🔗 Официальные источники

- **GitHub Wiki**: https://github.com/UB-Mannheim/tesseract/wiki
- **Все версии**: https://digi.bib.uni-mannheim.de/tesseract/
- **GitHub Releases**: https://github.com/UB-Mannheim/tesseract/releases



