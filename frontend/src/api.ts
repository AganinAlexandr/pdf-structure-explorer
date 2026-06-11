// Клиент API backend (спецификация v1). Все запросы идут через /api/v1,
// в dev-режиме vite проксирует их на FastAPI (см. vite.config.ts).

export const API = "/api/v1";

export interface ApiEnvelope<T> {
  ok: boolean;
  data: T;
  error?: { code: string; message: string };
}

export interface DocumentCard {
  documentId: string;
  fileName: string;
  fileCrc32?: string;
  pageCount: number;
  status: string;
  hasNativeLayers: boolean;
  hasTables: boolean;
  hasImages: boolean;
  error?: string;
}

export interface ParseStatus {
  documentId: string;
  status: string;
  processedPages: number;
  totalPages: number;
  progressPercent: number;
  error?: string;
}

export interface PageSummary {
  pageId: string;
  pageNumber: number;
  pageWidth: number;
  pageHeight: number;
  elementCount: number;
  textCount: number;
  lineCount: number;
  frameCount: number;
  imageCount: number;
  tableCount: number;
  tableCellCount: number;
  languageCount: number;
  brokenEncodingCount: number;
}

export interface Element {
  elementId: string;
  pageNumber: number;
  layerId: string;
  groupId: GroupId;
  subtypeId: string;
  relatedTableId: string;
  relatedImageId: string;
  drawOrder: number;
  depthLevel: number;
  x1: number; y1: number; x2: number; y2: number;
  width: number; height: number; bboxArea: number;
  strokeWidth?: number;
  lineLength?: number;
  fontName?: string;
  fontSize?: number;
  fontColor?: string;
  rotation?: number;
  languageCode?: string;
  encodingStatus?: string;
  charCount?: number;
  cellCount?: number;
  segmentCount?: number;
  placementCount?: number;
}

export interface TableCell {
  cellId: string;
  rowIndex: number;
  columnIndex: number;
  rowSpan: number;
  columnSpan: number;
  textValue: string;
  languageCode: string;
  encodingStatus: string;
  x1: number; y1: number; x2: number; y2: number;
}

export interface TableCardData {
  tableId: string;
  elementId: string;
  pageNumber: number;
  tableKind: string;
  detectionConfidence: string;
  rowCount: number;
  columnCount: number;
  cellCount: number;
  cellsWithText: number;
  textFillRatio: number;
  hasMergedCells: boolean;
  cells: TableCell[];
}

export interface Layer {
  layerId: string;
  layerName: string;
  layerKind: string;
  isNativePdfLayer: boolean;
  isLogicalLayer: boolean;
}

export interface LanguageStat {
  languageCode: string;
  segmentCount: number;
  charCount: number;
  brokenEncodingCount: number;
}

export type GroupId =
  | "text" | "lines" | "frames" | "images" | "tables" | "other_vector";

export const GROUPS: { id: GroupId; name: string; color: string }[] = [
  { id: "text", name: "Текст", color: "#29A8E0" },
  { id: "lines", name: "Линии", color: "#F2A33C" },
  { id: "frames", name: "Рамки", color: "#5B8DEF" },
  { id: "images", name: "Изображения", color: "#C06BD6" },
  { id: "tables", name: "Таблицы", color: "#E0524F" },
  { id: "other_vector", name: "Прочая графика", color: "#8A93A6" },
];

export const GROUP_COLOR = Object.fromEntries(
  GROUPS.map((g) => [g.id, g.color]),
) as Record<GroupId, string>;

export const LANG_COLOR: Record<string, string> = {
  ru: "#29A8E0",
  en: "#F2A33C",
  unknown: "#707A8E",
  broken_encoding: "#E0524F",
};

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url);
  const j = (await r.json()) as ApiEnvelope<T>;
  if (!j.ok) throw new Error(j.error?.message ?? "Ошибка API");
  return j.data;
}

export const api = {
  upload: async (file: File): Promise<DocumentCard> => {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch(`${API}/documents`, { method: "POST", body: fd });
    const j = (await r.json()) as ApiEnvelope<DocumentCard>;
    if (!j.ok) throw new Error(j.error?.message ?? "Не удалось загрузить файл");
    return j.data;
  },
  parse: (id: string) =>
    fetch(`${API}/documents/${id}/parse`, { method: "POST" }),
  status: (id: string) => get<ParseStatus>(`${API}/documents/${id}/status`),
  pages: (id: string) =>
    get<{ items: PageSummary[] }>(`${API}/documents/${id}/pages`),
  // элементы страницы: добираем постранично, на CAD-листах их тысячи
  pageElements: async (id: string, page: number): Promise<Element[]> => {
    const out: Element[] = [];
    for (let offset = 0; ; offset += 2000) {
      const d = await get<{ items: Element[]; total: number }>(
        `${API}/documents/${id}/elements?pageNumber=${page}&limit=2000&offset=${offset}`,
      );
      out.push(...d.items);
      if (out.length >= d.total || d.items.length === 0) break;
    }
    return out;
  },
  table: (id: string, tableId: string) =>
    get<TableCardData>(`${API}/documents/${id}/tables/${tableId}`),
  layers: (id: string) => get<{ items: Layer[] }>(`${API}/documents/${id}/layers`),
  languages: (id: string) =>
    get<{ items: LanguageStat[] }>(`${API}/documents/${id}/languages`),
  exportDoc: (id: string) =>
    fetch(`${API}/documents/${id}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format: "csv_bundle" }),
    }).then((r) => r.json()),
  previewUrl: (id: string, page: number, scale: number) =>
    `${API}/documents/${id}/pages/${page}/preview?scale=${scale}`,
};
