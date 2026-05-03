import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load database settings from environment variables.
load_dotenv()

def _resolve_database_url() -> str:
    # Prefer explicit SQLAlchemy URL, then Railway-style MySQL URL.
    raw_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")

    # Build from Railway component variables if a full URL was not provided.
    if not raw_url:
        host = os.getenv("MYSQLHOST")
        user = os.getenv("MYSQLUSER")
        password = os.getenv("MYSQLPASSWORD")
        port = os.getenv("MYSQLPORT")
        database = os.getenv("MYSQLDATABASE")

        if all([host, user, password, port, database]):
            raw_url = (
                "mysql+pymysql://"
                f"{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database}"
            )

    if not raw_url:
        raise RuntimeError(
            "Database connection is not configured. Set DATABASE_URL, MYSQL_URL, "
            "or MYSQLHOST/MYSQLUSER/MYSQLPASSWORD/MYSQLPORT/MYSQLDATABASE."
        )

    # SQLAlchemy needs an explicit driver for MySQL.
    if raw_url.startswith("mysql://"):
        raw_url = raw_url.replace("mysql://", "mysql+pymysql://", 1)

    return raw_url


DATABASE_URL = _resolve_database_url()

# SQLite needs a different connection argument than MySQL.
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {"connect_timeout": 10}

# Build the SQLAlchemy engine, session factory, and declarative base.
engine = create_engine(
    DATABASE_URL,
    future=True,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=280,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


# Dependency helper that gives each request its own database session.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
