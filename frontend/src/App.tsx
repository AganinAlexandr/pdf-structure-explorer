import { useCallback, useEffect, useRef, useState } from "react";
import {
  api, DocumentCard, Element, GroupId, GROUPS, Layer, LanguageStat,
  PageSummary, ParseStatus,
} from "./api";
import { Thumbnails } from "./components/Thumbnails";
import { Viewer, CursorMode, HighlightMode } from "./components/Viewer";
import { Inspector } from "./components/Inspector";

export default function App() {
  const [doc, setDoc] = useState<DocumentCard | null>(null);
  const [status, setStatus] = useState<ParseStatus | null>(null);
  const [pages, setPages] = useState<PageSummary[]>([]);
  const [pageNumber, setPageNumber] = useState(1);
  const [elements, setElements] = useState<Element[]>([]);
  const [loadingPage, setLoadingPage] = useState(false);
  const [layers, setLayers] = useState<Layer[]>([]);
  const [languages, setLanguages] = useState<LanguageStat[]>([]);

  const [enabledGroups, setEnabledGroups] = useState<Set<GroupId>>(
    new Set(GROUPS.map((g) => g.id)),
  );
  const [soloGroup, setSoloGroup] = useState<GroupId | null>(null);
  const [highlightMode, setHighlightMode] = useState<HighlightMode>("group");
  const [cursorMode, setCursorMode] = useState<CursorMode>("pointer");
  const [zoom, setZoom] = useState(1.0);
  const [hovered, setHovered] = useState<Element | null>(null);
  const [selected, setSelected] = useState<Element | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState("");
  const pollRef = useRef<number | null>(null);

  // ---------------- загрузка и разбор --------------------------------
  const openFile = useCallback(async (file: File) => {
    setError("");
    try {
      const d = await api.upload(file);
      setDoc(d);
      setPages([]);
      setElements([]);
      setSelected(null);
      setPageNumber(1);
      await api.parse(d.documentId);
      const poll = async () => {
        const s = await api.status(d.documentId);
        setStatus(s);
        if (s.status === "processing") {
          pollRef.current = window.setTimeout(poll, 1500);
          // страницы доступны по мере разбора
          api.pages(d.documentId).then((p) => setPages(p.items)).catch(() => {});
        } else if (s.status === "parsed") {
          const p = await api.pages(d.documentId);
          setPages(p.items);
          api.layers(d.documentId).then((l) => setLayers(l.items));
          api.languages(d.documentId).then((l) => setLanguages(l.items));
        } else if (s.status === "failed") {
          setError(`Разбор не удался: ${s.error ?? ""}`);
        }
      };
      poll();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => () => {
    if (pollRef.current) window.clearTimeout(pollRef.current);
  }, []);

  // ---------------- элементы текущей страницы ------------------------
  useEffect(() => {
    if (!doc) return;
    const ready = pages.some((p) => p.pageNumber === pageNumber);
    if (!ready) return;
    let cancelled = false;
    setLoadingPage(true);
    api.pageElements(doc.documentId, pageNumber)
      .then((els) => { if (!cancelled) setElements(els); })
      .catch((e) => setError(String(e)))
      .finally(() => { if (!cancelled) setLoadingPage(false); });
    setHovered(null);
    setSelected(null);
    return () => { cancelled = true; };
  }, [doc, pageNumber, pages]);

  const page = pages.find((p) => p.pageNumber === pageNumber) ?? null;

  const resetFilters = () => {
    setEnabledGroups(new Set(GROUPS.map((g) => g.id)));
    setSoloGroup(null);
    setHighlightMode("group");
    setSelected(null);
  };

  // ---------------- drag & drop --------------------------------------
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = Array.from(e.dataTransfer.files).find((x) =>
      x.name.toLowerCase().endsWith(".pdf"),
    );
    if (f) openFile(f);
  };

  return (
    <div
      className="app"
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={(e) => { if (e.target === e.currentTarget) setDragOver(false); }}
      onDrop={onDrop}
    >
      <header>
        <div className="logo">
          Разбор <b>PDF</b>
          <small>структура · постранично</small>
        </div>
        <label className="btn primary">
          Открыть PDF…
          <input
            type="file" accept="application/pdf,.pdf" hidden
            onChange={(e) => e.target.files?.[0] && openFile(e.target.files[0])}
          />
        </label>
        {doc && (
          <div className="docinfo">
            <span className="mono">{doc.fileName}</span>
            {status?.status === "processing" && (
              <span className="progress">
                <span className="bar" style={{ width: `${status.progressPercent}%` }} />
                <span className="pct mono">
                  {status.processedPages}/{status.totalPages}
                </span>
              </span>
            )}
            {status?.status === "parsed" && (
              <span className="badge ok">разобран</span>
            )}
            {status?.status === "parsed" && (
              <button
                className="btn"
                onClick={() =>
                  api.exportDoc(doc.documentId).then((r) =>
                    alert(r.ok ? `Экспорт готов: ${r.data.exportPath}` :
                      `Ошибка экспорта: ${r.error?.message}`))
                }
              >
                Экспорт CSV
              </button>
            )}
          </div>
        )}
        {error && <span className="badge err">{error}</span>}
      </header>

      {!doc ? (
        <div className={"dropzone" + (dragOver ? " over" : "")}>
          <div>
            <h1>Перетащите PDF-файл сюда</h1>
            <p>
              Документ будет разобран постранично: текст, линии, рамки,
              изображения и таблицы с ячейками. Backend должен быть запущен
              на порту 8000.
            </p>
          </div>
        </div>
      ) : (
        <div className="cols">
          <Thumbnails
            documentId={doc.documentId}
            pages={pages}
            current={pageNumber}
            onSelect={setPageNumber}
          />
          <Viewer
            documentId={doc.documentId}
            page={page}
            elements={elements}
            loading={loadingPage}
            zoom={zoom} setZoom={setZoom}
            pageNumber={pageNumber} setPageNumber={setPageNumber}
            totalPages={doc.pageCount}
            enabledGroups={enabledGroups}
            soloGroup={soloGroup}
            highlightMode={highlightMode} setHighlightMode={setHighlightMode}
            cursorMode={cursorMode} setCursorMode={setCursorMode}
            hovered={hovered} setHovered={setHovered}
            selected={selected} setSelected={setSelected}
            onResetFilters={resetFilters}
          />
          <Inspector
            documentId={doc.documentId}
            page={page}
            elements={elements}
            layers={layers}
            languages={languages}
            enabledGroups={enabledGroups} setEnabledGroups={setEnabledGroups}
            soloGroup={soloGroup} setSoloGroup={setSoloGroup}
            hovered={hovered}
            selected={selected} setSelected={setSelected}
          />
        </div>
      )}
      {dragOver && doc && <div className="dropveil">Отпустите, чтобы открыть PDF</div>}
    </div>
  );
}
