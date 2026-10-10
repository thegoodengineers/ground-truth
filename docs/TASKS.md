# Tasks

Each task is self-contained: what to do, the files it touches, and a test for "done". Anyone can pick one up without earlier context. Read `docs/PLAN.md` and `docs/STACK.md` first. Tick a task when its done-test passes, then commit.

Owners: **Abhijeet** (thegoodengineer) = AWS · **Chirag** (Chirag6722) = backend, tests, story · **Bhumika** (Bhumika-1432006) = site and design · **Ayush** (AyushVUpadhye) = QA and review, once he's on the repo.

## Must

- [x] **Spike: is the data good enough?** Files: `spike/`. Done: `spike/RESULTS.md` answers it.
- [x] **Backfill from the archive** (#7). Files: `src/backfill.py`. Done: `python src/backfill.py out.json --days 29` writes 52 stations.
- [x] **Scorer: three checks** (#8). Files: `src/scorer.py`. Done: `make test` green; 235 and 8235 match `spike/RESULTS.md`.
- [x] **Tests + CI** (#9). Files: `tests/`, `.github/workflows/test.yml`. Done: CI green on the PR; breaking the 11-17 window turns it red.
- [x] **Ingest Lambda + SAM + Makefile.** Files: `src/ingest.py`, `template.yaml`, `Makefile`, `tests/test_ingest.py`. Done: `make lint test` green.
- [ ] **AWS account, profile, key in SSM** (#1, Abhijeet). Done: `aws sts get-caller-identity --profile groundtruth` works and the SSM parameter exists. *Profile and parameter done; the parameter holds a placeholder until someone signs up for an OpenAQ key.*
- [x] **First deploy** (#2, Abhijeet). Uses `template.yaml`. Done: `make deploy && make url` prints an HTTPS URL that serves `index.html`. *CloudFront is blocked on the account; a Lambda function URL serves HTTPS (#64).*
- [ ] **Live data** (#3, Abhijeet). Done: `make seed && make run` prints `"scored": true` and an `overlap_ratio` near 1.0 for pm10/pm25; two scheduled runs later `data_through` has advanced.
- [x] **Site v1: map + station panel + `?demo=1`** (#12-#14). Files: `site/index.html`, `site/app.js`, `site/theme.css`, `site/scene3d.js`. Done: `make local`, open `http://localhost:8000`: all stations on the map; clicking one opens three check cards and the hour-of-day chart; `?demo=1` plays the tour by itself; no console errors.
- [x] **Video pipeline** (#10). Files: `video/script.md`, `video/narrate.py`, `video/scenes/scenes.html`, `video/record.py`, `video/capture_demo.py`, `video/console_clip.py`, `video/music.py`, `video/assemble.py`. Done: `make video` produces `video/final.mp4` under 3:00, never sped up. *Re-render on Saturday against the live data, then upload and link in the submission.*
- [x] **Console clip** (#4). Done: `video/supply/console.mp4`, 12 s, 1920x1080, from the real console by `video/console_clip.py` (a read-only federated session). *Re-run on Saturday so the invocation graph shows a day of hourly bars.*
- [ ] **Writeup + submission** (#11, Chirag, Sunday, after the video). Files: `docs/submission.md`, `README.md`. Done: form submitted, screenshot in #11.

## Should

- [x] **UI rounds with screenshots** (#15). Files: `site/*`. Done: screenshots at 1440, 1024 and 400 px reviewed and fixed; no horizontal scroll; loading, empty and error states designed.
- [x] **README for judges.** Files: `README.md`, `docs/img/demo.gif`. Done: GIF at the top, architecture, `make local`, test count from a real run. Live URL and video link get filled in on Sunday.
- [x] **Deploy from CI on merge to main** (OIDC role, no stored keys). Files: `.github/workflows/deploy.yml`, `infra/github-oidc.yaml`. Done: a merge updates the live site.
- [ ] **Blog on AWS Builder Center** (enters the top-5 blogs prize). Files: `docs/BLOG.md` (drafted). Done: published and linked in the submission.

## Nice

- [x] **Station history page** journalists can link to (`#235/history`): the month strip in every panel, the city-wide month chart, and the Atom feed of changes (#98, #101).
- [x] **NASA FIRMS fire layer** for stubble-burning days (#73; needs a FIRMS key in SSM to light up).
- [ ] **Hindi copy** for the statuses and the limits section.

## Ayush (once he's a collaborator)

- QA on Saturday: the live URL on 3 phones and 2 browsers, every station clicked, bugs filed.
- Voice-over review for the video.
- Check the writeup's claims against `spike/RESULTS.md`.
