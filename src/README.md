# src

The backend. Pure Python 3.11 standard library, with no dependencies, so the same code runs locally, in pytest and in Lambda.

| File | What it does |
|---|---|
| `stations.tsv` | The 52 OpenAQ locations in the Delhi box (id, name, lat, lon), from the spike sweep. |
| `backfill.py` | Builds hourly history from the public OpenAQ archive on S3 (no key). Lists the bucket to find files, retries every error and checks every gzip. Writes `{station_id: {param: {"YYYY-MM-DDTHH": value}}}` with IST hour keys. |
| `ingest.py` | The hourly Lambda (#3). Reads the OpenAQ key from SSM, fetches raw readings per sensor from the API (paced under 60 requests/min), averages them into IST hours like the backfill, keeps a 29-day cache in S3 (`data/raw/hourly.json`), runs the scorer and writes `data/latest.json` + `data/stations/<id>.json`. |
| `scorer.py` | The three checks per station (physics, neighbours, history). Writes `latest.json` and `stations/<id>.json` in the shape in `docs/STACK.md`. |

## Run

```
python src/backfill.py hourly.json --end 2026-10-04 --days 29 --cache .cache
python src/scorer.py hourly.json out            # scores the 28 days ending at the latest hour in the file
python src/scorer.py hourly.json out --now 2025-11-30T23 --days 61
```

The archive runs about 4 days behind real time, so for live data `ingest.py` adds the latest hours from the OpenAQ API. Deploy and run it with the root `Makefile` (`make deploy`, `make seed`, `make run`).

## How the checks work

See the table in `docs/PLAN.md`. In short:
- **physics:** share of the last 7 days' hours with PM2.5 > 1.05 × PM10, out-of-range values or a stuck PM sensor. Watch above 1%, flag above 5%.
- **neighbours:** daytime (11-17) minus night (22-06) PM10 gap against the median of the 4 nearest stations within 12 km, corrected for daytime mixing with a Theil-Sen line across the city. Robust z: watch at 2, flag at 3.
- **history:** the same contrast for PM10 and humidity, last 7 days against the previous 21 days, in robust SDs. Watch at 2, flag at 3.

Scoring runs twice: stations flagged in the first pass are left out of their neighbours' references in the second.

## Regions

A city is a file in `regions/`: `delhi.json` (the default) and `mumbai.json` (a trial, see `docs/LEARNINGS.md`). It names the stations file, the bounding box, the neighbour rule, the area names and the map. `backfill.py` and `scorer.py` take `--region`, the Lambda reads `REGION`, and the scorer writes a `region` block into `latest.json`. To try a city: list its monitors with `spike/find_region.py`, write the two files, then `python src/backfill.py out.json --days 29 --region <id>` and `python src/scorer.py out.json out_dir --region <id>`.
