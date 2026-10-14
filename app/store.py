import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ACTIONS = ("EIN", "PAUSE", "ZURUECK", "AUS")
LABELS = {"EIN": "EIN", "PAUSE": "PAUSE", "ZURUECK": "ZURÜCK", "AUS": "AUS"}

OUT = "OUT"
WORKING = "WORKING"
ON_BREAK = "ON BREAK"

ALLOWED = {
    OUT: ("EIN",),
    WORKING: ("PAUSE", "AUS"),
    ON_BREAK: ("ZURUECK",),
}
STATUS_AFTER = {"EIN": WORKING, "ZURUECK": WORKING, "PAUSE": ON_BREAK, "AUS": OUT}

MAX_NAME = 60
MAX_NOTE = 200
LOCAL_TZ = ZoneInfo("Europe/Zurich")

SCHEMA = """
CREATE TABLE IF NOT EXISTS stamps (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT    NOT NULL,
    person_key TEXT    NOT NULL,
    person     TEXT    NOT NULL,
    action     TEXT    NOT NULL CHECK (action IN ('EIN', 'PAUSE', 'ZURUECK', 'AUS')),
    note       TEXT    NOT NULL DEFAULT '',
    pod        TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS stamps_person_ts ON stamps (person_key, ts);
CREATE TABLE IF NOT EXISTS persons (
    key     TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    created TEXT NOT NULL
);
-- Databases from before persons existed: everyone who has stamped is a person.
INSERT OR IGNORE INTO persons (key, name, created)
    SELECT s.person_key, s.person, s.ts FROM stamps s
    WHERE s.id = (SELECT MIN(id) FROM stamps WHERE person_key = s.person_key);
"""


class InvalidInput(ValueError):
    pass


class UnknownPerson(LookupError):
    def __init__(self, name: str):
        super().__init__(f"{name} doesn't exist yet, create the person first")


class InvalidTransition(ValueError):
    def __init__(self, person: str, status: str, action: str):
        self.status = status
        self.allowed = ALLOWED[status]
        super().__init__(f"{person} is {status}, {action} not allowed")


@dataclass(frozen=True)
class Stamp:
    ts: datetime
    person: str
    action: str
    note: str
    pod: str

    def as_dict(self) -> dict:
        return {
            "ts": self.ts.isoformat(timespec="seconds"),
            "person": self.person,
            "action": self.action,
            "note": self.note,
            "pod": self.pod,
        }


@dataclass(frozen=True)
class PersonStatus:
    person: str
    status: str
    worked_seconds: int

    @property
    def allowed(self) -> tuple[str, ...]:
        return ALLOWED[self.status]


def person_key(name: str) -> str:
    return " ".join(name.split()).casefold()


def clean_name(name: str) -> str:
    name = " ".join(str(name or "").split())
    if not name:
        raise InvalidInput("name is required")
    if len(name) > MAX_NAME:
        raise InvalidInput(f"name is longer than {MAX_NAME} characters")
    return name


def clean_action(action: str) -> str:
    action = str(action or "").strip().upper()
    if action not in ACTIONS:
        raise InvalidInput(f"unknown action, allowed: {', '.join(ACTIONS)}")
    return action


def clean_note(note: str) -> str:
    note = str(note or "").strip()
    if len(note) > MAX_NOTE:
        raise InvalidInput(f"note is longer than {MAX_NOTE} characters")
    return note


def status_after(stamps: list[Stamp], initial: str = OUT) -> str:
    status = initial
    for stamp in stamps:
        status = STATUS_AFTER[stamp.action]
    return status


def worked_seconds(stamps: list[Stamp], initial: str, start: datetime, now: datetime) -> int:
    """Seconds spent WORKING between start and now. A stretch that was already
    running at start (clocked in before midnight) counts from start."""
    total = timedelta()
    status = initial
    since = start
    for stamp in stamps:
        if status == WORKING:
            total += stamp.ts - since
        status = STATUS_AFTER[stamp.action]
        since = stamp.ts
    if status == WORKING:
        total += now - since
    return max(0, int(total.total_seconds()))


def start_of_day(now: datetime) -> datetime:
    local = now.astimezone(LOCAL_TZ)
    return datetime.combine(local.date(), time(), LOCAL_TZ).astimezone(timezone.utc)


