"""Database operations - contact submissions and spam logging."""
import os
import logging
import sqlite3
from typing import Optional, Union
from datetime import datetime, timezone

# PERF FIX [PERF-001]: Use a psycopg2 connection pool instead of opening a
# new connection on every request. Pool is initialised once at startup.
from psycopg2 import pool as pg_pool
from psycopg2 import DatabaseError, OperationalError

logger = logging.getLogger(__name__)
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Module-level connection pool (PostgreSQL only)
_pg_pool: Optional[pg_pool.ThreadedConnectionPool] = None


def init_pool() -> None:
    """Initialise the PostgreSQL connection pool (called once at startup)."""
    global _pg_pool
    if DATABASE_URL and _pg_pool is None:
        try:
            _pg_pool = pg_pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=DATABASE_URL)
            logger.info("PostgreSQL connection pool initialised (min=1, max=10).")
        except OperationalError as exc:
            logger.error("Failed to create connection pool: %s", exc)
            raise


def _get_connection() -> Union["psycopg2.extensions.connection", sqlite3.Connection]:
    """Return a connection from the pool (PostgreSQL) or a SQLite connection (dev)."""
    if _pg_pool:
        return _pg_pool.getconn()
    # Fallback: SQLite for local dev without PostgreSQL
    return sqlite3.connect("contact_form_dev.db")


def _release_connection(conn: Union["psycopg2.extensions.connection", sqlite3.Connection]) -> None:
    """Return a pooled connection back to the pool, or close a SQLite connection."""
    if _pg_pool and not isinstance(conn, sqlite3.Connection):
        _pg_pool.putconn(conn)
    else:
        conn.close()


def init_db() -> None:
    """
    Initialise the database schema.
    CQ FIX [CQ-001]: Execute the full SQL script as a single statement rather
    than splitting on ';', which was fragile and could break on comments or
    SQL strings containing semicolons.
    """
    schema_path = os.path.join(os.path.dirname(__file__), "../db/schema.sql")
    init_pool()
    conn = _get_connection()
    try:
        with open(schema_path) as f:
            schema_sql = f.read()
        with conn.cursor() as cur:
            cur.execute(schema_sql)   # CQ FIX [CQ-001]: execute full script atomically
        conn.commit()
        logger.info("Database schema initialised.")
    except (DatabaseError, OperationalError, OSError) as exc:
        # CQ FIX [CQ-002]: Catch specific exceptions; log with full stack trace
        logger.error("DB init failed: %s", exc, exc_info=True)
        raise
    finally:
        _release_connection(conn)


def log_submission(
    full_name: str, email: str, phone: Optional[str],
    subject: str, message: str, ip_address: str,
    captcha_passed: bool, captcha_score: float, email_sent: bool,
) -> int:
    """Insert a contact form submission row and a linked email_notifications row."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO contact_submissions
                   (full_name, email, phone, subject, message, ip_address,
                    captcha_passed, captcha_score, status, submitted_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING submission_id""",
                (
                    full_name, email, phone, subject, message, ip_address,
                    captcha_passed, captcha_score,
                    "processed" if email_sent else "pending",
                    datetime.now(timezone.utc),
                ),
            )
            row = cur.fetchone()
            sid = row[0] if row else -1

            cur.execute(
                """INSERT INTO email_notifications
                   (submission_id, recipient_email, status, sent_at)
                   VALUES (%s, %s, %s, %s)""",
                (
                    sid,
                    os.getenv("COMPANY_EMAIL"),
                    "sent" if email_sent else "failed",
                    datetime.now(timezone.utc) if email_sent else None,
                ),
            )
        conn.commit()
        return sid
    except (DatabaseError, OperationalError) as exc:
        # CQ FIX [CQ-002]: Catch specific DB exceptions; re-raise so FastAPI returns 500
        conn.rollback()
        logger.error("DB log_submission failed: %s", exc, exc_info=True)
        raise
    finally:
        _release_connection(conn)


def log_spam_attempt(ip_address: str, captcha_passed: bool) -> None:
    """Record a failed CAPTCHA / spam attempt for audit purposes."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO spam_log (ip_address, captcha_passed, blocked, attempt_at)
                   VALUES (%s, %s, %s, %s)""",
                (ip_address, captcha_passed, True, datetime.now(timezone.utc)),
            )
        conn.commit()
    except (DatabaseError, OperationalError) as exc:
        # CQ FIX [CQ-002]: Log with full traceback for debuggability
        logger.error("Spam log failed: %s", exc, exc_info=True)
    finally:
        _release_connection(conn)
