"""Scorer tests. The fixture is real data: 16 north-Delhi stations, 3-30 Nov 2025, from the public OpenAQ archive
(built with src/backfill.py, then trimmed to these stations and dates)."""
import copy, datetime as dt, gzip, json, os, sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import backfill, scorer  # noqa: E402

NOW = dt.datetime(2025, 11, 30, 23)
QUIET = 8917  # Ashok Vihar: ok on every check in the untouched fixture


@pytest.fixture(scope="module")
def data():
    with gzip.open(os.path.join(HERE, "fixtures", "hourly_nov2025.json.gz"), "rt") as f:
        hourly = json.load(f)
    return hourly, backfill.stations(os.path.join(HERE, "fixtures", "stations.tsv"))


@pytest.fixture(scope="module")
def baseline(data):
    hourly, stations = data
    return scorer.score(hourly, stations, NOW)


def by_id(latest):
    return {s["id"]: s for s in latest["stations"]}


def plant(hourly, sid, factor=0.6):
    """Multiply one station's PM10 by `factor` from 11:00 to 16:59 IST on each of the last 7 days."""
    out = copy.deepcopy(hourly)
    pm10 = out[str(sid)]["pm10"]
    for k in list(pm10):
        day = dt.datetime.strptime(k, "%Y-%m-%dT%H")
        if 11 <= day.hour <= 16 and (NOW - day).days < 7:
            pm10[k] = pm10[k] * factor
    return out


# ---------- planted anomaly ----------

def test_quiet_station_starts_ok(baseline):
    s = by_id(baseline[0])[QUIET]
    assert {c["status"] for c in s["checks"].values()} == {"ok"}


def test_planted_daytime_drop_is_flagged(data, baseline):
    hourly, stations = data
    latest, _ = scorer.score(plant(hourly, QUIET), stations, NOW)
    s = by_id(latest)[QUIET]
    assert s["checks"]["neighbours"]["status"] == "flag"
    assert s["checks"]["history"]["status"] == "flag"
    assert s["checks"]["history"]["param"] == "pm10"
    assert s["checks"]["physics"]["status"] == "ok"  # a lower PM10 is not physically impossible
    assert s["status"] == "flag"


def test_every_quiet_station_is_caught(data, baseline):
    """Plant the same drop in each station that is ok on every check; each one must be flagged."""
    hourly, stations = data
    before = by_id(baseline[0])
    quiet = [sid for sid, s in before.items() if all(c["status"] == "ok" for c in s["checks"].values())]
    assert len(quiet) >= 8
    missed = [q for q in quiet if by_id(scorer.score(plant(hourly, q), stations, NOW)[0])[q]["status"] != "flag"]
    assert missed == []


def test_planting_one_station_does_not_flag_the_others(data, baseline):
    """Stations flagged in the first pass are dropped from their neighbours' references, so the planted drop
    doesn't flag anyone else. Borderline stations may still move between ok and watch."""
    hourly, stations = data
    before = by_id(baseline[0])
    after = by_id(scorer.score(plant(hourly, QUIET), stations, NOW)[0])
    others = [sid for sid in before if sid != QUIET]
    assert [sid for sid in others if after[sid]["status"] == "flag" and before[sid]["status"] != "flag"] == []
    assert sum(before[sid]["status"] != after[sid]["status"] for sid in others) <= 2


def test_daytime_window_matters(data):
    """The same drop planted at night (00-05) must not read as a daytime drop."""
    hourly, stations = data
    night = copy.deepcopy(hourly)
    pm10 = night[str(QUIET)]["pm10"]
    for k in list(pm10):
        day = dt.datetime.strptime(k, "%Y-%m-%dT%H")
        if day.hour <= 5 and (NOW - day).days < 7:
            pm10[k] *= 0.6
    s = by_id(scorer.score(night, stations, NOW)[0])[QUIET]
    assert s["checks"]["neighbours"]["z"] > 0  # night drop raises day-minus-night, the opposite sign


# ---------- physics ----------

def synthetic(pm10, pm25):
    keys = scorer.hour_keys(NOW, 7)
    return {"1": {"pm10": dict(zip(keys, pm10, strict=False)), "pm25": dict(zip(keys, pm25, strict=False))}}, keys


def phys(hourly, keys):
    clean, physics = scorer.prepare(hourly["1"], keys)
    return scorer.physics_check(physics)


def wobble(n, base):
    return [base + (i % 7) * 3.1 + (i % 5) * 1.3 for i in range(n)]


def test_clean_data_passes_physics():
    pm10 = wobble(168, 200.0)
    h, keys = synthetic(pm10, [v * 0.5 for v in pm10])
    assert phys(h, keys)["status"] == "ok"


def test_pm25_above_pm10_is_flagged():
    pm10 = wobble(168, 200.0)
    pm25 = [v * (1.3 if i % 10 == 0 else 0.5) for i, v in enumerate(pm10)]  # 10% of hours impossible
    h, keys = synthetic(pm10, pm25)
    r = phys(h, keys)
    assert r["status"] == "flag" and 9 <= r["fail_pct"] <= 11


