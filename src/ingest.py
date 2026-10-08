"""Hourly ingest Lambda: OpenAQ API -> rolling hourly cache in S3 -> scorer -> JSON for the site.

Each run:
1. Load the cache `data/raw/hourly.json` (seeded once from the public archive with backfill.py) and the
   sensor map `data/raw/sensors.json` (fetched from the API the first time a station is seen).
2. For every station and parameter, fetch raw readings from the last stored hour (minus 2 h, to pick up
   late data) up to now, and average them into IST hours exactly as the archive backfill does. The free key
   allows 60 requests/min, so calls are paced. The stations with the oldest data go first, so whatever a run
   leaves over (call budget, API errors) is picked up first by the next one.
3. Trim the cache to 29 days and save it, run the scorer, and write `data/stations/<id>.json` + `data/latest.json`,
   unless the result is worse than what is already published (`why_not_publish`); then the old files stay.

Environment: SITE_BUCKET (required), OPENAQ_KEY_PARAM (default /ground-truth/openaq-key), MAX_CALLS (default 300).
"""
import datetime as dt, json, os, statistics, time, urllib.error, urllib.parse, urllib.request

import backfill, scorer

API = "https://api.openaq.org/v3"
RAW_KEY, SENSORS_KEY = "data/raw/hourly.json", "data/raw/sensors.json"
KEEP_DAYS, LOOKBACK_HOURS, REFETCH_HOURS = 29, 6 * 24, 2
TRIES, MAX_FAILS_IN_A_ROW = 3, 5
IST = backfill.IST
UTC = dt.timezone.utc


def ist_key(t):
    return t.astimezone(IST).strftime("%Y-%m-%dT%H")


def key_time(k):
    return dt.datetime.strptime(k, "%Y-%m-%dT%H").replace(tzinfo=IST)


class OpenAQ:
    """Minimal v3 client. Paced below 60 requests/min. 429, 5xx and network errors are tried up to 3 times,
    waiting as long as Retry-After asks (at most 60 s). Other HTTP errors, 401/403 (a wrong key) included, raise."""

    def __init__(self, key, pace=1.1, opener=urllib.request.urlopen, sleep=time.sleep):
        self.key, self.pace, self.opener, self.sleep = key, pace, opener, sleep
        self.calls = self.retries = 0

    def get(self, path, **params):
        url = f"{API}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
        req = urllib.request.Request(url, headers={"X-API-Key": self.key, "Accept": "application/json"})
        for attempt in range(TRIES):
            self.sleep(self.pace)
            self.calls += 1
            try:
                with self.opener(req, timeout=30) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == TRIES - 1:
                    raise
                after = str((e.headers or {}).get("Retry-After", ""))
                wait = int(after) if after.isdigit() else 5 * 2 ** attempt
            except urllib.error.URLError:
                if attempt == TRIES - 1:
                    raise
                wait = 5 * 2 ** attempt
            self.retries += 1
            self.sleep(min(60, wait))

    def sensors(self, location_id):
        """{param: sensor_id} for the parameters we score."""
        res = self.get(f"/locations/{location_id}")["results"]
        out = {}
        for s in (res[0].get("sensors", []) if res else []):
            name = s.get("parameter", {}).get("name")
            if name in backfill.PARAMS:
                out[name] = s["id"]
        return out

    def hours(self, param, sensor_id, since):
        """{IST hour key: mean} built from raw readings since `since` (UTC). The API's own /hours endpoint
        averages over UTC hours, which are half an hour off IST hours; grouping the raw 15-min readings with
        backfill.to_hourly keeps live hours identical to the archive's."""
        rows, page = [], 1
        while True:
            body = self.get(f"/sensors/{sensor_id}/measurements", datetime_from=since.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            limit=1000, page=page)
            for r in body.get("results", []):
                end = r.get("period", {}).get("datetimeTo", {}).get("utc")
                if end is not None and r.get("value") is not None:
                    rows.append({"parameter": param, "value": r["value"], "datetime": end.replace("Z", "+00:00")})
            if len(body.get("results", [])) < 1000:
                break
            page += 1
        first = ist_key(since)
        return {k: v for k, v in backfill.to_hourly(rows).get(param, {}).items() if k >= first}


def trim(hourly, now):
    cutoff = ist_key(now - dt.timedelta(days=KEEP_DAYS))
    for st in hourly.values():
        for p in list(st):
            st[p] = {k: v for k, v in st[p].items() if k >= cutoff}


def score_hour(hourly, n_stations):
    """Latest IST hour that at least half the stations reported PM for, so one early clock can't move 'now'."""
    count = {}
    for st in hourly.values():
        for k in set(st.get("pm10", {})) | set(st.get("pm25", {})):
            count[k] = count.get(k, 0) + 1
    good = [k for k, n in count.items() if n >= n_stations / 2]
    return max(good) if good else None


def stale_first(stations, hourly):
    """Stations ordered by their newest cached hour, oldest (or none) first; ties keep their order."""
    return sorted(stations, key=lambda st: max((max(v) for v in hourly.get(str(st["id"]), {}).values() if v), default=""))


