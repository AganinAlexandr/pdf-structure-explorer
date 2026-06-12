# -*- coding: utf-8 -*-
"""Хранилище документов: загрузка, фоновый разбор, агрегаты."""
from __future__ import annotations
import os, threading, uuid, datetime, zlib
import fitz

from app import model

STORAGE_DIR = os.environ.get("PSE_STORAGE_DIR", "./storage")
EXPORT_DIR = os.environ.get("PSE_EXPORT_DIR", "./storage/exports")


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


class Document:
    def __init__(self, document_id, file_name, file_path, size, crc32):
        self.document_id = document_id
        self.file_name = file_name
        self.file_path = file_path
        self.file_size = size
        self.file_crc32 = crc32
        self.status = "uploaded"        # uploaded|processing|parsed|failed
        self.error = ""
        self.page_count = 0
        self.pdf_version = ""
        self.has_native_layers = False
        self.native_layers = []
        self.parsed_at = ""
        self.processed_pages = 0
        self.pages = {}                 # page_number -> результат parse_page
        self.export = None
        self.lock = threading.Lock()
        with fitz.open(file_path) as d:
            self.page_count = d.page_count
            self.pdf_version = (d.metadata or {}).get("format", "")
            ocgs = d.get_ocgs() or {}
            self.has_native_layers = bool(ocgs)
            self.native_layers = [{"layerId": f"layer_native_{x}",
                                   "layerName": v.get("name", str(x)),
                                   "isNativePdfLayer": True}
                                  for x, v in ocgs.items()]

    # ------------------------------------------------------------------
    def parse(self):
        self.status = "processing"
        self.processed_pages = 0
        try:
            doc = fitz.open(self.file_path)
            for n in range(1, self.page_count + 1):
                data = model.parse_page(doc, n, self.document_id)
                with self.lock:
                    self.pages[n] = data
                    self.processed_pages = n
            doc.close()
            self.status = "parsed"
            self.parsed_at = _now()
        except Exception as e:               # noqa: BLE001
            self.status = "failed"
            self.error = f"{type(e).__name__}: {e}"

    def parse_async(self):
        threading.Thread(target=self.parse, daemon=True).start()

    # ------------------------------------------------------------------
    def all_records(self, kind):
        out = []
        for n in sorted(self.pages):
            out.extend(self.pages[n][kind])
        return out

    def page_summary(self, n):
        p = self.pages[n]
        cnt = {}
        for el in p["elements"]:
            cnt[el["groupId"]] = cnt.get(el["groupId"], 0) + 1
        langs = {t["languageCode"] for t in p["textSegments"]}
        broken = sum(1 for t in p["textSegments"]
                     if t["encodingStatus"] == "broken_encoding")
        n_text = cnt.get("text", 0)
        n_vec = cnt.get("lines", 0) + cnt.get("frames", 0) + cnt.get("other_vector", 0)
        n_img = cnt.get("images", 0)
        if n_text == 0 and n_vec <= 5 and n_img >= 1:
            page_kind = "scanned"
        elif n_text == 0 and n_vec > 50:
            page_kind = "text_outlined_suspect"
        elif n_img >= 1 and n_vec > 500:
            page_kind = "hybrid"
        else:
            page_kind = "vector"
        return {"pageId": p["pageId"], "pageNumber": n,
                "pageWidth": p["pageWidth"], "pageHeight": p["pageHeight"],
                "rotation": p["rotation"],
                "elementCount": len(p["elements"]),
                "textCount": cnt.get("text", 0),
                "lineCount": cnt.get("lines", 0),
                "frameCount": cnt.get("frames", 0),
                "imageCount": cnt.get("images", 0),
                "otherVectorCount": cnt.get("other_vector", 0),
                "pageKind": page_kind,
                "tableCount": len(p["tables"]),
                "tableCellCount": len(p["tableCells"]),
                "languageCount": len(langs),
                "brokenEncodingCount": broken}

    def layers(self):
        logical = [
            {"layerId": "layer_text", "layerName": "Текст",
             "layerKind": "text"},
            {"layerId": "layer_vector", "layerName": "Векторная графика",
             "layerKind": "vector_graphics"},
            {"layerId": "layer_images", "layerName": "Изображения",
             "layerKind": "images"},
        ]
        for i, l in enumerate(logical):
            l.update({"isNativePdfLayer": False, "isLogicalLayer": True,
                      "displayOrder": i, "isVisibleByDefault": True})
        native = [dict(l, layerKind="native_pdf_layer", isLogicalLayer=False,
                       displayOrder=100 + i, isVisibleByDefault=True)
                  for i, l in enumerate(self.native_layers)]
        return logical + native

    def card(self):
        any_text = any(p["textSegments"] for p in self.pages.values())
        return {"documentId": self.document_id, "fileName": self.file_name,
                "filePath": self.file_path, "fileSizeBytes": self.file_size,
                "fileCrc32": self.file_crc32,
                "pageCount": self.page_count, "pdfVersion": self.pdf_version,
                "status": self.status, "error": self.error,
                "parsedAt": self.parsed_at,
                "hasNativeLayers": self.has_native_layers,
                "hasTextLayer": any_text,
                "hasImages": any(p["images"] for p in self.pages.values()),
                "hasTables": any(p["tables"] for p in self.pages.values())}


class Store:
    def __init__(self):
        self.docs: dict[str, Document] = {}
        os.makedirs(os.path.join(STORAGE_DIR, "uploads"), exist_ok=True)
        os.makedirs(EXPORT_DIR, exist_ok=True)

    def add(self, file_name: str, content: bytes) -> Document:
        document_id = "doc_" + uuid.uuid4().hex[:8]
        path = os.path.join(STORAGE_DIR, "uploads", f"{document_id}.pdf")
        with open(path, "wb") as f:
            f.write(content)
        crc32 = f"{zlib.crc32(content) & 0xffffffff:08X}"
        d = Document(document_id, file_name, path, len(content), crc32)
        self.docs[document_id] = d
        return d

    def find_by_crc(self, crc32: str) -> Document | None:
        for d in self.docs.values():
            if d.file_crc32 == crc32:
                return d
        return None

    def get(self, document_id: str) -> Document | None:
        return self.docs.get(document_id)


store = Store()
