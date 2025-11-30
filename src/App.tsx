import React, { useState } from "react";

// Базовый URL API (измените на ваш, если backend на другом порту)
const API_BASE_URL = "http://localhost:8000";

// Поддерживаемые языки ввода
type SupportedLang = "ru" | "ar" | "zh";

const LANGS: { id: SupportedLang; label: string }[] = [
  { id: "ru", label: "Русский" },
  { id: "ar", label: "Арабский" },
  { id: "zh", label: "Китайский" },
];

// Модели LLM для разных доменов перевода
type ModelId = "general" | "engineering" | "academic" | "scientific";

const MODELS: { id: ModelId; label: string; hint: string }[] = [
  {
    id: "general",
    label: "General",
    hint: "Обычный перевод, смешанная тематика",
  },
  {
    id: "engineering",
    label: "Engineering",
    hint: "Техническая и инженерная лексика",
  },
  {
    id: "academic",
    label: "Academic",
    hint: "Академические тексты, статьи, эссе",
  },
  {
    id: "scientific",
    label: "Scientific",
    hint: "Научные тексты, термины, отчёты",
  },
];

export default function App() {
  const [sourceLang, setSourceLang] = useState<SupportedLang>("ru");
  const [sourceText, setSourceText] = useState("");
  const [isTranslating, setIsTranslating] = useState(false);

  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState("");
  const [fileResult, setFileResult] = useState(""); // ожидаем ссылку/инфо о .docx
  const [downloadUrl, setDownloadUrl] = useState(""); // URL для скачивания .docx
  const [isFileTranslating, setIsFileTranslating] = useState(false);
  const [fileError, setFileError] = useState("");

  const [model, setModel] = useState<ModelId>("general");
  const [showModels, setShowModels] = useState(false);

  // Отправка текста на перевод (результат всё равно .docx)
  async function handleTranslate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!sourceText.trim()) return;

    setIsTranslating(true);
    setFileResult("");
    setDownloadUrl("");

    try {
      const res = await fetch(`${API_BASE_URL}/api/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          sourceLang, 
          text: sourceText, 
          model 
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Неизвестная ошибка" }));
        throw new Error(errorData.detail || `Ошибка ${res.status}`);
      }

      const data = await res.json();
      setDownloadUrl(`${API_BASE_URL}${data.downloadUrl}`);
      setFileResult(
        `✅ ${data.message}\n\n` +
        `Файл готов к скачиванию. Нажмите кнопку "Скачать .docx" ниже.`
      );
      setIsTranslating(false);
    } catch (err) {
      console.error(err);
      const errorMessage = err instanceof Error ? err.message : "Неизвестная ошибка";
      setFileResult(`❌ Ошибка при переводе текста: ${errorMessage}\n\nПроверьте, что backend запущен на ${API_BASE_URL}`);
      setIsTranslating(false);
    }
  }

  function handleClear() {
    setSourceText("");
    setFileResult("");
    setDownloadUrl("");
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    if (!f) return;

    const allowed = [
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
    ];

    if (!allowed.includes(f.type)) {
      setFile(null);
      setFileName("");
      setFileError("Поддерживаются только PDF, DOC, DOCX и TXT.");
      return;
    }

    setFileError("");
    setFile(f);
    setFileName(f.name);
    setFileResult("");
    setDownloadUrl("");
  }

  async function handleFileTranslate() {
    if (!file) return;
    setIsFileTranslating(true);
    setFileResult("");
    setDownloadUrl("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("sourceLang", sourceLang);
      formData.append("model", model);

      const res = await fetch(`${API_BASE_URL}/api/translate-file`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Неизвестная ошибка" }));
        throw new Error(errorData.detail || `Ошибка ${res.status}`);
      }

      const data = await res.json();
      setDownloadUrl(`${API_BASE_URL}${data.downloadUrl}`);
      setFileResult(
        `✅ ${data.message}\n\n` +
        `Файл "${fileName}" успешно переведен. Нажмите кнопку "Скачать .docx" ниже.`
      );
      setIsFileTranslating(false);
    } catch (err) {
      console.error(err);
      const errorMessage = err instanceof Error ? err.message : "Неизвестная ошибка";
      setFileResult(`❌ Ошибка при переводе файла: ${errorMessage}\n\nПроверьте, что backend запущен на ${API_BASE_URL}`);
      setIsFileTranslating(false);
    }
  }

  function handleFileClear() {
    setFile(null);
    setFileName("");
    setFileResult("");
    setFileError("");
    setDownloadUrl("");
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-20">
        <div className="max-w-4xl mx-auto flex items-center justify-between py-3 px-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-2xl bg-indigo-500 flex items-center justify-center text-sm font-bold">
              Tr
            </div>
            <span className="font-semibold tracking-tight text-lg">
              Mini Translator
            </span>
          </div>
          <span className="text-[11px] text-slate-400 hidden sm:inline">
            RU / AR / ZH → EN → DOCX
          </span>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-4xl">
          <div className="mb-6">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight mb-2">
              Сервис перевода на английский с результатом в .docx
            </h1>
            <p className="text-sm text-slate-300 max-w-2xl">
              Введите текст на русском, арабском или китайском, либо загрузите файл
              (PDF, DOC, DOCX, TXT). Результат перевода должен приходить только в
              виде файла <span className="font-mono">.docx</span> для скачивания.
            </p>
          </div>

          {/* Блок выбора модели LLM — сворачиваемый */}
          <section className="mb-6 border border-slate-800 rounded-2xl bg-slate-900/70">
            <button
              type="button"
              onClick={() => setShowModels((prev) => !prev)}
              className="w-full flex items-center justify-between px-4 py-3 text-left text-xs uppercase tracking-[0.16em] text-slate-400 hover:bg-slate-900/60 transition"
            >
              <span>Модель LLM для перевода</span>
              <span className="text-slate-400 text-lg">{showModels ? "▲" : "▼"}</span>
            </button>

            {showModels && (
              <div className="p-4 flex flex-col gap-3 border-t border-slate-800">
                <p className="text-[11px] text-slate-500 max-w-xl">
                  Выберите модель, которая лучше всего подходит под тематику текста:
                  инженерная, академическая или научная лексика. Выбор модели
                  будет отправляться на backend вместе с текстом или файлом.
                </p>

                <div className="flex flex-wrap gap-2 mt-1">
                  {MODELS.map((m) => {
                    const isActive = m.id === model;
                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => setModel(m.id)}
                        className={
                          "px-3 py-1.5 text-xs rounded-xl border transition-colors text-left " +
                          (isActive
                            ? "border-indigo-400 bg-indigo-500/20 text-slate-50"
                            : "border-slate-700 bg-slate-900/80 text-slate-200 hover:border-slate-500")
                        }
                      >
                        <div className="font-semibold text-[11px] mb-0.5">{m.label}</div>
                        <div className="text-[11px] text-slate-400">{m.hint}</div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </section>

          {/* Текст + файл: две колонки */}
          <div className="grid md:grid-cols-2 gap-4 md:gap-6">
            {/* Left: text input */}
            <form
              onSubmit={handleTranslate}
              className="border border-slate-800 rounded-2xl bg-slate-900/70 p-4 flex flex-col gap-3"
            >
              <div className="flex items-center justify-between gap-2">
                <label className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  Исходный текст
                </label>
                <select
                  value={sourceLang}
                  onChange={(e) => setSourceLang(e.target.value as SupportedLang)}
                  className="text-xs bg-slate-900 border border-slate-700 rounded-xl px-2 py-1 outline-none focus:border-indigo-500"
                >
                  {LANGS.map((lang) => (
                    <option key={lang.id} value={lang.id}>
                      {lang.label}
                    </option>
                  ))}
                </select>
              </div>

              <textarea
                value={sourceText}
                onChange={(e) => setSourceText(e.target.value)}
                placeholder="Напишите текст для перевода..."
                className="min-h-[180px] max-h-[260px] w-full text-sm bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 resize-y outline-none focus:border-indigo-500"
              />

              <div className="flex flex-wrap gap-2 justify-between items-center pt-1">
                <div className="flex gap-2 text-[11px] text-slate-500">
                  <span>Язык: {sourceLang.toUpperCase()}</span>
                  <span>•</span>
                  <span>Символов: {sourceText.length}</span>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleClear}
                    className="px-3 py-1.5 text-xs rounded-xl border border-slate-700 hover:border-slate-500 text-slate-300 transition-colors"
                  >
                    Очистить
                  </button>
                  <button
                    type="submit"
                    disabled={!sourceText.trim() || isTranslating}
                    className="px-4 py-1.5 text-xs rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-60 disabled:cursor-not-allowed font-medium transition-colors"
                  >
                    {isTranslating ? "Обработка..." : "Текст → .docx (EN)"}
                  </button>
                </div>
              </div>
            </form>

            {/* Right: file upload */}
            <div className="border border-slate-800 rounded-2xl bg-slate-900/70 p-4 flex flex-col gap-3">
              <div className="flex items-center justify-between gap-2 mb-1">
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                    Перевод файла
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Поддерживаемые форматы: PDF, DOC, DOCX, TXT
                  </p>
                </div>
              </div>

              <label className="flex flex-col items-center justify-center gap-2 border border-dashed border-slate-700 rounded-xl px-4 py-6 cursor-pointer hover:border-indigo-500 transition-colors">
                <span className="text-xs text-slate-300">
                  Нажмите, чтобы выбрать файл
                </span>
                <span className="text-[11px] text-slate-500">
                  или перетащите его сюда (drag & drop потребует отдельной обработки)
                </span>
                <input
                  type="file"
                  className="hidden"
                  accept=".pdf,.doc,.docx,.txt"
                  onChange={handleFileChange}
                />
              </label>

              {fileName && (
                <div className="text-[11px] text-slate-300 flex items-center justify-between gap-2">
                  <span className="truncate">Выбран файл: {fileName}</span>
                  <button
                    type="button"
                    onClick={handleFileClear}
                    className="px-2 py-1 text-[11px] rounded-lg border border-slate-700 hover:border-slate-500 text-slate-300 transition-colors flex-shrink-0"
                  >
                    Убрать
                  </button>
                </div>
              )}

              {fileError && (
                <p className="text-[11px] text-rose-400">{fileError}</p>
              )}

              <div className="flex justify-end mt-1">
                <button
                  type="button"
                  onClick={handleFileTranslate}
                  disabled={!file || !!fileError || isFileTranslating}
                  className="px-4 py-1.5 text-xs rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-60 disabled:cursor-not-allowed font-medium transition-colors"
                >
                  {isFileTranslating
                    ? "Обработка файла..."
                    : "Файл → .docx (EN)"}
                </button>
              </div>
            </div>
          </div>

          {/* Result section: всегда про .docx */}
          <div className="mt-6 border border-slate-800 rounded-2xl bg-slate-900/40 p-4 flex flex-col gap-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  Результат (файл .docx)
                </p>
                <p className="text-[11px] text-slate-500">
                  Здесь должна появиться ссылка или информация о скачивании файла
                  с переводом на английский.
                </p>
              </div>
            </div>

            <div className="relative flex-1">
              <div className="min-h-[140px] max-h-[220px] w-full text-sm bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 overflow-auto whitespace-pre-wrap">
                {fileResult ? (
                  fileResult
                ) : (
                  <span className="text-slate-500 text-xs">
                    Введите текст или загрузите файл для перевода. После успешного запроса
                    здесь появится информация о результате и кнопка для скачивания
                    <span className="font-mono"> .docx</span>-файла.
                  </span>
                )}
              </div>
            </div>

            {downloadUrl && (
              <div className="flex justify-end">
                <a
                  href={downloadUrl}
                  download
                  className="px-4 py-2 text-sm rounded-xl bg-indigo-500 hover:bg-indigo-400 font-medium transition-colors inline-flex items-center gap-2"
                >
                  <span>📥</span>
                  <span>Скачать .docx</span>
                </a>
              </div>
            )}

            <p className="text-[11px] text-slate-500">
              Backend API: endpoints
              <span className="font-mono"> /api/translate</span> и
              <span className="font-mono"> /api/translate-file</span> принимают
              текст или файл и выбранную LLM-модель и возвращают ссылку на готовый
              <span className="font-mono"> .docx</span>-документ с переводом на
              английский.
            </p>
          </div>

          <div className="mt-6 text-[11px] text-slate-500 border-t border-slate-800 pt-3 flex flex-wrap gap-2 justify-between">
            <span>
              Построено на <span className="font-mono">React</span> +
              <span className="font-mono"> Tailwind CSS</span>
            </span>
            <span>
              Пример: RU / AR / ZH → EN — текст и файлы, выбор модели LLM, только
              фронтенд, без реального API.
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}
