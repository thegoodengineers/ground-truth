"""Weather context for city-wide changes: wind, mixing height and a plain sentence, as data/weather.json.

When every monitor moves at once the cause is usually the weather, not the monitors: calm air and a low
mixing (boundary) layer let pollution build up, wind and a high layer clear it. The hourly Lambda fetches the
current wind and the boundary-layer height for the region's centre from Open-Meteo (free, no key) and writes:

    {"fetched_at": "...", "time": "2026-10-09T03:30", "wind_kmh": 5.0, "wind_from_deg": 139, "wind_from": "SE",
     "boundary_layer_m": 420, "temperature_c": 25.3, "humidity_pct": 81, "line": "Calm air right now ...", "source": "Open-Meteo"}

`line` is what the site's hero says; the 3D dust drifts with `wind_from_deg` and `wind_kmh`.
"""
import datetime as dt, json, urllib.parse, urllib.request

API = "https://api.open-meteo.com/v1/forecast"
KEY = "data/weather.json"
CALM_KMH, BREEZY_KMH = 6.0, 15.0
LOW_LAYER_M = 500
COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
COMPASS_WORDS = {"N": "north", "NE": "north-east", "E": "east", "SE": "south-east", "S": "south", "SW": "south-west",
                 "W": "west", "NW": "north-west"}


def compass(deg):
    return COMPASS[int(((deg % 360) + 22.5) // 45) % 8]


def line(wind_kmh, wind_from_deg, layer_m, hour=None):
    """One sentence a visitor can act on. Never blames a monitor; this is about the air, not the sensors."""
    when = "tonight" if hour is not None and (hour >= 20 or hour < 6) else "right now"
    frm = COMPASS_WORDS[compass(wind_from_deg)] if wind_from_deg is not None else None
    low = layer_m is not None and layer_m < LOW_LAYER_M
    if wind_kmh is None:
        return None
    if wind_kmh < CALM_KMH:
        tail = " and the air is mixing only a few hundred metres up" if low else ""
        return f"Calm air {when} (wind {wind_kmh:.0f} km/h){tail}: pollution is building up across the city."
    if wind_kmh < BREEZY_KMH:
        return f"A light wind from the {frm} {when} ({wind_kmh:.0f} km/h): the air is moving a little, so readings drift together."
    return f"Wind from the {frm} at {wind_kmh:.0f} km/h {when}: the air is being cleared across the city, so every monitor falls together."


def fetch(lat, lon, opener=urllib.request.urlopen, now=None):
    """Current wind and the hour's boundary-layer height for (lat, lon), as the weather.json document."""
    q = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "wind_speed_unit": "kmh",
                                "current": "wind_speed_10m,wind_direction_10m,temperature_2m,relative_humidity_2m",
                                "hourly": "boundary_layer_height", "forecast_days": 1, "timezone": "Asia/Kolkata"})
    with opener(urllib.request.Request(f"{API}?{q}", headers={"Accept": "application/json"}), timeout=20) as r:
        body = json.load(r)
    cur = body.get("current", {})
    hours = body.get("hourly", {})
    layer = None
    if cur.get("time") and hours.get("time"):
        key = cur["time"][:13]
        for t, v in zip(hours["time"], hours.get("boundary_layer_height", []), strict=False):
            if t[:13] == key and v is not None:
                layer = round(v)
                break
    wind, deg = cur.get("wind_speed_10m"), cur.get("wind_direction_10m")
    hour = int(cur["time"][11:13]) if cur.get("time") else None
    return {
        "fetched_at": (now or dt.datetime.now(dt.timezone.utc)).isoformat(timespec="seconds"),
        "time": cur.get("time"),
        "wind_kmh": wind, "wind_from_deg": deg, "wind_from": compass(deg) if deg is not None else None,
        "boundary_layer_m": layer, "temperature_c": cur.get("temperature_2m"), "humidity_pct": cur.get("relative_humidity_2m"),
        "line": line(wind, deg, layer, hour),
        "source": "Open-Meteo",
    }


def publish(store, region, opener=urllib.request.urlopen, now=None):
    """Fetch for the region's map centre and write data/weather.json; returns the doc, or the error as a string."""
    try:
        lat, lon = region["map"]["centre"]
        doc = fetch(lat, lon, opener, now)
        store.put_json(KEY, doc, max_age=300)
        return doc
    except Exception as e:  # the weather is context, never a reason for the run to fail
        return f"{type(e).__name__}: {e}"
