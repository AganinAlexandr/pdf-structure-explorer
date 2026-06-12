# -*- coding: utf-8 -*-
"""Привязка текста к ячейкам таблиц и семантическое подтверждение.

Принципы (зафиксированы при обсуждении ТЗ):
  - пустая ячейка — нормальное состояние (графа "Примечание",
    незаполненные строки штампа): она остаётся ячейкой таблицы
    с has_text=False и не уменьшает доверие к таблице;
  - геометрический кандидат подтверждается таблицей, если текст
    есть хотя бы в confirm_text_cells ячейках; иначе понижается
    до frame_group (кирпичная кладка на сечениях, орнаменты);
  - аномально большая ячейка БЕЗ текста (пустое поле листа,
    замкнутое рамкой и штампом) исключается из таблицы:
    площадь > huge_cell_ratio x медианы площадей текстовых ячеек.

Связь с геометрией: модуль не меняет geometry.py, он принимает
его structures и обогащает их.
"""
from __future__ import annotations
from dataclasses import dataclass
from statistics import median


@dataclass
class TextBindConfig:
    confirm_text_cells: int = 2     # минимум текстовых ячеек для таблицы
    huge_cell_ratio: float = 12.0   # отсев пустых ячеек крупнее медианы в N раз
    center_eps: float = 0.5         # pt, допуск попадания центра span в ячейку
    symbol_serial_min: int = 5
    symbol_cell_max_w: float = 60.0
    symbol_cell_max_h: float = 40.0
    symbol_cells_max: int = 12
    max_cell_page_ratio: float = 0.35


def extract_spans(page):
    """Текстовые span'ы страницы в плоском виде."""
    spans = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for ln in b["lines"]:
            for sp in ln["spans"]:
                t = sp["text"]
                if not t.strip():
                    continue
                x0, y0, x1, y1 = sp["bbox"]
                spans.append({
                    "text": t, "bbox": sp["bbox"],
                    "cx": (x0+x1)/2, "cy": (y0+y1)/2,
                    "font": sp["font"], "size": round(sp["size"], 2),
                    "flags": sp["flags"], "color": sp["color"],
                    "dir": ln.get("dir", (1, 0)),
                })
    return spans


def _inside(sp, bbox, eps):
    x0, y0, x1, y1 = bbox
    return (x0-eps <= sp["cx"] <= x1+eps) and (y0-eps <= sp["cy"] <= y1+eps)


def bind_text(structures, spans, cfg: TextBindConfig | None = None,
              page_area: float | None = None):
    """Обогащает structures текстом; возвращает (structures, free_spans).

    Таблицы получают: cells[*].text/has_text/spans,
    cells_with_text, text_fill_ratio, confirmed.
    Неподтверждённые таблицы понижаются до kind='frame_group'.
    free_spans — текст, не попавший ни в одну ячейку (подписи,
    выноски, основной текст страницы).
    """
    cfg = cfg or TextBindConfig()
    used = [False] * len(spans)
    span_index = {id(sp): k for k, sp in enumerate(spans)}

    for st in structures:
        if st.get("kind") != "table" or "cells" not in st:
            continue
        cells = st["cells"]
        # сортировка ячеек сверху вниз, слева направо — порядок чтения
        cells.sort(key=lambda c: (c["row"], c["col"]))
        for c in cells:
            c["spans"] = []
        # привязка: центр span внутри bbox ячейки; при вложенности
        # (ячейка в ячейке после объединений) побеждает меньшая
        for k, sp in enumerate(spans):
            best, best_area = None, None
            for c in cells:
                if _inside(sp, c["bbox"], cfg.center_eps):
                    x0, y0, x1, y1 = c["bbox"]
                    area = (x1-x0) * (y1-y0)
                    if best is None or area < best_area:
                        best, best_area = c, area
            if best is not None:
                best["spans"].append(sp)
                used[k] = True
        for c in cells:
            c["spans"].sort(key=lambda s: (round(s["cy"], 1), s["cx"]))
            c["text"] = " ".join(s["text"] for s in c["spans"]).strip()
            c["has_text"] = bool(c["text"])

        # Drop oversized sheet-field cells, even when they captured page text.
        text_areas = [(c["bbox"][2]-c["bbox"][0]) * (c["bbox"][3]-c["bbox"][1])
                      for c in cells if c["has_text"]]
        if text_areas or page_area:
            lim = cfg.huge_cell_ratio * median(text_areas) if text_areas else None
            page_lim = cfg.max_cell_page_ratio * page_area if page_area else None

            def keep_cell(cell):
                area = ((cell["bbox"][2] - cell["bbox"][0]) *
                        (cell["bbox"][3] - cell["bbox"][1]))
                if page_lim is not None and area > page_lim:
                    return False
                if cell["has_text"]:
                    return True
                return lim is None or area <= lim

            kept = [c for c in cells if keep_cell(c)]
            if len(kept) != len(cells):
                dropped = [c for c in cells if not keep_cell(c)]
                for cell in dropped:
                    for sp in cell.get("spans", []):
                        idx = span_index.get(id(sp))
                        if idx is not None:
                            used[idx] = False
                st["dropped_huge_cells"] = len(cells) - len(kept)
                st["cells"] = cells = kept
                st["cell_count"] = len(cells)
                if cells:
                    st["table_bbox"] = (
                        min(c["bbox"][0] for c in cells),
                        min(c["bbox"][1] for c in cells),
                        max(c["bbox"][2] for c in cells),
                        max(c["bbox"][3] for c in cells))

        n_text = sum(1 for c in cells if c["has_text"])
        st["cells_with_text"] = n_text
        st["text_fill_ratio"] = round(n_text / len(cells), 3) if cells else 0.0
        st["confirmed"] = n_text >= cfg.confirm_text_cells and len(cells) >= 2
        if not st["confirmed"]:
            st["kind"] = "frame_group"     # геометрия таблицы без текста

    _demote_symbol_grids(structures, cfg)
    free = [sp for k, sp in enumerate(spans) if not used[k]]
    return structures, free


def _demote_symbol_grids(structures, cfg: TextBindConfig):
    groups = {}
    for st in structures:
        if st.get("kind") not in ("table", "frame_group") or not st.get("cells"):
            continue
        cells = st["cells"]
        if len(cells) > cfg.symbol_cells_max:
            continue
        widths = sorted(c["bbox"][2] - c["bbox"][0] for c in cells)
        heights = sorted(c["bbox"][3] - c["bbox"][1] for c in cells)
        med_w = widths[len(widths) // 2]
        med_h = heights[len(heights) // 2]
        if med_w > cfg.symbol_cell_max_w or med_h > cfg.symbol_cell_max_h:
            continue
        key = (
            st.get("rows"),
            st.get("cols"),
            round(med_w / 5),
            round(med_h / 5),
        )
        groups.setdefault(key, []).append(st)

    for members in groups.values():
        if len(members) < cfg.symbol_serial_min:
            continue
        for st in members:
            st["kind"] = "symbol_grid"
            st["symbol_series"] = len(members)


def table_matrix(table):
    """Таблица -> матрица строк (None для перекрытых merged-ячеек),
    в духе page.find_tables().extract()."""
    cells = table.get("cells", [])
    if not cells:
        return []
    rows = sorted({c["row"] for c in cells})
    cols = sorted({c["col"] for c in cells})
    rindex = {r: i for i, r in enumerate(rows)}
    cindex = {c: i for i, c in enumerate(cols)}
    mat = [[None] * len(cols) for _ in rows]
    for c in cells:
        mat[rindex[c["row"]]][cindex[c["col"]]] = c.get("text", "")
    return mat
