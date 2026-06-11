#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import re
import subprocess
import zlib
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font


ROOT = Path(r"E:\Projects\Объекты\архив_проектов\упрощенные_объекты")
OUTPUT_CSV = Path(r"E:\commons\pdf-structure-explorer\reference\simplified_objects_section_map.csv")

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

EXCLUDE_MARKERS = ("ИУЛ", "УИЛ")
PHRASE_SECTION_MAP = {
    "ПОЯСНИТЕЛЬНАЯ ЗАПИСКА": "ПЗ",
    "КОНСТРУКТИВНЫЕ РЕШЕНИЯ": "КР",
    "ПРОЕКТ ОРГАНИЗАЦИИ СТРОИТЕЛЬСТВА": "ПОС",
    "СМЕТА НА СТРОИТЕЛЬСТВО": "СМ",
}
SECTION_ALIASES = {
    "ИОС1": "ЭС",
    "ИОС1.1": "ЭС",
    "ИОС1.2": "ЭС",
    "ИОС1.3": "ЭС",
    "ИОС2": "ВС",
    "ИОС2.1": "ВС",
    "ИОС2.2": "ВС",
    "ИОС2.3": "ВС",
    "ИОС3": "ВО",
    "ИОС3.1": "ВО",
    "ИОС3.2": "ВО",
    "ИОС3.3": "ВО",
    "ИОС4": "ОВ",
    "ИОС4.1": "ОВ",
    "ИОС4.2": "ОВ",
    "ИОС4.3": "ОВ",
    "ИОС5.1": "ЭС",
    "ИОС5.2": "ВС",
    "ИОС5.3": "ВО",
    "ИОС5.4": "ОВ",
    "ИОС5.4.1": "ОВ",
    "ИОС5.4.2": "ОВ",
    "ИОС5.5": "СС",
    "ИОС5.6": "ГС",
}

CODE_PATTERNS = [
    re.compile(r"\b(ИОС\d+(?:\.\d+)?)\b", re.IGNORECASE),
    re.compile(r"\b(ИЛО\d+(?:\.\d+)?)\b", re.IGNORECASE),
    re.compile(r"\b(ТКР\d+(?:\.\d+)?)\b", re.IGNORECASE),
    re.compile(r"\b(ПОКР|ПЗУ|ГОЧС|ТБЭ|ООС|ПОС|ПБ|КР|АР|ПЗ|СМ|ТХ|ППО|ПРБ|РЗ)\b", re.IGNORECASE),
]
RAW_SECTION_PATTERN = re.compile(
    r"РАЗДЕЛ(?:\s+ПД)?\s*[№N]?\s*\d+(?:\.\d+)?[_\s-]+([A-ZА-ЯЁ0-9._-]{2,20})",
    re.IGNORECASE,
)
OBJECT_CODE_PATTERN = re.compile(r"^\s*(\d{1,4}(?:[-_]\d{2})?)(?=$|[^\d])")
TOKEN_SPLIT_PATTERN = re.compile(r"[^A-ZА-ЯЁ0-9.]+", re.IGNORECASE)
SIMPLE_SECTION_CODES = {
    "ПОКР", "ПЗУ", "ГОЧС", "ТБЭ", "ООС", "ПОС", "ПБ", "КР", "АР",
    "ПЗ", "СМ", "ТХ", "ППО", "ПРБ", "РЗ", "ОВ", "ВК", "ЭС", "СС",
    "ВС", "ГС", "ВО", "ТТР", "ИД",
}


