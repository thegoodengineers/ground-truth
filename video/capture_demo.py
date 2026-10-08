"""Capture the site for the CAPTURE rows of the script: video/build/seg-NN.mp4 at 1920x1080.

    python video/capture_demo.py [--url http://localhost:8000] [5 6 7 8]

Needs the site served with data (make local, or the live URL) and ffmpeg. The page runs on a fake clock
(video/frames.py) so every frame is 1/30 s of page time: never sped up, however slowly the 3D city renders.
?capture=1 exposes the tour's moves on window.__gt and lightens the 3D scene; each shot is timed to its
narration row (plus a pad), so a long sentence holds on the panel instead of the tour racing ahead.

Shots (the station ids are the ones the script names; check them against the live data before the final render):
  5 start    the hero, the live example and the stats, then down to the map and into 3D
  6 physics  fly to Vikas Sadan (301), which fails the physics check; the card outlined
  7 chart    Anand Vihar (235), the hour-of-day chart with the 11-17 band
  8 history  Jahangirpuri (8235), the history card, then "this station vs the 4 nearest now"
"""
import sys

from playwright.sync_api import sync_playwright

from frames import BUILD, H, W, Recorder, launch, vo_seconds
from record import PAD

MIN = {5: 9.0, 6: 8.0, 7: 9.0, 8: 9.0}
PHYSICS, CHART, HISTORY = 301, 235, 8235


def ready(page, name, max_s=20):
    for _ in range(max_s * 10):
        page.clock.run_for(100)
        if page.evaluate(f"(window.__milestones || []).some(m => m.name === '{name}')"):
            return True
    return False


def main(args):
    url = "http://localhost:8000"
    if "--url" in args:
        url = args[args.index("--url") + 1]
    wanted = {int(a) for a in args if a.isdigit()} or {5, 6, 7, 8}
    BUILD.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = launch(p)
        page = b.new_page(viewport={"width": W, "height": H})
        page.clock.install()
        page.goto(f"{url}/?capture=1", wait_until="domcontentloaded")
        page.evaluate("document.fonts.ready")
        page.add_style_tag(content=".drift { animation-play-state: paused !important; }")  # CSS runs on the real clock
        assert ready(page, "map:ready"), "the map never became ready: is the site served with data?"
        page.clock.run_for(1500)

        def shot(n, steps):
            """steps: [(seconds into the shot, js)] run on the fake clock while recording."""
            dur = max(MIN.get(n, 8.0), vo_seconds(n) + PAD)
            rec = Recorder(page, BUILD / f"seg-{n:02d}.mp4")
            pending = sorted(steps)

            def each(t):
                while pending and pending[0][0] <= t:
                    page.evaluate(pending.pop(0)[1])
            rec.shoot(dur, each)
            print(f"{n:02d} capture {rec.finish():5.1f}s -> {rec.out.name}")

        def go(sid, spot):
            return f"window.__gt.select({sid}, {{fly: true, spot: '{spot}'}})"

        def say(k, text):
            return f"window.__gt.caption({k!r}, {text!r})"

        if 5 in wanted:
            page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
            shot(5, [(0.2, say("Ground Truth", "Every monitor in Delhi and the NCR, checked every hour.")),
                     (2.2, "window.__gt.scrollTo('#live')"),
                     (4.2, "window.__gt.enterImmersive()")])
        if 6 in wanted:
            shot(6, [(0.0, "window.__gt.enterImmersive()"),
                     (0.3, go(PHYSICS, "physics")),
                     (0.4, say("Physics", "Vikas Sadan reports readings that can't be real. Its numbers don't add up."))])
        if 7 in wanted:
            shot(7, [(0.0, "window.__gt.enterImmersive()"),
                     (0.3, go(CHART, "neighbours")),
                     (0.4, say("Neighbours", "Anand Vihar, hour by hour, against the four stations around it. "
                                             "The shaded band is 11:00 to 17:00.")),
                     (6.0, "document.querySelector('#panel canvas')?.scrollIntoView({behavior: 'smooth', block: 'center'})")])
        if 8 in wanted:
            shot(8, [(0.0, "window.__gt.enterImmersive()"),
                     (0.3, go(HISTORY, "history")),
                     (0.4, say("History", "Jahangirpuri against its own last three weeks. Worth a look, not proof.")),
                     (6.5, say("What to do", "When a station is in doubt, use what the stations around it read right now.")),
                     (6.6, "document.querySelector('#panel .now')?.scrollIntoView({behavior: 'smooth', block: 'center'})")])
        b.close()


if __name__ == "__main__":
    main(sys.argv[1:])
