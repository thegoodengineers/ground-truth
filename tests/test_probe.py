"""The uptime probe: a healthy site, a broken page, a missing data file, and the metrics it publishes."""
import datetime as dt
import io
import json
import os
import sys
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import probe  # noqa: E402

NOW = dt.datetime(2026, 10, 11, 5, 0, tzinfo=dt.timezone.utc)
LATEST = {"generated_at": "2026-10-11T09:30:00+05:30", "stations": [{"id": 235}]}


class Resp(io.BytesIO):
    def __init__(self, body, status=200):
        super().__init__(body)
        self.status = status


def opener(pages):
    def open_(req, timeout=None):
        body = pages[req.full_url]
        if isinstance(body, Exception):
            raise body
        return Resp(body if isinstance(body, bytes) else json.dumps(body).encode())
    return open_


def test_healthy_site_reports_up_latency_and_run_age():
    ticks = iter([0.0, 0.25])
    r = probe.check("https://x/", opener({"https://x/": b"<!doctype html><html>", "https://x/data/latest.json": LATEST}),
                    clock=lambda: next(ticks), now=NOW)
    assert r == {"up": True, "latency_ms": 250.0, "run_age_h": 1.0, "error": None}
    m = {d["MetricName"]: d["Value"] for d in probe.metrics(r, "gt")}
    assert m == {"SiteUp": 1.0, "SiteLatencyMs": 250.0, "RunAgeHours": 1.0}


def test_a_page_that_is_not_html_or_a_failed_data_file_is_down():
    r = probe.check("https://x", opener({"https://x/": b'{"message":"Forbidden"}'}), now=NOW)
    assert r["up"] is False and r["error"] == "page 200"
    err = urllib.error.HTTPError("https://x/data/latest.json", 403, "Forbidden", None, None)
    r = probe.check("https://x", opener({"https://x/": b"<html>", "https://x/data/latest.json": err}), now=NOW)
    assert r["up"] is False and "403" in r["error"]
    m = {d["MetricName"]: d["Value"] for d in probe.metrics(r, "gt")}
    assert m["SiteUp"] == 0.0 and "RunAgeHours" not in m