def test_stuck_sensor_is_flagged():
    pm10 = wobble(168, 200.0)
    pm10[50:62] = [222.0] * 12  # 12 identical hours = 7%
    h, keys = synthetic(pm10, [v * 0.5 for v in wobble(168, 200.0)])
    assert phys(h, keys)["status"] == "flag"


def test_out_of_range_is_caught():
    pm10 = wobble(168, 200.0)
    pm10[10] = 0.0
    pm10[11] = 5000.0
    h, keys = synthetic(pm10, [v * 0.5 for v in wobble(168, 200.0)])
    r = phys(h, keys)
    assert r["status"] == "watch" and r["fail_pct"] == pytest.approx(100 * 2 / 168, abs=0.1)


def test_no_data_is_nodata():
    keys = scorer.hour_keys(NOW, 7)
    assert scorer.physics_check(scorer.prepare({}, keys)[1])["status"] == "nodata"


# ---------- contract (docs/STACK.md) ----------

STATUSES = {"ok", "watch", "flag", "nodata"}


def test_latest_json_contract(baseline):
    latest, per_station = baseline
    json.dumps(latest)  # serialisable, no NaN
    assert latest["data_through"] == "2025-11-30T23:00:00+05:30"
    for s in latest["stations"]:
        assert {"id", "name", "lat", "lon", "region", "status", "checks", "latest", "neighbours_latest",
                "last_reading", "band", "neighbours_band"} <= set(s)
        assert s["band"] in scorer.BANDS + (None,) and s["neighbours_band"] in scorer.BANDS + (None,)
        assert set(s["neighbours_latest"]) == {"pm25", "pm10"}
        assert s["status"] in STATUSES and s["region"] in {"Delhi", "NCR"}
        assert set(s["checks"]) == {"physics", "neighbours", "history"}
        for c in s["checks"].values():
            assert c["status"] in STATUSES and isinstance(c["detail"], str) and c["detail"]
        worst = max(scorer.RANK[c["status"]] for c in s["checks"].values())
        assert scorer.RANK[s["status"]] == worst or (s["status"] == "nodata" and s["detail"].startswith("No reading"))
        assert set(s["latest"]) == set(scorer.PARAMS)


def test_station_json_contract(baseline):
    _, per_station = baseline
    for doc in per_station.values():
        s = json.dumps(doc, allow_nan=False)
        assert "NaN" not in s
        for key in ("hour_profile", "hour_profile_7d"):
            assert set(doc[key]) == set(scorer.PARAMS)
            assert all(len(v) == 24 for v in doc[key].values())
        assert len(doc["daily"]) == 28
        assert doc["id"] not in doc["neighbours"]
        r48 = doc["recent_48h"]
        assert len(r48["hours"]) == 48
        assert len(r48["pm25"]) == 48
        assert set(r48["neighbours_pm25"]) == {str(n) for n in doc["neighbours"]}


def test_neighbours_latest_is_the_median_of_the_neighbours_now(baseline, data):
    hourly, stations = data
    latest, per_station = baseline
    s = by_id(latest)[8235]
    keys = scorer.hour_keys(NOW, 28)
    values = []
    for i in per_station[8235]["neighbours"]:
        clean, _ = scorer.prepare(hourly[str(i)], keys)
        values.append(scorer.last_value(clean["pm25"]))
    import statistics
    assert s["neighbours_latest"]["pm25"] == pytest.approx(statistics.median([v for v in values if v is not None]), abs=0.01)


# ---------- freshness and AQI band ----------

def test_silent_station_is_nodata_with_its_last_reading(data, baseline):
    """A monitor whose last 4 hours are empty isn't judged; every other monitor keeps its answer."""
    hourly, stations = data
    quiet = copy.deepcopy(hourly)
    gone = {(NOW - dt.timedelta(hours=h)).strftime("%Y-%m-%dT%H") for h in range(4)}
    for series in quiet[str(QUIET)].values():
        for k in gone:
            series.pop(k, None)
    before, after = by_id(baseline[0]), by_id(scorer.score(quiet, stations, NOW)[0])
    s = after[QUIET]
    assert s["status"] == "nodata"
    assert s["last_reading"] == "2025-11-30T19:00:00+05:30"
    assert s["detail"] == "No reading since 19:00 on 30 Nov."
    assert s["checks"] == before[QUIET]["checks"]  # its last checks stay visible
    assert before[QUIET]["last_reading"] == "2025-11-30T23:00:00+05:30" and "detail" not in before[QUIET]
    others = lambda latest: {sid: x["status"] for sid, x in latest.items() if sid != QUIET}  # noqa: E731
    assert others(after) == others(before)


