"""Shared test isolation for the FastAPI persistence dependency.

The production API keeps its normal database default. Tests replace that
dependency with a temporary SQLite database so regression requests cannot
write to the developer database.
"""

from __future__ import annotations

import atexit
import tempfile
from pathlib import Path

import api.main as api_main
from database import Database
from investigation_repository import InvestigationRepository


_test_database_directory = tempfile.TemporaryDirectory(prefix="riskguard-tests-")
api_main.repository.database.close()
api_main.repository = InvestigationRepository(Path(_test_database_directory.name) / "test-api.db")


@atexit.register
def _close_test_database() -> None:
    api_main.repository.database.close()
    _test_database_directory.cleanup()
