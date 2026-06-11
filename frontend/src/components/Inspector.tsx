import { useEffect, useState } from "react";
import {
  api, Element, GroupId, GROUPS, GROUP_COLOR, LANG_COLOR, Layer,
  LanguageStat, PageSummary, TableCardData,
} from "../api";

interface Props {
  documentId: string;
  page: PageSummary | null;
  elements: Element[];
  layers: Layer[];
  languages: LanguageStat[];
  enabledGroups: Set<GroupId>;
  setEnabledGroups: (s: Set<GroupId>) => void;
  soloGroup: GroupId | null;
  setSoloGroup: (g: GroupId | null) => void;
  hovered: Element | null;
  selected: Element | null;
  setSelected: (e: Element | null) => void;
}

const FIELD_LABELS: [keyof Element, string, (v: unknown) => string][] = [
  ["subtypeId", "Подтип", String],
  ["layerId", "Слой", String],
  ["drawOrder", "Порядок отрисовки", String],
  ["width", "Ширина, pt", (v) => String(v)],
  ["height", "Высота, pt", (v) => String(v)],
  ["bboxArea", "Площадь, pt²", (v) => String(v)],
  ["strokeWidth", "Толщина линии", (v) => `${v} pt`],
  ["lineLength", "Длина", (v) => `${v} pt`],
  ["fontName", "Шрифт", String],
  ["fontSize", "Кегль", (v) => `${v} pt`],
  ["languageCode", "Язык", String],
  ["encodingStatus", "Кодировка", String],
  ["charCount", "Символов", String],
  ["segmentCount", "Сегментов", String],
  ["cellCount", "Ячеек", String],
  ["placementCount", "Размещений", String],
];

function ElementCard({ el }: { el: Element }) {
  return (
    <div className="card">
      <div className="card-head">
        <span className="dot" style={{ background: GROUP_COLOR[el.groupId] }} />
        <span className="mono">{el.elementId}</span>
      </div>
      <dl className="props">
        {FIELD_LABELS.map(([key, label, fmt]) => {
          const v = el[key];
          if (v === undefined || v === "" || v === null) return null;
          return (
            <div key={String(key)}>
              <dt>{label}</dt>
              <dd className="mono">{fmt(v)}</dd>
            </div>
          );
        })}
        <div>
          <dt>bbox</dt>
          <dd className="mono">
            {el.x1}; {el.y1} — {el.x2}; {el.y2}
          </dd>
        </div>
      </dl>
    </div>
  );
}

function TableCard({ documentId, el }: { documentId: string; el: Element }) {
  const [table, setTable] = useState<TableCardData | null>(null);
  useEffect(() => {
    setTable(null);
    if (el.relatedTableId)
      api.table(documentId, el.relatedTableId).then(setTable).catch(() => {});
  }, [documentId, el.relatedTableId]);
  if (!table) return null;
  const filled = table.cells.filter((c) => c.textValue);
  return (
    <div className="card">
      <div className="card-head">
        <span className="dot" style={{ background: GROUP_COLOR.tables }} />
        <span className="mono">{table.tableId}</span>
        <span className={"badge " + (table.detectionConfidence === "high" ? "ok" : "warn")}>
          {table.detectionConfidence}
        </span>
      </div>
      <dl className="props">
        <div><dt>Сетка</dt><dd className="mono">{table.rowCount} × {table.columnCount}</dd></div>
        <div><dt>Ячеек</dt><dd className="mono">{table.cellCount}</dd></div>
        <div><dt>С текстом</dt><dd className="mono">{table.cellsWithText} ({Math.round(table.textFillRatio * 100)}%)</dd></div>
        {table.hasMergedCells && <div><dt>Объединения</dt><dd>есть</dd></div>}
      </dl>
      <div className="cells">
        {filled.slice(0, 30).map((c) => (
          <div key={c.cellId} className="cellrow">
            <span className="mono dim">[{c.rowIndex};{c.columnIndex}]</span>
            <span className={c.encodingStatus === "broken_encoding" ? "broken" : ""}>
              {c.textValue}
            </span>
          </div>
        ))}
        {filled.length > 30 && (
          <div className="dim">… ещё {filled.length - 30} текстовых ячеек</div>
        )}
      </div>
    </div>
  );
}

