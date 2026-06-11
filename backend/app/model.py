# -*- coding: utf-8 -*-
"""Преобразование страницы PDF в модель данных спецификации.

Выход parse_page(): словарь с записями
  elements, text_segments, images, tables, table_cells
в терминах и полях «Спецификации API и экспорта» (разделы 4, 6).
"""
from __future__ import annotations
import fitz

from pdf_structure import geometry, text_binding

GROUPS = ("text", "lines", "frames", "images", "tables", "other_vector")

SUBTYPES = [
    ("text_span", "text", "Текстовый span"),
    ("line_segment", "lines", "Осепараллельный отрезок"),
    ("polyline", "lines", "Ломаная из отрезков"),
    ("diagonal_line", "lines", "Диагональный отрезок"),
    ("rectangle_frame", "frames", "Замкнутый прямоугольный контур"),
    ("frame_group", "frames", "Группа смежных контуров без текста"),
    ("raster_image", "images", "Растровое изображение"),
    ("tiled_pattern", "images", "Многократно размещённый растровый тайл"),
    ("grid_table", "tables", "Таблица по сетке линий"),
    ("curve", "other_vector", "Кривая Безье"),
    ("complex_vector", "other_vector", "Сложная векторная структура (чертёж)"),
]

# слой назначается по группе; нативные OCG-слои добавляются на уровне документа
LAYER_BY_GROUP = {"text": "layer_text", "lines": "layer_vector",
                  "frames": "layer_vector", "tables": "layer_vector",
                  "other_vector": "layer_vector", "images": "layer_images"}

IMAGE_TILE_CAP = 30      # больше размещений одного xref => один элемент-паттерн
REPLACEMENT_CHARS = "\u00b7\ufffd\u25a1\u25cf"


def lang_and_encoding(text: str):
    """Эвристика языка и кодировки: ru / en / unknown / broken_encoding."""
    if not text:
        return "unknown", "ok"
    repl = sum(text.count(c) for c in REPLACEMENT_CHARS)
    if len(text) >= 3 and repl / len(text) > 0.3:
        return "broken_encoding", "broken_encoding"
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "unknown", "ok"
    cyr = sum(1 for c in letters if 'а' <= c.lower() <= 'я' or c.lower() == 'ё')
    lat = sum(1 for c in letters if 'a' <= c.lower() <= 'z')
    if cyr > lat:
        return "ru", "ok"
    if lat > cyr:
        return "en", "ok"
    return "unknown", "ok"


def _bbox_fields(b):
    x1, y1, x2, y2 = (round(v, 2) for v in b)
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "width": round(x2 - x1, 2), "height": round(y2 - y1, 2),
            "bboxArea": round((x2 - x1) * (y2 - y1), 2)}


def _color_hex(c):
    if c is None:
        return ""
    if isinstance(c, int):
        return f"#{c:06x}"
    try:
        return "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in c[:3])
    except Exception:
        return ""


