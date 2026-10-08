"""Render the HTML scenes (video/scenes/scenes.html) to video/build/seg-NN.mp4, one per `scene:` and
`terminal:` row of the script, each as long as its narration plus a short pad.

    python video/record.py            # every HTML scene
    python video/record.py 3 11       # only rows 3 and 11
    python video/record.py --preview 11 4.5   # a PNG of scene row 11 at 4.5 s, to check the layout

Frames come from a fake clock (video/frames.py), so a scene takes exactly its narration's time whatever the
machine. Run video/narrate.py first; without a voice file a scene gets a default length.
"""
import os, sys, urllib.parse

from playwright.sync_api import sync_playwright

from frames import BUILD, FPS, H, HERE, W, Recorder, launch, vo_seconds  # noqa: F401
from narrate import rows

SCENES = HERE / "scenes" / "scenes.html"
PAD = 0.5          # seconds of silence after each narration
MIN_SCENE = 4.0    # a scene never flashes by


def scene_rows():
    for n, scene, text in rows():
        kind, _, name = scene.partition(":")
        if kind in ("scene", "terminal"):
            yield n, kind, name.strip(), text


SITE_URL = os.environ.get("SITE_URL_PUBLIC", "zsx5rsh4vklo266budro23qama0cpbpi.lambda-url.us-east-1.on.aws")


def url_for(kind, name, dur):
    scene = "terminal" if kind == "terminal" else name
    return f"{SCENES.as_uri()}?scene={scene}&dur={dur:.2f}&url={urllib.parse.quote(SITE_URL)}"


def open_scene(page, kind, name, dur):
    page.goto(url_for(kind, name, dur), wait_until="domcontentloaded")
    if kind == "terminal":
        text = (HERE / "assets" / name).read_text(encoding="utf-8") if (HERE / "assets" / name).exists() else ""
        page.evaluate("t => { window.__pytest = '$ make test\\n\\n' + t; }", text)
        page.reload(wait_until="domcontentloaded")
        page.evaluate("t => { window.__pytest = '$ make test\\n\\n' + t; }", text)
    page.evaluate("document.fonts.ready")
    page.clock.run_for(50)


def main(args):
    preview = "--preview" in args
    nums = [a for a in args if a.replace(".", "").isdigit()]
    wanted = {int(nums[0])} if preview and nums else {int(a) for a in nums}
    BUILD.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = launch(p)
        page = b.new_page(viewport={"width": W, "height": H})
        page.clock.install()
        for n, kind, name, _text in scene_rows():
            if wanted and n not in wanted:
                continue
            dur = max(MIN_SCENE, vo_seconds(n) + PAD)
            open_scene(page, kind, name, dur)
            if preview:
                t = float(nums[1]) if len(nums) > 1 else dur / 2
                page.clock.run_for(round(t * 1000))
                out = BUILD / f"preview-{n:02d}.png"
                page.screenshot(path=str(out))
                print(f"{n:02d} {name:<10} at {t:.1f}s -> {out}")
                continue
            rec = Recorder(page, BUILD / f"seg-{n:02d}.mp4")
            rec.shoot(dur)
            got = rec.finish()
            print(f"{n:02d} {name:<10} {got:5.1f}s -> {rec.out.name}")
        b.close()


if __name__ == "__main__":
    main(sys.argv[1:])
