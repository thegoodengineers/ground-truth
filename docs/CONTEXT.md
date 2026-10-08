# Context: where the project stands and how we work

Read this first when picking up the work. It collects the decisions made so far, which are spread across chats and PRs. The plan, rubric and timeline are in [PLAN.md](PLAN.md). The task list is in [TASKS.md](TASKS.md). Open work is in the GitHub issues.

_Last updated: 8 Oct 2026._

## The project in one paragraph

Ground Truth is for Environmental Hacks 2026 (WeMakeDevs × AWS, Air track). Submission is on **Sunday 11 Oct 2026**, and the deadline hour isn't published, so submit early. It checks every air-quality monitor in Delhi and the NCR every hour, with three checks:
- **Physics:** is the reading possible?
- **Neighbours:** does it agree with the 4 nearest monitors?
- **History:** has it suddenly changed against its own last 3 weeks?

Each monitor gets one plain answer: agrees with neighbours, worth a look, doesn't add up, or not enough data. When a monitor is in doubt, the site shows what its neighbours read.

The October 2025 water-tanker story is our motivation, not our claim. We tested it: the monitors named in the reports didn't stand out (Anand Vihar 6th, Jahangirpuri 13th of 38). A flag never means "someone cheated".

## Working rules (agreed, keep to them)

- **Git:**
  - Commit as `Chirag <chiraghonnyal6722@gmail.com>`.
  - Work on a branch and open a PR. Merge to main **only when Chirag says so**.
  - Never rewrite someone else's branch.
- **No tool credits** anywhere: code, comments, commits, PR text, issues or docs. No co-author trailers and no "generated with" lines.
- **Keys never go in chat or in git.** The OpenAQ key lives in SSM at `/ground-truth/openaq-key`.
- **Video and recordings are made on Sunday,** not before. The README GIF is allowed.
- **Wording:**
  - Never say fake, tampered or sprayed about a monitor. A test enforces this.
  - Say "the numbers don't add up", and show the evidence.

## Design decisions

- **Light mode only.** No dark mode.
- **No reference to the old Leash design.** From neatlogs.com we took only the fog hero, two-tone headlines (a grey first line over a black second line), mono labels and the window frame.
- **Fonts and libraries:**
  - Geist and Geist Mono.
  - Chart.js 4.4.1 and three.js 0.160.0, both vendored in `site/vendor/`, because CDNs may be blocked.
  - No build step.
- **Status colours:** ok `#0ca30c`, watch `#f2a60c`, flag `#d03b3b`, no data `#a3a4a9`. Every state also has a shape and a word, never colour alone.
- **The map is our own 3D Delhi** (`site/scene3d.js`), not a tile map:
  - DataMeet wards, city blocks, trees and three landmarks;
  - a mast per monitor, with a column as tall as its PM2.5 reading and smog;
  - fog and floating dust.
- **The October 2025 illustration** (`site/spray3d.js`) is in the same style: a tanker sprays a monitor and its reading drops while the monitors nearby don't. The page labels it an illustration.
- **The preview link Chirag shares is private** (a private preview link), not GitHub Pages. GitHub Pages was removed.

## Data facts that cost us time

- **History:** the OpenAQ public archive on S3 (Open Data on AWS) runs about 4 days behind. Download only files that appear in the bucket listing, retry every error, and check the gzip.
- **Live hours:** they come from the OpenAQ API v3 (raw measurements), which we group into **IST hours** ourselves. The API's own hourly averages use UTC hours, which are 30 minutes off.
- **CO units:** CO is labelled ppb but is really mg/m³. Don't convert it.
- **Duplicate names:** "Pusa" and "Lodhi Road" each exist twice; show the OpenAQ id next to them.

## Code map

| Path | What it is |
|---|---|
| `src/backfill.py` | Seeds the 28-day hourly cache from the archive |
| `src/scorer.py` | The three checks; writes `latest.json` and `stations/<id>.json` (contract in [STACK.md](STACK.md)) |
| `src/ingest.py` | The hourly Lambda: OpenAQ API → cache → scorer → S3 |
| `tests/` | 62 tests, most on real November 2025 data, plus Playwright smoke tests in `tests/site/`, including the planted-anomaly test |
| `template.yaml` | AWS SAM: S3 (private) + CloudFront + hourly EventBridge → Lambda, SSM key |
| `site/` | The website: `index.html`, `app.js`, `theme.css`, `scene3d.js`, `spray3d.js` |
| `sample/data/` | Real scorer output up to 4 Oct 2026, for running the site without AWS |
| `video/` | Video script and narration helper, for Sunday |

## Running it

- **Mac or Linux:** `make local`, then open http://localhost:8000. Add `?demo=1` for the self-playing tour.
- **Windows** (no `make`), in PowerShell from the repo folder:
  ```
  Remove-Item -Recurse -Force site\data -ErrorAction SilentlyContinue
  Copy-Item -Recurse sample\data site\data
  python -m http.server 8000 -d site
  ```
- **Tests:** `pip install -r requirements-dev.txt`, then `pytest -q`, `ruff check .` and `cfn-lint template.yaml`.

## State on 8 Oct 2026

**Done, on main:**
- data spike;
- backfill, scorer and ingest, with tests and CI;
- the AWS template;
- the full site: problem and answer, the ten-second explainer, the four answers, live 3D map and panel, every monitor by area with filters, the three checks with formulas, the tanker illustration, proof, AWS, FAQ;
- README, submission text (`docs/submission.md`) and blog draft (`docs/BLOG.md`).

**Also on main (PR #54 and Bhumika's PRs, merged 8 Oct):**
- #18 freshness, #19 ingest resilience, #30 CPCB bands, #24 phones and no-WebGL;
- #21 status smoothing ("flagged since", no flip-flopping), #25 list view and keyboard access, #26 copy link, #28 Hindi toggle, #31 48-hour evidence chart, #32 who runs each monitor, #33 nightly archive re-sync, #34 browser smoke tests in CI, #37 CSV download.
- Still to review by the team: the one-line advice per AQI band (`BAND_TODO` in `site/app.js`) and the Hindi copy.

**Not done:**
- **Nothing is deployed yet.** AWS issues #1–#3 are with Abhijeet. The live site, and the Live pill showing "Live", wait on that.
- **#17 live data check** needs the OpenAQ key, set locally by Chirag (never in chat).
- **The README GIF is choppy** (#27).
- **Sunday:** video (#10), submission (#11), publish the blog (#38).

**Old issues:**
- #12, #13 and #14 describe the old design and are replaced by the current site. Close them if Chirag agrees.
- #10 and #11 still say Saturday; the plan is now Sunday.

**Open decision for Chirag:** the hackathon rules ask teams to list the coding tools they used in the write-up. Decide before submitting.

## Team

- **Chirag** (@Chirag6722): backend, data, write-up.
- **Abhijeet** (@thegoodengineer): AWS.
- **Bhumika** (@Bhumika-1432006): site.
- **Ayush** (@AyushVUpadhye): not a repo collaborator yet; needs an invite.
