"""Small DB-API bridge: PostgreSQL in hosted mode, SQLite for offline development."""
import os, sqlite3
from contextlib import contextmanager

def postgres(): return bool(os.getenv('DATABASE_URL'))

class Row(dict):
    def __getitem__(self,key):
        return list(self.values())[key] if isinstance(key,int) else super().__getitem__(key)

class Cursor:
    def __init__(self,cursor): self.cursor=cursor
    @property
    def rowcount(self): return self.cursor.rowcount
    def fetchone(self):
        row=self.cursor.fetchone();return Row(row) if row is not None else None
    def fetchall(self): return [Row(r) for r in self.cursor.fetchall()]
    def __iter__(self): return iter(self.fetchall())

class Connection:
    def __init__(self,conn):self.conn=conn
    def execute(self,sql,params=()):
        return Cursor(self.conn.execute(sql.replace('?','%s'),params))

_pool=None
def pool():
    global _pool
    if _pool is None:
        from psycopg_pool import ConnectionPool
        from psycopg.rows import dict_row
        _pool=ConnectionPool(os.environ['DATABASE_URL'],min_size=1,max_size=int(os.getenv('DB_POOL_SIZE','12')),kwargs={'row_factory':dict_row},open=True)
    return _pool

@contextmanager
def connection(data):
    if postgres():
        with pool().connection() as conn: yield Connection(conn)
    else:
        conn=sqlite3.connect(data/'studio.db',timeout=30);conn.row_factory=sqlite3.Row
        try:
            with conn: yield conn
        finally: conn.close()

def duplicate(exc):
    return isinstance(exc,sqlite3.IntegrityError) or getattr(exc,'sqlstate',None)=='23505'
