"""Ground Truth scorer: three checks per station, written as the JSON contract in docs/STACK.md.

    python src/scorer.py HOURLY.json OUT_DIR [--now YYYY-MM-DDTHH] [--days 28] [--region delhi]

Pure Python (no pandas), so the same code runs in pytest and in the ingest Lambda.
`hourly` is {station_id: {param: {"YYYY-MM-DDTHH": value}}} with IST hour keys (see backfill.py).

Checks, each ok / watch / flag / nodata:
- physics:    share of the last 7 days' hours with PM2.5 > 1.05 x PM10, out-of-range values or a stuck PM sensor.
- neighbours: last 7 days' daytime (11-17) minus night (22-06) PM10 gap against the 4 nearest stations, corrected
              for the city-wide pull of daytime mixing (stations high at night drift towards neighbours by day),
              as a robust z-score across stations.
- history:    the same daytime-minus-night contrast for PM10 and humidity, last 7 days against the 21 before,
              in robust SDs of the station's own day-to-day spread.
"""
import argparse, csv, datetime as dt, io, json, math, os, statistics

PARAMS = ("pm10", "pm25", "no2", "co", "relativehumidity")
LOG_PARAMS = ("pm10", "pm25", "no2", "co")
RANGE = {"pm10": (1, 2000), "pm25": (1, 1500), "no2": (0.5, 1000), "co": (0.02, 50), "relativehumidity": (1, 100)}
STUCK_PARAMS = ("pm10", "pm25", "no2", "co")  # humidity legitimately sits still (e.g. 100% at night)
DAY_H, NIGHT_H = frozenset(range(11, 17)), frozenset({22, 23, 0, 1, 2, 3, 4, 5})
K, RADIUS_KM, COLOC_KM = 4, 12.0, 0.5  # Delhi's; a region file (src/regions/) can set its own
RECENT_DAYS = 7
PHYS_FLAG, PHYS_WATCH = 0.05, 0.01
Z_FLAG, Z_WATCH = 3.0, 2.0
NCR = ("Noida", "Ghaziabad", "Gurugram", "Faridabad", "Bahadurgarh", "Manesar")
RANK = {"nodata": -1, "ok": 0, "watch": 1, "flag": 2}
SILENT_HOURS = 3  # no PM reading in the last 3 hours: the monitor isn't judged, its neighbours are shown instead
# CPCB National Air Quality Index (CPCB, "National Air Quality Index", Control of Urban Pollution Series
# CUPS/82/2014-15): the top of each band for the 24-hour average, in µg/m³. The AQI is the worst sub-index,
# and a 24-hour average needs at least 16 hours of data.
BANDS = ("Good", "Satisfactory", "Moderate", "Poor", "Very poor", "Severe")
BAND_TOP = {"pm25": (30, 60, 90, 120, 250), "pm10": (50, 100, 250, 350, 430)}
MIN_HOURS_24H = 16


# ---------- small helpers ----------

