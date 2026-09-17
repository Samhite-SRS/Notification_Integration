"""
SQLAlchemy engine/session setup. Works against MySQL (DATABASE_URL=
mysql+pymysql://...) or, for a zero-setup local MVP, SQLite
(DATABASE_URL=sqlite:///./notification.db) - see spec section 10 which
explicitly allows SQLite for local MVP use.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist yet (MVP convenience).

    For a real MySQL deployment you can instead run Backend/schema.sql
    directly - both define the same two tables.
    """
    from app import models  # noqa: F401  (ensures models are registered on Base)

    Base.metadata.create_all(bind=engine)
