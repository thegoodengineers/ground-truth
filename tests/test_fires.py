"""The farm-fire layer (src/fires.py) against a fake FIRMS: parsing, the bearing and the sentence, the document,
and that no key or a failure never breaks the run."""
import datetime as dt, io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import fires  # noqa: E402

CSV = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight
30.90,75.80,341.2,0.5,0.5,2026-10-08,0730,N,VIIRS,n,2.0NRT,295.1,4.2,D
30.40,75.20,367.9,0.5,0.5,2026-10-08,0731,N,VIIRS,h,2.0NRT,300.0,12.0,D
29.70,76.10,330.0,0.5,0.5,2026-10-08,2012,N,VIIRS,l,2.0NRT,290.0,1.1,N
bad,row
"""
REGION = {"map": {"centre": [28.62, 77.2]}}


class MemStore:
    def __init__(self):
        self.data, self.cache = {}, {}

    def put_json(self, key, obj, max_age=None):
        self.data[key], self.cache[key] = obj, max_age


def opener_for(text, calls):
    def opener(req, timeout=None):
        calls.append(req.full_url)
        return io.BytesIO(text.encode())
    return opener


def test_parse_sorts_the_brightest_first_and_skips_bad_rows():
    rows = fires.parse(CSV)
    assert [r[2] for r in rows] == [367.9, 341.2, 330.0]
    assert rows[0][:2] == (30.4, 75.2) and rows[0][3:] == ("2026-10-08", "0731", "h")


def test_bearing_direction_and_the_sentence():
    assert round(fires.bearing((28.62, 77.2), (30.9, 75.8))) == 332  # Punjab is north-west of Delhi
    assert fires.direction(331) == "north-west" and fires.direction(0) == "north" and fires.direction(100) == "east"
    assert fires.line(312, "north-west") == "312 farm fires in the last 24 h, north-west of the city."
    assert fires.line(1, "north") == "1 farm fire in the last 24 h, north of the city."
    assert fires.line(0, "north-west").startswith("No farm fires")


def test_publish_writes_fires_json():
    store, calls = MemStore(), []
    doc = fires.publish(store, REGION, "k123", opener_for(CSV, calls), now=dt.datetime(2026, 10, 8, 22, tzinfo=dt.timezone.utc))
    assert calls == [f"{fires.API}/k123/{fires.SOURCE}/73.5,27.5,79.5,32.5/1"]
    assert store.data[fires.KEY] == doc and store.cache[fires.KEY] == 300
    assert doc["count"] == 3 and doc["high_confidence"] == 1 and doc["direction"] == "north-west"
    assert 150 < doc["distance_km"] < 260 and len(doc["points"]) == 3 and doc["points"][0][2] == 367.9
    assert doc["line"] == "3 farm fires in the last 24 h, north-west of the city."
    for bad in ("fake", "tamper", "spray", "cheat", "fraud"):
        assert bad not in doc["line"].lower()


def test_no_key_and_failures_are_quiet():
    store = MemStore()
    assert fires.publish(store, REGION, None) == "no FIRMS key"
    assert store.data[fires.KEY]["count"] is None and store.data[fires.KEY]["line"] is None  # a stub, not a 404

    def broken(req, timeout=None):
        raise OSError("no network")
    store = MemStore()
    assert fires.publish(store, REGION, "k", broken) == "OSError: no network" and store.data == {}
    empty = fires.publish(store, REGION, "k", opener_for("latitude,longitude\n", []))
    assert empty["count"] == 0 and empty["bearing_deg"] is None and empty["line"].startswith("No farm fires")
