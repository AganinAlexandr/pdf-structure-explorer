#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font


DEFAULT_WORKBOOK = Path(r"E:\output\pdf-structure-explorer\Elements_PDF.xlsx")
DEFAULT_LINKS = Path(r"E:\output\pdf-structure-explorer\Elements_PDF_document_links.csv")
DEFAULT_PIVOT_LINKS = Path(r"E:\output\pdf-structure-explorer\Elements_PDF_document_links_pivot.csv")
DEFAULT_OUTPUT = Path(r"E:\output\pdf-structure-explorer\Elements_PDF_enriched.xlsx")

LINK_FIELDS = [
    "object_code",
    "object_name",
    "document_role",
    "section_type",
    "section_filter",
    "subsection_type",
    "subsection_filter",
    "source_catalog_group",
    "match_found",
    "match_count",
    "match_mode",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an enriched workbook with object and section metadata.")
    parser.add_argument("--workbook", default=str(DEFAULT_WORKBOOK))
    parser.add_argument("--links", default=str(DEFAULT_LINKS))
    parser.add_argument("--pivot-links", default=str(DEFAULT_PIVOT_LINKS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def normalize_text(value) -> str:
    return "" if value is None else str(value)


def load_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return rows, list(reader.fieldnames or [])


def build_link_index(path: Path) -> tuple[dict[str, dict[str, str]], list[dict[str, str]], list[str]]:
    rows, columns = load_csv_rows(path)
    index = {row["document_id"]: row for row in rows if row.get("document_id")}
    return index, rows, columns


def autofit(sheet, widths: dict[int, int]) -> None:
    for column_index, width in widths.items():
        sheet.column_dimensions[_column_letter(column_index)].width = width


def _column_letter(index: int) -> str:
    result = ""
    while index:
        index, rem = divmod(index - 1, 26)
        result = chr(65 + rem) + result
    return result


def append_table_sheet(workbook: Workbook, title: str, rows: list[dict[str, str]], columns: list[str]) -> None:
    sheet = workbook.create_sheet(title)
    sheet.append(columns)
    for row in rows:
        sheet.append([row.get(column, "") for column in columns])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    widths = {}
    for idx, column in enumerate(columns, start=1):
        width = 18
        if "path" in column:
            width = 72
        elif "file_name" in column:
            width = 42
        elif "object_name" in column:
            width = 32
        elif "section" in column:
            width = 18
        widths[idx] = width
    autofit(sheet, widths)


def enrich_sheet_rows(header: list[str], data_rows: list[list[str]], link_index: dict[str, dict[str, str]]) -> tuple[list[str], list[list[str]]]:
    if "document_id" not in header:
        return header, data_rows

    doc_idx = header.index("document_id")
    enriched_header = header + [f"linked_{field}" for field in LINK_FIELDS]
    enriched_rows = []
    for row in data_rows:
        doc_id = row[doc_idx] if doc_idx < len(row) else ""
        linked = link_index.get(doc_id, {})
        enriched_row = list(row)
        for field in LINK_FIELDS:
            enriched_row.append(linked.get(field, ""))
        enriched_rows.append(enriched_row)
    return enriched_header, enriched_rows


def main() -> int:
    args = parse_args()
    source_path = Path(args.workbook)
    links_path = Path(args.links)
    pivot_links_path = Path(args.pivot_links)
    output_path = Path(args.output)

    link_index, link_rows, link_columns = build_link_index(links_path)
    pivot_rows, pivot_columns = load_csv_rows(pivot_links_path)

    source_wb = load_workbook(source_path, read_only=True, data_only=True)
    out_wb = Workbook()
    out_wb.remove(out_wb.active)

    append_table_sheet(out_wb, "00_document_links", link_rows, link_columns)
    append_table_sheet(out_wb, "00_pivot_linked", pivot_rows, pivot_columns)

    for sheet in source_wb.worksheets[1:]:
        rows_iter = sheet.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration:
            continue
        header = [normalize_text(value) for value in header_row]
        data_rows = [[normalize_text(value) for value in row] for row in rows_iter]
        enriched_header, enriched_rows = enrich_sheet_rows(header, data_rows, link_index)

        out_sheet = out_wb.create_sheet(f"{sheet.title}_linked"[:31])
        out_sheet.append(enriched_header)
        for row in enriched_rows:
            out_sheet.append(row)
        for cell in out_sheet[1]:
            cell.font = Font(bold=True)
        out_sheet.freeze_panes = "A2"
        out_sheet.auto_filter.ref = out_sheet.dimensions

        widths = {}
        for idx, column in enumerate(enriched_header, start=1):
            width = 16
            if "document_id" == column:
                width = 18
            elif "file_name" in column:
                width = 42
            elif "object_name" in column:
                width = 32
            elif "section" in column:
                width = 18
            elif "path" in column:
                width = 60
            widths[idx] = width
        autofit(out_sheet, widths)

    out_wb.save(output_path)
    print(f"Output workbook: {output_path}")
    print(f"Document links rows: {len(link_rows)}")
    print(f"Pivot linked rows: {len(pivot_rows)}")
    print(f"Linked sheets created: {len(source_wb.worksheets) - 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