@pytest.mark.parametrize("pm25,pm10,expected", [
    (30, None, "Good"), (30.01, None, "Satisfactory"), (60, None, "Satisfactory"), (60.5, None, "Moderate"),
    (90, None, "Moderate"), (91, None, "Poor"), (120, None, "Poor"), (121, None, "Very poor"),
    (250, None, "Very poor"), (251, None, "Severe"),
    (None, 50, "Good"), (None, 51, "Satisfactory"), (None, 100, "Satisfactory"), (None, 101, "Moderate"),
    (None, 250, "Moderate"), (None, 251, "Poor"), (None, 350, "Poor"), (None, 351, "Very poor"),
    (None, 430, "Very poor"), (None, 431, "Severe"),
    (20, 300, "Poor"), (200, 40, "Very poor"),  # the worse of the two
    (None, None, None)])
def test_cpcb_band_edges(pm25, pm10, expected):
    assert scorer.band(pm25, pm10) == expected


def test_24h_average_needs_16_hours():
    assert scorer.mean_24h([None] * 9 + [100.0] * 15) is None
    assert scorer.mean_24h([None] * 8 + [100.0] * 16) == 100.0


def test_neighbours_band_comes_from_the_neighbours_24h_averages(baseline, data):
    hourly, stations = data
    latest, per_station = baseline
    keys = scorer.hour_keys(NOW, 28)
    import statistics
    for s in latest["stations"]:
        nb = [scorer.prepare(hourly[str(i)], keys)[0] for i in per_station[s["id"]]["neighbours"]]
        avg = {p: [m for m in (scorer.mean_24h(c[p]) for c in nb) if m is not None] for p in ("pm25", "pm10")}
        want = scorer.band(*(statistics.median(avg[p]) if len(avg[p]) >= 2 else None for p in ("pm25", "pm10")))
        assert s["neighbours_band"] == want


def test_copy_never_accuses(baseline):
    text = json.dumps(baseline[0]).lower()
    for word in ("fake", "tamper", "spray", "cheat", "fraud"):
        assert word not in text


def test_matches_spike_numbers():
    """Over Oct-Nov 2025 the scorer reproduces spike/RESULTS.md for the two named stations."""
    path = os.environ.get("GT_HOURLY_2025")
    if not path:
        pytest.skip("set GT_HOURLY_2025 to a backfill of 2025-10-01..2025-11-30 to run")
    hourly = json.load(open(path))
    _, per = scorer.score(hourly, backfill.stations(), NOW, days=61)
    import statistics
    for sid, pm10, rh in ((235, -0.17, 7.2), (8235, -0.04, 6.4)):
        d = per[sid]["daily"]
        assert statistics.median([r["d_pm10"] for r in d if r["d_pm10"] is not None]) == pytest.approx(pm10, abs=0.01)
        assert statistics.median([r["d_relativehumidity"] for r in d if r["d_relativehumidity"] is not None]) == pytest.approx(rh, abs=0.1)


# ---------- CSV output ----------

def test_csv_has_one_row_per_station(baseline):
    import csv, io
    latest, _ = baseline
    text = scorer.to_csv(latest)
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == len(latest["stations"])


def test_csv_statuses_match_json(baseline):
    import csv, io
    latest, _ = baseline
    text = scorer.to_csv(latest)
    rows = {int(r["id"]): r for r in csv.DictReader(io.StringIO(text))}
    for s in latest["stations"]:
        assert rows[s["id"]]["status"] == s["status"]
        assert rows[s["id"]]["physics_status"] == s["checks"]["physics"]["status"]
        assert rows[s["id"]]["neighbours_status"] == s["checks"]["neighbours"]["status"]
        assert rows[s["id"]]["history_status"] == s["checks"]["history"]["status"]


def test_region_file_matches_the_delhi_defaults():
    """src/regions/delhi.json is the source of Delhi's settings; the module constants must agree with it."""
    cfg = backfill.region("delhi")
    assert cfg["id"] == "delhi" and os.path.exists(cfg["stations_path"])
    nb = cfg["neighbours"]
    assert (nb["k"], nb["radius_km"], nb["colocated_km"]) == (scorer.K, scorer.RADIUS_KM, scorer.COLOC_KM)
    assert tuple(cfg["areas"]["outer_words"]) == scorer.NCR
    assert len(backfill.stations(region_name="delhi")) == 52


def test_scoring_with_the_delhi_region_changes_nothing(data):
    hourly, stations = data
    plain, _ = scorer.score(hourly, stations, NOW)
    with_region, _ = scorer.score(hourly, stations, NOW, region=backfill.region("delhi"))
    assert with_region["region"]["id"] == "delhi"
    assert with_region["stations"] == plain["stations"]


def test_a_region_can_widen_the_neighbour_search(data):
    hourly, stations = data
    wide = {"id": "test", "neighbours": {"k": 6, "radius_km": 40.0, "colocated_km": 0.5},
            "areas": {"core": "City", "outer": "Edge", "outer_words": ["Zzz"]}}
    latest, per = scorer.score(hourly, stations, NOW, region=wide)
    assert max(len(doc["neighbours"]) for doc in per.values()) == 6
    assert {s["region"] for s in latest["stations"]} == {"City"}
