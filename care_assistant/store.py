"""SQLite data layer for CareScribe: clients and their daily notes."""
import sqlite3
from pathlib import Path
from datetime import datetime, date, timedelta

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "carescribe.db"

def _conn(db=None):
    path = Path(db) if db else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c

def init_db(db=None):
    with _conn(db) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS clients(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            profile TEXT DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS notes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            note_date TEXT NOT NULL,
            raw_input TEXT DEFAULT '',
            final_note TEXT NOT NULL,
            created_at TEXT DEFAULT '',
            FOREIGN KEY(client_id) REFERENCES clients(id))""")

def list_clients(db=None):
    with _conn(db) as c:
        return [dict(r) for r in c.execute("SELECT * FROM clients ORDER BY name")]

def get_client(client_id, db=None):
    with _conn(db) as c:
        r = c.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        return dict(r) if r else None

def add_client(name, profile="", db=None):
    with _conn(db) as c:
        return c.execute("INSERT INTO clients(name, profile) VALUES(?,?)", (name, profile)).lastrowid

def add_note(client_id, note_date, raw_input, final_note, db=None):
    with _conn(db) as c:
        c.execute("INSERT INTO notes(client_id, note_date, raw_input, final_note, created_at) "
                  "VALUES(?,?,?,?,?)",
                  (client_id, note_date, raw_input, final_note,
                   datetime.now().isoformat(timespec="seconds")))

def get_notes(client_id, db=None):
    with _conn(db) as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM notes WHERE client_id=? ORDER BY note_date", (client_id,))]

def week_start(d):
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return (d - timedelta(days=d.weekday())).isoformat()

def get_weeks(client_id, db=None):
    """Return {week_start_iso: [notes]} newest-first."""
    weeks = {}
    for n in get_notes(client_id, db):
        weeks.setdefault(week_start(n["note_date"]), []).append(n)
    return dict(sorted(weeks.items(), reverse=True))

def seed_if_empty(db=None):
    init_db(db)
    if list_clients(db):
        return
    from .seed_data import SEED
    for client in SEED:
        cid = add_client(client["name"], client.get("profile", ""), db)
        for note in client["notes"]:
            add_note(cid, note["date"], note.get("raw", ""), note["final"], db)


SESSIONS_DIR = DB_PATH.parent / "sessions"


def new_session_db(max_age_hours=24):
    """Create a fresh, seeded database for one visitor's session.

    The hosted demo is public, so each visitor works in their own copy:
    clients and notes they add are never shown to anyone else. Copies older
    than ``max_age_hours`` are cleaned up as new sessions start.
    """
    import time
    import uuid
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - max_age_hours * 3600
    for old in SESSIONS_DIR.glob("*.db"):
        try:
            if old.stat().st_mtime < cutoff:
                old.unlink()
        except OSError:
            pass
    path = SESSIONS_DIR / f"{uuid.uuid4().hex}.db"
    seed_if_empty(path)
    return path