def km(a, b):
    p = math.pi / 180
    h = (math.sin((b[0] - a[0]) * p / 2) ** 2
         + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin((b[1] - a[1]) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(h))


def med(xs, need=1):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if len(xs) >= need else None


def robust_sd(xs):
    m = statistics.median(xs)
    return 1.4826 * statistics.median([abs(x - m) for x in xs])


def level(z):
    if z is None:
        return "nodata"
    return "flag" if abs(z) >= Z_FLAG else "watch" if abs(z) >= Z_WATCH else "ok"


def pct(log_gap):
    return (math.exp(log_gap) - 1) * 100


def updown(p):
    return "about the same" if abs(p) < 0.5 else f"{abs(p):.0f}% {'higher' if p > 0 else 'lower'}"


def last_value(series, hours=3):
    v = next((x for x in reversed(series[-hours:]) if x is not None), None)
    return None if v is None else round(v, 2)


def mean_24h(series):
    xs = [x for x in series[-24:] if x is not None]
    return statistics.fmean(xs) if len(xs) >= MIN_HOURS_24H else None


def band(pm25, pm10):
    """CPCB AQI band of 24-hour PM2.5 and PM10 averages: the worse of the two, None if neither is known."""
    worst = None
    for p, v in (("pm25", pm25), ("pm10", pm10)):
        if v is not None:
            i = next((i for i, top in enumerate(BAND_TOP[p]) if v <= top), len(BANDS) - 1)
            worst = i if worst is None else max(worst, i)
    return None if worst is None else BANDS[worst]


def iso(key):
    return f"{key}:00:00+05:30"


def last_reading(raw, keys):
    """IST hour key of the newest PM2.5 or PM10 value the monitor sent (stuck or not), None if none in the window."""
    pm = [raw.get(p, {}) for p in ("pm10", "pm25")]
    return next((k for k in reversed(keys) if any(s.get(k) is not None for s in pm)), None)


def hour_keys(now, days):
    return [(now - dt.timedelta(hours=n)).strftime("%Y-%m-%dT%H") for n in range(days * 24 - 1, -1, -1)]


# ---------- per-station series ----------

def prepare(raw, keys):
    """Aligned series per param, plus a per-hour physics verdict (True = fails, False = passes, None = no PM data)."""
    clean, bad = {}, [False] * len(keys)
    for p in PARAMS:
        src = raw.get(p, {})
        vals = [src.get(k) for k in keys]
        lo, hi = RANGE[p]
        for i, v in enumerate(vals):
            if v is not None and not lo <= v <= hi:
                vals[i] = None
                if p in ("pm10", "pm25"):
                    bad[i] = True
        if p in STUCK_PARAMS:
            i = 0
            while i < len(vals):
                j = i
                while j + 1 < len(vals) and vals[i] is not None and vals[j + 1] == vals[i]:
                    j += 1
                if vals[i] is not None and j - i + 1 >= 3:
                    for n in range(i, j + 1):
                        vals[n] = None
                        if p in ("pm10", "pm25"):
                            bad[n] = True
                i = j + 1
        clean[p] = vals
    pm10_raw, pm25_raw = raw.get("pm10", {}), raw.get("pm25", {})
    physics = []
    for i, k in enumerate(keys):
        a, b = pm10_raw.get(k), pm25_raw.get(k)
        if a is None and b is None:
            physics.append(None)
        else:
            physics.append(bad[i] or (a is not None and b is not None and b > 1.05 * a))
    return clean, physics


def neighbours_of(st, stations, has_data, cfg=None):
    nb = (cfg or {}).get("neighbours", {})
    k, radius, coloc = nb.get("k", K), nb.get("radius_km", RADIUS_KM), nb.get("colocated_km", COLOC_KM)
    d = sorted((km((st["lat"], st["lon"]), (o["lat"], o["lon"])), o["id"]) for o in stations if o["id"] != st["id"])
    return [i for dist, i in d if coloc <= dist <= radius and has_data[i]][:k]


def gaps(me, refs):
    out = {}
    for p in PARAMS:
        g = []
        for i, v in enumerate(me[p]):
            r = med([s[p][i] for s in refs], need=2)
            if v is None or r is None:
                g.append(None)
            elif p in LOG_PARAMS:
                g.append(math.log(v / r))
            else:
                g.append(v - r)
        out[p] = g
    return out


def daily(keys, gap, physics):
    """Per IST day: median daytime gap minus median night gap (>= 4 hours each), and the physics fail share."""
    days = {}
    for i, k in enumerate(keys):
        days.setdefault(k[:10], []).append((int(k[11:13]), i))
    rows = []
    for date, hrs in days.items():
        row = {"date": date}
        for p in PARAMS:
            day = [gap[p][i] for h, i in hrs if h in DAY_H and gap[p][i] is not None]
            night = [gap[p][i] for h, i in hrs if h in NIGHT_H and gap[p][i] is not None]
            row[f"d_{p}"] = (statistics.median(day) - statistics.median(night)) if len(day) >= 4 and len(night) >= 4 else None
            row[f"night_{p}"] = statistics.median(night) if len(night) >= 4 else None
        ph = [physics[i] for _, i in hrs if physics[i] is not None]
        row["physics_fail_pct"] = round(100 * sum(ph) / len(ph), 1) if ph else None
        rows.append(row)
    return rows


def profile(keys, gap, last_n_hours=None):
    sl = slice(-last_n_hours, None) if last_n_hours else slice(None)
    ks, out = keys[sl], {}
    for p in PARAMS:
        g = gap[p][sl]
        by_h = [[] for _ in range(24)]
        for k, v in zip(ks, g, strict=False):
            if v is not None:
                by_h[int(k[11:13])].append(v)
        out[p] = [round(statistics.median(v), 3) if len(v) >= 3 else None for v in by_h]
    return out


# ---------- the three checks ----------

def physics_check(physics):
    recent = [x for x in physics[-RECENT_DAYS * 24:] if x is not None]
    if len(recent) < 24:
        return {"status": "nodata", "detail": "Fewer than 24 hours of PM data in the last 7 days."}
    share = sum(recent) / len(recent)
    status = "flag" if share > PHYS_FLAG else "watch" if share > PHYS_WATCH else "ok"
    return {"status": status, "fail_pct": round(100 * share, 1),
            "detail": f"{100 * share:.1f}% of the last 7 days' hours report impossible values "
                      "(PM2.5 above PM10, out of range, or a stuck sensor)."}


def history_check(rows):
    best = None
    for p, unit in (("pm10", "log"), ("relativehumidity", "pts")):
        vals = [r[f"d_{p}"] for r in rows]
        recent = [v for v in vals[-RECENT_DAYS:] if v is not None]
        prior = [v for v in vals[:-RECENT_DAYS] if v is not None]
        if len(recent) < 4 or len(prior) < 10:
            continue
        shift = statistics.median(recent) - statistics.median(prior)
        sd = max(robust_sd(prior), 0.02 if unit == "log" else 1.0)
        z = shift / sd
        if best is None or abs(z) > abs(best[1]):
            best = (p, z, shift)
    if best is None:
        return {"status": "nodata", "detail": "Not enough days to compare against its own history."}
    p, z, shift = best
    if p == "pm10":
        text = f"Its daytime PM10, against its neighbours, reads {updown(pct(shift))} than over its previous 3 weeks."
    else:
        text = (f"Its daytime humidity, against its neighbours, reads {abs(shift):.1f} pts "
                f"{'higher' if shift > 0 else 'lower'} than over its previous 3 weeks.")
    return {"status": level(z), "z": round(z, 2), "param": p, "detail": text}


def neighbour_checks(recent, exclude=frozenset()):
    """recent: {id: (median d_pm10, median night pm10 gap)} over the last 7 days. Robust z of the mixing-corrected
    residual. The city line and spread come from stations not in `exclude` (suspects from the first pass)."""
    pts = [(sid, d, n) for sid, (d, n) in recent.items() if d is not None and n is not None]
    out = {sid: {"status": "nodata", "detail": "Not enough recent data from this station or its neighbours."} for sid in recent}
    base = [x for x in pts if x[0] not in exclude]
    if len(base) < 8:
        return out
    # Theil-Sen: one odd station can't tilt the city-wide line the way it would a least-squares fit
    slopes = [(base[j][1] - base[i][1]) / (base[j][2] - base[i][2])
              for i in range(len(base)) for j in range(i + 1, len(base)) if base[j][2] != base[i][2]]
    b = statistics.median(slopes) if slopes else 0.0
    a = statistics.median([d - b * n for _, d, n in base])
    resid = {sid: d - (a + b * n) for sid, d, n in pts}
    base_resid = [resid[sid] for sid, _, _ in base]
    m, sd = statistics.median(base_resid), max(robust_sd(base_resid), 0.02)
    for sid, d, n in pts:
        z = (resid[sid] - m) / sd
        out[sid] = {"status": level(z), "z": round(z, 2),
                    "detail": f"Against its neighbours, its daytime PM10 reads {updown(pct(d))} than at night "
                              f"({updown(pct(a + b * n))} is typical for a station like it)."}
    return out


# ---------- top level ----------

def score(hourly, stations, now, days=28, region=None):
    """Two passes: stations flagged in the first are left out of everyone else's reference in the second,
    so one misbehaving station can't drag its neighbours' gaps with it. `region` is a src/regions/ config
    (neighbour radius, area names); None means Delhi's defaults."""
    keys = hour_keys(now, days)
    prepared = {s["id"]: prepare(hourly.get(str(s["id"]), {}), keys) for s in stations}
    has_data = {sid: any(v is not None for v in c["pm10"]) for sid, (c, _) in prepared.items()}
    first = _run(keys, stations, prepared, has_data, exclude=set(), cfg=region)
    suspects = {sid for sid, (checks, _) in first.items()
                if "flag" in (checks["neighbours"]["status"], checks["history"]["status"])}
    final = _run(keys, stations, prepared, has_data, exclude=suspects, cfg=region) if suspects else first
    last = {s["id"]: last_reading(hourly.get(str(s["id"]), {}), keys) for s in stations}
    return _assemble(keys, now, stations, prepared, final, last, region)


def _run(keys, stations, prepared, has_data, exclude, cfg=None):
    recent, rows_by = {}, {}
    usable = {sid: ok and sid not in exclude for sid, ok in has_data.items()}
    for s in stations:
        clean, physics = prepared[s["id"]]
        nb = neighbours_of(s, stations, usable, cfg)
        gap = gaps(clean, [prepared[i][0] for i in nb]) if len(nb) >= 2 else {p: [None] * len(keys) for p in PARAMS}
        rows = daily(keys, gap, physics)
        rows_by[s["id"]] = (nb, gap, rows, physics, clean)
        last = rows[-RECENT_DAYS:]
        recent[s["id"]] = (med([r["d_pm10"] for r in last], need=4), med([r["night_pm10"] for r in last], need=4))
    nchecks = neighbour_checks(recent, exclude)
    return {sid: ({"physics": physics_check(prepared[sid][1]), "neighbours": nchecks[sid], "history": history_check(rows)},
                  (nb, gap, rows)) for sid, (nb, gap, rows, _, _) in rows_by.items()}


def _assemble(keys, now, stations, prepared, result, last, cfg=None):
    areas = (cfg or {}).get("areas", {"core": "Delhi", "outer": "NCR", "outer_words": list(NCR)})
    out_stations, per_station = [], {}
    for s in stations:
        checks, (nb, gap, rows) = result[s["id"]]
        clean = prepared[s["id"]][0]
        ranks = [RANK[c["status"]] for c in checks.values()]
        status = max(ranks)
        latest = {p: last_value(clean[p]) for p in PARAMS}
        # what the stations around it read right now: the number to use when this one is in doubt
        around = {p: med([last_value(prepared[i][0][p]) for i in nb], need=2) for p in ("pm25", "pm10")}
        around_24h = {p: med([mean_24h(prepared[i][0][p]) for i in nb], need=2) for p in ("pm25", "pm10")}
        doc = {
            "id": s["id"], "name": s["name"], "lat": s["lat"], "lon": s["lon"],
            "operator": s.get("operator"),
            "region": areas["outer"] if any(w in s["name"] for w in areas["outer_words"]) else areas["core"],
            "status": next(k for k, v in RANK.items() if v == status), "checks": checks, "latest": latest,
            "neighbours_latest": {p: None if v is None else round(v, 2) for p, v in around.items()},
            "last_reading": last[s["id"]] and iso(last[s["id"]]),
            "band": band(mean_24h(clean["pm25"]), mean_24h(clean["pm10"])),
            "neighbours_band": band(around_24h["pm25"], around_24h["pm10"])}
        # a monitor that has gone quiet keeps its last checks in view but isn't judged on them
        if last[s["id"]] is None or last[s["id"]] < keys[-SILENT_HOURS]:
            doc["status"] = "nodata"
            if last[s["id"]] is None:
                doc["detail"] = "No reading in the last 4 weeks."
            else:
                t = dt.datetime.strptime(last[s["id"]], "%Y-%m-%dT%H")
                doc["detail"] = f"No reading since {t:%H}:00 on {t.day} {t:%b}."
        out_stations.append(doc)
        # Last 48 h of PM2.5 for this station and each neighbour, for the evidence chart.
        recent_keys = keys[-48:]
        nb_pm25 = {str(nid): [round(v, 2) if v is not None else None for v in prepared[nid][0]["pm25"][-48:]] for nid in nb}
        per_station[s["id"]] = {
            "id": s["id"], "name": s["name"], "neighbours": nb,
            "hour_profile": profile(keys, gap), "hour_profile_7d": profile(keys, gap, RECENT_DAYS * 24),
            "daily": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if not k.startswith("night_")}
                      for r in rows],
            "recent_48h": {
                "hours": recent_keys,
                "pm25": [round(v, 2) if v is not None else None for v in clean["pm25"][-48:]],
                "neighbours_pm25": nb_pm25,
            }}
    latest_json = {
        "generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).isoformat(timespec="seconds"),
        "data_through": iso(now.strftime("%Y-%m-%dT%H")),
        "stations": out_stations}
    if cfg:  # which city this is, for a site that serves more than one
        latest_json["region"] = {k: cfg[k] for k in ("id", "name", "label", "map") if k in cfg}
    return latest_json, per_station


