import React, { useState } from "react";

// Supported source languages
type SupportedLang = "ru" | "ar" | "zh";

const LANGS: { id: SupportedLang; label: string }[] = [
  { id: "ru", label: "Russian" },
  { id: "ar", label: "Arabic" },
  { id: "zh", label: "Chinese" },
];

// LLM models for different translation domains
type ModelId = "general" | "engineering" | "academic" | "scientific";

const MODELS: { id: ModelId; label: string; hint: string }[] = [
  {
    id: "general",
    label: "General",
    hint: "Generic translation, mixed topics",
  },
  {
    id: "engineering",
    label: "Engineering",
    hint: "Technical and engineering terminology",
  },
  {
    id: "academic",
    label: "Academic",
    hint: "Academic texts, papers, essays",
  },
  {
    id: "scientific",
    label: "Scientific",
    hint: "Scientific texts, terms, reports",
  },
];

export default function App() {
  const [sourceLang, setSourceLang] = useState<SupportedLang>("ru");
  const [sourceText, setSourceText] = useState("");
  const [isTranslating, setIsTranslating] = useState(false);

  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState("");
  const [fileResult, setFileResult] = useState(""); // link/info for .docx
  const [isFileTranslating, setIsFileTranslating] = useState(false);
  const [fileError, setFileError] = useState("");

  const [model, setModel] = useState<ModelId>("general");
  const [showModels, setShowModels] = useState(false);

  // Text translation (result is still .docx)
  async function handleTranslate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!sourceText.trim()) return;

    setIsTranslating(true);
    setFileResult("");

    try {
      // YOUR TEXT→DOCX TRANSLATION API CALL GOES HERE
      // Example call to your backend:
      // const res = await fetch("/api/translate", {
      //   method: "POST",
      //   headers: { "Content-Type": "application/json" },
      //   body: JSON.stringify({ sourceLang, text: sourceText, model }),
      // });
      // const data = await res.json();
      // setFileResult(data.downloadUrl); // link to .docx

      // Demo placeholder so the UI works without backend
      setTimeout(() => {
        setFileResult(
          "[Demo] This is where a link to a .docx file with the English translation of the text should appear.\n\n" +
            `Selected model: ${model.toUpperCase()}.` +
            "\nConnect your backend to /api/translate to return a real .docx file and download link based on the chosen model."
        );
        setIsTranslating(false);
      }, 600);
    } catch (err) {
      console.error(err);
      setFileResult("Error while translating text. Please check your server connection.");
      setIsTranslating(false);
    }
  }

  function handleClear() {
    setSourceText("");
    setFileResult("");
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
      setFileError("Only PDF, DOC, DOCX and TXT are supported.");
      return;
    }

    setFileError("");
    setFile(f);
    setFileName(f.name);
    setFileResult("");
  }

  async function handleFileTranslate() {
    if (!file) return;
    setIsFileTranslating(true);
    setFileResult("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("sourceLang", sourceLang);
      formData.append("model", model);

      // YOUR FILE→DOCX TRANSLATION API CALL GOES HERE
      // Example:
      // const res = await fetch("/api/translate-file", {
      //   method: "POST",
      //   body: formData,
      // });
      // const data = await res.json();
      // setFileResult(data.downloadUrl); // link to generated .docx

      // Demo placeholder for files
      setTimeout(() => {
        setFileResult(
          "[Demo] This is where a link to a .docx file with the English translation of the uploaded document should appear.\n\n" +
            `File: ${fileName}\nModel: ${model.toUpperCase()}.` +
            "\nConnect your backend to /api/translate-file to generate a real .docx using the selected model."
        );
        setIsFileTranslating(false);
      }, 800);
    } catch (err) {
      console.error(err);
      setFileResult("Error while translating file. Please check your server.");
      setIsFileTranslating(false);
    }
  }

  function handleFileClear() {
    setFile(null);
    setFileName("");
    setFileResult("");
    setFileError("");
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
              Translation service to English with .docx output
            </h1>
            <p className="text-sm text-slate-300 max-w-2xl">
              Enter text in Russian, Arabic or Chinese, or upload a document
              (PDF, DOC, DOCX, TXT). The translation result is always returned as
              an <span className="font-mono">.docx</span> file ready to download.
            </p>
          </div>

          {/* Collapsible LLM model selection */}
          <section className="mb-6 border border-slate-800 rounded-2xl bg-slate-900/70">
            <button
              type="button"
              onClick={() => setShowModels((prev) => !prev)}
              className="w-full flex items-center justify-between px-4 py-3 text-left text-xs uppercase tracking-[0.16em] text-slate-400 hover:bg-slate-900/60 transition"
            >
              <span>LLM model for translation</span>
              <span className="text-slate-400 text-lg">{showModels ? "▲" : "▼"}</span>
            </button>

            {showModels && (
              <div className="p-4 flex flex-col gap-3 border-t border-slate-800">
                <p className="text-[11px] text-slate-500 max-w-xl">
                  Choose the model that best matches the domain of your text:
                  engineering, academic or scientific terminology. The selected
                  model will be sent to the backend together with the text or file.
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

          {/* Text + file: two columns */}
          <div className="grid md:grid-cols-2 gap-4 md:gap-6">
            {/* Left: text input */}
            <form
              onSubmit={handleTranslate}
              className="border border-slate-800 rounded-2xl bg-slate-900/70 p-4 flex flex-col gap-3"
            >
              <div className="flex items-center justify-between gap-2">
                <label className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  Source text
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
                placeholder="Type text to translate..."
                className="min-h-[180px] max-h-[260px] w-full text-sm bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 resize-y outline-none focus:border-indigo-500"
              />

              <div className="flex flex-wrap gap-2 justify-between items-center pt-1">
                <div className="flex gap-2 text-[11px] text-slate-500">
                  <span>Language: {sourceLang.toUpperCase()}</span>
                  <span>•</span>
                  <span>Characters: {sourceText.length}</span>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleClear}
                    className="px-3 py-1.5 text-xs rounded-xl border border-slate-700 hover:border-slate-500 text-slate-300 transition-colors"
                  >
                    Clear
                  </button>
                  <button
                    type="submit"
                    disabled={!sourceText.trim() || isTranslating}
                    className="px-4 py-1.5 text-xs rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-60 disabled:cursor-not-allowed font-medium transition-colors"
                  >
                    {isTranslating ? "Processing..." : "Text → .docx (EN)"}
                  </button>
                </div>
              </div>
            </form>

            {/* Right: file upload */}
            <div className="border border-slate-800 rounded-2xl bg-slate-900/70 p-4 flex flex-col gap-3">
              <div className="flex items-center justify-between gap-2 mb-1">
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                    File translation
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Supported formats: PDF, DOC, DOCX, TXT
                  </p>
                </div>
              </div>

              <label className="flex flex-col items-center justify-center gap-2 border border-dashed border-slate-700 rounded-xl px-4 py-6 cursor-pointer hover:border-indigo-500 transition-colors">
                <span className="text-xs text-slate-300">
                  Click to choose a file
                </span>
                <span className="text-[11px] text-slate-500">
                  or drag and drop it here (drag & drop handling not implemented yet)
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
                  <span className="truncate">Selected file: {fileName}</span>
                  <button
                    type="button"
                    onClick={handleFileClear}
                    className="px-2 py-1 text-[11px] rounded-lg border border-slate-700 hover:border-slate-500 text-slate-300 transition-colors flex-shrink-0"
                  >
                    Remove
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
                    ? "Processing file..."
                    : "File → .docx (EN)"}
                </button>
              </div>
            </div>
          </div>

          {/* Result section: always about .docx */}
          <div className="mt-6 border border-slate-800 rounded-2xl bg-slate-900/40 p-4 flex flex-col gap-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  Result (.docx file)
                </p>
                <p className="text-[11px] text-slate-500">
                  This is where the download link or information about the
                  generated .docx file will appear.
                </p>
              </div>
            </div>

            <div className="relative flex-1">
              <div className="min-h-[140px] max-h-[220px] w-full text-sm bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 overflow-auto whitespace-pre-wrap">
                {fileResult ? (
                  fileResult
                ) : (
                  <span className="text-slate-500 text-xs">
                    After a successful backend request, you should return a link
                    to a <span className="font-mono">.docx</span> file. You can
                    show that link here or render a “Download .docx” button.
                  </span>
                )}
              </div>
            </div>

            <p className="text-[11px] text-slate-500">
              Backend logic: endpoints
              <span className="font-mono"> /api/translate</span> and
              <span className="font-mono"> /api/translate-file</span> accept text
              or a file plus the selected LLM model and return a link to the
              generated <span className="font-mono">.docx</span> document with the
              English translation.
            </p>
          </div>

          <div className="mt-6 text-[11px] text-slate-500 border-t border-slate-800 pt-3 flex flex-wrap gap-2 justify-between">
            <span>
              Built with <span className="font-mono">React</span> +
              <span className="font-mono"> Tailwind CSS</span>
            </span>
            <span>
              Example: RU / AR / ZH → EN — text and files, LLM model selection,
              frontend-only demo without a real API.
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}
