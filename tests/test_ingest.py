"""Ingest tests with a fake OpenAQ API and an in-memory store: no network, no AWS, no key."""
import datetime as dt, io, json, os, sys, urllib.error, urllib.parse

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import ingest  # noqa: E402

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 8, 9, 30, tzinfo=UTC)  # 15:00 IST
STATIONS = [{"id": i, "name": f"S{i}", "lat": 28.6 + i * 0.01, "lon": 77.2} for i in range(1, 5)]


class MemStore:
    def __init__(self, data=None):
        self.data, self.cache = dict(data or {}), {}

    def get_json(self, key):
        return json.loads(json.dumps(self.data[key])) if key in self.data else None

    def put_json(self, key, obj, max_age=None):
        self.data[key], self.cache[key] = json.loads(json.dumps(obj)), max_age

    def put_text(self, key, text, content_type=None, max_age=None):
        self.data[key] = text


class FakeAPI:
    """Serves /locations/{id} and /sensors/{id}/hours. Sensor id = location*10 + param index."""

    def __init__(self, fail_first=0, now=NOW, retry_after=None):
        self.requests, self.fail_first, self.now, self.retry_after = [], fail_first, now, retry_after

    def __call__(self, req, timeout=None):
        assert req.get_header("X-api-key") == "k"
        u = urllib.parse.urlparse(req.full_url)
        q = dict(urllib.parse.parse_qsl(u.query))
        self.requests.append((u.path, q))
        if self.fail_first:
            self.fail_first -= 1
            hdrs = {"Retry-After": self.retry_after} if self.retry_after else {}
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", hdrs, None)
        parts = u.path.split("/")
        if parts[-2] == "locations":
            loc = int(parts[-1])
            sensors = [{"id": loc * 10 + i, "parameter": {"name": p}} for i, p in enumerate(ingest.backfill.PARAMS)]
            sensors.append({"id": loc * 10 + 9, "parameter": {"name": "o3"}})  # ignored
            body = {"results": [{"id": loc, "sensors": sensors}]}
        else:
            sid = int(parts[-2])
            start = dt.datetime.fromisoformat(q["datetime_from"].replace("Z", "+00:00"))
            rows, t = [], start
            while t + dt.timedelta(minutes=15) <= self.now:  # 15-min readings, stamped at the interval's end
                value = 100.0 + sid if sid % 10 != 1 else 50.0 + sid  # pm25 below pm10
                end = t + dt.timedelta(minutes=15)
                rows.append({"value": value, "period": {"datetimeFrom": {"utc": t.strftime("%Y-%m-%dT%H:%M:%SZ")},
                                                        "datetimeTo": {"utc": end.strftime("%Y-%m-%dT%H:%M:%SZ")}}})
                t = end
            body = {"results": rows}
        return io.BytesIO(json.dumps(body).encode())


def api(fake):
    return ingest.OpenAQ("k", opener=fake, sleep=lambda s: None)


def test_first_run_fetches_sensors_and_six_days():
    store, fake = MemStore(), FakeAPI()
    log = ingest.run(store, api(fake), STATIONS, NOW)
    assert set(store.data[ingest.SENSORS_KEY]["1"]) == set(ingest.backfill.PARAMS)
    pm10 = store.data[ingest.RAW_KEY]["1"]["pm10"]
    assert len(pm10) == 6 * 24  # 15:00 IST six days ago through the complete 14:00-15:00 hour today
    assert max(pm10) == "2026-10-08T14"
    assert log["scored"] and log["data_through"] == max(pm10)
    assert store.cache["data/latest.json"] == 300
    assert {s["id"] for s in store.data["data/latest.json"]["stations"]} == {1, 2, 3, 4}


def test_second_run_only_fetches_recent_hours_and_keeps_history():
    store = MemStore()
    ingest.run(store, api(FakeAPI()), STATIONS, NOW)
    before = len(store.data[ingest.RAW_KEY]["1"]["pm10"])
    fake = FakeAPI(now=NOW + dt.timedelta(hours=1))
    ingest.run(store, api(fake), STATIONS, NOW + dt.timedelta(hours=1))
    hours_calls = [q for p, q in fake.requests if p.endswith("/measurements")]
    assert not any(p.startswith("/v3/locations") for p, _ in fake.requests)  # sensor map is cached
    assert len(hours_calls) == 4 * 5
    since = dt.datetime.fromisoformat(hours_calls[0]["datetime_from"].replace("Z", "+00:00"))
    assert NOW - since <= dt.timedelta(hours=3)
    assert len(store.data[ingest.RAW_KEY]["1"]["pm10"]) == before + 1


