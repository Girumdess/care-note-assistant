"""SQLite data layer for CareScribe: clients and their daily notes."""
import sqlite3
from pathlib import Path
from datetime import datetime, date, timedelta

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "carescribe.db"

def _conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with _conn() as c:
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

def list_clients():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM clients ORDER BY name")]

def get_client(client_id):
    with _conn() as c:
        r = c.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        return dict(r) if r else None

def add_client(name, profile=""):
    with _conn() as c:
        return c.execute("INSERT INTO clients(name, profile) VALUES(?,?)", (name, profile)).lastrowid

def add_note(client_id, note_date, raw_input, final_note):
    with _conn() as c:
        c.execute("INSERT INTO notes(client_id, note_date, raw_input, final_note, created_at) "
                  "VALUES(?,?,?,?,?)",
                  (client_id, note_date, raw_input, final_note,
                   datetime.now().isoformat(timespec="seconds")))

def get_notes(client_id):
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM notes WHERE client_id=? ORDER BY note_date", (client_id,))]

def week_start(d):
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return (d - timedelta(days=d.weekday())).isoformat()

def get_weeks(client_id):
    """Return {week_start_iso: [notes]} newest-first."""
    weeks = {}
    for n in get_notes(client_id):
        weeks.setdefault(week_start(n["note_date"]), []).append(n)
    return dict(sorted(weeks.items(), reverse=True))

def seed_if_empty():
    init_db()
    if list_clients():
        return
    from .seed_data import SEED
    for client in SEED:
        cid = add_client(client["name"], client.get("profile", ""))
        for note in client["notes"]:
            add_note(cid, note["date"], note.get("raw", ""), note["final"])
