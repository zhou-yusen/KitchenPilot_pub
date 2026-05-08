from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from kitchenpilot.core.config import get_settings
from kitchenpilot.db.base import Base


settings = get_settings()
engine = create_engine(settings.sqlite_database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_all() -> None:
    """Create all configured SQLite tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for FastAPI dependencies."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