def list_pdf_files(root: Path) -> list[Path]:
    script = (
        f"Get-ChildItem -LiteralPath '{root}' -Recurse -File | "
        "Where-Object { $_.Extension -match '^(?i)\\.pdf$' } | "
        "Select-Object -ExpandProperty FullName"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def compute_crc32(path: Path) -> str:
    crc = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            crc = zlib.crc32(chunk, crc)
    return f"{crc & 0xFFFFFFFF:08X}"


def object_fields(top_folder: str) -> tuple[str, str]:
    match = OBJECT_CODE_PATTERN.match(top_folder)
    code = match.group(1) if match else ""
    return code, top_folder


def normalize_name(name: str) -> str:
    upper = name.upper()
    upper = upper.replace(".PDF", "")
    upper = upper.replace(".DOCX", "")
    upper = upper.replace("№", " ")
    upper = re.sub(r"[()!]+", " ", upper)
    upper = re.sub(r"\s+", " ", upper)
    return upper.strip()


def token_candidates(normalized: str) -> list[str]:
    return [token for token in TOKEN_SPLIT_PATTERN.split(normalized) if token]


def normalize_ios_with_suffix(tokens: list[str], index: int, code: str) -> str:
    if not code.startswith("ИОС"):
        return SECTION_ALIASES.get(code, code)
    if index + 1 < len(tokens):
        next_token = tokens[index + 1].upper()
        if next_token in SIMPLE_SECTION_CODES:
            return next_token
    return SECTION_ALIASES.get(code, code)


def extract_section_type(file_name: str) -> tuple[str, str, str]:
    normalized = normalize_name(file_name)
    if any(marker in normalized for marker in EXCLUDE_MARKERS):
        return "", "", "excluded_iul"

    for phrase, code in PHRASE_SECTION_MAP.items():
        if phrase in normalized:
            return code, code, "phrase"

    tokens = token_candidates(normalized)
    for index, token in enumerate(tokens):
        upper = token.upper()
        for pattern in CODE_PATTERNS:
            match = pattern.fullmatch(upper)
            if match:
                code = match.group(1).upper()
                code = normalize_ios_with_suffix(tokens, index, code)
                return code, code, "code"
        simple_base = upper.split(".", 1)[0]
        if simple_base in SIMPLE_SECTION_CODES:
            return simple_base, simple_base, "token"

    raw_match = RAW_SECTION_PATTERN.search(normalized)
    if raw_match:
        raw = raw_match.group(1).strip("._- ").upper()
        return raw, raw, "raw_section"

    return "", "", "non_section"


def build_rows(root: Path) -> tuple[list[dict[str, str]], Counter]:
    rows: list[dict[str, str]] = []
    stats: Counter = Counter()

    for full_path in list_pdf_files(root):
        stats["pdf_found"] += 1
        relative = full_path.relative_to(root)
        top_folder = relative.parts[0]
        file_name = full_path.name
        section_type, section_filter, method = extract_section_type(file_name)

        if method == "excluded_iul":
            stats["excluded_iul"] += 1
            continue

        object_code, object_name = object_fields(top_folder)
        stat = full_path.stat()
        rows.append({
            "object_code": object_code,
            "object_name": object_name,
            "document_role": "section" if section_type else "non_section",
            "section_type": section_type,
            "section_filter": section_filter,
            "subsection_type": "",
            "subsection_filter": "",
            "file_name": file_name,
            "file_crc32": compute_crc32(full_path),
            "source_root": str(root),
            "relative_path": str(relative.parent) if str(relative.parent) != "." else "",
            "full_path": str(full_path),
            "file_size_bytes": str(stat.st_size),
            "last_modified": dt.datetime.fromtimestamp(
                stat.st_mtime,
                tz=dt.timezone.utc,
            ).isoformat(timespec="seconds"),
            "source_catalog_group": root.name,
            "is_preferred_source": "false",
            "notes": method,
        })
        stats["section" if section_type else "non_section"] += 1

    mark_preferred_sources(rows)
    rows.sort(key=lambda row: (
        row["object_code"],
        row["document_role"],
        row["section_type"],
        row["file_name"].casefold(),
        row["full_path"].casefold(),
    ))
    return rows, stats


def mark_preferred_sources(rows: list[dict[str, str]]) -> None:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["file_name"].casefold(), row["file_crc32"])].append(row)
    for group in grouped.values():
        group.sort(key=lambda row: row["full_path"].casefold())
        group[0]["is_preferred_source"] = "true"


def write_csv(path: Path, rows: list[dict[str, str]], encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding=encoding) as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(path: Path, rows: list[dict[str, str]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "simplified_objects"
    sheet.append(CSV_HEADER)
    for row in rows:
        sheet.append([row.get(column, "") for column in CSV_HEADER])

    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions

    width_map = {
        "A": 16, "B": 32, "C": 14, "D": 16, "E": 16, "F": 18, "G": 18,
        "H": 44, "I": 14, "J": 24, "K": 42, "L": 96, "M": 16, "N": 24,
        "O": 24, "P": 18, "Q": 16,
    }
    for column, width in width_map.items():
        sheet.column_dimensions[column].width = width

    workbook.save(path)


def main() -> int:
    rows, stats = build_rows(ROOT)
    write_csv(OUTPUT_CSV, rows, "utf-8")
    write_csv(OUTPUT_CSV.with_name(f"{OUTPUT_CSV.stem}_excel.csv"), rows, "utf-8-sig")
    write_xlsx(OUTPUT_CSV.with_suffix(".xlsx"), rows)

    print(f"Output CSV: {OUTPUT_CSV}")
    print(f"Rows written: {len(rows)}")
    print(f"PDF found: {stats['pdf_found']}")
    print(f"Excluded IUL: {stats['excluded_iul']}")
    print(f"Sections: {stats['section']}")
    print(f"Non-sections: {stats['non_section']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
