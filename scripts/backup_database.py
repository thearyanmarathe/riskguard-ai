"""Create and verify a SQLite backup without copying the live file directly."""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "riskguard.db"
REQUIRED_TABLES = {"investigations", "investigation_events"}


def _connect_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _counts(connection: sqlite3.Connection) -> tuple[int, int]:
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not REQUIRED_TABLES.issubset(tables):
        raise ValueError("Database is missing required investigation tables.")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise ValueError(f"SQLite integrity check failed: {integrity}")
    return connection.execute(
        "SELECT (SELECT COUNT(*) FROM investigations), (SELECT COUNT(*) FROM investigation_events)"
    ).fetchone()


def create_backup(source: Path, destination: Path) -> None:
    source = source.resolve()
    destination = destination.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Source database does not exist: {source}")
    if not destination.is_absolute() or destination == source:
        raise ValueError("Destination must be an absolute path different from the source.")
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing destination: {destination}")
    if not destination.parent.is_dir():
        raise ValueError("Destination parent directory must already exist.")

    with closing(_connect_read_only(source)) as source_connection:
        source_counts = _counts(source_connection)
        with closing(sqlite3.connect(destination)) as destination_connection:
            source_connection.backup(destination_connection)
            destination_counts = _counts(destination_connection)
    if source_counts != destination_counts:
        raise ValueError(f"Backup counts differ: source={source_counts}, backup={destination_counts}")
    print(f"Source: {source}")
    print(f"Backup: {destination}")
    print(f"Source counts (investigations, audit_events): {source_counts}")
    print(f"Backup counts (investigations, audit_events): {destination_counts}")
    print(f"Source SHA-256: {_digest(source)}")
    print(f"Backup SHA-256: {_digest(destination)}")
    print("Backup integrity: ok")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a verified SQLite backup without overwriting files.")
    parser.add_argument("destination", type=Path, help="New absolute backup path; it must not already exist.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Source database (default: data/riskguard.db).")
    arguments = parser.parse_args()
    try:
        create_backup(arguments.source, arguments.destination)
    except (OSError, sqlite3.Error, ValueError) as error:
        print(f"Backup failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
