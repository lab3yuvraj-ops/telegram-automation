"""Minimal user table used to isolate Telegram productions by chat."""
from . import store


def init():
    with store.db() as c:
        if store.database.postgres():
            c.execute('SELECT pg_advisory_xact_lock(7128502)')
        c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL DEFAULT 'telegram-only', role TEXT NOT NULL DEFAULT 'member')")