def test_cache_is_trimmed_to_29_days():
    old = {"1": {"pm10": {"2026-08-01T10": 99.0, "2026-10-07T10": 98.0}}}
    store = MemStore({ingest.RAW_KEY: old})
    ingest.run(store, api(FakeAPI()), STATIONS, NOW)
    keys = store.data[ingest.RAW_KEY]["1"]["pm10"]
    assert "2026-08-01T10" not in keys and "2026-10-07T10" in keys


def test_call_budget_is_respected_and_rest_is_skipped():
    fake = FakeAPI()
    a = api(fake)
    log = ingest.run(MemStore(), a, STATIONS, NOW, max_calls=8)
    assert a.calls <= 8 + 1 and log["skipped"] > 0


def test_rate_limit_is_retried():
    fake = FakeAPI(fail_first=2)
    a = api(fake)
    assert a.sensors(1)["pm10"] == 10
    assert a.calls == 3


def test_other_http_errors_are_raised():
    def boom(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)
    with pytest.raises(urllib.error.HTTPError):
        ingest.OpenAQ("k", opener=boom, sleep=lambda s: None).sensors(1)


def test_overlap_ratio_reports_units_agreement():
    """Archive values already in the cache are compared with the API's for the same hours."""
    seed = {str(s["id"]): {"pm10": {"2026-10-08T10": 100.0 + s["id"] * 10}} for s in STATIONS}
    store = MemStore({ingest.RAW_KEY: seed})
    log = ingest.run(store, api(FakeAPI()), STATIONS, NOW)
    assert log["overlap_ratio"]["pm10"] == pytest.approx(1.0)


def test_score_hour_ignores_a_single_early_clock():
    hourly = {"1": {"pm10": {"2026-10-08T12": 1, "2026-10-08T20": 1}}, "2": {"pm10": {"2026-10-08T12": 1}},
              "3": {"pm25": {"2026-10-08T12": 1}}, "4": {}}
    assert ingest.score_hour(hourly, 4) == "2026-10-08T12"


# ---------- resilience (#19) ----------

def test_retry_after_is_respected_and_tries_stop_at_three():
    waits = []
    a = ingest.OpenAQ("k", opener=FakeAPI(fail_first=1, retry_after="7"), sleep=waits.append)
    assert a.sensors(1)["pm10"] == 10
    assert 7 in waits and a.retries == 1
    a = ingest.OpenAQ("k", opener=FakeAPI(fail_first=5), sleep=lambda s: None)
    with pytest.raises(urllib.error.HTTPError):
        a.sensors(1)
    assert a.calls == 3


def test_next_run_starts_with_the_stations_the_budget_skipped():
    store = MemStore()
    ingest.run(store, api(FakeAPI()), STATIONS, NOW, max_calls=8)  # station 1 in full, one sensor of station 2
    fake = FakeAPI()
    ingest.run(store, api(fake), STATIONS, NOW)
    assert fake.requests[0][0] == "/v3/locations/3"
    assert all(len(store.data[ingest.RAW_KEY][str(i)]) == 5 for i in range(1, 5))


def test_wrong_key_stops_the_run_and_says_so():
    calls = []

    def refused(req, timeout=None):
        calls.append(req)
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)
    log = ingest.run(MemStore(), ingest.OpenAQ("k", opener=refused, sleep=lambda s: None), STATIONS, NOW)
    assert len(calls) == 1 and "rejected the API key" in log["error"] and log["published"] is False


