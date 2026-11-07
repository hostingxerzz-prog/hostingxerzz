import os, sqlite3, re
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

DB = os.getenv("DB_PATH", "users.db")
TS_FMT = "%Y-%m-%d %H:%M:%S"

def now():
    return datetime.now().strftime(TS_FMT)

def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = conn()
    c.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT,
                 balance REAL DEFAULT 0, reseller INTEGER DEFAULT 0, created_at TEXT,
                 name TEXT, spent REAL DEFAULT 0, orders INTEGER DEFAULT 0,
                 referrals INTEGER DEFAULT 0, ref_earned REAL DEFAULT 0,
                 ref_by INTEGER, last_lucky TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS keys (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 uid INTEGER, product TEXT, label TEXT, license TEXT, price REAL,
                 ts TEXT, resets INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS topups (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 uid INTEGER, amount REAL, method TEXT, status TEXT, ts TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS resellers (login TEXT PRIMARY KEY,
                 password TEXT, used_by INTEGER)""")
    c.commit(); c.close()

def get_user(uid, name=None):
    c = conn()
    row = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        c.execute("INSERT INTO users (id, created_at, name) VALUES (?,?,?)",
                  (uid, now(), name or "User"))
        c.commit()
        row = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    elif name:
        c.execute("UPDATE users SET name=? WHERE id=?", (name, uid))
        c.commit()
        row = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    c.close()
    return dict(row)

def change_balance(uid, delta):
    get_user(uid)
    c = conn()
    c.execute("UPDATE users SET balance=ROUND(balance+?,2) WHERE id=?", (delta, uid))
    c.commit(); c.close()

def set_lang(uid, lang):
    get_user(uid)
    c = conn()
    c.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))
    c.commit(); c.close()

def tier(uid, admin_id):
    if uid == admin_id: return "ADMIN"
    u = get_user(uid)
    return "RESELLER" if u.get("reseller") else "USER"

def touch_lucky(uid):
    c = conn()
    c.execute("UPDATE users SET last_lucky=? WHERE id=?", (now(), uid))
    c.commit(); c.close()