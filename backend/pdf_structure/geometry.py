# -*- coding: utf-8 -*-
"""Геометрический движок pdf-structure-explorer, v2.

Изменения относительно v1 (по результатам прогона на реальных файлах):
  - граф связности: пространственная хэш-сетка вместо O(n^2);
  - нормализация: один проход по отсортированным сегментам;
  - проверка покрытия границ ячеек: предвычисленные объединённые
    интервалы по кластерам координат + бинарный поиск;
  - защита от взрыва кандидатной сетки на CAD-страницах
    (max_grid_cells) -> класс 'complex' без поячеечного разбора;
  - дедупликация изображений по objId (штриховка тайлами в CAD
    даёт тысячи ссылок на одни и те же объекты).
"""
from __future__ import annotations
from dataclasses import dataclass
from bisect import bisect_right
import math


@dataclass
class EngineConfig:
    eps_join: float = 1.5
    eps_join_max: float = 3.0
    eps_grid: float = 1.0
    eps_dup: float = 1.0
    thin_fill_max: float = 2.5
    cover_min: float = 0.85
    diag_tol: float = 0.5
    max_grid_cells: int = 20000     # кандидатных ячеек на компоненту
    max_cells_store: int = 3000
    min_cell_size: float = 3.5     # pt, отсев вырожденных ячеек     # хранить геометрию ячеек не более


@dataclass
class Segment:
    axis: str
    pos: float
    a: float
    b: float
    thickness: float
    color: tuple | None
    draw_order: int
    source: str
    rect_id: int | None = None

    @property
    def length(self): return self.b - self.a

    def bbox(self):
        return (self.a, self.pos, self.b, self.pos) if self.axis == 'h' \
            else (self.pos, self.a, self.pos, self.b)


# ---------------------------------------------------------------- шаг 0
def extract_primitives(page, cfg: EngineConfig):
    segments, native_rects, others = [], [], []
    rect_seq = 0
    for order, d in enumerate(page.get_drawings()):
        color = d.get("color") or d.get("fill")
        width = d.get("width") or 0.0
        if d["type"] in ("f", "fs") and len(d["items"]) == 1 \
                and d["items"][0][0] == "re":
            r = d["items"][0][1]
            if min(r.width, r.height) <= cfg.thin_fill_max \
                    and max(r.width, r.height) > 3 * min(r.width, r.height):
                if r.width >= r.height:
                    segments.append(Segment('h', (r.y0+r.y1)/2, r.x0, r.x1,
                                            r.height, color, order, 'filled_rect'))
                else:
                    segments.append(Segment('v', (r.x0+r.x1)/2, r.y0, r.y1,
                                            r.width, color, order, 'filled_rect'))
                continue
        for it in d["items"]:
            kind = it[0]
            if kind == "re":
                r = it[1]
                rid = rect_seq; rect_seq += 1
                native_rects.append({"id": rid, "rect": (r.x0, r.y0, r.x1, r.y1),
                                     "draw_order": order, "color": color,
                                     "width": width, "filled": d["type"] != "s"})
                segments += [
                    Segment('h', r.y0, r.x0, r.x1, width, color, order, 'rect_edge', rid),
                    Segment('h', r.y1, r.x0, r.x1, width, color, order, 'rect_edge', rid),
                    Segment('v', r.x0, r.y0, r.y1, width, color, order, 'rect_edge', rid),
                    Segment('v', r.x1, r.y0, r.y1, width, color, order, 'rect_edge', rid)]
            elif kind == "l":
                p1, p2 = it[1], it[2]
                if abs(p1.y - p2.y) <= cfg.diag_tol:
                    a, b = sorted((p1.x, p2.x))
                    if b - a > 1e-6:
                        segments.append(Segment('h', (p1.y+p2.y)/2, a, b,
                                                width, color, order, 'stroke'))
                elif abs(p1.x - p2.x) <= cfg.diag_tol:
                    a, b = sorted((p1.y, p2.y))
                    if b - a > 1e-6:
                        segments.append(Segment('v', (p1.x+p2.x)/2, a, b,
                                                width, color, order, 'stroke'))
                else:
                    others.append({"subtype": "diagonal_line",
                                   "bbox": (min(p1.x,p2.x), min(p1.y,p2.y),
                                            max(p1.x,p2.x), max(p1.y,p2.y)),
                                   "length": math.dist(p1, p2),
                                   "thickness": width, "color": color,
                                   "draw_order": order})
            else:
                pts = [p for p in it[1:] if hasattr(p, "x")]
                xs = [p.x for p in pts] or [0]; ys = [p.y for p in pts] or [0]
                others.append({"subtype": "curve" if kind == "c" else str(kind),
                               "bbox": (min(xs), min(ys), max(xs), max(ys)),
                               "thickness": width, "color": color,
                               "draw_order": order})
    return segments, native_rects, others


