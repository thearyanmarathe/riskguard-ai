"""Shared test-only replacement for the API's live persistence dependency."""

from __future__ import annotations

import atexit
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import api.main as api_main  # noqa: E402
from database import Database  # noqa: E402
from investigation_repository import InvestigationRepository  # noqa: E402


_database_directory = tempfile.TemporaryDirectory(prefix="riskguard-tests-")
api_main.repository.database.close()
api_main.repository = InvestigationRepository(Database(Path(_database_directory.name) / "test-api.db"))


@atexit.register
def _close_database() -> None:
    api_main.repository.database.close()
    _database_directory.cleanup()
