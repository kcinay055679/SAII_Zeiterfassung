import threading
from datetime import datetime, timedelta, timezone

import pytest

from store import (ON_BREAK, OUT, WORKING, InvalidInput, InvalidTransition,
                   Store, UnknownPerson, start_of_day)

# 10:00 in Zurich (CEST, UTC+2)
NOON = datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "test.db")
    s.init()
    for name in ("Anna", "Ben", "Anna Meyer"):
        s.add_person(name)
    return s


def at(minutes):
    return NOON + timedelta(minutes=minutes)


def test_full_day_cycle(store):
    store.record("Anna", "EIN", now=at(0))
    store.record("Anna", "PAUSE", now=at(60))
    store.record("Anna", "ZURUECK", now=at(90))
    store.record("Anna", "AUS", now=at(150))
    anna = store.status_of("Anna", now=at(200))
    assert anna.status == OUT
    assert anna.worked_seconds == 120 * 60


def test_open_interval_counts_up_to_now(store):
    store.record("Anna", "EIN", now=at(0))
    assert store.status_of("Anna", now=at(45)).worked_seconds == 45 * 60


@pytest.mark.parametrize("history,action,expected_status", [
    ([], "PAUSE", OUT),
    ([], "AUS", OUT),
    ([], "ZURUECK", OUT),
    (["EIN"], "EIN", WORKING),
    (["EIN"], "ZURUECK", WORKING),
    (["EIN", "PAUSE"], "AUS", ON_BREAK),
    (["EIN", "PAUSE"], "PAUSE", ON_BREAK),
    (["EIN", "AUS"], "AUS", OUT),
])
def test_invalid_transitions_are_rejected(store, history, action, expected_status):
    for i, a in enumerate(history):
        store.record("Anna", a, now=at(i))
    with pytest.raises(InvalidTransition) as err:
        store.record("Anna", action, now=at(10))
    assert err.value.status == expected_status
    assert len(store.recent()) == len(history)


def test_people_are_independent(store):
    store.record("Anna", "EIN", now=at(0))
    store.record("Ben", "EIN", now=at(1))
    store.record("Anna", "PAUSE", now=at(2))
    statuses = {p.person: p.status for p in store.board(now=at(3))}
    assert statuses == {"Anna": ON_BREAK, "Ben": WORKING, "Anna Meyer": OUT}


def test_names_match_case_and_whitespace_insensitive(store):
    store.record("Anna Meyer", "EIN", now=at(0))
    stamp = store.record("  anna   MEYER ", "AUS", now=at(10))
    assert stamp.person == "Anna Meyer"
    assert store.find_person("ANNA meyer") == "Anna Meyer"


def test_shift_across_midnight_counts_only_today(store):
    late = datetime(2026, 7, 1, 21, 0, tzinfo=timezone.utc)  # 23:00 Zurich
    store.record("Anna", "EIN", now=late)
    next_morning = late + timedelta(hours=3)  # 02:00 Zurich next day
    assert start_of_day(next_morning) == late + timedelta(hours=1)
    assert store.status_of("Anna", now=next_morning).worked_seconds == 2 * 3600


@pytest.mark.parametrize("name,action,note", [
    ("", "EIN", ""),
    ("   ", "EIN", ""),
    ("x" * 61, "EIN", ""),
    ("Anna", "KAFFEE", ""),
    ("Anna", "EIN", "x" * 201),
])
def test_invalid_input(store, name, action, note):
    with pytest.raises(InvalidInput):
        store.record(name, action, note)


def test_action_is_case_insensitive(store):
    assert store.record("Anna", "ein").action == "EIN"


def test_concurrent_ein_accepts_exactly_one(tmp_path):
    """Several replicas stamping at once must not let the same person in twice."""
    path = tmp_path / "shared.db"
    Store(path).init()
    Store(path).add_person("Anna")
    results = []
    barrier = threading.Barrier(8)

    def worker():
        s = Store(path)
        barrier.wait()
        try:
            s.record("Anna", "EIN")
            results.append("ok")
        except InvalidTransition:
            results.append("rejected")

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count("ok") == 1
    assert results.count("rejected") == 7


def test_stamping_an_unknown_person_is_rejected(store):
    with pytest.raises(UnknownPerson):
        store.record("Nobody", "EIN")
    assert store.recent() == []


def test_add_person_is_idempotent_and_keeps_first_spelling(store):
    assert store.add_person("Clara Huber") == ("Clara Huber", True)
    assert store.add_person("  clara HUBER ") == ("Clara Huber", False)
    assert store.people().count("Clara Huber") == 1


def test_person_without_stamps_is_on_the_board(store):
    store.add_person("Clara")
    clara = store.status_of("Clara", now=at(0))
    assert (clara.status, clara.worked_seconds) == (OUT, 0)
    assert "Clara" in [p.person for p in store.board(now=at(0))]


def test_people_are_sorted_case_insensitive(store):
    store.add_person("bert")
    assert store.people() == ["Anna", "Anna Meyer", "Ben", "bert"]


def test_existing_stamps_become_persons_on_upgrade(tmp_path):
    """Databases from 1.3 have stamps but no persons table."""
    import sqlite3
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE stamps (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL,
            person_key TEXT NOT NULL, person TEXT NOT NULL, action TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '', pod TEXT NOT NULL DEFAULT '');
        INSERT INTO stamps (ts, person_key, person, action)
            VALUES ('2026-07-01T08:00:00+00:00', 'anna meyer', 'Anna Meyer', 'EIN');
    """)
    conn.commit()
    conn.close()
    store = Store(path)
    store.init()
    assert store.people() == ["Anna Meyer"]
    assert store.status_of("Anna Meyer", now=at(30)).status == WORKING