def why_not_publish(new, old, n_stations):
    """None if `new` may replace the published `old` latest.json, else the reason to keep the old one."""
    through = dt.datetime.fromisoformat(new["data_through"])
    recent = (through - dt.timedelta(hours=scorer.SILENT_HOURS - 1)).isoformat()
    covered = sum((s.get("last_reading") or "") >= recent for s in new["stations"])
    if covered < n_stations / 2:
        return f"only {covered} of {n_stations} stations have a recent reading"
    if old and old.get("data_through", "") > new["data_through"]:
        return f"older than the published hour {old['data_through']}"
    return None


def run(store, api, stations, now, max_calls=300, key_param="/ground-truth/openaq-key"):
    hourly = store.get_json(RAW_KEY) or {}
    sensors = store.get_json(SENSORS_KEY) or {}
    log = {"new_hours": 0, "skipped": 0, "overlap_ratio": {}}
    ratios, stop, fails = {}, None, 0

    for st in stale_first(stations, hourly):
        sid = str(st["id"])
        if stop or api.calls >= max_calls:
            log["skipped"] += len(sensors.get(sid, {})) or 1
            continue
        try:
            if sid not in sensors:
                sensors[sid] = api.sensors(st["id"])
            for p, sensor_id in sensors[sid].items():
                if api.calls >= max_calls:
                    log["skipped"] += 1
                    continue
                have = hourly.setdefault(sid, {}).setdefault(p, {})
                since = key_time(max(have)) - dt.timedelta(hours=REFETCH_HOURS) if have else now - dt.timedelta(hours=LOOKBACK_HOURS)
                new = api.hours(p, sensor_id, since.astimezone(UTC))
                for k, v in new.items():
                    if k in have and have[k] > 0:
                        ratios.setdefault(p, []).append(v / have[k])
                    elif k not in have:
                        log["new_hours"] += 1
                    have[k] = v
            fails = 0
        except (OSError, ValueError) as e:  # HTTP and network errors, timeouts, bad JSON
            log["skipped"] += 1
            fails += 1
            if getattr(e, "code", None) in (401, 403):
                stop = f"OpenAQ rejected the API key (HTTP {e.code}): check the SSM parameter {key_param}"
            elif fails >= MAX_FAILS_IN_A_ROW:
                stop = f"OpenAQ unreachable: {fails} stations failed in a row, last error {e!r}"
    if stop:
        log["error"] = stop

    # API vs archive on overlapping hours: ~1.0 means same units and same hour labels
    log["overlap_ratio"] = {p: round(statistics.median(r), 3) for p, r in ratios.items() if r}
    log.update(api_calls=api.calls, retries=api.retries)
    trim(hourly, now)
    # the cache first: a crash after this leaves the results behind the cache, never ahead of it
    store.put_json(SENSORS_KEY, sensors)
    store.put_json(RAW_KEY, hourly)

    last = score_hour(hourly, len(stations))
    if last is None:
        log.update(scored=False, published=False, reason="no hour has PM data from half the stations")
        return log
    latest, per_station = scorer.score(hourly, stations, dt.datetime.strptime(last, "%Y-%m-%dT%H"))
    counts = {}
    for s in latest["stations"]:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    log.update(scored=True, data_through=last, statuses=counts)
    reason = why_not_publish(latest, store.get_json("data/latest.json"), len(stations))
    if reason:
        log.update(published=False, reason=reason)
        return log
    for sid, doc in per_station.items():
        store.put_json(f"data/stations/{sid}.json", doc, max_age=300)
    store.put_json("data/latest.json", latest, max_age=300)
    store.put_text("data/latest.csv", scorer.to_csv(latest), content_type="text/csv; charset=utf-8", max_age=300)
    log["published"] = True
    return log


class S3Store:
    def __init__(self, bucket, client):
        self.bucket, self.s3 = bucket, client

    def get_json(self, key):
        try:
            return json.load(self.s3.get_object(Bucket=self.bucket, Key=key)["Body"])
        except self.s3.exceptions.NoSuchKey:
            return None

    def put_json(self, key, obj, max_age=None):
        extra = {"CacheControl": f"public, max-age={max_age}"} if max_age else {}
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=json.dumps(obj, separators=(",", ":")).encode(),
                           ContentType="application/json", **extra)

    def put_text(self, key, text, content_type="text/plain", max_age=None):
        extra = {"CacheControl": f"public, max-age={max_age}"} if max_age else {}
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=text.encode("utf-8"),
                           ContentType=content_type, **extra)


def handler(event, context):
    import boto3  # in the Lambda runtime; not needed for tests
    param = os.environ.get("OPENAQ_KEY_PARAM", "/ground-truth/openaq-key")
    key = boto3.client("ssm").get_parameter(Name=param, WithDecryption=True)["Parameter"]["Value"]
    store = S3Store(os.environ["SITE_BUCKET"], boto3.client("s3"))
    log = run(store, OpenAQ(key), backfill.stations(), dt.datetime.now(UTC), int(os.environ.get("MAX_CALLS", "300")), param)
    print(json.dumps(log))
    return log
