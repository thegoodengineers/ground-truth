# Learnings

What we already know, so nobody re-learns it this weekend. Dated entries, newest last.

## Before the event: First Commit (Leash, 28/30)

- **Design and the demo video cost 1 point each.** Both were left to the end. This time the design pass gets its own slot (Saturday morning, on real data), and the video script starts Thursday.
- A real AWS console clip in the video proves the cloud part isn't a mock (#4).
- Submit the night before the deadline. Sunday is a buffer only.
- One working feature beats five half-finished ones. The three checks share one data path; if time runs short, cut the history check, not the polish.

## 2026-10-08: the data spike (`spike/`)

- **OpenAQ archive:** `https://openaq-data-archive.s3.amazonaws.com/records/csv.gz/locationid=<id>/year=<Y>/month=<MM>/location-<id>-<YYYYMMDD>.csv.gz`. Public, us-east-1, 15-minute rows, timestamps in +05:30.
- **The archive is about 4 days behind** (8 Oct: latest file 4 Oct). Live data must come from the API.
- **Through the proxy, S3 sometimes answers 404, or cuts a transfer short, for files that exist.** List the prefix to decide which files exist, retry every error, and check that every gzip decompresses. A naive loop silently lost about 20% of the days.
- **The units label lies:** CO is tagged "ppb" but the values are CPCB mg/m³ (median about 1.5). NO2 is tagged "ppb" too. Don't convert. Every station shares the label, and logs of ratios cancel it.
- **Ids:** Anand Vihar 235, Jahangirpuri 8235, and 52 stations in total in `spike/delhi_stations.tsv`. Pusa and Lodhi Road each appear twice (DPCC/IMD, IMD/IITM, under 0.5 km apart). Don't use co-located twins as each other's neighbours.
- **Mixing confound:** by day the boundary layer mixes, so any station that reads high at night moves towards its neighbours by day (r = −0.72 across stations). A raw daytime dip is not evidence of anything. Compare a station against its own history, or correct for its night level.
- **Gas contrasts are noisy** (NO2 day-night gap ranges −0.8 to +1.4 across stations, against PM10's −0.3 to +0.4). Don't subtract them in a score; show them side by side.
- **Physics checks fire on real data:** PM2.5 > PM10 in 1,044 of 66,831 station-hours. Vikas Sadan, Gurugram: 31% of hours, plus 720 zero or negative hourly values. These are our clearest, least arguable flags.
- **Honest headline:** with this method, neither station named in the news stands out. Say so on the site and in the video. It makes everything else more credible.

## 2026-10-08: building the scorer and the ingest

- **The planted-anomaly experiment** (52 stations, Nov 2025): a 40% daytime PM10 cut over 7 days is caught at 30 of 30 quiet stations. It newly flags 3 other stations across all 30 plantings, and moves about 1.6 others per planting (mostly between ok and watch).
- Two things made that work. A **Theil-Sen** city line, because a least-squares line let the planted station tilt everyone's z-scores. And a **second pass** that leaves first-pass suspects out of their neighbours' references.
- **Edge stations** (Narela, Najafgarh, the NCR fringe) have 2-3 neighbours, so their references are less stable. Expect more ok/watch flicker there.
- **The API's `/hours` endpoint averages UTC hours, which run 13:30-14:30 IST, not 13:00-14:00.** Mixing those with archive hours would shift the 11-17 window by half an hour for live data only. The ingest fetches raw `/measurements` and groups them into IST hours with the same code as the backfill.
- **The ingest logs `overlap_ratio`**: API values divided by archive values on the hours both have. On the first live run it should be about 1.0 for every parameter. If CO shows about 1000, the API serves µg/m³ where the archive has mg/m³.
- **On 4 Oct 2026 data** Jahangirpuri is flagged on history: daytime humidity against its neighbours is +5.2 pts above its previous 3 weeks. It's the same signature as after the Oct 2025 reports. It is still one humidity sensor, so present it as "worth a look", not as evidence of spraying.

## 2026-10-08: reading the rules and the organisers' post

- The judges see only the repo, the video and the writeup. "If the video does not show it, it does not count."
- The organisers' warning: "a map mostly tells people something they can already sense." So each flagged station now carries what its 4 neighbours read right now (`neighbours_latest`): a number a person can act on, not just a red dot.
- "Say plainly in your demo where your numbers come from and how fresh they are." The site shows `data_through` and the source on every page.

## 2026-10-08: the 3D map

- First built with MapLibre on real map tiles; replaced the same day by our own three.js scene, so it looks the same everywhere (including where tile servers are blocked) and matches the fog theme.

- MapLibre waits for every source before firing `load`, so one unreachable tile server stalls the whole map. The base city (wards, boundary) loads from our own files first; the online streets and 3D buildings are added only after a reachability check.
- MapLibre positions markers itself; a `position` rule on the marker element breaks it.
- Headless Chromium needs `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist` to render WebGL for screenshots and the video capture.

## 2026-10-08: phones, slow laptops and no WebGL (#24)

- **Measure with the GPU on:** on a Windows box, headless Chromium with `--use-gl=angle --use-angle=d3d11 --enable-gpu` uses the real GPU. Without flags it falls back to SwiftShader, which is a fair stand-in for a laptop without a GPU.
- **On a phone, each WebGL call costs, not the pixels.** At 390 px with a 4x CPU throttle the map ran at 10 fps with 9 objects per monitor. A blank WebGL canvas of the same size ran at 60, so the cost was ours. Instancing the monitors (7 draw calls for 52) and merging the wards got it to about 30 fps once the quality steps settle.
- **Per-instance opacity:** tinting puffs towards the fog colour instead of fading them looked lighter over the city. A one-line shader hook (`alpha` instanced attribute, `diffuseColor.a *= vAlpha`) matched the old smog exactly (mean brightness 207.6 vs 207.7).
- **Two 3D scenes on one page both run** unless each checks it is actually visible. The tanker illustration kept animating under the full-screen map.
- **`$(".window")` takes the first window on the page.** Once the tanker illustration was added above the map, "Explore Delhi in 3D" made the illustration full screen. Find the map's window from `#map`.

## 2026-10-09: the first deploy (#2, #22, #23, #35, #36)

- **CloudFront is off for unverified accounts.** The first `sam deploy` rolled back with `Your account must be verified before you can add new CloudFront resources`. Only AWS Support can lift it. The stack now takes `UseCloudFront`; off, a Lambda function URL serves the bucket over HTTPS and sends the same security headers the CloudFront policy would, and the S3 website endpoint serves HTTP. Keep the CSP in `src/serve.py` and `template.yaml` identical; `tests/test_serve.py` fails if they drift.
- **A public function URL needs two permissions since 2025:** `lambda:InvokeFunctionUrl` *and* `lambda:InvokeFunction` with the condition `lambda:InvokedViaFunctionUrl = true`. With only the first, every request is 403 `Forbidden`.
- **A new account's Lambda concurrency limit is 10,** so `ReservedConcurrentExecutions: 1` fails (`decreases account's UnreservedConcurrentExecution below its minimum`). Dropped: one run an hour with a 15-minute timeout can't overlap anyway.
- **SNS email subscriptions need a confirmation**, but the token in the email can be confirmed with `aws sns confirm-subscription` instead of a click.
- **Cost allocation tags activate only after billing has seen the tag**, up to a day after the first tagged usage. The `AWS::Budgets::Budget` with a tag filter was accepted before that, but the budget reads $0 until the tag is active (`aws ce update-cost-allocation-tags-status --cost-allocation-tags-status TagKey=project,Status=Active`).
- **Deploy from CI without keys:** `infra/github-oidc.yaml` creates the OIDC provider, a deploy role trusted only for `repo:thegoodengineers/ground-truth:ref:refs/heads/main`, and a CloudFormation service role that does the actual resource work; the deploy role can only drive this stack, upload the SAM artifact, sync `site/` (an explicit Deny on `data/*`) and invalidate CloudFront.
- **The stale-data alarm fires until the real OpenAQ key is in SSM:** without it the Lambda can only score the archive, which runs about 4 days behind.

## 2026-10-09: the region as a setting, and Mumbai (#40)

- Everything Delhi-specific now lives in `src/regions/delhi.json`: the bounding box, the stations file, the neighbour rule (4 within 12 km, co-located twins under 0.5 km excluded), the area names (Delhi / NCR and the words that mark NCR), the map centre and files. `backfill.py`, `scorer.py` and the Lambda take `--region` / `REGION` (default `delhi`); the scorer's output gains a `region` block. Every Delhi result is unchanged (a test checks the region file against the module defaults, and that scoring with it equals scoring without).
- **Mumbai from the archive** (`src/regions/mumbai.json`, 14 monitors found by `spike/find_region.py`: 10 MPCB, 4 IITM, ids 6927-11611): `python src/scorer.py .cache/mumbai_hourly.json out --region mumbai` produces valid output (8 ok, 2 flag, 4 not enough data on 5 Oct 2026).
- **The data is thinner.** Over the 29 days to 5 Oct 2026, Mumbai's monitors had PM readings in 53% of station-hours against Delhi's 72%; four monitors (Colaba, Powai, Borivali East MPCB, Vile Parle West) were below 30% and sit at "not enough data". Only 2 of 14 report humidity (39 of 52 in Delhi), so the history check's humidity half is mostly silent. The neighbour radius had to grow to 14 km, and Nerul still has one neighbour. Not shipped on the site: the method runs, the coverage doesn't earn the answers yet. The write-up can say exactly that.
- The site still reads Delhi's geo files; a second city needs its boundary in `site/geo/` and the scene to read `latest.json`'s `region.map`. That is the next step, not this one.

## 2026-10-09: the live data check (#17)

**What we saw on 9 Oct, 13:55 IST**
- The live `data_through` moved from 5 Oct 23:00 (all the archive has) to 7 Oct 19:00, so hours are now arriving from the API: the key in SSM is being accepted.
- 40 of the 52 monitors stop at exactly 7 Oct 19:00 IST, and none is newer. That isn't our fetch: OpenAQ's own Explorer pages for Jahangirpuri (8235) and Anand Vihar (235) said "Updated 2 days ago", with no data in the last 24 hours. The CPCB feed through OpenAQ was itself about 2 days behind.
- So an hour-old `data_through` depends on the source too, not only on our run. The site now says so in one line under the hero whenever the newest hour is more than 3 hours old, instead of looking as if the check had stopped.
- `New Delhi-8118` (8118) and `Lodhi Road, Delhi` (11607) still have no reading in 4 weeks. 11607 did report in Oct-Nov 2025; 8118 has no PM2.5 or PM10 in the archive at all.
- From the code: a full run fetches 52 stations x up to 5 sensors, about 260 calls, paced at 1.1 s (`OpenAQ.pace`), so about 5 minutes and under 60 a minute.

**Still to record from one run's log line** (`make run`, or `out.json` from `aws lambda invoke`): `overlap_ratio` for `pm25` and `pm10` (0.95-1.05 means the API and the archive agree on units and IST hours), `api_calls`, `skipped`, and `published`.

**The check, once the key is in SSM** (`/ground-truth/openaq-key`)
1. Run the Lambda once (`make run`) and read its JSON log line.
2. `overlap_ratio` for `pm25` and `pm10` should be 0.95-1.05; that means the API and the archive agree on units and on IST hour labels. About 1000 for `co` would mean the API serves µg/m³ where the archive has mg/m³.
3. `data_through` should be within 2 hours of the newest hour OpenAQ's Explorer shows for these monitors (not necessarily of now: see above), and `published` should be `true`.
4. Every station should resolve to PM2.5 and PM10 sensors (`data/raw/sensors_v2.json`); list any that don't.
5. Spot-check three stations' latest IST hour against the CPCB dashboard.
6. Write the real numbers here, replacing this list.
