# -*- coding: utf-8 -*-
"""FastAPI backend pdf-structure-explorer (спецификация API v1).

Запуск:  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations
import io

import fitz
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.store import store, EXPORT_DIR
from app import exporter

app = FastAPI(title="pdf-structure-explorer", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

API = "/api/v1"


# ---------------------------------------------------------------- конверт
def ok(data):
    return {"ok": True, "data": data}


class ApiError(Exception):
    def __init__(self, code, message, status=404):
        self.code, self.message, self.status = code, message, status


@app.exception_handler(ApiError)
async def api_error_handler(_req: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status,
                        content={"ok": False,
                                 "error": {"code": exc.code,
                                           "message": exc.message}})


def get_doc(document_id, need_parsed=False):
    d = store.get(document_id)
    if d is None:
        raise ApiError("DOCUMENT_NOT_FOUND", f"Document {document_id} not found")
    if need_parsed and d.status not in ("parsed", "processing"):
        raise ApiError("PARSE_FAILED" if d.status == "failed" else
                       "VALIDATION_ERROR",
                       f"Document status is '{d.status}', parse it first", 409)
    return d


# ---------------------------------------------------------------- справка
@app.get(API + "/health")
def health():
    return ok({"status": "ok"})


@app.get(API + "/config")
def config():
    return ok({
        "groups": [g for g, *_ in exporter.GROUP_ROWS],
        "cursorModes": ["pointer", "crosshair", "precision", "focus"],
        "languageCodes": ["ru", "en", "unknown", "broken_encoding"],
        "exportFormats": ["csv_bundle"],
        "exportDir": EXPORT_DIR})


# ---------------------------------------------------------------- документы
@app.post(API + "/documents")
async def upload_document(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise ApiError("INVALID_FILE_TYPE", "Only PDF files are accepted", 400)
    content = await file.read()
    import zlib
    crc32 = f"{zlib.crc32(content) & 0xffffffff:08X}"
    existing = store.find_by_crc(crc32)
    if existing is not None:
        return ok({"documentId": existing.document_id,
                   "fileName": existing.file_name,
                   "fileCrc32": existing.file_crc32,
                   "pageCount": existing.page_count,
                   "status": existing.status,
                   "duplicateOf": existing.document_id})
    try:
        d = store.add(file.filename, content)
    except Exception as e:                                  # noqa: BLE001
        raise ApiError("UPLOAD_FAILED", str(e), 500)
    return ok({"documentId": d.document_id, "fileName": d.file_name,
               "fileCrc32": d.file_crc32,
               "pageCount": d.page_count, "status": d.status})


class ParseOptions(BaseModel):
    parseTables: bool = True
    parseImages: bool = True
    parseTextGlyphs: bool = False


@app.post(API + "/documents/{document_id}/parse")
def parse_document(document_id: str, _opts: ParseOptions | None = None):
    d = get_doc(document_id)
    if d.status == "processing":
        return ok({"documentId": d.document_id, "status": d.status})
    d.parse_async()
    return ok({"documentId": d.document_id, "status": "processing"})


@app.get(API + "/documents")
def list_documents():
    return ok({"items": [d.card() for d in store.docs.values()]})


@app.get(API + "/documents/{document_id}")
def get_document(document_id: str):
    return ok(get_doc(document_id).card())


@app.get(API + "/documents/{document_id}/status")
def get_status(document_id: str):
    d = get_doc(document_id)
    pct = round(100 * d.processed_pages / d.page_count, 1) if d.page_count else 0
    return ok({"documentId": d.document_id, "status": d.status,
               "processedPages": d.processed_pages,
               "totalPages": d.page_count, "progressPercent": pct,
               "error": d.error})


# ---------------------------------------------------------------- страницы
@app.get(API + "/documents/{document_id}/pages")
def list_pages(document_id: str, includeSummary: bool = True):
    d = get_doc(document_id, need_parsed=True)
    items = [d.page_summary(n) if includeSummary else
             {"pageId": d.pages[n]["pageId"], "pageNumber": n}
             for n in sorted(d.pages)]
    return ok({"items": items, "total": d.page_count,
               "processedPages": d.processed_pages})


def get_page(d, page_number):
    if page_number not in d.pages:
        if 1 <= page_number <= d.page_count:
            raise ApiError("PAGE_NOT_FOUND",
                           f"Page {page_number} is not parsed yet", 409)
        raise ApiError("PAGE_NOT_FOUND", f"Page {page_number} not found")
    return d.pages[page_number]


@app.get(API + "/documents/{document_id}/pages/{page_number}")
def page_meta(document_id: str, page_number: int):
    d = get_doc(document_id, need_parsed=True)
    get_page(d, page_number)
    return ok(d.page_summary(page_number))


@app.get(API + "/documents/{document_id}/pages/{page_number}/preview")
def page_preview(document_id: str, page_number: int, scale: float = 1.0):
    d = get_doc(document_id)
    if not (1 <= page_number <= d.page_count):
        raise ApiError("PAGE_NOT_FOUND", f"Page {page_number} not found")
    scale = max(0.1, min(scale, 4.0))
    with fitz.open(d.file_path) as pdf:
        pix = pdf[page_number - 1].get_pixmap(matrix=fitz.Matrix(scale, scale))
        png = pix.tobytes("png")
    return Response(content=png, media_type="image/png")


# ---------------------------------------------------------------- элементы
@app.get(API + "/documents/{document_id}/elements")
def list_elements(document_id: str, pageNumber: int | None = None,
                  layerId: str | None = None, groupId: str | None = None,
                  subtypeId: str | None = None,
                  languageCode: str | None = None,
                  encodingStatus: str | None = None,
                  tableId: str | None = None,
                  limit: int = 200, offset: int = 0):
    d = get_doc(document_id, need_parsed=True)
    els = (d.pages[pageNumber]["elements"] if pageNumber and
           pageNumber in d.pages else d.all_records("elements"))
    def keep(e):
        return ((layerId is None or e["layerId"] == layerId) and
                (groupId is None or e["groupId"] == groupId) and
                (subtypeId is None or e["subtypeId"] == subtypeId) and
                (languageCode is None or e.get("languageCode") == languageCode) and
                (encodingStatus is None or e.get("encodingStatus") == encodingStatus) and
                (tableId is None or e.get("relatedTableId") == tableId))
    filt = [e for e in els if keep(e)]
    agg = {}
    for e in filt:
        agg[e["groupId"]] = agg.get(e["groupId"], 0) + 1
    return ok({"items": filt[offset:offset + max(1, min(limit, 2000))],
               "total": len(filt), "aggregates": agg})


@app.get(API + "/documents/{document_id}/elements/{element_id}")
def get_element(document_id: str, element_id: str):
    d = get_doc(document_id, need_parsed=True)
    for n in d.pages:
        for e in d.pages[n]["elements"]:
            if e["elementId"] == element_id:
                card = dict(e)
                if e["groupId"] == "tables" and e.get("relatedTableId"):
                    card["cells"] = [c for c in d.pages[n]["tableCells"]
                                     if c["tableId"] == e["relatedTableId"]]
                return ok(card)
    raise ApiError("ELEMENT_NOT_FOUND", f"Element {element_id} not found")


@app.get(API + "/documents/{document_id}/groups")
def list_groups(document_id: str, pageNumber: int | None = None,
                layerId: str | None = None):
    d = get_doc(document_id, need_parsed=True)
    els = (d.pages[pageNumber]["elements"] if pageNumber and
           pageNumber in d.pages else d.all_records("elements"))
    agg = {g: 0 for g, *_ in exporter.GROUP_ROWS}
    for e in els:
        if layerId is None or e["layerId"] == layerId:
            agg[e["groupId"]] += 1
    return ok({"items": [{"groupId": g, "elementCount": c}
                         for g, c in agg.items()]})


@app.get(API + "/documents/{document_id}/layers")
def list_layers(document_id: str):
    return ok({"items": get_doc(document_id).layers()})


@app.get(API + "/documents/{document_id}/languages")
def list_languages(document_id: str):
    d = get_doc(document_id, need_parsed=True)
    agg = {}
    for t in d.all_records("textSegments"):
        a = agg.setdefault(t["languageCode"],
                           {"languageCode": t["languageCode"],
                            "segmentCount": 0, "charCount": 0,
                            "brokenEncodingCount": 0})
        a["segmentCount"] += 1
        a["charCount"] += t["charCount"]
        if t["encodingStatus"] == "broken_encoding":
            a["brokenEncodingCount"] += 1
    return ok({"items": sorted(agg.values(),
                               key=lambda x: -x["segmentCount"])})


@app.get(API + "/documents/{document_id}/tables")
def list_tables(document_id: str, pageNumber: int | None = None,
                detectionConfidence: str | None = None):
    d = get_doc(document_id, need_parsed=True)
    tbls = (d.pages[pageNumber]["tables"] if pageNumber and
            pageNumber in d.pages else d.all_records("tables"))
    if detectionConfidence:
        tbls = [t for t in tbls
                if t["detectionConfidence"] == detectionConfidence]
    return ok({"items": tbls, "total": len(tbls)})


@app.get(API + "/documents/{document_id}/tables/{table_id}")
def get_table(document_id: str, table_id: str):
    d = get_doc(document_id, need_parsed=True)
    for n in d.pages:
        for t in d.pages[n]["tables"]:
            if t["tableId"] == table_id:
                card = dict(t)
                card["cells"] = [c for c in d.pages[n]["tableCells"]
                                 if c["tableId"] == table_id]
                card["textSegments"] = [
                    s["textSegmentId"] for s in d.pages[n]["textSegments"]
                    if s.get("cellId") and any(c["cellId"] == s["cellId"]
                                               for c in card["cells"])]
                return ok(card)
    raise ApiError("TABLE_NOT_FOUND", f"Table {table_id} not found")


# ---------------------------------------------------------------- hit-test
RADIUS = {"pointer": 1.5, "crosshair": 4.0, "precision": 0.5, "focus": 10.0}


@app.get(API + "/documents/{document_id}/pages/{page_number}/hit-test")
def hit_test(document_id: str, page_number: int, x: float, y: float,
             groupId: str | None = None, layerId: str | None = None,
             cursorMode: str = "pointer"):
    d = get_doc(document_id, need_parsed=True)
    p = get_page(d, page_number)
    r = RADIUS.get(cursorMode, 1.5)
    cands = []
    for e in p["elements"]:
        if groupId and e["groupId"] != groupId:
            continue
        if layerId and e["layerId"] != layerId:
            continue
        dx = max(e["x1"] - x, 0, x - e["x2"])
        dy = max(e["y1"] - y, 0, y - e["y2"])
        dist = (dx*dx + dy*dy) ** 0.5
        if dist <= r:
            cands.append((dist, e["bboxArea"], e))
    cands.sort(key=lambda c: (c[0], c[1]))
    return ok({"primaryElementId": cands[0][2]["elementId"] if cands else None,
               "candidates": [{"elementId": e["elementId"],
                               "groupId": e["groupId"],
                               "subtypeId": e["subtypeId"],
                               "distance": round(dist, 2)}
                              for dist, _a, e in cands[:10]]})


# ---------------------------------------------------------------- экспорт
class ExportOptions(BaseModel):
    format: str = "csv_bundle"
    includePreviews: bool = False
    includeTableCells: bool = True


@app.post(API + "/documents/{document_id}/export")
def export_document(document_id: str, opts: ExportOptions | None = None):
    d = get_doc(document_id, need_parsed=True)
    if d.status != "parsed":
        raise ApiError("VALIDATION_ERROR",
                       f"Export requires status 'parsed', current is "
                       f"'{d.status}' ({d.processed_pages}/{d.page_count} "
                       f"pages processed)", 409)
    opts = opts or ExportOptions()
    if opts.format != "csv_bundle":
        raise ApiError("VALIDATION_ERROR",
                       f"Unsupported format '{opts.format}'", 400)
    try:
        path, files = exporter.export_csv_bundle(d, EXPORT_DIR)
    except Exception as e:                                  # noqa: BLE001
        raise ApiError("EXPORT_FAILED", str(e), 500)
    d.export = {"documentId": d.document_id, "exportId": "exp_1",
                "status": "ready", "exportPath": path, "files": files}
    return ok(d.export)


@app.get(API + "/documents/{document_id}/export")
def export_status(document_id: str):
    d = get_doc(document_id)
    if not d.export:
        return ok({"documentId": d.document_id, "status": "none"})
    return ok(d.export)


# ---------------------------------------------------------------- frontend
# если рядом лежит собранный фронтенд (frontend/dist), раздаём его с того же
# порта: http://127.0.0.1:8000/ открывает приложение целиком
import os
from fastapi.staticfiles import StaticFiles

_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
