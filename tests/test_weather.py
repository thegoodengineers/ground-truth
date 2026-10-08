"""Weather context (src/weather.py) against a fake Open-Meteo: the sentence, the compass, the document, and
that a failure never breaks the run."""
import datetime as dt, io, json, os, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import weather  # noqa: E402

BODY = {"current": {"time": "2026-10-09T03:30", "wind_speed_10m": 5.0, "wind_direction_10m": 139,
                    "temperature_2m": 25.3, "relative_humidity_2m": 81},
        "hourly": {"time": ["2026-10-09T02:00", "2026-10-09T03:00", "2026-10-09T04:00"],
                   "boundary_layer_height": [300.0, 412.4, 600.0]}}


class MemStore:
    def __init__(self):
        self.data, self.cache = {}, {}

    def put_json(self, key, obj, max_age=None):
        self.data[key], self.cache[key] = obj, max_age


def opener_for(body, calls):
    def opener(req, timeout=None):
        calls.append(dict(urllib.parse.parse_qsl(urllib.parse.urlparse(req.full_url).query)))
        return io.BytesIO(json.dumps(body).encode())
    return opener


def test_compass_and_the_sentence():
    assert [weather.compass(d) for d in (0, 22, 23, 139, 180, 270, 337, 338)] == ["N", "N", "NE", "SE", "S", "W", "NW", "N"]
    calm = weather.line(3.0, 10, 300, hour=22)
    assert calm.startswith("Calm air tonight (wind 3 km/h) and the air is mixing only a few hundred metres up")
    assert "building up" in calm
    assert weather.line(9.0, 300, 900, hour=14) == ("A light wind from the north-west right now (9 km/h): "
                                                      "the air is moving a little, so readings drift together.")
    assert "cleared" in weather.line(22.0, 270, None, hour=14)
    assert weather.line(None, None, None) is None
    for text in (calm, weather.line(9.0, 300, 900), weather.line(22.0, 270, None)):
        for bad in ("fake", "tamper", "spray", "cheat", "fraud"):
            assert bad not in text.lower()


def test_fetch_builds_the_document():
    calls = []
    doc = weather.fetch(28.62, 77.2, opener_for(BODY, calls), now=dt.datetime(2026, 10, 8, 22, 0, tzinfo=dt.timezone.utc))
    assert calls[0]["latitude"] == "28.62" and calls[0]["wind_speed_unit"] == "kmh" and "boundary_layer_height" in calls[0]["hourly"]
    assert doc["wind_kmh"] == 5.0 and doc["wind_from_deg"] == 139 and doc["wind_from"] == "SE"
    assert doc["boundary_layer_m"] == 412  # the 03:00 hour, matching the current time's hour
    assert doc["line"].startswith("Calm air tonight")
    assert doc["source"] == "Open-Meteo" and doc["fetched_at"] == "2026-10-08T22:00:00+00:00"


def test_publish_writes_weather_json_and_swallows_failures():
    store, calls = MemStore(), []
    region = {"map": {"centre": [28.62, 77.2]}}
    doc = weather.publish(store, region, opener_for(BODY, calls))
    assert store.data[weather.KEY] == doc and store.cache[weather.KEY] == 300

    def broken(req, timeout=None):
        raise OSError("no network")
    assert weather.publish(MemStore(), region, broken) == "OSError: no network"
