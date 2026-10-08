# sample

`data/` is real scorer output for the 28 days ending 4 Oct 2026, 17:00 IST (the last hour in the public archive on 8 Oct). It has exactly the shape the live site will get from S3:

- `data/latest.json`: every station with its status, its three checks and its latest readings.
- `data/stations/<id>.json`: neighbours, the hour-of-day gap profiles (28 days and 7 days) and the daily contrasts.

Build the site against this, not hand-written mocks. To serve it locally next to the site, copy `sample/data` to `site/data`.

On this data: 36 stations ok, 7 watch, 4 flag, 5 no data. Three of the five (NSIT Dwarka, Sector 30 and Sector 11 Faridabad) stopped reporting a day or more before the data ends, so they aren't judged; the other two have no readings at all. The flags are Vikas Sadan (physics), IGI Airport and Indirapuram (neighbours), and Jahangirpuri (history: daytime humidity up 5.2 pts on its previous 3 weeks).

To regenerate:
```
python src/backfill.py hourly.json --end 2026-10-04 --days 29 --cache .cache
python src/scorer.py hourly.json sample/data
```

`weather.json` is a real Open-Meteo reading for central Delhi, so the site has the weather line locally and the smoke tests see no missing file; the Lambda rewrites it every hour.
`fires.json` is the stub the Lambda writes when no FIRMS key is configured (no count, no line).
