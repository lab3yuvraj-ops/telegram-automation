"""Opaque server sessions, scrypt password hashes and encrypted per-account keys."""
import hashlib, hmac, os, secrets, time
from cryptography.fernet import Fernet
from . import store

COOKIE='nightfall_session'
SESSION_SECONDS=43200

def password_hash(password):
    salt=secrets.token_bytes(16)
    value=hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1).hex()
    return 'scrypt$'+salt.hex()+'$'+value

def password_matches(password,encoded):
    try:
        _,salt,expected=encoded.split('$')
        actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
        return hmac.compare_digest(actual,expected)
    except (ValueError,TypeError): return False

def cipher():
    secret=os.getenv('APP_ENCRYPTION_KEY')
    if not secret: raise RuntimeError('APP_ENCRYPTION_KEY must be configured')
    return Fernet(secret.encode())

def init():
    cipher()
    seed_hash=os.getenv('ADMIN_PASSWORD_HASH')
    if not seed_hash: seed_hash=password_hash(secrets.token_urlsafe(48))
    with store.db() as c:
        if store.database.postgres():c.execute('SELECT pg_advisory_xact_lock(7128502)')
        c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT \'member\', key_cipher TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, csrf TEXT NOT NULL, expires DOUBLE PRECISION NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS login_attempts (ip TEXT NOT NULL, at DOUBLE PRECISION NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS job_keys (job_id TEXT PRIMARY KEY, key_cipher TEXT NOT NULL)')
        seeded=c.execute('INSERT INTO users (username,password_hash,role) VALUES (?,?,?) ON CONFLICT(username) DO NOTHING',('admin',seed_hash,'admin')).rowcount
        c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))

def login(username,password,ip):
    now=time.time()
    with store.db() as c:
        c.execute('DELETE FROM login_attempts WHERE at<?',(now-900,))
        if c.execute('SELECT COUNT(*) FROM login_attempts WHERE ip=?',(ip,)).fetchone()[0]>=8:
            return None,'Too many attempts. Try again in 15 minutes.'
        c.execute('INSERT INTO login_attempts VALUES (?,?)',(ip,now))
        user=c.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
    # Equal work for unknown accounts avoids an inexpensive username probe.
    encoded=user['password_hash'] if user else os.environ['ADMIN_PASSWORD_HASH']
    valid=password_matches(password,encoded)
    if not user or not valid: return None,'Incorrect ID or password.'
    token=secrets.token_urlsafe(48);csrf=secrets.token_urlsafe(32)
    with store.db() as c:
        c.execute('INSERT INTO sessions VALUES (?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),username,csrf,now+SESSION_SECONDS))
        c.execute('DELETE FROM login_attempts WHERE ip=?',(ip,))
    return {'token':token,'csrf':csrf,'username':username,'role':user['role']},None

def session(token):
    if not token: return None
    with store.db() as c:
        row=c.execute('SELECT sessions.username,csrf,expires,role FROM sessions JOIN users USING(username) WHERE token_hash=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
    return dict(row) if row else None

def logout(token):
    with store.db() as c: c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256((token or '').encode()).hexdigest(),))

def set_key(username,key):
    value=cipher().encrypt(key.encode()).decode() if key else None
    with store.db() as c: c.execute('UPDATE users SET key_cipher=? WHERE username=?',(value,username))

def get_key(username):
    with store.db() as c: row=c.execute('SELECT key_cipher FROM users WHERE username=?',(username,)).fetchone()
    return cipher().decrypt(row[0].encode()).decode() if row and row[0] else None

def save_job_key(ident,key):
    with store.db() as c: c.execute('INSERT INTO job_keys VALUES (?,?) ON CONFLICT(job_id) DO UPDATE SET key_cipher=excluded.key_cipher',(ident,cipher().encrypt(key.encode()).decode()))

def job_key(ident):
    with store.db() as c: row=c.execute('SELECT key_cipher FROM job_keys WHERE job_id=?',(ident,)).fetchone()
    return cipher().decrypt(row[0].encode()).decode() if row else None

def add_user(username,password):
    with store.db() as c:
        c.execute('INSERT INTO users(username,password_hash,role) VALUES (?,?,?)',(username,password_hash(password),'member'))
