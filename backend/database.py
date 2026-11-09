import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

logger = logging.getLogger("uvicorn.error")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "ai_crm")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Gupta@4148")  


def build_database_url(
    database: str | None = DB_NAME,
    user: str | None = None,
    password: str | None = None,
    host: str | None = None,
    port: int | None = None,
) -> URL:
    """Build the SQLAlchemy URL. URL.create escapes special characters (@, #, ...)."""
    return URL.create(
        drivername="mysql+pymysql",
        username=DB_USER if user is None else user,
        password=DB_PASSWORD if password is None else password,
        host=DB_HOST if host is None else host,
        port=DB_PORT if port is None else port,
        database=database,
        query={"charset": "utf8mb4"},
    )


def make_engine(url: URL) -> Engine:
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={"connect_timeout": 5},
    )


DATABASE_URL = build_database_url()
engine = make_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DatabaseUnavailableError(RuntimeError):
    """MySQL cannot be used. The message is safe to show (never has the password)."""


def _describe(exc: Exception, db_name: str, user: str, host: str, port: int) -> str:

    orig = getattr(exc, "orig", None)
    code = orig.args[0] if orig is not None and orig.args else None
    detail = orig.args[1] if orig is not None and len(orig.args) > 1 else exc.__class__.__name__
    if code == 1045:
        return f"MySQL rejected the login for user '{user}' (wrong DB_USER/DB_PASSWORD in .env)."
    if code == 1049:
        return (f"MySQL database '{db_name}' does not exist. "
                "Run database/schema.sql in MySQL Workbench first.")
    if code in (2003, 2002, 2013) or "Can't connect" in str(detail):
        return (f"Cannot connect to MySQL at {host}:{port}. "
                "Check that the MySQL service is running and DB_HOST/DB_PORT are correct.")
    return f"MySQL error ({exc.__class__.__name__}): {detail}"


def check_connection(db_engine: Engine | None = None, require_schema: bool = True) -> None:
    """Raise DatabaseUnavailableError with a clear message if MySQL is not usable.

    Read-only: it runs SELECT 1 and inspects metadata. It never creates anything.
    """
    db_engine = db_engine or engine
    url = db_engine.url
    try:
        with db_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        if require_schema and not inspect(db_engine).has_table("leads"):
            raise DatabaseUnavailableError(
                f"Table 'leads' was not found in database '{url.database}'. "
                "Run database/schema.sql in MySQL Workbench first."
            )
    except DatabaseUnavailableError:
        raise
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError(
            _describe(exc, str(url.database), str(url.username), str(url.host), int(url.port or 3306))
        ) from None


def is_connection_error(exc: Exception) -> bool:
    return isinstance(exc, OperationalError)


def get_db():
    """One database session per API request; rolled back on error, always closed."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
