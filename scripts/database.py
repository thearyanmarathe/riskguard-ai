"""SQLAlchemy SQLite setup for stored, validated investigation results."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "riskguard.db"


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, path: str | Path = DEFAULT_DATABASE_PATH) -> None:
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{self.path.resolve().as_posix()}"
        else:
            url = "sqlite:///:memory:"
        self.engine = create_engine(url, connect_args={"check_same_thread": False})

    def initialize(self) -> None:
        from investigation_repository import InvestigationModel

        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        self.engine.dispose()