CSV_COLUMNS = [
    "id", "name", "operator", "lat", "lon",
    "status",
    "physics_status", "physics_detail",
    "neighbours_status", "neighbours_detail",
    "history_status", "history_detail",
    "pm25", "pm10", "no2", "co", "relativehumidity",
    "neighbours_pm25", "neighbours_pm10",
    "last_reading", "band", "neighbours_band",
    "data_through",
]


def to_csv(latest_json):
    """Return latest.json as a UTF-8 CSV string, one row per station."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    data_through = latest_json.get("data_through", "")
    for s in latest_json["stations"]:
        row = {
            "id": s["id"], "name": s["name"], "operator": s.get("operator", ""),
            "lat": s["lat"], "lon": s["lon"],
            "status": s["status"],
            "physics_status": s["checks"]["physics"]["status"],
            "physics_detail": s["checks"]["physics"].get("detail", ""),
            "neighbours_status": s["checks"]["neighbours"]["status"],
            "neighbours_detail": s["checks"]["neighbours"].get("detail", ""),
            "history_status": s["checks"]["history"]["status"],
            "history_detail": s["checks"]["history"].get("detail", ""),
            "pm25": s["latest"].get("pm25"), "pm10": s["latest"].get("pm10"),
            "no2": s["latest"].get("no2"), "co": s["latest"].get("co"),
            "relativehumidity": s["latest"].get("relativehumidity"),
            "neighbours_pm25": s.get("neighbours_latest", {}).get("pm25"),
            "neighbours_pm10": s.get("neighbours_latest", {}).get("pm10"),
            "last_reading": s.get("last_reading"), "band": s.get("band"), "neighbours_band": s.get("neighbours_band"),
            "data_through": data_through,
        }
        w.writerow(row)
    return buf.getvalue()


def write(out_dir, latest_json, per_station):
    os.makedirs(os.path.join(out_dir, "stations"), exist_ok=True)
    with open(os.path.join(out_dir, "latest.json"), "w") as f:
        json.dump(latest_json, f, separators=(",", ":"))
    with open(os.path.join(out_dir, "latest.csv"), "w", encoding="utf-8", newline="") as f:
        f.write(to_csv(latest_json))
    for sid, doc in per_station.items():
        with open(os.path.join(out_dir, "stations", f"{sid}.json"), "w") as f:
            json.dump(doc, f, separators=(",", ":"))


def main():
    import backfill
    ap = argparse.ArgumentParser()
    ap.add_argument("hourly")
    ap.add_argument("out")
    ap.add_argument("--now", help="last hour to score, IST, e.g. 2025-11-30T23 (default: latest hour in the data)")
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--region", default=backfill.DEFAULT_REGION, help="a file in src/regions/ (default: delhi, or $REGION)")
    a = ap.parse_args()
    hourly = json.load(open(a.hourly))
    last = a.now or max(k for st in hourly.values() for s in st.values() for k in s)
    cfg = backfill.region(a.region)
    latest_json, per_station = score(hourly, backfill.stations(region_name=a.region),
                                     dt.datetime.strptime(last, "%Y-%m-%dT%H"), a.days, region=cfg)
    write(a.out, latest_json, per_station)
    counts = {}
    for s in latest_json["stations"]:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    print(f"scored {len(latest_json['stations'])} stations through {last}: {counts} -> {a.out}")


if __name__ == "__main__":
    main()