# ---------------------------------------------------------------- шаг 1
def normalize_segments(segments, cfg: EngineConfig):
    out = []
    for axis in ('h', 'v'):
        ss = sorted((s for s in segments if s.axis == axis),
                    key=lambda s: (s.pos, s.a))
        groups = []
        for s in ss:                      # цепная группировка по pos
            if groups and s.pos - groups[-1][-1].pos <= cfg.eps_dup:
                groups[-1].append(s)
            else:
                groups.append([s])
        for g in groups:
            pos = sum(x.pos for x in g) / len(g)
            g.sort(key=lambda s: s.a)
            merged = []
            for s in g:
                eps = min(max(cfg.eps_join, 2*s.thickness), cfg.eps_join_max)
                if merged and s.a - merged[-1].b <= eps:
                    m = merged[-1]
                    m.b = max(m.b, s.b)
                    m.thickness = max(m.thickness, s.thickness)
                else:
                    merged.append(Segment(axis, pos, s.a, s.b, s.thickness,
                                          s.color, s.draw_order, s.source, s.rect_id))
            out += merged
    return out


# ---------------------------------------------------------------- шаг 2
def _seg_distance(s1: Segment, s2: Segment) -> float:
    def gap(a1, b1, a2, b2):
        return max(0.0, max(a1, a2) - min(b1, b2))
    if s1.axis == s2.axis:
        if s1.axis == 'h':
            return math.hypot(gap(s1.a, s1.b, s2.a, s2.b), s1.pos - s2.pos)
        return math.hypot(s1.pos - s2.pos, gap(s1.a, s1.b, s2.a, s2.b))
    h, v = (s1, s2) if s1.axis == 'h' else (s2, s1)
    return math.hypot(gap(h.a, h.b, v.pos, v.pos), gap(v.a, v.b, h.pos, h.pos))


class _UF:
    def __init__(self, n):
        self.p = list(range(n)); self.r = [0]*n
    def find(self, i):
        p = self.p
        while p[i] != i:
            p[i] = p[p[i]]; i = p[i]
        return i
    def union(self, i, j):
        ri, rj = self.find(i), self.find(j)
        if ri == rj: return
        if self.r[ri] < self.r[rj]: ri, rj = rj, ri
        self.p[rj] = ri
        if self.r[ri] == self.r[rj]: self.r[ri] += 1