def parse_page(doc: fitz.Document, page_number: int,
               document_id: str, cfg: geometry.EngineConfig | None = None):
    """page_number: 1-based. Возвращает записи модели для страницы."""
    page = doc[page_number - 1]
    page_id = f"{document_id}_p_{page_number}"
    res = geometry.analyze_page(page, cfg)
    spans = text_binding.extract_spans(page)
    structures, _free = text_binding.bind_text(res["structures"], spans)

    seq = {"el": 0, "txt": 0, "img": 0, "tbl": 0}
    def next_id(kind):
        seq[kind] += 1
        return f"{kind}_{page_number}_{seq[kind]}"

    elements, text_segments, images, tables, table_cells = [], [], [], [], []

    def add_element(group, subtype, bbox, draw_order=0, **extra):
        el = {"elementId": next_id("el"), "documentId": document_id,
              "pageId": page_id, "pageNumber": page_number,
              "layerId": LAYER_BY_GROUP[group], "groupId": group,
              "subtypeId": subtype, "parentElementId": extra.pop("parent", ""),
              "relatedTableId": extra.pop("tableId", ""),
              "relatedImageId": extra.pop("imageId", ""),
              "relatedTextSegmentId": extra.pop("textSegmentId", ""),
              "drawOrder": draw_order, "depthLevel": draw_order,
              **_bbox_fields(bbox), "isVisible": True}
        el.update(extra)
        elements.append(el)
        return el

    # ---------- таблицы (первыми: текст ячеек должен знать tableId) ----
    span_table = {}          # id(span) -> (table_id, cell_id)
    for st in structures:
        if st["kind"] != "table":
            continue
        tid = next_id("tbl")
        el = add_element("tables", "grid_table", st["table_bbox"],
                         st["draw_order"], tableId=tid,
                         strokeWidth=round(st.get("thickness", 0), 2))
        cells = st.get("cells", [])
        n_text_el = 0
        for c in cells:
            cid = f"cell_{seq['tbl']}_{c['row']}_{c['col']}"
            lang, enc = lang_and_encoding(c.get("text", ""))
            table_cells.append({
                "cellId": cid, "tableId": tid, "documentId": document_id,
                "pageId": page_id, "pageNumber": page_number,
                "rowIndex": c["row"], "columnIndex": c["col"],
                "rowSpan": c.get("row_span", 1), "columnSpan": c.get("col_span", 1),
                "textValue": c.get("text", ""),
                "languageCode": lang, "encodingStatus": enc,
                "childElementCount": len(c.get("spans", [])),
                **_bbox_fields(c["bbox"])})
            for sp in c.get("spans", []):
                span_table[id(sp)] = (tid, cid)
                n_text_el += 1
        tables.append({
            "tableId": tid, "elementId": el["elementId"],
            "documentId": document_id, "pageId": page_id,
            "pageNumber": page_number, "layerId": el["layerId"],
            "tableKind": "grid_table",
            "detectionConfidence": st.get("confidence", "partial"),
            "rowCount": st.get("rows", 0), "columnCount": st.get("cols", 0),
            "cellCount": st.get("cell_count", len(cells)),
            "textElementCount": n_text_el,
            "lineElementCount": st.get("segment_count", 0),
            "frameElementCount": 1 if st.get("extra_frame") else 0,
            "hasMergedCells": bool(st.get("has_merged_cells")),
            "cellsWithText": st.get("cells_with_text", 0),
            "textFillRatio": st.get("text_fill_ratio", 0.0),
            **_bbox_fields(st["table_bbox"])})

    # ---------- текст ---------------------------------------------------
    for sp in spans:
        lang, enc = lang_and_encoding(sp["text"])
        txt_id = next_id("txt")
        tid, cid = span_table.get(id(sp), ("", ""))
        el = add_element("text", "text_span", sp["bbox"], 0,
                         tableId=tid, textSegmentId=txt_id,
                         fontName=sp["font"], fontSize=sp["size"],
                         fontColor=_color_hex(sp["color"]),
                         rotation=0 if sp["dir"] == (1, 0) else 90,
                         languageCode=lang, encodingStatus=enc,
                         charCount=len(sp["text"]))
        text_segments.append({
            "textSegmentId": txt_id, "elementId": el["elementId"],
            "documentId": document_id, "pageId": page_id,
            "pageNumber": page_number, "layerId": "layer_text",
            "languageCode": lang, "languageConfidence": 0.8,
            "encodingStatus": enc, "textValue": sp["text"],
            "normalizedText": " ".join(sp["text"].split()).lower(),
            "charCount": len(sp["text"]),
            "wordCount": len(sp["text"].split()),
            "cellId": cid, **_bbox_fields(sp["bbox"])})

    # ---------- векторные структуры ------------------------------------
    for st in structures:
        k = st["kind"]
        if k == "table":
            continue
        if k == "line":
            b = st["bbox"]
            add_element("lines", "line_segment", b, st["draw_order"],
                        strokeWidth=round(st.get("thickness", 0), 2),
                        lineLength=round(max(b[2]-b[0], b[3]-b[1]), 2))
        elif k == "polyline":
            add_element("lines", "polyline", st["bbox"], st["draw_order"],
                        strokeWidth=round(st.get("thickness", 0), 2),
                        segmentCount=st.get("segments", st.get("segment_count", 0)))
        elif k == "frame":
            add_element("frames", "rectangle_frame", st["bbox"],
                        st["draw_order"],
                        strokeWidth=round(st.get("thickness", 0), 2))
        elif k == "frame_group":
            add_element("frames", "frame_group", st["bbox"], st["draw_order"],
                        strokeWidth=round(st.get("thickness", 0), 2),
                        cellCount=st.get("cell_count", 0))
        elif k == "complex":
            add_element("other_vector", "complex_vector", st["bbox"],
                        st["draw_order"],
                        segmentCount=st.get("segment_count", 0))
    for o in res["others"]:
        if o["subtype"] == "diagonal_line":
            add_element("lines", "diagonal_line", o["bbox"], o["draw_order"],
                        strokeWidth=round(o.get("thickness", 0), 2),
                        lineLength=round(o.get("length", 0), 2))
        else:
            add_element("other_vector", "curve", o["bbox"], o["draw_order"],
                        strokeWidth=round(o.get("thickness", 0), 2))

    # ---------- изображения (дедупликация по xref) ----------------------
    by_xref = {}
    try:
        infos = page.get_image_info(xrefs=True)
    except Exception:
        infos = []
    for inf in infos:
        by_xref.setdefault(inf.get("xref", 0), []).append(inf)
    for xref, places in by_xref.items():
        meta = places[0]
        size_bytes, fmt = 0, ""
        if xref:
            try:
                raw = doc.extract_image(xref)
                size_bytes, fmt = len(raw["image"]), raw["ext"]
            except Exception:
                pass
        img_id = next_id("img")
        if len(places) > IMAGE_TILE_CAP:      # штриховка тайлами
            xs = [p["bbox"] for p in places]
            union = (min(b[0] for b in xs), min(b[1] for b in xs),
                     max(b[2] for b in xs), max(b[3] for b in xs))
            el = add_element("images", "tiled_pattern", union, 0,
                             imageId=img_id, placementCount=len(places))
            bbox = union
        else:
            bbox = places[0]["bbox"]
            el = add_element("images", "raster_image", bbox, 0,
                             imageId=img_id, placementCount=len(places))
            for extra in places[1:]:
                add_element("images", "raster_image", extra["bbox"], 0,
                            imageId=img_id, parent=el["elementId"])
        images.append({
            "imageId": img_id, "elementId": el["elementId"],
            "documentId": document_id, "pageId": page_id,
            "pageNumber": page_number, "layerId": "layer_images",
            "imageFormat": fmt, "colorSpace": meta.get("cs-name", ""),
            "widthPx": meta.get("width", 0), "heightPx": meta.get("height", 0),
            "placementCount": len(places),
            "binarySizeBytes": size_bytes, "previewPath": "",
            **{"bboxWidth": _bbox_fields(bbox)["width"],
               "bboxHeight": _bbox_fields(bbox)["height"],
               "bboxArea": _bbox_fields(bbox)["bboxArea"]}})

    rect = page.rect
    return {"pageId": page_id, "pageNumber": page_number,
            "pageWidth": round(rect.width, 2), "pageHeight": round(rect.height, 2),
            "rotation": page.rotation,
            "elements": elements, "textSegments": text_segments,
            "images": images, "tables": tables, "tableCells": table_cells}
