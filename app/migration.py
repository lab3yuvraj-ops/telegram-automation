"""One-time, non-destructive import from the original Railway volume."""
import sqlite3
from . import store,storage

def migrate_local():
    path=store.DATA/'studio.db'
    if not path.exists():return
    with store.db() as c:
        c.execute('SELECT pg_advisory_xact_lock(7128503)')
        c.execute('CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY)')
        if not c.execute("SELECT name FROM migrations WHERE name='sqlite-v1'").fetchone():
            source=sqlite3.connect(path);source.row_factory=sqlite3.Row
            try:
                for table in ('users','sessions','login_attempts','job_keys','jobs'):
                    for row in source.execute('SELECT * FROM '+table):
                        values=dict(row)
                        if table=='jobs' and values['status'] in ('running','queued'):values.update(status='paused',stage='Migrated. Resume your production.')
                        columns=','.join(values);marks=','.join('?' for _ in values)
                        c.execute(f'INSERT INTO {table} ({columns}) VALUES ({marks}) ON CONFLICT DO NOTHING',tuple(values.values()))
            finally:source.close()
            c.execute("INSERT INTO migrations VALUES ('sqlite-v1')")
    # Import private files after metadata commit; each upload is independently idempotent.
    with store.db() as c:
        if c.execute("SELECT name FROM migrations WHERE name='sqlite-assets-v1'").fetchone():return
    for job in store.all_jobs():
        if store.folder(job['id']).exists():storage.sync(job['id'])
    with store.db() as c:c.execute("INSERT INTO migrations VALUES ('sqlite-assets-v1') ON CONFLICT DO NOTHING")
