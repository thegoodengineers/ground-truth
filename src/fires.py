"""Farm fires from NASA FIRMS: the last 24 h of VIIRS fire points north-west of the city, as data/fires.json.

In October and November a city-wide jump is often stubble smoke, not a broken monitor. The hourly run fetches
the last day of VIIRS (Suomi NPP, near-real-time) detections for the region's fire box from the FIRMS area API,
with the key in SSM next to the OpenAQ key (/ground-truth/firms-key; without it the step is skipped), and writes:

    {"fetched_at": "...", "count": 312, "box": [73.5, 27.5, 79.5, 32.5], "centre": [28.62, 77.2],
     "bearing_deg": 318, "direction": "north-west", "distance_km": 210, "high_confidence": 201,
     "points": [[30.9, 75.8, 341.2, "2026-10-08", "0730"], ...],
     "line": "312 farm fires in the last 24 h, north-west of the city.", "source": "NASA FIRMS, VIIRS SNPP NRT"}

`points` is [lat, lon, brightness, date, time] for up to MAX_POINTS fires (the brightest first), enough for the
3D scene to put embers on the horizon in the right direction.
"""
import csv, datetime as dt, io, math, urllib.request

API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
SOURCE = "VIIRS_SNPP_NRT"
KEY = "data/fires.json"
MAX_POINTS = 400
DEFAULT_BOX = [73.5, 27.5, 79.5, 32.5]  # west, south, east, north: Punjab, Haryana and west UP
STUB = {"count": None, "line": None, "points": [], "source": "NASA FIRMS, VIIRS SNPP NRT",
        "note": "no FIRMS key in SSM: put one at /ground-truth/firms-key to turn the fire layer on"}
COMPASS_WORDS = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"]


def bearing(a, b):
    """Initial bearing from a to b in degrees, (lat, lon) pairs."""
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def km(a, b):
    p = math.pi / 180
    h = (math.sin((b[0] - a[0]) * p / 2) ** 2 + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin((b[1] - a[1]) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(h))


def direction(deg):
    return COMPASS_WORDS[int(((deg % 360) + 22.5) // 45) % 8]


def parse(text):
    """FIRMS CSV -> [(lat, lon, brightness, date, time, confidence)], the brightest first."""
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        try:
            rows.append((float(r["latitude"]), float(r["longitude"]), float(r.get("bright_ti4") or r.get("brightness") or 0),
                         r.get("acq_date", ""), r.get("acq_time", ""), (r.get("confidence") or "").lower()[:1]))
        except (KeyError, ValueError):
            continue
    rows.sort(key=lambda x: -x[2])
    return rows


def line(count, where):
    if count == 0:
        return "No farm fires seen in the last 24 h to the north-west."
    return f"{count} farm fire{'s' if count != 1 else ''} in the last 24 h, {where} of the city."


def summarise(rows, centre, box, now=None):
    count = len(rows)
    doc = {"fetched_at": (now or dt.datetime.now(dt.timezone.utc)).isoformat(timespec="seconds"), "count": count,
           "box": box, "centre": centre, "bearing_deg": None, "direction": None, "distance_km": None,
           "high_confidence": sum(1 for r in rows if r[5] == "h"), "points": [list(r[:5]) for r in rows[:MAX_POINTS]],
           "line": None, "source": "NASA FIRMS, VIIRS SNPP NRT"}
    if count:
        mid = (sum(r[0] for r in rows) / count, sum(r[1] for r in rows) / count)
        doc["bearing_deg"] = round(bearing(centre, mid))
        doc["direction"] = direction(doc["bearing_deg"])
        doc["distance_km"] = round(km(centre, mid))
    doc["line"] = line(count, doc["direction"] or "north-west")
    return doc


def fetch(key, box, opener=urllib.request.urlopen):
    url = f"{API}/{key}/{SOURCE}/{','.join(str(v) for v in box)}/1"  # the last 1 day
    with opener(urllib.request.Request(url, headers={"Accept": "text/csv"}), timeout=30) as r:
        return parse(r.read().decode("utf-8"))


def publish(store, region, key, opener=urllib.request.urlopen, now=None):
    """Fetch the region's fire box and write data/fires.json; returns the doc, or the error as a string.
    No key: writes a stub with no count (so the site finds a file and shows no fire line) and returns "no FIRMS key"."""
    if not key:
        store.put_json(KEY, STUB, max_age=300)
        return "no FIRMS key"
    try:
        box = region.get("fires", {}).get("box", DEFAULT_BOX)
        rows = fetch(key, box, opener)
        doc = summarise(rows, list(region["map"]["centre"]), box, now)
        store.put_json(KEY, doc, max_age=300)
        return doc
    except Exception as e:  # context, never a reason for the run to fail
        return f"{type(e).__name__}: {e}"
