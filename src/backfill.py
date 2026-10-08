"""Seed the hourly cache from the public OpenAQ archive (us-east-1, no key).

    python src/backfill.py OUT.json [--end YYYY-MM-DD] [--days 28] [--cache DIR]

Writes {station_id: {param: {"YYYY-MM-DDTHH": value}}} with IST hour keys, for the `days` days ending on
`end` (default: today, IST). The archive lags about 4 days; the hourly ingest fills the rest from the API.
Which files exist comes from the bucket listing. Every error is retried, 404 included: through a proxy S3
sometimes answers 404, or cuts a transfer short, for files that exist. Every gzip is checked before use.
"""
import argparse, csv, datetime as dt, gzip, io, json, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

BUCKET = "https://openaq-data-archive.s3.amazonaws.com"
PARAMS = ("pm10", "pm25", "no2", "co", "relativehumidity")
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
HERE = os.path.dirname(os.path.abspath(__file__))
MISSED = []


STATIONS_TSV = os.path.join(HERE, "stations.tsv")


def stations(path=STATIONS_TSV):
    out = []
    for line in open(path):
        if line.strip():
            parts = line.rstrip("\n").split("\t")
            i, name, lat, lon = parts[:4]
            operator = parts[4] if len(parts) > 4 else None
            out.append({"id": int(i), "name": name.rsplit(" - ", 1)[0].strip(),
                        "lat": float(lat), "lon": float(lon), "operator": operator})
    return out


def fetch(url, check_gzip=False):
    for attempt in range(8):
        try:
            raw = urllib.request.urlopen(url, timeout=60).read()
            if check_gzip:
                gzip.decompress(raw)
            return raw
        except Exception:
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"gave up on {url}")


def listed_days(sid, months):
    keys = []
    for y, m in months:
        xml = fetch(f"{BUCKET}/?list-type=2&prefix=records/csv.gz/locationid={sid}/year={y}/month={m:02d}/").decode()
        keys += re.findall(r"<Key>([^<]+)</Key>", xml)
    return keys


def day_rows(key, cache):
    path = os.path.join(cache, key.rsplit("/", 1)[1]) if cache else None
    raw = None
    if path and os.path.exists(path):
        try:
            raw = open(path, "rb").read()
            gzip.decompress(raw)
        except Exception:
            raw = None
    if raw is None:
        try:
            raw = fetch(f"{BUCKET}/{key}", check_gzip=True)
        except RuntimeError:
            MISSED.append(key)  # reported at the end; a rerun with --cache picks it up
            return []
        if path:
            with open(path, "wb") as f:
                f.write(raw)
    return list(csv.DictReader(io.StringIO(gzip.decompress(raw).decode("utf-8"))))


def hour_key(stamp):
    """A stamp marks the end of its 15-min interval, so 11:15..12:00 make up hour 11 (IST)."""
    t = dt.datetime.fromisoformat(stamp).astimezone(IST) - dt.timedelta(minutes=1)
    return t.strftime("%Y-%m-%dT%H")


def to_hourly(rows):
    """15-min rows -> {param: {hour: mean}}, needing >= 2 readings per hour. Units kept as published."""
    acc = {}
    for r in rows:
        p = r["parameter"]
        if p not in PARAMS:
            continue
        try:
            v = float(r["value"])
        except ValueError:
            continue
        acc.setdefault(p, {}).setdefault(hour_key(r["datetime"]), []).append(v)
    return {p: {h: round(sum(v) / len(v), 3) for h, v in hours.items() if len(v) >= 2} for p, hours in acc.items()}


def backfill(end, days, cache=None, station_list=None):
    station_list = station_list or stations()
    start = end - dt.timedelta(days=days - 1)
    # UTC file days straddle IST days, so read one extra day each side and trim by hour key afterwards
    lo, hi = start - dt.timedelta(days=1), end + dt.timedelta(days=1)
    months = sorted({(d.year, d.month) for d in (lo + dt.timedelta(n) for n in range((hi - lo).days + 1))})
    if cache:
        os.makedirs(cache, exist_ok=True)
    first, last = start.strftime("%Y-%m-%dT00"), end.strftime("%Y-%m-%dT23")

    def one(st):
        keys = [k for k in listed_days(st["id"], months) if lo.strftime("%Y%m%d") <= k[-15:-7] <= hi.strftime("%Y%m%d")]
        rows = [r for k in keys for r in day_rows(k, cache)]
        hourly = to_hourly(rows)
        return str(st["id"]), {p: {h: v for h, v in s.items() if first <= h <= last} for p, s in hourly.items()}

    with ThreadPoolExecutor(12) as ex:
        return dict(ex.map(one, station_list))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--end", default=dt.datetime.now(IST).date().isoformat())
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--cache")
    a = ap.parse_args()
    data = backfill(dt.date.fromisoformat(a.end), a.days, a.cache)
    with open(a.out, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    n = sum(len(s) for st in data.values() for s in st.values())
    print(f"{len(data)} stations, {n} station-param-hours -> {a.out}")
    if MISSED:
        print(f"{len(MISSED)} files failed after retries; rerun to fill them:", *MISSED[:5], sep="\n  ")
