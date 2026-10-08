"""The README GIF, frame by frame on a fake clock, so it plays at an even 20 fps however slowly a frame renders.

    python video/capture_gif.py [--url http://localhost:8000] [--out docs/img/demo.gif]

Needs the site served with data (make local) and ffmpeg on the PATH. Each frame: advance the page's clock by 50 ms
(timers, requestAnimationFrame and performance.now all follow it), then screenshot. ?capture=1 turns off shadows,
caps the pixel ratio and drops the dust in the 3D scene.

Shots: the hero (2 s), the ten-second explainer (4 s), into 3D and orbit (3.8 s), a flagged monitor's panel (4 s).
The orbit changes every pixel of every frame, so it is what sets the size: 3 s of it and an 80-colour palette with
no dithering keep the GIF under 6 MB, with the status colours intact.
"""
import argparse, os, shutil, subprocess, tempfile

from playwright.sync_api import sync_playwright

FPS, STEP_MS = 20, 50
W, H, GIF_W = 1280, 800, 800
FLAGGED = "Indirapuram"  # flagged on the neighbours check in the sample data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--out", default="docs/img/demo.gif")
    ap.add_argument("--keep", help="also keep the PNG frames in this folder")
    a = ap.parse_args()
    frames = tempfile.mkdtemp(prefix="gt-gif-")
    n = 0

    with sync_playwright() as p:
        # a real GPU where there is one; headless Chromium falls back to software otherwise
        b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
        page = b.new_page(viewport={"width": W, "height": H})
        page.clock.install()
        page.goto(f"{a.url}/?capture=1", wait_until="domcontentloaded")
        page.evaluate("document.fonts.ready")
        # CSS animations run on the real clock, not the fake one: freeze the drifting fog so frames stay alike
        page.add_style_tag(content=".drift { animation-play-state: paused !important; }")
        for _ in range(100):  # up to 10 s of page time for the data and the 3D city
            page.clock.run_for(100)
            if page.evaluate("(window.__milestones || []).some(m => m.name === 'map:ready')"):
                break
        page.clock.run_for(1500)  # let the hero settle

        def shoot(seconds, each=None):
            nonlocal n
            for i in range(round(seconds * FPS)):
                if each:
                    each(i / max(1, round(seconds * FPS) - 1))
                page.clock.run_for(STEP_MS)
                page.screenshot(path=os.path.join(frames, f"f{n:04d}.png"))
                n += 1

        def scroll_to(selector, seconds=1.0, then=0.0):
            start = page.evaluate("scrollY")
            end = page.evaluate(f"document.querySelector('{selector}').getBoundingClientRect().top + scrollY - 70")
            ease = lambda t: t * t * (3 - 2 * t)  # noqa: E731
            shoot(seconds, lambda t: page.evaluate(f"scrollTo({{top: {start + (end - start) * ease(t)}, behavior: 'instant'}})"))
            shoot(then)

        shoot(2)                                    # the hero
        scroll_to("#story", 1.0, then=3.0)          # the ten-second explainer
        scroll_to("#live", 0.8)
        page.click("#enter3d")
        shoot(3.0)                                # into 3D, then the slow orbit
        page.evaluate(f"document.querySelector('.gt-marker[aria-label^=\"{FLAGGED}\"]').click()")
        shoot(4)                                    # a flagged monitor: the camera flies there and the panel opens
        b.close()

    palette = f"fps={FPS},scale={GIF_W}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=80:stats_mode=full[p];" \
              "[b][p]paletteuse=dither=none:diff_mode=rectangle"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(frames, "f%04d.png"),
                    "-vf", palette, "-loop", "0", a.out], check=True)
    if a.keep:
        shutil.copytree(frames, a.keep, dirs_exist_ok=True)
    shutil.rmtree(frames)
    print(f"{n} frames, {n / FPS:.1f} s at {FPS} fps -> {a.out} ({os.path.getsize(a.out) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
