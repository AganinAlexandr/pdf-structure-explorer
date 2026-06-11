#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font


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
    source = Path(r"E:\commons\pdf-structure-explorer\reference\object_file_map.csv")
    excel_csv = source.with_name(f"{source.stem}_excel.csv")
    xlsx_path = source.with_suffix(".xlsx")

    with source.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    write_excel_csv(excel_csv, rows)
    write_xlsx(xlsx_path, rows)

    print(f"Source CSV: {source}")
    print(f"Excel CSV: {excel_csv}")
    print(f"Excel XLSX: {xlsx_path}")
    print(f"Rows exported: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
