from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,Session
from dotenv import load_dotenv
import os
from contextvars import ContextVar


# Load environment variables
load_dotenv()

# Your existing values
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_DRIVER = os.getenv("DB_DRIVER")

DB_URL = f"{DB_DRIVER}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(
    DB_URL,
    pool_size=15,           # a bit higher base pool
    max_overflow=30,        # handle burst traffic
    pool_timeout=15,        # fail fast if pool exhausted
    pool_recycle=1800,      # 30 min recycling (less chance of stale)
    pool_pre_ping=True,     # 🔥 must enable this for cloud DBs
    connect_args={"connect_timeout": 10},  # abort quickly on bad network
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ✅ Context variable for session
_db_context: ContextVar[Session] = ContextVar("db_session", default=None)

def set_db_session() -> Session:
    db = SessionLocal()
    _db_context.set(db)
    return db

def get_db_session() -> Session:
    db = _db_context.get()
    if db is None:
        raise RuntimeError("DB session not found in context")
    return db

def remove_db_session():
    db = _db_context.get()
    if db:
        db.close()
        _db_context.set(None)