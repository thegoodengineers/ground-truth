"""Shared by record.py and capture_demo.py: a page on a fake clock, stepped frame by frame into an MP4.

Playwright's clock drives timers, requestAnimationFrame and performance.now, so each frame is exactly
1/FPS of page time however slowly it renders, and the film is never sped up (video/script.md). CSS animations
run on the real clock, so scenes animate in JS from performance.now() and the site's drift is paused.
"""
import os, shutil, subprocess, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
VO = HERE / "vo"
W, H, FPS = 1920, 1080, 30
GPU = ["--use-gl=angle", "--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"]
SOFT = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]


def duration(path):
    """Seconds of an audio or video file (ffprobe)."""
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(path)]).decode().strip())


def vo_seconds(n, default=4.0):
    """How long row n's narration runs; the default when it hasn't been rendered yet."""
    p = VO / f"{n:02d}.mp3"
    return duration(p) if p.exists() else default


def launch(p, headless=True):
    """Chromium with the real GPU where there is one (Windows d3d11), else SwiftShader."""
    try:
        return p.chromium.launch(headless=headless, args=GPU)
    except Exception:
        return p.chromium.launch(headless=headless, args=SOFT)


class Recorder:
    """Collects JPEG frames, then encodes them with ffmpeg."""

    def __init__(self, page, out):
        self.page, self.out, self.n = page, Path(out), 0
        self.dir = tempfile.mkdtemp(prefix="gt-frames-")

    def shoot(self, seconds, each=None):
        """Advance the page clock 1/FPS at a time for `seconds`, screenshotting every step.
        `each(t)` runs before each frame with t = seconds into this shot."""
        total = round(seconds * FPS)
        for i in range(total):
            if each:
                each(i / FPS)
            self.page.clock.run_for(round(1000 / FPS))
            self.page.screenshot(path=os.path.join(self.dir, f"f{self.n:05d}.jpg"), type="jpeg", quality=92)
            self.n += 1

    def finish(self):
        self.out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", os.path.join(self.dir, "f%05d.jpg"),
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-vf", f"scale={W}:{H}", str(self.out)], check=True)
        shutil.rmtree(self.dir, ignore_errors=True)
        return self.n / FPS
