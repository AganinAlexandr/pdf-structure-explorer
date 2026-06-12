#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import shutil
import zlib
from pathlib import Path


DEFAULT_EXPORTS_ROOT = Path(r"E:\output\pdf-structure-explorer\exports")
DEFAULT_UPLOADS_ROOT = Path(r"E:\output\pdf-structure-explorer\storage\uploads")
DEFAULT_BACKUP_ROOT = Path(r"E:\output\pdf-structure-explorer\migration_backups")
CSV_FILES = [
    "documents.csv",
    "pages.csv",
    "layers.csv",
    "elements.csv",
    "text_segments.csv",
    "images.csv",
    "tables.csv",
    "table_cells.csv",
    "language_summary.csv",
    "group_summary.csv",
    "page_summary.csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate export bundle folder names and document IDs to doc_<crc32> format.",
    )
    parser.add_argument("--exports-root", default=str(DEFAULT_EXPORTS_ROOT))
    parser.add_argument("--uploads-root", default=str(DEFAULT_UPLOADS_ROOT))
    parser.add_argument("--backup-root", default=str(DEFAULT_BACKUP_ROOT))
    parser.add_argument("--skip-backup", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def normalize_text(value: str) -> str:
    return str(value or "").strip()


def document_id_for_crc32(crc32: str) -> str:
    return f"doc_{normalize_text(crc32).lower()}"


def compute_crc32(path: Path) -> str:
    crc = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            crc = zlib.crc32(chunk, crc)
    return f"{crc & 0xFFFFFFFF:08X}"


def load_documents_row(bundle_dir: Path) -> dict[str, str]:
    doc_csv = bundle_dir / "documents.csv"
    with doc_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        try:
            return next(reader)
        except StopIteration as exc:
            raise ValueError(f"Empty documents.csv in {bundle_dir}") from exc


def iter_bundle_dirs(exports_root: Path) -> list[Path]:
    return sorted(
        [
            path for path in exports_root.iterdir()
            if path.is_dir() and path.name.startswith("doc_") and (path / "documents.csv").exists()
        ],
        key=lambda path: path.name.casefold(),
    )


def plan_migration(exports_root: Path, uploads_root: Path) -> list[dict[str, object]]:
    plan = []
    target_ids = {}
    for bundle_dir in iter_bundle_dirs(exports_root):
        row = load_documents_row(bundle_dir)
        old_id = normalize_text(row.get("document_id", "")) or bundle_dir.name
        crc32 = normalize_text(row.get("file_crc32", ""))
        upload_path = Path(normalize_text(row.get("file_path", "")).replace("/", "\\"))
        if not crc32 and upload_path.exists():
            crc32 = compute_crc32(upload_path)
        if not crc32:
            raise ValueError(f"Missing file_crc32 for {bundle_dir}")
        new_id = document_id_for_crc32(crc32)
        if new_id in target_ids and target_ids[new_id] != bundle_dir:
            raise ValueError(
                f"Target ID collision: {bundle_dir.name} and {target_ids[new_id].name} -> {new_id}",
            )
        target_ids[new_id] = bundle_dir
        plan.append(
            {
                "bundle_dir": bundle_dir,
                "old_id": old_id,
                "new_id": new_id,
                "crc32": crc32,
                "upload_path": upload_path if upload_path.exists() else uploads_root / f"{old_id}.pdf",
                "new_upload_path": uploads_root / f"{new_id}.pdf",
            },
        )
    return plan


def backup_plan(plan: list[dict[str, object]], backup_root: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_root = backup_root / f"crc32_id_migration_{stamp}"
    exports_backup = session_root / "exports"
    uploads_backup = session_root / "uploads"
    exports_backup.mkdir(parents=True, exist_ok=False)
    uploads_backup.mkdir(parents=True, exist_ok=False)

    for item in plan:
        bundle_dir = item["bundle_dir"]
        upload_path = item["upload_path"]
        shutil.copytree(bundle_dir, exports_backup / bundle_dir.name)
        if Path(upload_path).exists():
            shutil.copy2(upload_path, uploads_backup / Path(upload_path).name)

    return session_root


def replace_id_value(column: str, value: str, old_id: str, new_id: str) -> str:
    text = value
    lower_col = column.casefold()
    if text == old_id:
        return new_id
    if lower_col in {"page_id", "pageid"} and text.startswith(old_id + "_p_"):
        return new_id + text[len(old_id):]
    if lower_col in {"file_path", "filepath", "path"} and old_id in text:
        return text.replace(old_id, new_id)
    return text


def rewrite_csv(path: Path, old_id: str, new_id: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    rewritten = []
    for row in rows:
        out = {}
        for column in fieldnames:
            out[column] = replace_id_value(column, row.get(column, ""), old_id, new_id)
        rewritten.append(out)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rewritten)


def rewrite_manifest(path: Path, old_id: str, new_id: str) -> None:
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("documentId") == old_id:
        data["documentId"] = new_id
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def migrate_bundle(item: dict[str, object]) -> None:
    bundle_dir = Path(item["bundle_dir"])
    old_id = str(item["old_id"])
    new_id = str(item["new_id"])
    upload_path = Path(item["upload_path"])
    new_upload_path = Path(item["new_upload_path"])

    for file_name in CSV_FILES:
        csv_path = bundle_dir / file_name
        if csv_path.exists():
            rewrite_csv(csv_path, old_id, new_id)
    rewrite_manifest(bundle_dir / "manifest.json", old_id, new_id)

    if upload_path.exists() and upload_path != new_upload_path:
        if new_upload_path.exists():
            raise FileExistsError(f"Target upload already exists: {new_upload_path}")
        shutil.move(str(upload_path), str(new_upload_path))

    target_bundle_dir = bundle_dir.with_name(new_id)
    if bundle_dir != target_bundle_dir:
        if target_bundle_dir.exists():
            raise FileExistsError(f"Target bundle already exists: {target_bundle_dir}")
        bundle_dir.rename(target_bundle_dir)


def verify_bundle(exports_root: Path, uploads_root: Path, new_id: str, crc32: str) -> None:
    bundle_dir = exports_root / new_id
    if not bundle_dir.exists():
        raise FileNotFoundError(f"Migrated bundle missing: {bundle_dir}")

    row = load_documents_row(bundle_dir)
    if normalize_text(row.get("document_id", "")) != new_id:
        raise ValueError(f"documents.csv document_id mismatch in {bundle_dir}")
    if normalize_text(row.get("file_crc32", "")).upper() != crc32.upper():
        raise ValueError(f"documents.csv file_crc32 mismatch in {bundle_dir}")

    upload_path = uploads_root / f"{new_id}.pdf"
    if upload_path.exists():
        expected = str(upload_path).replace("\\", "/").replace("/uploads/", "/storage/uploads/")
        # documents.csv stores a mixed slash path in current exporter, so compare by tail
        if f"{new_id}.pdf" not in normalize_text(row.get("file_path", "")):
            raise ValueError(f"documents.csv file_path was not updated in {bundle_dir}")


def main() -> int:
    args = parse_args()
    exports_root = Path(args.exports_root)
    uploads_root = Path(args.uploads_root)
    backup_root = Path(args.backup_root)

    plan = plan_migration(exports_root, uploads_root)
    affected = [item for item in plan if item["old_id"] != item["new_id"]]

    print(f"Bundles found: {len(plan)}")
    print(f"Bundles to migrate: {len(affected)}")
    for item in affected[:10]:
        print(f"{item['old_id']} -> {item['new_id']} ({item['crc32']})")
    if len(affected) > 10:
        print(f"... and {len(affected) - 10} more")

    if args.dry_run:
        print("Dry run only, no changes applied.")
        return 0

    if not args.skip_backup and affected:
        backup_dir = backup_plan(affected, backup_root)
        print(f"Backup created: {backup_dir}")

    for item in affected:
        migrate_bundle(item)

    for item in affected:
        verify_bundle(exports_root, uploads_root, str(item["new_id"]), str(item["crc32"]))

    print("Migration complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
