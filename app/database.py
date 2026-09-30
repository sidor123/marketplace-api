from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import database_url, positive_int

DATABASE_URL = database_url()
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=positive_int('DB_POOL_SIZE', '5'),
    max_overflow=0,
    pool_timeout=5,
    connect_args={"connect_timeout": 5, "options": "-c timezone=UTC -c statement_timeout=15000"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
