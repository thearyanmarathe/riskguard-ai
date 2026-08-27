"""Initialize the local RiskGuard SQLite database without deleting records."""

from __future__ import annotations

from database import Database, DEFAULT_DATABASE_PATH
from investigation_repository import InvestigationRepository


def main() -> None:
    database = Database(DEFAULT_DATABASE_PATH)
    InvestigationRepository(database)
    database.close()
    print(f"Initialized SQLite database at {DEFAULT_DATABASE_PATH}")


if __name__ == "__main__":
    main()