def test_api_down_keeps_the_published_hour():
    store = MemStore()
    ingest.run(store, api(FakeAPI()), STATIONS, NOW)
    before = store.data["data/latest.json"]

    def down(req, timeout=None):
        raise urllib.error.URLError("no route to host")
    later = NOW + dt.timedelta(hours=1)
    log = ingest.run(store, ingest.OpenAQ("k", opener=down, sleep=lambda s: None), STATIONS, later)
    assert log["new_hours"] == 0 and log["skipped"] > 0
    assert store.data["data/latest.json"]["data_through"] == before["data_through"]
    # and with the cache lost too, nothing can be scored, so the old file is left alone
    kept = store.data["data/latest.json"]  # the second run republished the same hour (a new generated_at)
    store.data[ingest.RAW_KEY] = {}
    log = ingest.run(store, ingest.OpenAQ("k", opener=down, sleep=lambda s: None), STATIONS, later)
    assert log["published"] is False and store.data["data/latest.json"] is kept
    same = lambda d: {k: v for k, v in d.items() if k != "generated_at"}  # noqa: E731
    assert same(kept) == same(before)


def test_a_worse_result_is_not_published():
    st = lambda last: {"latest": {}, "last_reading": last}  # noqa: E731
    new = {"data_through": "2026-10-08T14:00:00+05:30",
           "stations": [st("2026-10-08T14:00:00+05:30"), st("2026-10-08T12:00:00+05:30"), st("2026-10-08T11:00:00+05:30"), st(None)]}
    assert ingest.why_not_publish(new, None, 4) is None  # 2 of 4 reported in the last 3 hours
    new["stations"][1] = st("2026-10-08T11:00:00+05:30")
    assert "only 1 of 4" in ingest.why_not_publish(new, None, 4)
    new["stations"][1] = st("2026-10-08T13:00:00+05:30")
    assert "older than" in ingest.why_not_publish(new, {"data_through": "2026-10-08T15:00:00+05:30"}, 4)
# ---------- hysteresis ----------

def _make_latest(statuses):
    return {"stations": [{"id": str(i), "status": s} for i, s in enumerate(statuses)]}


def test_hysteresis_worsening_is_immediate():
    hist = {}
    latest = _make_latest(["ok"])
    ingest.apply_hysteresis(latest, hist, "2026-10-08T10")
    assert latest["stations"][0]["status"] == "ok"
    latest2 = _make_latest(["flag"])
    ingest.apply_hysteresis(latest2, hist, "2026-10-08T11")
    assert latest2["stations"][0]["status"] == "flag"


def test_hysteresis_improving_needs_three_hours():
    hist = {}
    for hour in range(3):
        latest = _make_latest(["flag"])
        ingest.apply_hysteresis(latest, hist, f"2026-10-08T{hour:02d}")
    # now drop to ok
    for hour in range(3, 5):
        latest = _make_latest(["ok"])
        ingest.apply_hysteresis(latest, hist, f"2026-10-08T{hour:02d}")
        assert latest["stations"][0]["status"] == "flag", f"should still be flag at hour {hour}"
    # third ok in a row — should drop
    latest = _make_latest(["ok"])
    ingest.apply_hysteresis(latest, hist, "2026-10-08T05")
    assert latest["stations"][0]["status"] == "ok"


def test_hysteresis_status_since_tracks_change():
    hist = {}
    latest = _make_latest(["ok"])
    ingest.apply_hysteresis(latest, hist, "2026-10-08T10")
    assert latest["stations"][0]["status_since"] == "2026-10-08T10"
    # worsen immediately
    latest2 = _make_latest(["flag"])
    ingest.apply_hysteresis(latest2, hist, "2026-10-08T11")
    assert latest2["stations"][0]["status_since"] == "2026-10-08T11"
# ---------- archive re-sync (#33) ----------

class DictStore:
    def __init__(self, data=None):
        self._d = dict(data or {})
    def get_json(self, key):
        return self._d.get(key)
    def put_json(self, key, obj, **_):
        self._d[key] = obj


def _make_hourly(sid="1", p="pm10", hours=None):
    vals = hours or {"2025-11-26T10": 100.0, "2025-11-26T11": 110.0}
    return {sid: {p: vals}}


def test_resync_replaces_api_hour(monkeypatch):
    import ingest, backfill as bf
    monkeypatch.setattr(bf, "listed_days", lambda *a, **kw: ["fake_20251126.csv.gz"])
    monkeypatch.setattr(bf, "day_rows", lambda *a, **kw: [
        {"parameter": "pm10", "value": "90.0", "datetime": "2025-11-26T05:15:00+00:00"},
        {"parameter": "pm10", "value": "92.0", "datetime": "2025-11-26T05:30:00+00:00"},
    ])
    hourly = _make_hourly("1", "pm10", {"2025-11-26T10": 100.0})
    now = dt.datetime(2025, 11, 30, 0, 0, tzinfo=ingest.IST)
    store = DictStore()
    result = ingest.resync_archive(hourly, now, store)
    assert result["resync_changed_hours"] > 0 or "resync_max_diff" in result


