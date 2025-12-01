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

type ModelFeature = {
  name: string;
  score: number; // 0-100
};

type ModelInfo = {
  id: ModelId;
  label: string;
  hint: string;
  description: string;
  bestFor: string[];
  features: ModelFeature[];
  icon: string;
};

const MODELS: ModelInfo[] = [
  {
    id: "general",
    label: "General",
    hint: "Generic translation, mixed topics",
    description: "Универсальная модель для повседневных текстов и смешанных тем",
    bestFor: [
      "Письма и сообщения",
      "Блоги и статьи",
      "Общая документация",
      "Разговорная речь"
    ],
    features: [
      { name: "Универсальность", score: 95 },
      { name: "Скорость", score: 90 },
      { name: "Техническая точность", score: 60 },
      { name: "Академический стиль", score: 55 },
      { name: "Научная терминология", score: 50 }
    ],
    icon: "🌐"
  },
  {
    id: "engineering",
    label: "Engineering",
    hint: "Technical and engineering terminology",
    description: "Специализированная модель для технических и инженерных документов",
    bestFor: [
      "Технические спецификации",
      "Инструкции по эксплуатации",
      "Чертежи и схемы",
      "Проектная документация"
    ],
    features: [
      { name: "Универсальность", score: 50 },
      { name: "Скорость", score: 75 },
      { name: "Техническая точность", score: 95 },
      { name: "Академический стиль", score: 70 },
      { name: "Научная терминология", score: 80 }
    ],
    icon: "⚙️"
  },
  {
    id: "academic",
    label: "Academic",
    hint: "Academic texts, papers, essays",
    description: "Оптимизирована для академических текстов, научных статей и эссе",
    bestFor: [
      "Научные статьи",
      "Диссертации",
      "Эссе и рефераты",
      "Академические презентации"
    ],
    features: [
      { name: "Универсальность", score: 60 },
      { name: "Скорость", score: 70 },
      { name: "Техническая точность", score: 75 },
      { name: "Академический стиль", score: 95 },
      { name: "Научная терминология", score: 85 }
    ],
    icon: "📚"
  },
  {
    id: "scientific",
    label: "Scientific",
    hint: "Scientific texts, terms, reports",
    description: "Высокая точность для научных текстов и специализированной терминологии",
    bestFor: [
      "Научные отчеты",
      "Исследовательские работы",
      "Медицинские документы",
      "Специализированные публикации"
    ],
    features: [
      { name: "Универсальность", score: 45 },
      { name: "Скорость", score: 65 },
      { name: "Техническая точность", score: 90 },
      { name: "Академический стиль", score: 90 },
      { name: "Научная терминология", score: 95 }
    ],
    icon: "🔬"
  },
];

