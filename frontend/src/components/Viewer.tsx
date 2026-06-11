import { memo, useMemo } from "react";
import { api, Element, GroupId, GROUP_COLOR, LANG_COLOR, PageSummary } from "../api";

export type HighlightMode = "group" | "depth" | "language" | "encoding";
export type CursorMode = "pointer" | "crosshair" | "precision" | "focus";

const CURSOR_CSS: Record<CursorMode, string> = {
  pointer: "default",
  crosshair: "crosshair",
  precision: "crosshair",
  focus: "pointer",
};

interface Props {
  documentId: string;
  page: PageSummary | null;
  elements: Element[];
  loading: boolean;
  zoom: number; setZoom: (z: number) => void;
  pageNumber: number; setPageNumber: (n: number) => void;
  totalPages: number;
  enabledGroups: Set<GroupId>;
  soloGroup: GroupId | null;
  highlightMode: HighlightMode; setHighlightMode: (m: HighlightMode) => void;
  cursorMode: CursorMode; setCursorMode: (m: CursorMode) => void;
  hovered: Element | null; setHovered: (e: Element | null) => void;
  selected: Element | null; setSelected: (e: Element | null) => void;
  onResetFilters: () => void;
}

function depthColor(order: number, max: number): string {
  // глубина: градиент от светлого к тёмному (ТЗ 7.2)
  const t = max > 0 ? order / max : 0;
  const v = Math.round(225 - t * 160);
  return `rgb(${v},${Math.round(v * 0.92)},${Math.round(60 + t * 60)})`;
}

export function elementColor(
  e: Element, mode: HighlightMode, maxOrder: number,
): string {
  switch (mode) {
    case "group": return GROUP_COLOR[e.groupId];
    case "depth": return depthColor(e.drawOrder, maxOrder);
    case "language":
      return LANG_COLOR[e.languageCode ?? "unknown"] ?? "#707A8E";
    case "encoding":
      return e.encodingStatus === "broken_encoding" ? "#E0524F" : "#3D4860";
  }
}

export const Viewer = memo(function Viewer(p: Props) {
  const maxOrder = useMemo(
    () => p.elements.reduce((m, e) => Math.max(m, e.drawOrder), 1),
    [p.elements],
  );
  const visible = useMemo(() => {
    return p.elements.filter((e) =>
      p.soloGroup ? e.groupId === p.soloGroup : p.enabledGroups.has(e.groupId),
    );
  }, [p.elements, p.enabledGroups, p.soloGroup]);

  const previewScale = Math.min(2, Math.max(0.5, p.zoom * 1.5));

  return (
    <div className="viewer">
      <div className="toolbar">
        <div className="group">
          <button className="btn" onClick={() => p.setPageNumber(Math.max(1, p.pageNumber - 1))}>‹</button>
          <span className="mono pageinfo">{p.pageNumber} / {p.totalPages}</span>
          <button className="btn" onClick={() => p.setPageNumber(Math.min(p.totalPages, p.pageNumber + 1))}>›</button>
        </div>
        <span className="sep" />
        <select value={p.zoom} onChange={(e) => p.setZoom(+e.target.value)} title="Масштаб">
          {[0.5, 0.75, 1, 1.5, 2].map((z) => (
            <option key={z} value={z}>{Math.round(z * 100)}%</option>
          ))}
        </select>
        <select
          value={p.highlightMode}
          onChange={(e) => p.setHighlightMode(e.target.value as HighlightMode)}
          title="Режим подсветки"
        >
          <option value="group">По типу элемента</option>
          <option value="depth">По глубине</option>
          <option value="language">По языку</option>
          <option value="encoding">Битые кодировки</option>
        </select>
        <select
          value={p.cursorMode}
          onChange={(e) => p.setCursorMode(e.target.value as CursorMode)}
          title="Режим курсора"
        >
          <option value="pointer">Обычный курсор</option>
          <option value="crosshair">Перекрестие</option>
          <option value="precision">Прицельный (мелкие)</option>
          <option value="focus">Фокус (усиленная подсветка)</option>
        </select>
        <button className="btn" onClick={p.onResetFilters}>Сбросить фильтры</button>
        <span className="counter mono">
          {p.loading ? "загрузка элементов…" : `элементов: ${visible.length}`}
        </span>
      </div>

      <div className="canvas-wrap">
        {p.page && (
          <div
            className="canvas-stack"
            style={{
              width: p.page.pageWidth * p.zoom,
              height: p.page.pageHeight * p.zoom,
              cursor: CURSOR_CSS[p.cursorMode],
            }}
          >
            <img
              src={api.previewUrl(p.documentId, p.pageNumber, previewScale)}
              width={p.page.pageWidth * p.zoom}
              height={p.page.pageHeight * p.zoom}
              alt={`Страница ${p.pageNumber}`}
              draggable={false}
            />
            <svg
              viewBox={`0 0 ${p.page.pageWidth} ${p.page.pageHeight}`}
              onMouseLeave={() => p.setHovered(null)}
              onClick={() => p.setSelected(p.hovered)}
            >
              {visible.map((e) => {
                const active =
                  p.hovered?.elementId === e.elementId ||
                  p.selected?.elementId === e.elementId;
                const color = elementColor(e, p.highlightMode, maxOrder);
                const boost = p.cursorMode === "focus" ? 0.25 : 0;
                const thin = p.cursorMode === "precision";
                return (
                  <rect
                    key={e.elementId}
                    x={e.x1} y={e.y1}
                    width={Math.max(e.width, 0.5)}
                    height={Math.max(e.height, 0.5)}
                    fill={color}
                    fillOpacity={active ? 0.42 + boost : 0.10 + boost / 2}
                    stroke={color}
                    strokeWidth={active ? (thin ? 1 : 2.2) : thin ? 0.4 : 0.9}
                    vectorEffect="non-scaling-stroke"
                    onMouseEnter={() => p.setHovered(e)}
                  />
                );
              })}
            </svg>
          </div>
        )}
        {!p.page && <div className="canvas-empty">Страница ещё разбирается…</div>}
      </div>
    </div>
  );
});
