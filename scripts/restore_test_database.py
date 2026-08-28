"""Restore a verified SQLite backup only after explicit confirmation."""

from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "riskguard.db"
REQUIRED_TABLES = {"investigations", "investigation_events"}
EXPECTED_COUNTS = (287, 402)


def _connect_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _validate(path: Path) -> tuple[int, int]:
    with closing(_connect_read_only(path)) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not REQUIRED_TABLES.issubset(tables):
            raise ValueError("Backup is missing required investigation tables.")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError(f"Backup integrity check failed: {integrity}")
        counts = connection.execute(
            "SELECT (SELECT COUNT(*) FROM investigations), (SELECT COUNT(*) FROM investigation_events)"
        ).fetchone()
    if tuple(counts) != EXPECTED_COUNTS:
        raise ValueError(f"Backup must contain {EXPECTED_COUNTS} records, found {counts}.")
    return tuple(counts)


def restore(backup: Path, database: Path, confirm: bool) -> None:
    backup = backup.resolve()
    database = database.resolve()
    if not confirm:
        raise ValueError("Restoration requires --confirm.")
    if not backup.is_file():
        raise FileNotFoundError(f"Backup does not exist: {backup}")
    if backup == database:
        raise ValueError("Backup and target database must be different paths.")
    if database.exists() and not database.is_file():
        raise ValueError("Target database path is not a regular file.")
    if not database.parent.is_dir():
        raise ValueError("Target database parent directory must already exist.")
    _validate(backup)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="riskguard-restore-", suffix=".db", dir=database.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
        with closing(_connect_read_only(backup)) as source_connection, closing(sqlite3.connect(temporary_path)) as destination_connection:
            source_connection.backup(destination_connection)
        counts = _validate(temporary_path)
        os.replace(temporary_path, database)
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    print(f"Restored: {database}")
    print(f"Backup SHA-256: {_digest(backup)}")
    print(f"Restored counts (investigations, audit_events): {counts}")
    print(f"Restored SHA-256: {_digest(database)}")
    print("Restored integrity: ok")


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a verified development SQLite database backup.")
    parser.add_argument("--backup", required=True, type=Path, help="Explicit verified backup path.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE, help="Target database (default: data/riskguard.db).")
    parser.add_argument("--confirm", action="store_true", help="Confirm replacement of the target database.")
    arguments = parser.parse_args()
    try:
        restore(arguments.backup, arguments.database, arguments.confirm)
    except (OSError, sqlite3.Error, ValueError) as error:
        print(f"Restore failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
