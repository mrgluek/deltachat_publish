import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

DB_PATH = os.getenv("DB_PATH", "publish.db")
_lock = threading.Lock()


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()

        # Key-value config table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # Published posts history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS published_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL,
                commit_sha TEXT,
                title TEXT,
                created_at INTEGER NOT NULL
            )
        ''')

        # Transport statistics table (Standard requirement)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transport_stats (
                addr TEXT PRIMARY KEY,
                msgs_sent INTEGER DEFAULT 0,
                msgs_received INTEGER DEFAULT 0,
                last_sent_at INTEGER,
                last_received_at INTEGER
            )
        ''')

        conn.commit()
        conn.close()


def set_config(key: str, value: str):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()


def get_config(key: str) -> Optional[str]:
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None


def get_admin_email() -> Optional[str]:
    db_val = get_config("admin_dc_email")
    if db_val and db_val.strip():
        return db_val.strip().lower()
    env_val = os.getenv("ADMIN_DC_EMAIL")
    return env_val.strip().lower() if env_val else None


def get_admin_fingerprint() -> Optional[str]:
    fp = get_config("admin_dc_fingerprint")
    if not fp:
        fp = os.getenv("ADMIN_DC_FINGERPRINT", "")
    if fp:
        cleaned = fp.strip().replace(" ", "").replace(":", "").upper()
        if re.match(r"^[0-9A-F]{32,64}$", cleaned):
            return cleaned
    return None


def set_admin_fingerprint(fp: str):
    if fp:
        cleaned = fp.strip().replace(" ", "").replace(":", "").upper()
        set_config("admin_dc_fingerprint", cleaned)
    else:
        set_config("admin_dc_fingerprint", "")


def is_authorized_sender(sender_addr: str, fingerprint: Optional[str] = None) -> bool:
    """
    Checks if incoming sender address / fingerprint matches configured admin.
    """
    admin_email = get_admin_email()
    admin_fp = get_admin_fingerprint()

    # If no admin is configured in DB or ENV, no one is authorized until /initadmin or set_admin.py is run.
    if not admin_email and not admin_fp:
        return False

    sender_addr_clean = (sender_addr or "").strip().lower()

    if admin_email and sender_addr_clean == admin_email:
        if admin_fp and fingerprint:
            fp_clean = fingerprint.strip().replace(" ", "").replace(":", "").upper()
            return fp_clean == admin_fp
        return True

    if admin_fp and fingerprint:
        fp_clean = fingerprint.strip().replace(" ", "").replace(":", "").upper()
        return fp_clean == admin_fp

    return False


def log_published_post(slug: str, title: str, commit_sha: str = ""):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO published_posts (slug, title, commit_sha, created_at) VALUES (?, ?, ?, ?)",
            (slug, title, commit_sha, int(time.time()))
        )
        conn.commit()
        conn.close()


def get_recent_posts(limit: int = 5) -> List[Dict[str, Any]]:
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT slug, title, commit_sha, created_at FROM published_posts ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {"slug": r[0], "title": r[1], "commit_sha": r[2], "created_at": r[3]}
            for r in rows
        ]


def update_transport_stats(addr: str, sent: bool = False, received: bool = False):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        now = int(time.time())
        cursor.execute("SELECT msgs_sent, msgs_received FROM transport_stats WHERE addr = ?", (addr,))
        row = cursor.fetchone()
        if row:
            s_cnt = row[0] + (1 if sent else 0)
            r_cnt = row[1] + (1 if received else 0)
            if sent:
                cursor.execute(
                    "UPDATE transport_stats SET msgs_sent = ?, last_sent_at = ? WHERE addr = ?",
                    (s_cnt, now, addr)
                )
            if received:
                cursor.execute(
                    "UPDATE transport_stats SET msgs_received = ?, last_received_at = ? WHERE addr = ?",
                    (r_cnt, now, addr)
                )
        else:
            cursor.execute(
                "INSERT INTO transport_stats (addr, msgs_sent, msgs_received, last_sent_at, last_received_at) VALUES (?, ?, ?, ?, ?)",
                (addr, 1 if sent else 0, 1 if received else 0, now if sent else None, now if received else None)
            )
        conn.commit()
        conn.close()


def get_all_transport_stats() -> List[Dict[str, Any]]:
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT addr, msgs_sent, msgs_received, last_sent_at, last_received_at FROM transport_stats")
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "addr": r[0],
                "msgs_sent": r[1],
                "msgs_received": r[2],
                "last_sent_at": r[3],
                "last_received_at": r[4]
            }
            for r in rows
        ]
