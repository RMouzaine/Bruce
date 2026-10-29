"""
Secure Database Module for Bruce AI / Orayzis
Enforces parameterized queries, secure password hashing (PBKDF2/scrypt),
WAL-mode SQLite configuration, access control, and audit logging.
"""

import os
import sqlite3
import hashlib
import secrets
import hmac
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any, List

# Try importing werkzeug security helpers; fallback to hashlib.pbkdf2_hmac
try:
    from werkzeug.security import generate_password_hash as _w_hash, check_password_hash as _w_check
    HAS_WERKZEUG = True
except ImportError:
    HAS_WERKZEUG = False

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "bruce_secure.db"))


def hash_password(password: str) -> str:
    """
    Hashes a password securely using werkzeug scrypt/pbkdf2 if available,
    or standard library hashlib.pbkdf2_hmac with 260,000 rounds and unique salt.
    """
    if HAS_WERKZEUG:
        return _w_hash(password)
    
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 260000)
    return f"pbkdf2:sha256:260000${salt}${key.hex()}"


def check_password(password_hash: str, password: str) -> bool:
    """
    Verifies password hash in constant time.
    """
    if HAS_WERKZEUG and not password_hash.startswith("pbkdf2:sha256:260000$"):
        try:
            return _w_check(password_hash, password)
        except Exception:
            pass
            
    try:
        parts = password_hash.split("$")
        if len(parts) == 3:
            algo_info, salt, stored_key = parts
            key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 260000)
            return hmac.compare_digest(key.hex(), stored_key)
    except Exception:
        return False
    return False


def verify_password(password: str, password_hash: str) -> bool:
    """Convenience alias for check_password with (password, hash) order."""
    return check_password(password_hash, password)


@contextmanager
def get_db_connection(custom_path: Optional[str] = None):
    """
    Context manager for SQLite connection with security best practices:
    - Row factory enabled for safe key-based access
    - Foreign keys enforced
    - Busy timeout configured to prevent locking DoS
    - WAL journal mode for concurrency and durability
    """
    target = custom_path or DB_PATH
    conn = sqlite3.connect(target, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        if target != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(admin_initial_password: Optional[str] = None):
    """
    Initializes database schema with strict constraints and creates default admin
    if configured.
    """
    with get_db_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'user', 'service')),
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key_hash TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                is_revoked INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ip_address TEXT,
                action TEXT NOT NULL,
                username TEXT,
                status TEXT NOT NULL CHECK(status IN ('SUCCESS', 'DENIED', 'FAILURE'))
            );
        """)

        # Check if any admin user exists
        cur = conn.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
        if cur.fetchone()["count"] == 0 and admin_initial_password:
            hashed = hash_password(admin_initial_password)
            now = datetime.utcnow().isoformat()
            conn.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, 'admin', ?)",
                ("admin", hashed, now)
            )


def create_user(username: str, password: str, role: str = "user") -> bool:
    """
    Creates a user with securely hashed credentials.
    Uses parameterized query to prevent SQL injection.
    """
    if role not in ('admin', 'user', 'service'):
        raise ValueError("Invalid role specified")

    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long")

    hashed = hash_password(password)
    now = datetime.utcnow().isoformat()

    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (username.strip(), hashed, role, now)
            )
            return True
    except sqlite3.IntegrityError:
        return False


def verify_user_credentials(username: str, password: str, ip_address: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Verifies user credentials using constant-time password hash checking.
    Logs authentication attempt in audit logs.
    """
    with get_db_connection() as conn:
        cur = conn.execute(
            "SELECT id, username, password_hash, role, is_active FROM users WHERE username = ?",
            (username.strip(),)
        )
        user = cur.fetchone()

        if not user or not user["is_active"]:
            log_audit(conn, "AUTH_LOGIN", username, ip_address, "DENIED")
            return None

        if check_password(user["password_hash"], password):
            now = datetime.utcnow().isoformat()
            conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user["id"]))
            log_audit(conn, "AUTH_LOGIN", username, ip_address, "SUCCESS")
            return {"id": user["id"], "username": user["username"], "role": user["role"]}
        else:
            log_audit(conn, "AUTH_LOGIN", username, ip_address, "DENIED")
            return None


def log_audit(conn: sqlite3.Connection, action: str, username: Optional[str], ip_address: Optional[str], status: str):
    """
    Appends an entry to the audit log table using parameterized statement.
    """
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO audit_logs (timestamp, ip_address, action, username, status) VALUES (?, ?, ?, ?, ?)",
        (now, ip_address or "unknown", action, username or "anonymous", status)
    )


def get_recent_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves recent security audit logs for administrator review.
    """
    safe_limit = max(1, min(limit, 200))
    with get_db_connection() as conn:
        cur = conn.execute(
            "SELECT id, timestamp, ip_address, action, username, status FROM audit_logs ORDER BY id DESC LIMIT ?",
            (safe_limit,)
        )
        return [dict(row) for row in cur.fetchall()]
