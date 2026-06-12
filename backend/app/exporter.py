# -*- coding: utf-8 -*-
"""Экспортный пакет: 13 CSV + manifest.json (спецификация, разделы 5–6).

Правила CSV: запятая, UTF-8, заголовок, пустые значения — пустая строка,
логические true/false, даты ISO 8601, десятичная точка.
"""
from __future__ import annotations
import csv, json, os, datetime

SCHEMA_VERSION = "1.0.0"

GROUP_ROWS = [
    ("text", "Текст", "Текстовые элементы страницы", True),
    ("lines", "Линии", "Отрезки, ломаные, диагонали", True),
    ("frames", "Рамки", "Замкнутые контуры и их группы", True),
    ("images", "Изображения", "Растровые объекты", True),
    ("tables", "Таблицы", "Сетки с ячейками и текстом", True),
    ("other_vector", "Прочая графика", "Кривые и сложные структуры", True),
]


def _w(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(header)
        for r in rows:
            wr.writerow(["" if v is None else
                         ("true" if v is True else "false" if v is False else v)
                         for v in r])


def export_csv_bundle(doc, export_dir):
    out = os.path.join(export_dir, doc.document_id)
    os.makedirs(out, exist_ok=True)
    files = []

    def emit(name, header, rows):
        _w(os.path.join(out, name), header, rows)
        files.append(name)

    card = doc.card()
    emit("documents.csv",
         ["document_id", "file_name", "file_crc32", "file_path", "file_size_bytes",
          "page_count", "pdf_version", "has_native_layers", "has_text_layer",
          "has_images", "has_tables", "parse_status", "parsed_at"],
         [[doc.document_id, card["fileName"], card["fileCrc32"], card["filePath"],
           card["fileSizeBytes"], card["pageCount"], card["pdfVersion"],
           card["hasNativeLayers"], card["hasTextLayer"], card["hasImages"],
           card["hasTables"], card["status"], card["parsedAt"]]])

    summaries = [doc.page_summary(n) for n in sorted(doc.pages)]
    emit("pages.csv",
         ["page_id", "document_id", "page_number", "page_width", "page_height",
          "rotation", "element_count", "text_count", "line_count",
          "frame_count", "image_count", "table_count", "language_count"],
         [[s["pageId"], doc.document_id, s["pageNumber"], s["pageWidth"],
           s["pageHeight"], s["rotation"], s["elementCount"], s["textCount"],
           s["lineCount"], s["frameCount"], s["imageCount"], s["tableCount"],
           s["languageCount"]] for s in summaries])

    emit("layers.csv",
         ["layer_id", "document_id", "page_id", "layer_name", "layer_kind",
          "is_native_pdf_layer", "is_logical_layer", "display_order",
          "is_visible_by_default"],
         [[l["layerId"], doc.document_id, "", l["layerName"], l["layerKind"],
           l["isNativePdfLayer"], l["isLogicalLayer"], l["displayOrder"],
           l["isVisibleByDefault"]] for l in doc.layers()])

    emit("element_groups.csv",
         ["group_id", "group_name", "description", "is_enabled_by_default"],
         [list(g) for g in GROUP_ROWS])

    from app.model import SUBTYPES
    emit("element_subtypes.csv",
         ["subtype_id", "group_id", "subtype_name", "description"],
         [[sid, gid, sid, descr] for sid, gid, descr in SUBTYPES])

    els = doc.all_records("elements")
    emit("elements.csv",
         ["element_id", "document_id", "page_id", "page_number", "layer_id",
          "group_id", "subtype_id", "parent_element_id", "related_table_id",
          "related_image_id", "related_text_segment_id", "draw_order",
          "depth_level", "x1", "y1", "x2", "y2", "width", "height",
          "bbox_area", "stroke_width", "line_length", "perimeter",
          "font_name", "font_size", "font_color", "fill_color", "rotation",
          "language_code", "encoding_status", "char_count", "text_length",
          "binary_size_bytes", "is_visible", "is_selected_by_default"],
         [[e["elementId"], e["documentId"], e["pageId"], e["pageNumber"],
           e["layerId"], e["groupId"], e["subtypeId"], e["parentElementId"],
           e["relatedTableId"], e["relatedImageId"],
           e["relatedTextSegmentId"], e["drawOrder"], e["depthLevel"],
           e["x1"], e["y1"], e["x2"], e["y2"], e["width"], e["height"],
           e["bboxArea"], e.get("strokeWidth", ""), e.get("lineLength", ""),
           round(2*(e["width"]+e["height"]), 2),
           e.get("fontName", ""), e.get("fontSize", ""),
           e.get("fontColor", ""), e.get("fillColor", ""),
           e.get("rotation", ""), e.get("languageCode", ""),
           e.get("encodingStatus", ""), e.get("charCount", ""),
           e.get("charCount", ""), e.get("binarySizeBytes", ""),
           e["isVisible"], False] for e in els])

    txts = doc.all_records("textSegments")
    emit("text_segments.csv",
         ["text_segment_id", "element_id", "document_id", "page_id",
          "page_number", "layer_id", "language_code", "language_confidence",
          "encoding_status", "text_value", "normalized_text", "char_count",
          "word_count", "x1", "y1", "x2", "y2", "width", "height"],
         [[t["textSegmentId"], t["elementId"], t["documentId"], t["pageId"],
           t["pageNumber"], t["layerId"], t["languageCode"],
           t["languageConfidence"], t["encodingStatus"], t["textValue"],
           t["normalizedText"], t["charCount"], t["wordCount"],
           t["x1"], t["y1"], t["x2"], t["y2"], t["width"], t["height"]]
          for t in txts])

    imgs = doc.all_records("images")
    emit("images.csv",
         ["image_id", "element_id", "document_id", "page_id", "page_number",
          "layer_id", "image_format", "color_space", "width_px", "height_px",
          "bbox_width", "bbox_height", "bbox_area", "binary_size_bytes",
          "preview_path"],
         [[i["imageId"], i["elementId"], i["documentId"], i["pageId"],
           i["pageNumber"], i["layerId"], i["imageFormat"], i["colorSpace"],
           i["widthPx"], i["heightPx"], i["bboxWidth"], i["bboxHeight"],
           i["bboxArea"], i["binarySizeBytes"], i["previewPath"]]
          for i in imgs])

    tbls = doc.all_records("tables")
    emit("tables.csv",
         ["table_id", "element_id", "document_id", "page_id", "page_number",
          "layer_id", "table_kind", "detection_confidence", "row_count",
          "column_count", "cell_count", "text_element_count",
          "line_element_count", "frame_element_count",
          "x1", "y1", "x2", "y2", "width", "height", "bbox_area"],
         [[t["tableId"], t["elementId"], t["documentId"], t["pageId"],
           t["pageNumber"], t["layerId"], t["tableKind"],
           t["detectionConfidence"], t["rowCount"], t["columnCount"],
           t["cellCount"], t["textElementCount"], t["lineElementCount"],
           t["frameElementCount"], t["x1"], t["y1"], t["x2"], t["y2"],
           t["width"], t["height"], t["bboxArea"]] for t in tbls])

    cells = doc.all_records("tableCells")
    emit("table_cells.csv",
         ["cell_id", "table_id", "document_id", "page_id", "page_number",
          "row_index", "column_index", "row_span", "column_span",
          "text_value", "language_code", "encoding_status",
          "child_element_count", "x1", "y1", "x2", "y2", "width", "height",
          "bbox_area"],
         [[c["cellId"], c["tableId"], c["documentId"], c["pageId"],
           c["pageNumber"], c["rowIndex"], c["columnIndex"], c["rowSpan"],
           c["columnSpan"], c["textValue"], c["languageCode"],
           c["encodingStatus"], c["childElementCount"], c["x1"], c["y1"],
           c["x2"], c["y2"], c["width"], c["height"], c["bboxArea"]]
          for c in cells])

    lang_rows = []
    for n in sorted(doc.pages):
        agg = {}
        for t in doc.pages[n]["textSegments"]:
            a = agg.setdefault(t["languageCode"], [0, 0, 0])
            a[0] += 1
            a[1] += t["charCount"]
            a[2] += 1 if t["encodingStatus"] == "broken_encoding" else 0
        pid = doc.pages[n]["pageId"]
        for code, (sc, cc, bc) in sorted(agg.items()):
            lang_rows.append([doc.document_id, pid, n, code, sc, cc, bc])
    emit("language_summary.csv",
         ["document_id", "page_id", "page_number", "language_code",
          "segment_count", "char_count", "broken_encoding_count"], lang_rows)

    grp_rows = []
    for n in sorted(doc.pages):
        p = doc.pages[n]
        agg = {g: [0, 0.0, 0.0] for g, *_ in GROUP_ROWS}
        for e in p["elements"]:
            a = agg[e["groupId"]]
            a[0] += 1
            a[1] += e["bboxArea"]
            a[2] += e.get("lineLength", 0) or 0
        broken = sum(1 for t in p["textSegments"]
                     if t["encodingStatus"] == "broken_encoding")
        for g, (cnt, area, ll) in agg.items():
            grp_rows.append([doc.document_id, p["pageId"], n, g, cnt,
                             round(area, 2), round(ll, 2),
                             len(p["tables"]) if g == "tables" else 0,
                             len(p["tableCells"]) if g == "tables" else 0,
                             broken if g == "text" else 0])
    emit("group_summary.csv",
         ["document_id", "page_id", "page_number", "group_id",
          "element_count", "bbox_area_total", "line_length_total",
          "table_count", "cell_count", "broken_encoding_count"], grp_rows)

    emit("page_summary.csv",
         ["document_id", "page_id", "page_number", "element_count",
          "text_count", "line_count", "frame_count", "image_count",
          "other_vector_count", "page_kind",
          "table_count", "table_cell_count", "language_count",
          "broken_encoding_count"],
         [[doc.document_id, s["pageId"], s["pageNumber"], s["elementCount"],
           s["textCount"], s["lineCount"], s["frameCount"], s["imageCount"],
           s["otherVectorCount"], s["pageKind"],
           s["tableCount"], s["tableCellCount"], s["languageCount"],
           s["brokenEncodingCount"]] for s in summaries])

    manifest = {"schemaVersion": SCHEMA_VERSION,
                "documentId": doc.document_id,
                "exportedAt": datetime.datetime.now(
                    datetime.timezone.utc).isoformat(timespec="seconds"),
                "appMode": "local", "files": files}
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return out, files + ["manifest.json"]