def build_components(segments, cfg: EngineConfig):
    n = len(segments)
    uf = _UF(n)
    cell = max(2 * cfg.eps_join_max, 12.0)
    grid = {}
    for i, s in enumerate(segments):
        x0, y0, x1, y1 = s.bbox()
        e = cfg.eps_join_max
        for gx in range(int((x0-e)//cell), int((x1+e)//cell) + 1):
            for gy in range(int((y0-e)//cell), int((y1+e)//cell) + 1):
                grid.setdefault((gx, gy), []).append(i)
    for bucket in grid.values():
        L = len(bucket)
        for ii in range(L):
            si = segments[bucket[ii]]
            for jj in range(ii+1, L):
                i, j = bucket[ii], bucket[jj]
                if uf.find(i) == uf.find(j):
                    continue
                sj = segments[j]
                eps = min(max(cfg.eps_join,
                              2*max(si.thickness, sj.thickness)),
                          cfg.eps_join_max)
                if _seg_distance(si, sj) <= eps:
                    uf.union(i, j)
    comps = {}
    for i, s in enumerate(segments):
        comps.setdefault(uf.find(i), []).append(s)
    return list(comps.values())


# ---------------------------------------------------------------- шаг 3
class _AxisClusters:
    """Кластеры поперечных координат + объединённые интервалы покрытия."""
    def __init__(self, segs, eps):
        self.pos, self.ivals = [], []
        members, last = [], None
        for s in sorted(segs, key=lambda x: x.pos):
            if members and s.pos - last <= eps:
                members[-1].append(s)
            else:
                members.append([s])
            last = s.pos
        for m in members:
            self.pos.append(sum(x.pos for x in m) / len(m))
            iv = sorted((x.a, x.b) for x in m)
            merged = []
            for lo, hi in iv:
                if merged and lo <= merged[-1][1] + 1e-9:
                    merged[-1][1] = max(merged[-1][1], hi)
                else:
                    merged.append([lo, hi])
            self.ivals.append(merged)
        self._starts = [[iv[0] for iv in m] for m in self.ivals]

    def covered(self, idx, a, b, frac):
        """Доля покрытия [a,b] интервалами кластера idx >= frac ?"""
        need = frac * (b - a)
        ivs, starts = self.ivals[idx], self._starts[idx]
        k = max(0, bisect_right(starts, a) - 1)
        got = 0.0
        while k < len(ivs) and ivs[k][0] < b:
            got += max(0.0, min(ivs[k][1], b) - max(ivs[k][0], a))
            if got >= need: return True
            k += 1
        return got >= need


def classify_component(comp, cfg: EngineConfig):
    """Решёточный разбор компоненты. Возвращает СПИСОК структур.

    Узлы решётки: (кластер X) x (кластер Y). Ребро есть, если интервал
    между соседними кластерами фактически покрыт отрезками (cover_min).
    Ячейка ищется обходом от верхнего левого угла: вправо по верхним
    рёбрам до узла с ребром вниз, вниз по левым рёбрам до узла с ребром
    вправо, затем проверка нижней и правой границ. Это корректно
    обрабатывает объединённые ячейки и "чужие" кластеры компоненты
    (узлы без рёбер просто проходятся насквозь).
    """
    hs = [s for s in comp if s.axis == 'h']
    vs = [s for s in comp if s.axis == 'v']
    xs0 = min(s.bbox()[0] for s in comp); ys0 = min(s.bbox()[1] for s in comp)
    xs1 = max(s.bbox()[2] for s in comp); ys1 = max(s.bbox()[3] for s in comp)
    bbox = (xs0, ys0, xs1, ys1)
    if len(comp) == 1:
        return [{"kind": "line", "bbox": bbox}]
    if not hs or not vs:
        return [{"kind": "polyline", "bbox": bbox, "segments": len(comp)}]

    H = _AxisClusters(hs, cfg.eps_grid)      # кластеры по y
    V = _AxisClusters(vs, cfg.eps_grid)      # кластеры по x
    X, Y = V.pos, H.pos
    if len(X) < 2 or len(Y) < 2:
        return [{"kind": "polyline", "bbox": bbox, "segments": len(comp)}]
    if (len(X)-1) * (len(Y)-1) > cfg.max_grid_cells:
        return [{"kind": "complex", "bbox": bbox, "segments": len(comp),
                 "grid_x": len(X), "grid_y": len(Y)}]

    NX, NY = len(X), len(Y)
    # рёбра решётки
    hedge = [set() for _ in range(NY)]       # hedge[j] = {i: покрыт X[i]..X[i+1]}
    for j in range(NY):
        for i in range(NX-1):
            if H.covered(j, X[i], X[i+1], cfg.cover_min):
                hedge[j].add(i)
    vedge = [set() for _ in range(NX)]       # vedge[i] = {j: покрыт Y[j]..Y[j+1]}
    for i in range(NX):
        for j in range(NY-1):
            if V.covered(i, Y[j], Y[j+1], cfg.cover_min):
                vedge[i].add(j)

    def cell_at(i, j):
        i2 = i
        while True:                          # вправо по верхней границе
            if i2 >= NX-1 or i2 not in hedge[j]:
                return None
            i2 += 1
            if j in vedge[i2]:
                break
        j2 = j
        while True:                          # вниз по левой границе
            if j2 >= NY-1 or j2 not in vedge[i]:
                return None
            j2 += 1
            if i in hedge[j2]:
                break
        for k in range(i, i2):               # нижняя граница
            if k not in hedge[j2]:
                return None
        for k in range(j, j2):               # правая граница
            if k not in vedge[i2]:
                return None
        return (i, i2, j, j2)

    cells, seen = [], set()
    for j in range(NY-1):
        for i in range(NX-1):
            if i in hedge[j] and j in vedge[i]:
                c = cell_at(i, j)
                if c and c not in seen:
                    w, h = X[c[1]]-X[c[0]], Y[c[3]]-Y[c[2]]
                    if w >= cfg.min_cell_size and h >= cfg.min_cell_size:
                        seen.add(c); cells.append(c)

    if not cells:
        return [{"kind": "polyline", "bbox": bbox, "segments": len(comp)}]

    # группировка ячеек в таблицы по смежности на решётке
    uf = _UF(len(cells))
    for a in range(len(cells)):
        ia, i2a, ja, j2a = cells[a]
        for b in range(a+1, len(cells)):
            ib, i2b, jb, j2b = cells[b]
            touch_x = (i2a == ib or i2b == ia) and (ja < j2b and jb < j2a)
            touch_y = (j2a == jb or j2b == ja) and (ia < i2b and ib < i2a)
            if touch_x or touch_y:
                uf.union(a, b)
    groups = {}
    for k in range(len(cells)):
        groups.setdefault(uf.find(k), []).append(cells[k])

    out = []
    for g in groups.values():
        gb = (X[min(c[0] for c in g)], Y[min(c[2] for c in g)],
              X[max(c[1] for c in g)], Y[max(c[3] for c in g)])
        if len(g) == 1:
            out.append({"kind": "frame", "bbox": gb, "cell_count": 1})
            continue
        bands_r = set(); bands_c = set()
        for i, i2, j, j2 in g:
            bands_r.update(range(j, j2)); bands_c.update(range(i, i2))
        merged = any((i2-i > 1) or (j2-j > 1) for i, i2, j, j2 in g)
        full = len(g) == len(bands_r) * len(bands_c) and not merged
        res = {"kind": "table", "bbox": bbox, "table_bbox": gb,
               "rows": len(bands_r), "cols": len(bands_c),
               "cell_count": len(g), "has_merged_cells": merged,
               "confidence": "high" if (full or merged) else "partial",
               "extra_frame": gb != bbox}
        if len(g) <= cfg.max_cells_store:
            res["cells"] = [{"bbox": (X[i], Y[j], X[i2], Y[j2]),
                             "row": j, "col": i,
                             "row_span": j2-j, "col_span": i2-i}
                            for i, i2, j, j2 in g]
        out.append(res)
    return out


# ---------------------------------------------------------------- фасад
def analyze_page(page, cfg: EngineConfig | None = None):
    cfg = cfg or EngineConfig()
    raw, rects, others = extract_primitives(page, cfg)
    segs = normalize_segments(raw, cfg)
    comps = build_components(segs, cfg)
    structures = []
    for ci, comp in enumerate(comps):
        for st in classify_component(comp, cfg):
            st["component"] = ci
            st["segment_count"] = len(comp)
            st["draw_order"] = min(s.draw_order for s in comp)
            st["thickness"] = max(s.thickness for s in comp)
            structures.append(st)
    return {"raw_segments": len(raw), "segments": segs,
            "native_rects": rects, "others": others,
            "components": comps, "structures": structures, "config": cfg}
