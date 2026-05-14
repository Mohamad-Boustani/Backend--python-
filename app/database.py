import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
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


def ensure_attendance_manual_override_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    statements: list[str] = []

    if "attendance_record" in table_names:
        attendance_columns = {column["name"] for column in inspector.get_columns("attendance_record")}
        if "Manual_Override" not in attendance_columns:
            statements.append("ALTER TABLE attendance_record ADD COLUMN Manual_Override BOOLEAN NOT NULL DEFAULT 0")
        if "Override_Reason" not in attendance_columns:
            statements.append("ALTER TABLE attendance_record ADD COLUMN Override_Reason TEXT NULL")
        if "Archived_At" not in attendance_columns:
            statements.append("ALTER TABLE attendance_record ADD COLUMN Archived_At DATETIME NULL")

    if "student" in table_names:
        student_columns = {column["name"] for column in inspector.get_columns("student")}
        if "Archived_At" not in student_columns:
            statements.append("ALTER TABLE student ADD COLUMN Archived_At DATETIME NULL")

    if "department" in table_names or "departments" in table_names:
        # support both possible table naming
        name = "departments" if "departments" in table_names else "department"
        dept_columns = {column["name"] for column in inspector.get_columns(name)}
        if "Archived_At" not in dept_columns:
            statements.append(f"ALTER TABLE {name} ADD COLUMN Archived_At DATETIME NULL")

    if "major" in table_names:
        major_columns = {column["name"] for column in inspector.get_columns("major")}
        if "Archived_At" not in major_columns:
            statements.append("ALTER TABLE major ADD COLUMN Archived_At DATETIME NULL")

    if "course" in table_names:
        course_columns = {column["name"] for column in inspector.get_columns("course")}
        if "Archived_At" not in course_columns:
            statements.append("ALTER TABLE course ADD COLUMN Archived_At DATETIME NULL")

    if "section" in table_names:
        section_columns = {column["name"] for column in inspector.get_columns("section")}
        if "Archived_At" not in section_columns:
            statements.append("ALTER TABLE section ADD COLUMN Archived_At DATETIME NULL")

    if "instructor" in table_names:
        instr_columns = {column["name"] for column in inspector.get_columns("instructor")}
        if "Archived_At" not in instr_columns:
            statements.append("ALTER TABLE instructor ADD COLUMN Archived_At DATETIME NULL")

    if "admin" in table_names:
        admin_columns = {column["name"] for column in inspector.get_columns("admin")}
        if "Archived_At" not in admin_columns:
            statements.append("ALTER TABLE admin ADD COLUMN Archived_At DATETIME NULL")

    if "enrollment" in table_names:
        enrollment_columns = {column["name"] for column in inspector.get_columns("enrollment")}
        if "Archived_At" not in enrollment_columns:
            statements.append("ALTER TABLE enrollment ADD COLUMN Archived_At DATETIME NULL")

    if "face_template" in table_names:
        template_columns = {column["name"] for column in inspector.get_columns("face_template")}
        if "Archived_At" not in template_columns:
            statements.append("ALTER TABLE face_template ADD COLUMN Archived_At DATETIME NULL")

    if statements:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))


# Dependency helper that gives each request its own database session.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