// API base URL - используем прокси из vite.config.ts
// Для разработки прокси перенаправляет /api на localhost:8000
// Для продакшена можно задать VITE_API_URL в .env
const API_BASE_URL = "";

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
  const [hoveredModel, setHoveredModel] = useState<ModelId | null>(null);
  const [mobileModelDetail, setMobileModelDetail] = useState<ModelId | null>(null);

  // Text translation (result is still .docx)
  async function handleTranslate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!sourceText.trim()) return;

    setIsTranslating(true);
    setFileResult("");
    setFileError("");

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
        const errorData = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errorData.detail || `HTTP error! status: ${res.status}`);
      }

      const data = await res.json();
      
      // Формируем полный URL для скачивания
      const downloadUrl = data.downloadUrl.startsWith("http") 
        ? data.downloadUrl 
        : `${API_BASE_URL || window.location.origin}${data.downloadUrl}`;
      
      setFileResult(downloadUrl);
      setIsTranslating(false);
    } catch (err) {
      console.error(err);
      const errorMessage = err instanceof Error 
        ? `Error: ${err.message}` 
        : "Error while translating text. Please check your server connection.";
      setFileResult(errorMessage);
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
    setFileError("");

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
        const errorData = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errorData.detail || `HTTP error! status: ${res.status}`);
      }

      const data = await res.json();
      
      // Формируем полный URL для скачивания
      const downloadUrl = data.downloadUrl.startsWith("http") 
        ? data.downloadUrl 
        : `${API_BASE_URL || window.location.origin}${data.downloadUrl}`;
      
      setFileResult(downloadUrl);
      setIsFileTranslating(false);
    } catch (err) {
      console.error(err);
      const errorMessage = err instanceof Error 
        ? `Error: ${err.message}` 
        : "Error while translating file. Please check your server.";
      setFileResult(errorMessage);
      setIsFileTranslating(false);
    }
  }

  function handleFileClear() {
    setFile(null);
    setFileName("");
    setFileResult("");
    setFileError("");
  }

  function handleResultClear() {
    setFileResult("");
  }

  // Check if result is a URL (absolute or relative download path)
  function isUrl(str: string): boolean {
    if (!str) return false;
    // Проверяем абсолютные URL
    try {
      const url = new URL(str);
      return url.protocol === "http:" || url.protocol === "https:";
    } catch {
      // Проверяем относительные пути для скачивания
      return str.startsWith("/api/download/") || str.includes("/api/download/");
    }
  }

  // Check if result is an error
  function isError(str: string): boolean {
    return str.toLowerCase().includes("error") || str.toLowerCase().includes("failed");
  }

  // Компонент радарной диаграммы
  function RadarChart({ features, size = 200 }: { features: ModelFeature[]; size?: number }) {
    const centerX = size / 2;
    const centerY = size / 2;
    const radius = size * 0.35;
    const numPoints = features.length;
    const angleStep = (2 * Math.PI) / numPoints;

    // Вычисляем точки для полигона
    const points = features.map((feature, index) => {
      const angle = index * angleStep - Math.PI / 2; // Начинаем сверху
      const distance = (radius * feature.score) / 100;
      const x = centerX + distance * Math.cos(angle);
      const y = centerY + distance * Math.sin(angle);
      return { x, y };
    });

    // Создаем строку пути для полигона
    const pathData = points.map((point, index) => 
      `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`
    ).join(' ') + ' Z';

    // Создаем точки для осей и меток
    const axisPoints = Array.from({ length: numPoints }, (_, index) => {
      const angle = index * angleStep - Math.PI / 2;
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);
      return { x, y, angle, feature: features[index] };
    });

    // Создаем концентрические круги для сетки
    const gridLevels = [0.2, 0.4, 0.6, 0.8, 1.0];

    return (
      <svg width={size} height={size} className="mx-auto" viewBox={`0 0 ${size} ${size}`}>
        {/* Концентрические многоугольники сетки */}
        {gridLevels.map((level, idx) => {
          const gridPoints = axisPoints.map((point) => {
            const gridX = centerX + (point.x - centerX) * level;
            const gridY = centerY + (point.y - centerY) * level;
            return `${gridX},${gridY}`;
          }).join(' ');
          
          return (
            <polygon
              key={idx}
              points={gridPoints}
              fill="none"
              stroke="rgb(51, 65, 85)"
              strokeWidth="1"
              opacity={idx === gridLevels.length - 1 ? "0.5" : "0.2"}
            />
          );
        })}

        {/* Оси */}
        {axisPoints.map((point, index) => (
          <line
            key={index}
            x1={centerX}
            y1={centerY}
            x2={point.x}
            y2={point.y}
            stroke="rgb(51, 65, 85)"
            strokeWidth="1"
            opacity="0.4"
          />
        ))}

        {/* Полигон данных с градиентом */}
        <defs>
          <linearGradient id="radarGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgb(99, 102, 241)" stopOpacity="0.4" />
            <stop offset="100%" stopColor="rgb(139, 92, 246)" stopOpacity="0.3" />
          </linearGradient>
        </defs>
        <path
          d={pathData}
          fill="url(#radarGradient)"
          stroke="rgb(99, 102, 241)"
          strokeWidth="2.5"
          strokeLinejoin="round"
        />

        {/* Точки данных */}
        {points.map((point, index) => (
          <g key={index}>
            <circle
              cx={point.x}
              cy={point.y}
              r="5"
              fill="rgb(99, 102, 241)"
              stroke="rgb(30, 41, 59)"
              strokeWidth="2"
            />
            <circle
              cx={point.x}
              cy={point.y}
              r="2"
              fill="rgb(255, 255, 255)"
            />
          </g>
        ))}

        {/* Метки осей */}
        {axisPoints.map((point, index) => {
          const labelRadius = radius * 1.25;
          const labelX = centerX + labelRadius * Math.cos(point.angle);
          const labelY = centerY + labelRadius * Math.sin(point.angle);
          
          // Определяем выравнивание текста в зависимости от угла
          let textAnchor: "start" | "middle" | "end" = "middle";
          let dominantBaseline: "auto" | "middle" | "hanging" | "alphabetic" = "middle";
          
          if (Math.abs(Math.cos(point.angle)) > 0.7) {
            textAnchor = Math.cos(point.angle) > 0 ? "start" : "end";
          }
          if (Math.abs(Math.sin(point.angle)) > 0.7) {
            dominantBaseline = Math.sin(point.angle) > 0 ? "hanging" : "alphabetic";
          }
          
          return (
            <g key={index}>
              <text
                x={labelX}
                y={labelY}
                textAnchor={textAnchor}
                dominantBaseline={dominantBaseline}
                className="text-[10px] fill-slate-200 font-semibold"
                style={{ 
                  textShadow: '0 1px 2px rgba(0, 0, 0, 0.5)',
                }}
              >
                {point.feature.name}
              </text>
              <text
                x={labelX}
                y={labelY + (dominantBaseline === "hanging" ? 12 : -8)}
                textAnchor={textAnchor}
                dominantBaseline={dominantBaseline}
                className="text-[9px] fill-indigo-400 font-mono font-bold"
                style={{ 
                  textShadow: '0 1px 2px rgba(0, 0, 0, 0.5)',
                }}
              >
                {point.feature.score}%
              </text>
            </g>
          );
        })}
      </svg>
    );
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

                <div className="flex flex-wrap gap-2 mt-1 relative">
                  {MODELS.map((m) => {
                    const isActive = m.id === model;
                    const isHovered = hoveredModel === m.id;
                    return (
                      <div
                        key={m.id}
                        className="relative"
                        onMouseEnter={() => setHoveredModel(m.id)}
                        onMouseLeave={() => setHoveredModel(null)}
                      >
                        <button
                          type="button"
                          onClick={(e) => {
                            // На мобильных показываем детали, на десктопе просто выбираем
                            if (window.innerWidth < 768) {
                              e.stopPropagation();
                              setMobileModelDetail(m.id);
                            } else {
                              setModel(m.id);
                            }
                          }}
                          className={
                            "px-3 py-1.5 text-xs rounded-xl border transition-colors text-left relative z-10 " +
                            (isActive
                              ? "border-indigo-400 bg-indigo-500/20 text-slate-50"
                              : "border-slate-700 bg-slate-900/80 text-slate-200 hover:border-slate-500")
                          }
                        >
                          <div className="flex items-center gap-1.5">
                            <span className="text-base">{m.icon}</span>
                            <div>
                              <div className="font-semibold text-[11px] mb-0.5">{m.label}</div>
                              <div className="text-[11px] text-slate-400">{m.hint}</div>
                            </div>
                          </div>
                        </button>

                        {/* Всплывающее окно с информацией - только на десктопе */}
                        {isHovered && (
                          <div className="hidden md:block absolute left-0 top-full mt-2 w-80 max-w-[calc(100vw-2rem)] z-50 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-3 sm:p-4 transition-all duration-200 animate-in fade-in slide-in-from-top-2"
                            onMouseEnter={() => setHoveredModel(m.id)}
                            onMouseLeave={() => setHoveredModel(null)}
                            style={{ 
                              left: '50%',
                              transform: 'translateX(-50%)',
                              maxWidth: 'min(320px, calc(100vw - 2rem))'
                            }}
                          >
                            <div className="flex items-start gap-3 mb-3">
                              <span className="text-2xl">{m.icon}</span>
                              <div className="flex-1">
                                <h3 className="font-semibold text-sm text-slate-50 mb-1">{m.label}</h3>
                                <p className="text-[11px] text-slate-400 leading-relaxed">{m.description}</p>
                              </div>
                            </div>

                            {/* Диаграммы характеристик */}
                            <div className="mb-4 space-y-2.5">
                              <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">Характеристики</p>
                              {m.features.map((feature, idx) => {
                                // Определяем цвет в зависимости от значения
                                const getColorClass = (score: number) => {
                                  if (score >= 85) return "from-emerald-500 to-emerald-400";
                                  if (score >= 70) return "from-indigo-500 to-indigo-400";
                                  if (score >= 55) return "from-amber-500 to-amber-400";
                                  return "from-slate-500 to-slate-400";
                                };
                                
                                return (
                                  <div key={idx} className="space-y-1">
                                    <div className="flex items-center justify-between text-[11px]">
                                      <span className="text-slate-300">{feature.name}</span>
                                      <span className="text-slate-500 font-mono">{feature.score}%</span>
                                    </div>
                                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                      <div
                                        className={`h-full bg-gradient-to-r ${getColorClass(feature.score)} rounded-full transition-all duration-500`}
                                        style={{ width: `${feature.score}%` }}
                                      />
                                    </div>
                                  </div>
                                );
                              })}
                            </div>

                            {/* Лучше всего для */}
                            <div>
                              <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">Лучше всего для</p>
                              <div className="flex flex-wrap gap-1.5">
                                {m.bestFor.map((item, idx) => (
                                  <span
                                    key={idx}
                                    className="px-2 py-1 text-[10px] bg-slate-800/60 border border-slate-700 rounded-lg text-slate-300"
                                  >
                                    {item}
                                  </span>
                                ))}
                              </div>
                            </div>

                            {/* Стрелка указывающая на кнопку */}
                            <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-4 h-4 bg-slate-900 border-l border-t border-slate-700 rotate-45"></div>
                          </div>
                        )}
                      </div>
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

              <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2 sm:justify-between sm:items-center pt-1">
                <div className="flex gap-2 text-[11px] text-slate-500">
                  <span>Language: {sourceLang.toUpperCase()}</span>
                  <span>&#8226;</span>
                  <span>Characters: {sourceText.length}</span>
                </div>
                <div className="flex gap-2 w-full sm:w-auto">
                  <button
                    type="button"
                    onClick={handleClear}
                    className="flex-1 sm:flex-none px-3 py-1.5 text-xs rounded-xl border border-slate-700 hover:border-slate-500 text-slate-300 transition-colors"
                  >
                    Clear
                  </button>
                  <button
                    type="submit"
                    disabled={!sourceText.trim() || isTranslating}
                    className="flex-1 sm:flex-none px-4 py-1.5 text-xs rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-60 disabled:cursor-not-allowed font-medium transition-colors"
                  >
                    <span className="hidden sm:inline">{isTranslating ? "Processing..." : "Text → .docx (EN)"}</span>
                    <span className="sm:hidden">{isTranslating ? "Processing..." : "Translate"}</span>
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

            {/* Dropzone when NO file is selected */}
            {!fileName && (
              <label className="flex flex-col items-center justify-center gap-2 border border-dashed border-slate-700 rounded-xl px-4 py-6 cursor-pointer hover:border-indigo-500 transition-colors">
                <span className="text-xs text-slate-300">Click to choose a file</span>
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
            )}

            {/* Compact card when file IS selected */}
            {fileName && (
              <div className="flex flex-col items-center justify-center gap-2 border border-slate-700 rounded-xl px-4 py-6">
                <div className="flex flex-col items-center gap-1 w-full min-w-0">
                  {/* File icon */}
                  <span className="text-indigo-400 text-2xl">📄</span>
                  <span className="text-[11px] text-slate-200 truncate text-center w-full max-w-full px-2" title={fileName}>
                    {fileName}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleFileClear}
                  className="px-3 py-1 text-[11px] rounded-lg border border-slate-700 hover:border-slate-500 text-slate-300 transition-colors"
                >
                  Remove file
                </button>
              </div>
            )}

            {fileError && (
              <p className="text-[11px] text-rose-400 mt-1">{fileError}</p>
            )}

            <div className="flex justify-end mt-1">
              <button
                type="button"
                onClick={handleFileTranslate}
                disabled={!file || !!fileError || isFileTranslating}
                className="w-full sm:w-auto px-4 py-1.5 text-xs rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-60 disabled:cursor-not-allowed font-medium transition-colors"
              >
                <span className="hidden sm:inline">{isFileTranslating ? "Processing file..." : "File → .docx (EN)"}</span>
                <span className="sm:hidden">{isFileTranslating ? "Processing..." : "Translate"}</span>
              </button>
            </div>
          </div>
          </div>

          {/* Result section: always about .docx */}
          {(fileResult || isTranslating || isFileTranslating) && (
            <div className="mt-6 border border-slate-800 rounded-2xl bg-slate-900/70 p-4 flex flex-col gap-4 transition-all duration-300">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    isTranslating || isFileTranslating
                      ? "bg-indigo-500/20 border border-indigo-500/30"
                      : isError(fileResult)
                      ? "bg-rose-500/20 border border-rose-500/30"
                      : fileResult && isUrl(fileResult)
                      ? "bg-emerald-500/20 border border-emerald-500/30"
                      : fileResult
                      ? "bg-slate-800 border border-slate-700"
                      : "bg-slate-800 border border-slate-700"
                  }`}>
                    {isTranslating || isFileTranslating ? (
                      <svg className="w-5 h-5 text-indigo-400 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                    ) : isError(fileResult) ? (
                      <span className="text-rose-400 text-xl">⚠️</span>
                    ) : fileResult && isUrl(fileResult) ? (
                      <span className="text-emerald-400 text-xl">✓</span>
                    ) : fileResult ? (
                      <span className="text-slate-400 text-xl">📄</span>
                    ) : (
                      <span className="text-slate-500 text-xl">📋</span>
                    )}
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-400 mb-0.5">
                      Translation Result
                    </p>
                    <p className="text-[11px] text-slate-500">
                      {isTranslating || isFileTranslating
                        ? "Processing your request..."
                        : isError(fileResult)
                        ? "Translation failed"
                        : fileResult && isUrl(fileResult)
                        ? "Ready to download"
                        : fileResult
                        ? "Translation completed"
                        : "Waiting for result"}
                    </p>
                  </div>
                </div>
                {fileResult && !isTranslating && !isFileTranslating && (
                  <button
                    type="button"
                    onClick={handleResultClear}
                    className="mt-2 sm:mt-0 px-3 py-1.5 text-xs rounded-xl border border-slate-700 hover:border-slate-500 text-slate-300 transition-colors"
                  >
                    Clear
                  </button>
                )}
              </div>

              {fileResult && !isTranslating && !isFileTranslating && (
                <div className="space-y-3">
                  {isUrl(fileResult) ? (
                    <div className="flex flex-col gap-3">
                      <div className="flex items-center gap-2 p-3 bg-slate-950/60 border border-slate-800 rounded-xl">
                        <span className="text-emerald-400 text-lg">📥</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-slate-400 mb-1">Download link</p>
                          <a
                            href={fileResult}
                            download
                            className="text-sm text-indigo-400 hover:text-indigo-300 truncate block underline decoration-dotted underline-offset-2"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {fileResult}
                          </a>
                        </div>
                      </div>
                      <a
                        href={fileResult}
                        download
                        className="w-full px-4 py-3 text-sm rounded-xl bg-indigo-500 hover:bg-indigo-400 font-medium transition-colors flex items-center justify-center gap-2"
                      >
                        <span>⬇</span>
                        <span>Download .docx file</span>
                      </a>
                    </div>
                  ) : (
                    <div className="min-h-[100px] max-h-[200px] w-full text-sm bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-3 overflow-auto whitespace-pre-wrap">
                      <div className={isError(fileResult) ? "text-rose-400" : "text-slate-200"}>
                        {fileResult}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {(isTranslating || isFileTranslating) && (
                <div className="flex items-center gap-3 p-4 bg-slate-950/60 border border-slate-800 rounded-xl">
                  <div className="flex-1">
                    <div className="h-2 bg-slate-800 rounded-full overflow-hidden relative">
                      <div className="h-full bg-indigo-500 rounded-full w-3/5 animate-pulse"></div>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-2">
                      {isTranslating ? "Translating your text..." : "Processing your file..."}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

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

      {/* Модальное окно с радарной диаграммой для мобильных */}
      {mobileModelDetail && (
        <div 
          className="md:hidden fixed inset-0 z-50 bg-slate-950/95 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setMobileModelDetail(null)}
        >
          <div 
            className="w-full max-w-sm bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {(() => {
              const selectedModel = MODELS.find(m => m.id === mobileModelDetail);
              if (!selectedModel) return null;

              return (
                <>
                  {/* Заголовок */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <span className="text-3xl">{selectedModel.icon}</span>
                      <div>
                        <h3 className="font-semibold text-lg text-slate-50">{selectedModel.label}</h3>
                        <p className="text-[11px] text-slate-400">{selectedModel.hint}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => setMobileModelDetail(null)}
                      className="w-8 h-8 flex items-center justify-center rounded-lg border border-slate-700 hover:border-slate-500 text-slate-400 hover:text-slate-200 transition-colors"
                    >
                      ✕
                    </button>
                  </div>

                  {/* Описание */}
                  <p className="text-sm text-slate-300 mb-6 leading-relaxed">
                    {selectedModel.description}
                  </p>

                  {/* Радарная диаграмма */}
                  <div className="mb-6 p-4 bg-slate-950/60 border border-slate-800 rounded-xl">
                    <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-4 text-center">
                      Характеристики модели
                    </p>
                    <RadarChart features={selectedModel.features} size={280} />
                  </div>

                  {/* Лучше всего для */}
                  <div className="mb-6">
                    <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-3">
                      Лучше всего для
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {selectedModel.bestFor.map((item, idx) => (
                        <span
                          key={idx}
                          className="px-3 py-1.5 text-[11px] bg-slate-800/60 border border-slate-700 rounded-lg text-slate-300"
                        >
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Кнопка выбора */}
                  <button
                    onClick={() => {
                      setModel(selectedModel.id);
                      setMobileModelDetail(null);
                    }}
                    className={`w-full px-4 py-3 text-sm rounded-xl font-medium transition-colors ${
                      model === selectedModel.id
                        ? "bg-indigo-500 text-slate-50"
                        : "bg-indigo-500 hover:bg-indigo-400 text-slate-50"
                    }`}
                  >
                    {model === selectedModel.id ? "✓ Выбрано" : "Выбрать эту модель"}
                  </button>
                </>
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
}
