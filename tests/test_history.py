"""The day-by-day history (src/history.py) on the real November 2025 fixture: which days count, incremental
updates inside a budget, the per-station rows, the totals, and the changes between the last two days."""
import gzip, json, os, sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import backfill, history  # noqa: E402


class MemStore:
    def __init__(self):
        self.data, self.cache = {}, {}

    def get_json(self, key):
        return json.loads(json.dumps(self.data[key])) if key in self.data else None

    def put_json(self, key, obj, max_age=None):
        self.data[key], self.cache[key] = json.loads(json.dumps(obj)), max_age


@pytest.fixture(scope="module")
def data():
    with gzip.open(os.path.join(HERE, "fixtures", "hourly_nov2025.json.gz"), "rt") as f:
        hourly = json.load(f)
    return hourly, backfill.stations(os.path.join(HERE, "fixtures", "stations.tsv"))


def test_complete_days_end_on_the_last_scored_afternoon():
    assert history.complete_days("2025-11-30T23", 3) == ["2025-11-30", "2025-11-29", "2025-11-28"]
    assert history.complete_days("2025-11-30T16", 2) == ["2025-11-29", "2025-11-28"]  # 17:00 not reached yet
    assert history.complete_days("2025-11-30T17", 1) == ["2025-11-30"]


def test_first_run_builds_the_month_and_the_second_adds_nothing(data):
    hourly, stations = data
    store = MemStore()
    log = history.update(store, hourly, stations, "2025-11-30T23", budget_s=60)
    doc = store.data[history.KEY]
    assert log == {"days": 28, "scored": 28} and store.cache[history.KEY] == 300
    assert doc["days"][0] == "2025-11-03" and doc["days"][-1] == "2025-11-30" and doc["score_hour"] == 17
    assert set(doc["stations"]) == {str(s["id"]) for s in stations}
    row = doc["stations"][str(stations[0]["id"])][-1]
    assert row["d"] == "2025-11-30" and row["s"] in ("ok", "watch", "flag", "nodata")
    assert len(row["c"]) == 3 and set(row["c"]) <= set("owfn")
    assert len(doc["totals"]) == 28 and sum(doc["totals"][-1][k] for k in ("ok", "watch", "flag", "nodata")) == len(stations)
    again = history.update(store, hourly, stations, "2025-11-30T23", budget_s=60)
    assert again == {"days": 28, "scored": 0}
    assert store.data[history.KEY]["stations"] == doc["stations"]


def test_a_short_budget_scores_the_newest_days_first(data):
    hourly, stations = data
    store = MemStore()
    ticks = iter(range(0, 10_000, 40))  # a clock that jumps 40 s per call
    log = history.update(store, hourly, stations, "2025-11-30T23", budget_s=100, clock=lambda: next(ticks))
    doc = store.data[history.KEY]
    assert 1 <= log["scored"] < 28 and doc["days"][-1] == "2025-11-30"
    assert all(d > "2025-11-20" for d in doc["days"])  # the newest ones


def test_the_feed_lists_every_change_newest_first(data):
    import xml.etree.ElementTree as ET
    hourly, stations = data
    store = MemStore()
    store.put_text = lambda key, text, content_type=None, max_age=None: store.data.__setitem__(key, text)
    history.update(store, hourly, stations, "2025-11-30T23", budget_s=60, site_url="https://example.test/")
    xml = store.data[history.FEED_KEY]
    root = ET.fromstring(xml)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entries = root.findall("a:entry", ns)
    assert root.find("a:link", ns).get("href") == "https://example.test/" and entries
    titles = [e.find("a:title", ns).text for e in entries]
    assert all("→" in t for t in titles)
    dates = [e.find("a:updated", ns).text for e in entries]
    assert dates == sorted(dates, reverse=True)
    assert entries[0].find("a:link", ns).get("href").startswith("https://example.test/#")
    doc = store.data[history.KEY]
    n_changes = sum(1 for rows in doc["stations"].values() for a, b in zip(rows, rows[1:], strict=False) if a["s"] != b["s"])
    assert len(entries) == min(200, n_changes)
    for bad in ("fake", "tamper", "spray", "cheat", "fraud"):
        assert bad not in xml.lower().replace("not that anyone tampered", "")


def test_changes_are_the_newest_day_against_the_one_before(data):
    hourly, stations = data
    store = MemStore()
    history.update(store, hourly, stations, "2025-11-30T23", budget_s=60)
    doc = store.data[history.KEY]
    for c in doc["changes"]:
        rows = {r["d"]: r for r in doc["stations"][str(c["id"])]}
        assert rows["2025-11-29"]["s"] == c["from"] and rows["2025-11-30"]["s"] == c["to"] and c["from"] != c["to"]
    # and a monitor whose answer did not change is not listed
    changed = {c["id"] for c in doc["changes"]}
    for s in stations:
        rows = {r["d"]: r for r in doc["stations"][str(s["id"])]}
        if rows["2025-11-29"]["s"] == rows["2025-11-30"]["s"]:
            assert s["id"] not in changed
