"""Probe OpenAQ archive location ids for the monitors inside a bounding box (no API key): one day's file per id.

    python spike/find_region.py LAT_MIN LAT_MAX LON_MIN LON_MAX [--ids 1-12000] [--day 20251028] > out.tsv

Prints id, location name, lat, lon for every id whose file exists for that day and sits in the box. Ids of the
CPCB/state-board monitors India-wide are small (Delhi's run from 17 to 11607), so the default range covers them.
"""
import csv, gzip, io, sys, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://openaq-data-archive.s3.amazonaws.com/records/csv.gz"


def probe(i, day, box):
    url = f"{BASE}/locationid={i}/year={day[:4]}/month={day[4:6]}/location-{i}-{day}.csv.gz"
    try:
        raw = urllib.request.urlopen(url, timeout=20).read()
    except urllib.error.HTTPError:
        return None
    except Exception as e:
        return (i, "ERR", str(e), "")
    r = next(csv.DictReader(io.StringIO(gzip.decompress(raw).decode("utf-8"))), None)
    if not r:
        return None
    lat, lon = float(r["lat"]), float(r["lon"])
    if box[0] < lat < box[1] and box[2] < lon < box[3]:
        return (i, r["location"], lat, lon)
    return None


def main(args):
    box = tuple(float(a) for a in args[:4])
    ids = args[args.index("--ids") + 1] if "--ids" in args else "1-12000"
    day = args[args.index("--day") + 1] if "--day" in args else "20251028"
    lo, hi = (int(x) for x in ids.split("-"))
    with ThreadPoolExecutor(48) as ex:
        for res in ex.map(lambda i: probe(i, day, box), range(lo, hi + 1)):
            if res:
                print(*res, sep="\t", flush=True)
    print(f"# probed ids {lo}-{hi} on {day} inside {box}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