def _row_to_stamp(row: sqlite3.Row) -> Stamp:
    return Stamp(
        ts=datetime.fromisoformat(row["ts"]),
        person=row["person"],
        action=row["action"],
        note=row["note"],
        pod=row["pod"],
    )


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        # isolation_level=None lets us issue BEGIN IMMEDIATE ourselves, so the
        # status check and the insert hold the write lock together across replicas.
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA)

    def ping(self) -> None:
        with closing(self.connect()) as conn:
            conn.execute("SELECT 1 FROM stamps LIMIT 1").fetchall()

    def _status(self, conn: sqlite3.Connection, key: str) -> str:
        row = conn.execute(
            "SELECT action FROM stamps WHERE person_key = ? ORDER BY ts DESC, id DESC LIMIT 1",
            (key,),
        ).fetchone()
        return STATUS_AFTER[row["action"]] if row else OUT

    def add_person(self, name: str, now: datetime | None = None) -> tuple[str, bool]:
        """Returns the stored spelling and whether the person was newly created."""
        name = clean_name(name)
        now = now or datetime.now(timezone.utc)
        with closing(self.connect()) as conn:
            created = conn.execute(
                "INSERT OR IGNORE INTO persons (key, name, created) VALUES (?, ?, ?)",
                (person_key(name), name, now.isoformat(timespec="seconds")),
            ).rowcount == 1
            row = conn.execute(
                "SELECT name FROM persons WHERE key = ?", (person_key(name),)
            ).fetchone()
        return row["name"], created

    def find_person(self, name: str) -> str | None:
        with closing(self.connect()) as conn:
            row = conn.execute(
                "SELECT name FROM persons WHERE key = ?", (person_key(name),)
            ).fetchone()
        return row["name"] if row else None

    def people(self) -> list[str]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT name FROM persons ORDER BY key").fetchall()
        return [r["name"] for r in rows]

    def record(self, name: str, action: str, note: str = "", pod: str = "",
               now: datetime | None = None) -> Stamp:
        name = clean_name(name)
        action = clean_action(action)
        note = clean_note(note)
        key = person_key(name)
        now = now or datetime.now(timezone.utc)

        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            person = conn.execute(
                "SELECT name FROM persons WHERE key = ?", (key,)
            ).fetchone()
            if person is None:
                conn.execute("ROLLBACK")
                raise UnknownPerson(name)
            display = person["name"]
            status = self._status(conn, key)
            if action not in ALLOWED[status]:
                conn.execute("ROLLBACK")
                raise InvalidTransition(display, status, action)
            conn.execute(
                "INSERT INTO stamps (ts, person_key, person, action, note, pod) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (now.isoformat(timespec="seconds"), key, display, action, note, pod),
            )
            conn.execute("COMMIT")
        except sqlite3.Error:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()
        return Stamp(ts=now.replace(microsecond=0), person=display, action=action,
                     note=note, pod=pod)

    def status_of(self, name: str, now: datetime | None = None) -> PersonStatus:
        key = person_key(name)
        for entry in self.board(now):
            if person_key(entry.person) == key:
                return entry
        return PersonStatus(person=" ".join(name.split()), status=OUT, worked_seconds=0)

    def board(self, now: datetime | None = None) -> list[PersonStatus]:
        now = now or datetime.now(timezone.utc)
        start = start_of_day(now)
        start_iso = start.isoformat(timespec="seconds")
        with closing(self.connect()) as conn:
            people = conn.execute("SELECT key, name FROM persons").fetchall()
            result = []
            for row in people:
                key = row["key"]
                before = conn.execute(
                    "SELECT * FROM stamps WHERE person_key = ? AND ts < ? "
                    "ORDER BY ts DESC, id DESC LIMIT 1",
                    (key, start_iso),
                ).fetchone()
                today = [_row_to_stamp(r) for r in conn.execute(
                    "SELECT * FROM stamps WHERE person_key = ? AND ts >= ? AND ts <= ? "
                    "ORDER BY ts, id",
                    (key, start_iso, now.isoformat(timespec="seconds")),
                )]
                initial = STATUS_AFTER[before["action"]] if before else OUT
                result.append(PersonStatus(
                    person=row["name"],
                    status=status_after(today, initial),
                    worked_seconds=worked_seconds(today, initial, start, now),
                ))
        return sorted(result, key=lambda p: person_key(p.person))

    def recent(self, limit: int = 20) -> list[Stamp]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM stamps ORDER BY ts DESC, id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_stamp(r) for r in rows]
