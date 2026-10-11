"""Every 15 minutes, load the live site the way a visitor does: the page, then data/latest.json. Publishes SiteUp
(1 or 0), SiteLatencyMs and RunAgeHours (how long since the hourly run last wrote latest.json) to CloudWatch, where an
alarm emails when the site is down. The other alarms watch the system from inside; this one stands where a visitor
stands, so it also catches a broken function URL, a bad deploy or an expired permission."""
import datetime as dt
import json
import os
import time
import urllib.request

UTC = dt.timezone.utc


def check(site_url, opener=urllib.request.urlopen, clock=time.monotonic, now=None):
    """{"up": bool, "latency_ms": float, "run_age_h": float or None, "error": str or None} for one visit."""
    now = now or dt.datetime.now(UTC)
    base = site_url.rstrip("/") + "/"
    t0 = clock()
    try:
        with opener(urllib.request.Request(base, headers={"User-Agent": "ground-truth-probe"}), timeout=10) as r:
            page = r.read()
            if r.status != 200 or b"<html" not in page[:2000].lower():
                return {"up": False, "latency_ms": (clock() - t0) * 1000, "run_age_h": None, "error": f"page {r.status}"}
        latency = (clock() - t0) * 1000
        with opener(urllib.request.Request(base + "data/latest.json", headers={"User-Agent": "ground-truth-probe"}),
                    timeout=10) as r:
            latest = json.loads(r.read())
        generated = dt.datetime.fromisoformat(latest["generated_at"])
        age = round((now - generated).total_seconds() / 3600, 2)
        return {"up": len(latest.get("stations", [])) > 0, "latency_ms": round(latency, 1), "run_age_h": age, "error": None}
    except Exception as e:  # any failure to load is the answer: the site is down for a visitor
        return {"up": False, "latency_ms": round((clock() - t0) * 1000, 1), "run_age_h": None, "error": repr(e)[:200]}


def metrics(result, stack):
    dims = [{"Name": "Stack", "Value": stack}]
    out = [{"MetricName": "SiteUp", "Value": 1.0 if result["up"] else 0.0, "Unit": "Count", "Dimensions": dims},
           {"MetricName": "SiteLatencyMs", "Value": result["latency_ms"], "Unit": "Milliseconds", "Dimensions": dims}]
    if result["run_age_h"] is not None:
        out.append({"MetricName": "RunAgeHours", "Value": result["run_age_h"], "Unit": "None", "Dimensions": dims})
    return out


def handler(event, context):
    import boto3  # in the Lambda runtime; not needed for tests
    result = check(os.environ["SITE_URL"])
    boto3.client("cloudwatch").put_metric_data(Namespace=os.environ.get("METRIC_NAMESPACE", "GroundTruth"),
                                               MetricData=metrics(result, os.environ.get("STACK_NAME", "ground-truth")))
    print(json.dumps(result))
    return result
