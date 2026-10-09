"""The tour speaks each step from site/audio/tour-<lang>-<step>.mp3 (video/tour_voice.py): every step the tour
says, in every language the site offers, needs its file, and the voice script needs a line for it."""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "video"))
import tour_voice  # noqa: E402


def test_every_tour_step_has_a_line_and_a_file_in_each_language():
    app = open(os.path.join(ROOT, "site", "app.js"), encoding="utf-8").read()
    steps = sorted({int(n) for n in re.findall(r"\bsay\((\d+),", app)})
    assert steps == list(range(1, len(steps) + 1)) and len(steps) >= 5
    for lang in ("en", "hi"):
        assert len(tour_voice.LINES[lang]) == len(steps)
        missing = [n for n in steps if not os.path.getsize(os.path.join(ROOT, "site", "audio", f"tour-{lang}-{n}.mp3"))]
        assert missing == []
