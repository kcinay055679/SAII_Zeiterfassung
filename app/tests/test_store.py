import threading
from datetime import datetime, timedelta, timezone

import pytest

from store import (ON_BREAK, OUT, WORKING, InvalidInput, InvalidTransition,
                   Store, start_of_day)

# 10:00 in Zurich (CEST, UTC+2)
NOON = datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "test.db")
    s.init()
    return s


def at(minutes):
    return NOON + timedelta(minutes=minutes)


def test_full_day_cycle(store):
    store.record("Anna", "EIN", now=at(0))
    store.record("Anna", "PAUSE", now=at(60))
    store.record("Anna", "ZURUECK", now=at(90))
    store.record("Anna", "AUS", now=at(150))
    [anna] = store.board(now=at(200))
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
    assert statuses == {"Anna": ON_BREAK, "Ben": WORKING}


def test_names_match_case_and_whitespace_insensitive(store):
    store.record("Anna Meyer", "EIN", now=at(0))
    stamp = store.record("  anna   MEYER ", "AUS", now=at(10))
    assert stamp.person == "Anna Meyer"
    assert [p.person for p in store.board(now=at(11))] == ["Anna Meyer"]


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
