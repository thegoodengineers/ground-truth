"""A day-by-day history of every monitor's answer: data/history.json, kept up by the hourly run.

Each day of the last DAYS days is scored as the live site would have scored it at SCORE_HOUR IST (when the 11:00-17:00
window is complete), exactly as docs/VALIDATION.md does for Oct-Nov 2025, and the four statuses per monitor are kept:

    {"generated_at": "...", "score_hour": 17, "days": ["2026-09-12", ..., "2026-10-09"],
     "stations": {"235": [{"d": "2026-09-12", "s": "ok", "c": "ooo"}, ...]},     # s = status, c = physics/neighbours/history
     "totals": [{"d": "2026-09-12", "ok": 36, "watch": 7, "flag": 5, "nodata": 4}, ...],
     "changes": [{"id": 7005, "name": "Loni", "from": "ok", "to": "watch", "day": "2026-10-09"}, ...],  # newest day vs the one before
     "names": {"235": "Anand Vihar, New Delhi"}}

data/changes.xml is the same month of changes as an Atom feed (every pair of days, newest first), for a reporter's reader.

`c` packs the three check statuses as one letter each: o = ok, w = watch, f = flag, n = no data. The file is incremental:
a run scores only the days it doesn't have yet, newest first, inside a time budget, so the first run builds the
month in a minute and every later run adds one day.
"""
import datetime as dt, time
from xml.sax.saxutils import escape

import scorer

KEY = "data/history.json"
FEED_KEY = "data/changes.xml"
DAYS = 28
SCORE_HOUR = 17
BUDGET_S = 100
LETTER = {"ok": "o", "watch": "w", "flag": "f", "nodata": "n"}


def complete_days(last_key, days=DAYS):
    """The dates (newest first) whose SCORE_HOUR hour is at or before `last_key` (an IST hour key)."""
    last = dt.datetime.strptime(last_key, "%Y-%m-%dT%H")
    end = last.date() if last.hour >= SCORE_HOUR else last.date() - dt.timedelta(days=1)
    return [(end - dt.timedelta(days=i)).isoformat() for i in range(days)]


def score_day(hourly, stations, day, region=None):
    at = dt.datetime.fromisoformat(day).replace(hour=SCORE_HOUR)
    latest, _ = scorer.score(hourly, stations, at, region=region)
    checks = ("physics", "neighbours", "history")
    return {s["id"]: {"d": day, "s": s["status"], "c": "".join(LETTER[s["checks"][k]["status"]] for k in checks)}
            for s in latest["stations"]}


LABEL = {"ok": "agrees with neighbours", "watch": "worth a look", "flag": "doesn't add up", "nodata": "not enough data"}
NOTE = "A flag means the numbers don't add up, not that anyone tampered with the station."


def atom(doc, site_url, title="Ground Truth: monitors that changed their answer"):
    """The changes as an Atom feed a reporter can subscribe to: one entry per monitor per day it changed, newest first,
    over every pair of consecutive days in the document (not only the last one)."""
    site = site_url.rstrip("/") + "/"
    days = doc.get("days", [])
    entries = []
    for sid, rows in doc.get("stations", {}).items():
        by_day = {r["d"]: r["s"] for r in rows}
        name = doc.get("names", {}).get(sid) or f"monitor {sid}"
        for a, b in zip(days, days[1:], strict=False):
            if a in by_day and b in by_day and by_day[a] != by_day[b]:
                entries.append((b, sid, name, by_day[a], by_day[b]))
    entries.sort(key=lambda e: (e[0], e[2]), reverse=True)
    updated = doc.get("generated_at") or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    self_url = escape(site + FEED_KEY)
    out = ['<?xml version="1.0" encoding="utf-8"?>', '<feed xmlns="http://www.w3.org/2005/Atom">',
           f"  <title>{escape(title)}</title>", f'  <link href="{escape(site)}"/>', f'  <link rel="self" href="{self_url}"/>',
           f"  <id>{self_url}</id>", f"  <updated>{escape(updated)}</updated>",
           "  <subtitle>Every day at 17:00 IST each monitor in Delhi and the NCR is checked against its neighbours, its own past "
           "and physics; this feed lists the monitors whose answer changed from the day before.</subtitle>"]
    for day, sid, name, frm, to in entries[:200]:
        summary = f"{name}: {LABEL[frm]} → {LABEL[to]} ({day})"
        out += ["  <entry>", f"    <title>{escape(summary)}</title>", f'    <link href="{escape(site)}#{sid}/history"/>',
                f"    <id>{escape(site)}#{sid}/{day}</id>", f"    <updated>{day}T17:00:00+05:30</updated>",
                f"    <summary>{escape(summary)}. {NOTE}</summary>",
                "  </entry>"]
    out.append("</feed>")
    return "\n".join(out) + "\n"


def update(store, hourly, stations, last_key, region=None, budget_s=BUDGET_S, now=None, clock=time.monotonic, site_url=None):
    """Bring data/history.json up to `last_key`, and the Atom feed of changes when `site_url` is known.
    Returns {"days": n, "scored": how many days this run scored}."""
    wanted = complete_days(last_key)
    doc = store.get_json(KEY) or {}
    have = {}  # day -> {sid: row}
    for sid, rows in (doc.get("stations") or {}).items():
        for r in rows:
            have.setdefault(r["d"], {})[int(sid)] = r
    ids = {s["id"] for s in stations}
    t0, scored = clock(), 0
    for day in wanted:  # newest first, so a short budget still gives the days people look at
        if day in have and ids <= set(have[day]):
            continue
        if clock() - t0 > budget_s:
            break
        have[day] = score_day(hourly, stations, day, region)
        scored += 1
    days = sorted(d for d in wanted if d in have)
    out_stations = {str(s["id"]): [have[d][s["id"]] for d in days if s["id"] in have[d]] for s in stations}
    totals = []
    for d in days:
        t = {"d": d, "ok": 0, "watch": 0, "flag": 0, "nodata": 0}
        for s in stations:
            if s["id"] in have[d]:
                t[have[d][s["id"]]["s"]] += 1
        totals.append(t)
    changes = []
    if len(days) >= 2:
        a, b = have[days[-2]], have[days[-1]]
        for s in stations:
            if s["id"] in a and s["id"] in b and a[s["id"]]["s"] != b[s["id"]]["s"]:
                changes.append({"id": s["id"], "name": s["name"], "from": a[s["id"]]["s"], "to": b[s["id"]]["s"], "day": days[-1]})
    changes.sort(key=lambda c: (-scorer.RANK[c["to"]], c["name"]))
    doc = {
        "generated_at": (now or dt.datetime.now(dt.timezone.utc)).isoformat(timespec="seconds"),
        "score_hour": SCORE_HOUR, "days": days, "stations": out_stations, "totals": totals, "changes": changes,
        "names": {str(s["id"]): s["name"] for s in stations},
    }
    store.put_json(KEY, doc, max_age=300)
    if site_url:
        store.put_text(FEED_KEY, atom(doc, site_url), content_type="application/atom+xml; charset=utf-8", max_age=300)
    return {"days": len(days), "scored": scored}