export function Inspector(p: Props) {
  const [openList, setOpenList] = useState<GroupId | null>(null);
  const counts = new Map<GroupId, number>();
  for (const e of p.elements)
    counts.set(e.groupId, (counts.get(e.groupId) ?? 0) + 1);

  const toggleGroup = (g: GroupId) => {
    const next = new Set(p.enabledGroups);
    if (next.has(g)) next.delete(g); else next.add(g);
    p.setEnabledGroups(next);
  };

  const current = p.hovered ?? p.selected;

  return (
    <aside className="inspector">
      {/* ---- Группы элементов (ТЗ 7.1) ---- */}
      <section>
        <h2>Группы элементов</h2>
        {GROUPS.map((g) => {
          const n = counts.get(g.id) ?? 0;
          const off = !p.enabledGroups.has(g.id) && p.soloGroup !== g.id;
          const solo = p.soloGroup === g.id;
          return (
            <div key={g.id} className={"grouprow" + (off ? " off" : "") + (solo ? " solo" : "")}>
              <button
                className="groupname"
                title="Показать/скрыть группу"
                onClick={() => { p.setSoloGroup(null); toggleGroup(g.id); }}
              >
                <span className="dot" style={{ background: g.color }} />
                {g.name}
                <span className="mono cnt">{n}</span>
              </button>
              <button
                className={"mini" + (solo ? " active" : "")}
                title="Оставить только эту группу"
                onClick={() => p.setSoloGroup(solo ? null : g.id)}
              >
                solo
              </button>
              <button
                className="mini"
                title="Список элементов группы"
                onClick={() => setOpenList(openList === g.id ? null : g.id)}
              >
                список
              </button>
            </div>
          );
        })}
        {openList && (
          <div className="elist">
            {p.elements
              .filter((e) => e.groupId === openList)
              .slice(0, 200)
              .map((e) => (
                <button
                  key={e.elementId}
                  className={"erow" + (p.selected?.elementId === e.elementId ? " sel" : "")}
                  onClick={() => p.setSelected(e)}
                >
                  <span className="mono">{e.elementId}</span>
                  <span className="dim">{e.subtypeId}</span>
                </button>
              ))}
          </div>
        )}
      </section>

      {/* ---- Элемент под курсором / выбранный ---- */}
      <section>
        <h2>Элемент</h2>
        {current ? (
          <>
            <ElementCard el={current} />
            {current.groupId === "tables" && (
              <TableCard documentId={p.documentId} el={current} />
            )}
          </>
        ) : (
          <p className="dim">
            Наведите курсор на элемент страницы или выберите его из списка
            группы. Клик фиксирует выбор.
          </p>
        )}
      </section>

      {/* ---- Слои ---- */}
      <section>
        <h2>
          Слои <span className="badge note">Логические слои</span>
        </h2>
        {p.layers.map((l) => (
          <div key={l.layerId} className="layerrow">
            <span>{l.layerName}</span>
            <span className="mono dim">
              {l.isNativePdfLayer ? "нативный PDF" : l.layerKind}
            </span>
          </div>
        ))}
      </section>

      {/* ---- Языки ---- */}
      <section>
        <h2>Языки текста</h2>
        {p.languages.map((l) => (
          <div key={l.languageCode} className="layerrow">
            <span>
              <span className="dot" style={{ background: LANG_COLOR[l.languageCode] ?? "#707A8E" }} />
              {l.languageCode}
            </span>
            <span className="mono dim">
              {l.segmentCount} сегм. · {l.charCount} симв.
              {l.brokenEncodingCount > 0 && ` · битых: ${l.brokenEncodingCount}`}
            </span>
          </div>
        ))}
        {p.page && p.page.brokenEncodingCount > 0 && (
          <p className="broken">
            На странице {p.page.brokenEncodingCount} сегментов с битой кодировкой
          </p>
        )}
      </section>
    </aside>
  );
}
