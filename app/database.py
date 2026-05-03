import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load database settings from environment variables.
load_dotenv()

# Fall back to Railway MySQL URL when DATABASE_URL is not provided.
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:pKwQXadTVCZSuPzcVNKJFldpyEAipxod@mysql.railway.internal:3306/railway")

# SQLite needs a different connection argument than MySQL.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Build the SQLAlchemy engine, session factory, and declarative base.
engine = create_engine(DATABASE_URL, future=True, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


# Dependency helper that gives each request its own database session.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
