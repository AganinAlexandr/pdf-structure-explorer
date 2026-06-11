#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import zlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font


DEFAULT_ROOTS = [
    Path(r"E:\MSE_арх"),
    Path(r"E:\Projects\Объекты\архив_проектов\упрощенные_объекты"),
    Path(r"E:\Архив\ЭиКо\Текущие на 0101_24"),
    Path(r"E:\Архив\ЭиКо\_АРХИВ_2022"),
    Path(r"E:\Архив\ЭиКо\_АРХИВ_2021"),
]

DEFAULT_OUTPUT = Path(r"E:\commons\pdf-structure-explorer\reference\object_file_map.csv")
EXCLUDE_NAME_PARTS = ("ИУЛ",)

CSV_HEADER = [
    "object_code",
    "object_name",
    "document_role",
    "section_type",
    "section_filter",
    "subsection_type",
    "subsection_filter",
    "file_name",
    "file_crc32",
    "source_root",
    "relative_path",
    "full_path",
    "file_size_bytes",
    "last_modified",
    "source_catalog_group",
    "is_preferred_source",
    "notes",
]


@dataclass
class BuildStats:
    scanned_pdf: int = 0
    excluded_by_name: int = 0
    missing_roots: int = 0
    skipped_io_errors: int = 0
    written_rows: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build object_file_map.csv from object catalog roots.",
    )
    parser.add_argument(
        "--root",
        dest="roots",
        action="append",
        help="Additional or replacement root to scan. Can be passed multiple times.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output CSV path. Default: {DEFAULT_OUTPUT}",
    )
    return parser.parse_args()


def normalize_text(value: str) -> str:
    return value.casefold()


def should_exclude(file_name: str) -> bool:
    lowered = normalize_text(file_name)
    return any(normalize_text(part) in lowered for part in EXCLUDE_NAME_PARTS)


def compute_crc32(path: Path) -> str:
    crc = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            crc = zlib.crc32(chunk, crc)
    return f"{crc & 0xFFFFFFFF:08X}"


def build_row(root: Path, file_path: Path) -> dict[str, str]:
    stat = file_path.stat()
    parent_relative = file_path.parent.relative_to(root)
    relative_path = "" if str(parent_relative) == "." else str(parent_relative)
    return {
        "object_code": "",
        "object_name": "",
        "document_role": "unknown",
        "section_type": "",
        "section_filter": "",
        "subsection_type": "",
        "subsection_filter": "",
        "file_name": file_path.name,
        "file_crc32": compute_crc32(file_path),
        "source_root": str(root),
        "relative_path": relative_path,
        "full_path": str(file_path),
        "file_size_bytes": str(stat.st_size),
        "last_modified": dt.datetime.fromtimestamp(
            stat.st_mtime,
            tz=dt.timezone.utc,
        ).isoformat(timespec="seconds"),
        "source_catalog_group": root.name,
        "is_preferred_source": "false",
        "notes": "",
    }


def collect_rows(roots: list[Path]) -> tuple[list[dict[str, str]], BuildStats]:
    rows: list[dict[str, str]] = []
    stats = BuildStats()
    for root in roots:
        if not root.exists():
            stats.missing_roots += 1
            continue
        for file_path in root.rglob("*.pdf"):
            stats.scanned_pdf += 1
            if should_exclude(file_path.name):
                stats.excluded_by_name += 1
                continue
            try:
                rows.append(build_row(root, file_path))
            except OSError:
                stats.skipped_io_errors += 1
    mark_preferred_sources(rows)
    rows.sort(
        key=lambda row: (
            row["object_code"],
            row["object_name"],
            row["file_name"].casefold(),
            row["file_crc32"],
            row["full_path"].casefold(),
        ),
    )
    stats.written_rows = len(rows)
    return rows, stats


def mark_preferred_sources(rows: list[dict[str, str]]) -> None:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (row["file_name"].casefold(), row["file_crc32"])
        grouped[key].append(row)
    for group in grouped.values():
        group.sort(key=lambda row: row["full_path"].casefold())
        group[0]["is_preferred_source"] = "true"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def write_excel_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(path: Path, rows: list[dict[str, str]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "object_file_map"
    sheet.append(CSV_HEADER)
    for row in rows:
        sheet.append([row.get(column, "") for column in CSV_HEADER])

    header_font = Font(bold=True)
    for cell in sheet[1]:
        cell.font = header_font

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions

    width_map = {
        "A": 16, "B": 28, "C": 14, "D": 20, "E": 18, "F": 20, "G": 18,
        "H": 42, "I": 14, "J": 24, "K": 42, "L": 90, "M": 16, "N": 24,
        "O": 24, "P": 18, "Q": 24,
    }
    for column, width in width_map.items():
        sheet.column_dimensions[column].width = width

    workbook.save(path)


def main() -> int:
    args = parse_args()
    roots = [Path(value) for value in args.roots] if args.roots else list(DEFAULT_ROOTS)
    output = Path(args.output)
    rows, stats = collect_rows(roots)
    write_csv(output, rows)
    write_excel_csv(output.with_name(f"{output.stem}_excel.csv"), rows)
    write_xlsx(output.with_suffix(".xlsx"), rows)

    duplicate_groups = 0
    seen: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        seen[(row["file_name"].casefold(), row["file_crc32"])] += 1
    duplicate_groups = sum(1 for count in seen.values() if count > 1)

    print(f"Output: {output}")
    print(f"Roots scanned: {len(roots)}")
    print(f"PDF scanned: {stats.scanned_pdf}")
    print(f"Excluded by name rule: {stats.excluded_by_name}")
    print(f"Missing roots: {stats.missing_roots}")
    print(f"Skipped IO errors: {stats.skipped_io_errors}")
    print(f"Rows written: {stats.written_rows}")
    print(f"Duplicate file groups (file_name + file_crc32): {duplicate_groups}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
