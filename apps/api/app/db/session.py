"""Database engine and session dependency helpers."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SESSION_LOCAL = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Yield a database session and close it after use."""
    db = SESSION_LOCAL()
    try:
        yield db
    finally:
        db.close()
