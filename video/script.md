# Video script (issue #10)

**Style.** Calm, factual, a little cinematic: a morning decision in Delhi, then the evidence. The palette and fonts are the site's own (paper `#f6f6f3`, ink `#111`, one blue `#2457d6`, state colours only for state; Inter + JetBrains Mono). Dark scenes for the hook and the close, paper scenes for the product. The music is a slow, warm ambient bed under the voice, with a swell at the title and at the proof, fading on the close.

**Rules.** The film is under 3:00 and never sped up; if it runs long, cut words. Every number spoken or shown comes from the repo or the live data: the sources are in the last column. Never say or show "fake", "tampered" or "sprayed" about a station. Numbers are written the way they are spoken.

Scene kinds: `scene: <id>` = an HTML scene in `scenes/scenes.html` (rendered by `record.py`); `CAPTURE <step>` = a shot of the site driven like the `?demo=1` tour (`capture_demo.py`); `terminal: <file>` = real CLI output typed on screen (`assets/<file>`, from a real run); `SUPPLY <file>` = a shot only a human can record (`supply/<file>`).

**Render:** `make video` (narration with edge-tts, scenes and site shots frame by frame on a fake clock, cut by `assemble.py` with the music bed and burnt-in captions) writes `video/final.mp4`. The site must be served with data on `SITE_URL` (default `make local`). Each row runs as long as its narration plus half a second, so the film is never sped up; a row's shot holds its last frame if the sentence runs longer.

| # | Scene | On screen | Narration | Source |
|---|---|---|---|---|
| 1 | scene: hook | Dark. A phone lights up: 7:40, "Air quality near you: PM2.5 10". A school bell icon. | Seven forty in the morning. A principal in East Delhi checks the air before assembly. The nearest monitor says it's fine. | - |
| 2 | scene: problem | Three questions type on, one by one: "Is it working?" "Is it broken?" "Is someone gaming it?" | But is that monitor working? Last October, water tankers were filmed near a Delhi monitor. A published number tells you nothing about the station behind it. | news, Oct 2025 |
| 3 | scene: title | The GT mark pulses. "Ground Truth". "Which air-quality numbers can you trust?" | This is Ground Truth. It checks every monitor in Delhi and the NCR, every hour, and tells you in plain words whether its number adds up. | - |
| 4 | scene: checks | Three cards build: Physics, Neighbours, History, each with its question. | Three questions. Physics: can this reading even be real? Neighbours: does it agree with the four stations around it? History: has it suddenly changed? | `src/scorer.py` |
| 5 | CAPTURE start | The live site: hero, live example, stats, then the map. | Here are fifty-two stations, each with a plain answer. | `data/latest.json` |
| 6 | CAPTURE physics | Vikas Sadan opens; the Physics card is outlined. | Vikas Sadan, in Gurugram, reports more fine dust than total dust. That can't happen, so it fails the physics check. | `data/latest.json` |
| 7 | CAPTURE chart | Anand Vihar; the hour-of-day chart, the 11-to-5 band shaded. | Anand Vihar, against its neighbours, hour by hour. Its dust dips between eleven and five. That looks like spraying. But every polluted hotspot does this, because daytime air mixes. So we don't flag it. | `spike/RESULTS.md` |
| 8 | CAPTURE history | Jahangirpuri; the History card outlined; then "this station vs 4 nearest now". | Jahangirpuri's daytime humidity jumped against its own last three weeks. Worth a look, not proof. And when a station is in doubt, we show what its neighbours read right now. | `data/latest.json` |
| 9 | scene: proof | Huge "30 / 30". Under it: "planted daytime drops caught". | How do we know it works? We planted a forty percent daytime drop in real data, one station at a time. It was caught thirty times out of thirty. | `docs/LEARNINGS.md` |
| 10 | terminal: pytest.txt | The real `pytest` run typing out, ending green. | Every claim has a test, and the tests run on every change. | `make test` |
| 11 | scene: arch | The architecture: EventBridge, Lambda, Parameter Store, OpenAQ, S3, CloudFront light up as named. | On AWS, EventBridge runs a Lambda every hour. It reads new data from OpenAQ, runs the checks, and writes the results to S3, where the site is served from over HTTPS. One SAM template deploys it all. | `template.yaml` |
| 12 | SUPPLY console.mp4 | 10-15 s of the real AWS console: Lambda invocations, the EventBridge rule, S3 `data/` objects. | And here it is, running. | issue #4 |
| 13 | scene: learned | Three lessons build line by line. | What we learned. The archive runs four days behind, so live data needs the API. The API's hours are half an hour off India's. And our strongest result is the one we didn't claim. | `docs/LEARNINGS.md` |
| 14 | scene: close | Dark. GT mark, "Ground Truth", the URL and the repo. | Ground Truth. A flag means the numbers don't add up. Not that anyone cheated. | - |

## Music cue

The bed runs under the narration at about -22 dB, ducked further whenever the voice speaks. It swells gently at scene 3 (title) and scene 9 (proof), and fades out over the last 3 seconds of scene 14. Default: `video/music.py` generates a procedural ambient bed (numpy, no licence needed). To use a CC BY track instead, save it as `video/music.mp3` and credit it in the YouTube description.

## Human shot list (SUPPLY)

| File | What | Spec |
|---|---|---|
| `video/supply/console.mp4` | The AWS console: Lambda > Monitor (hourly invocations), the EventBridge rule, S3 `data/` with recent timestamps, the CloudFront distribution. | 1920x1080, 10-15 s, no cursor waving, no account ids or keys on screen. |

If the file is missing, `assemble.py` renders a placeholder card so the cut still builds.

## Check before the final render

- [ ] Scene 5's "fifty-two" matches the number of stations in the live `data/latest.json`.
- [ ] Scene 6: Vikas Sadan is still flagged on physics in the live data; if not, pick the station `?demo=1` picks and change the line.
- [ ] Scene 8: Jahangirpuri's history check still says humidity moved; if not, change the line to what its card says.
- [ ] Scene 10: `video/assets/pytest.txt` comes from a fresh `make test` run.