def test_should_resync_only_once_per_day(monkeypatch):
    import ingest
    now = dt.datetime(2025, 11, 30, 4, 0, tzinfo=ingest.IST)  # 04:00 IST
    store_fresh = DictStore()
    assert ingest._should_resync(now, store_fresh) is True
    store_done = DictStore({"data/raw/resync_marker.json": {"date": "2025-11-30"}})
    assert ingest._should_resync(now, store_done) is False


def test_should_not_resync_before_hour(monkeypatch):
    import ingest
    now = dt.datetime(2025, 11, 30, 2, 0, tzinfo=ingest.IST)  # 02:00 IST
    assert ingest._should_resync(now, DictStore()) is False


def test_hysteresis_shows_silence_at_once_and_ignores_reruns():
    hist = {}
    for hour, raw, shown in ((10, "flag", "flag"), (11, "nodata", "nodata"), (12, "ok", "ok"), (13, "watch", "watch")):
        latest = _make_latest([raw])
        ingest.apply_hysteresis(latest, hist, f"2026-10-08T{hour:02d}")
        assert latest["stations"][0]["status"] == shown
    for _ in range(3):  # the same hour three times is still one hour of 'ok'
        latest = _make_latest(["ok"])
        ingest.apply_hysteresis(latest, hist, "2026-10-08T14")
    assert latest["stations"][0]["status"] == "watch"


def test_metrics_report_data_age_and_run_errors():
    now = dt.datetime(2026, 10, 8, 12, 30, tzinfo=UTC)  # 18:00 IST
    m = dict((n, (v, u)) for n, v, u in ingest.metrics({"data_through": "2026-10-08T14"}, now))
    assert m["IngestErrors"] == (0.0, "Count")
    assert m["DataAgeHours"] == (3.0, "None")  # the 14:00 IST hour ended at 15:00; now is 18:00
    m = dict((n, (v, u)) for n, v, u in ingest.metrics({"error": "OpenAQ rejected the API key"}, now,
                                                        published={"data_through": "2026-10-08T17:00:00+05:30"}))
    assert m["IngestErrors"] == (1.0, "Count")
    assert m["DataAgeHours"] == (1.0, "None")  # falls back to the published hour
    assert ingest.metrics({}, now) == [("IngestErrors", 0.0, "Count")]  # nothing scored yet: no age point


def _location(*sensors):
    """An opener answering /locations/{id} with these (id, param, datetimeLast or None) sensors."""
    def opener(req, timeout=None):
        rows = [{"id": i, "parameter": {"name": p}, **({"datetimeLast": {"utc": last}} if last else {})} for i, p, last in sensors]
        return io.BytesIO(json.dumps({"results": [{"id": 235, "sensors": rows}]}).encode())
    return ingest.OpenAQ("k", opener=opener, sleep=lambda s: None)


def test_sensors_take_the_current_sensor_not_a_retired_one():
    # a retired sensor listed after the current one (as at Anand Vihar, 235) used to win
    a = _location((12235609, "pm10", None), (12235610, "pm25", None), (381, "pm10", None), (384, "pm25", None))
    assert a.sensors(235) == {"pm10": 12235609, "pm25": 12235610}
    # when the API says when each sensor last reported, that decides, whatever the ids
    a = _location((900, "pm25", "2024-01-01T00:00:00Z"), (50, "pm25", "2026-10-08T09:00:00Z"))
    assert a.sensors(235) == {"pm25": 50}


def test_a_map_saved_before_the_fix_is_rebuilt():
    stale = {str(s["id"]): {"pm10": 999} for s in STATIONS}  # retired sensors the old code picked
    store, fake = MemStore({"data/raw/sensors.json": stale}), FakeAPI()
    ingest.run(store, api(fake), STATIONS, NOW)
    assert sum(path.startswith("/v3/locations/") for path, _ in fake.requests) == len(STATIONS)
    assert store.data[ingest.SENSORS_KEY]["1"]["pm10"] == 10
    assert not any("/sensors/999/" in path for path, _ in fake.requests)
