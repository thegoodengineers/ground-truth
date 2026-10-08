"""Cut the film: video/final.mp4 from the segments, the narration, the music bed and burnt-in captions.

    python video/assemble.py [--no-music] [--out video/final.mp4]

For every row of video/script.md: the segment video/build/seg-NN.mp4 (from record.py or capture_demo.py; a
SUPPLY row uses video/supply/<file> scaled to 1920x1080, or the placeholder scene when the file is missing)
is cut or held on its last frame to the row's length (narration + pad), never sped up. The narration rows are
laid end to end, the bed is ducked under the voice, the spoken text is burnt in as captions, and the film is
checked to be under 3:00.
"""
import json, subprocess, sys
from pathlib import Path

from frames import BUILD, FPS, H, HERE, W, duration, vo_seconds
from narrate import rows
from record import MIN_SCENE, PAD

SUPPLY = HERE / "supply"
OUT = HERE / "final.mp4"
LIMIT = 180.0
MUSIC_DB = -22


def run(cmd):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *cmd], check=True)


# rows whose picture needs longer than its sentence: the walk into the 3D city, and the console proof shot
MIN_ROW = {5: 9.0, 12: 12.0}


def row_length(n, kind):
    base = vo_seconds(n) + PAD
    floor = MIN_ROW.get(n, MIN_SCENE if kind in ("scene", "terminal") else 2.0)
    return max(floor, base)


def source_for(n, kind, name):
    seg = BUILD / f"seg-{n:02d}.mp4"
    if kind == "SUPPLY":
        supplied = SUPPLY / name
        if supplied.exists():
            return supplied
        if not seg.exists():
            raise SystemExit(f"row {n}: neither {supplied} nor {seg}: run record.py (it renders the placeholder)")
    if not seg.exists():
        raise SystemExit(f"row {n}: {seg} is missing: run record.py / capture_demo.py first")
    return seg


def fit(src, length, out):
    """Scale to 1920x1080, cut to `length`, and hold the last frame if the source is shorter."""
    run(["-i", str(src), "-an",
         "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS},"
                f"tpad=stop_mode=clone:stop_duration={length + 1:.3f}",
         "-t", f"{length:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(out)])


def srt_time(s):
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main(args):
    out = Path(args[args.index("--out") + 1]) if "--out" in args else OUT
    music = "--no-music" not in args
    BUILD.mkdir(exist_ok=True)
    parts, audio, srt, t = [], [], [], 0.0
    swells = []
    for n, scene, text in rows():
        kind, _, name = scene.partition(":")
        kind = kind.strip().split()[0]
        name = name.strip() or scene.split()[-1]
        length = row_length(n, kind)
        fitted = BUILD / f"fit-{n:02d}.mp4"
        fit(source_for(n, kind, name), length, fitted)
        parts.append(fitted)
        vo = HERE / "vo" / f"{n:02d}.mp3"
        padded = BUILD / f"vo-{n:02d}.wav"
        run(["-i", str(vo), "-af", f"apad=whole_dur={length:.3f}", "-t", f"{length:.3f}", "-ar", "48000", "-ac", "2", str(padded)])
        audio.append(padded)
        spoken = vo_seconds(n)
        srt.append(f"{len(srt) + 1}\n{srt_time(t + 0.1)} --> {srt_time(t + spoken + 0.3)}\n{text}\n")
        if name in ("title", "proof"):
            swells.append(t)
        print(f"{n:02d} {scene:<22} {length:5.1f}s  (spoken {spoken:4.1f}s)")
        t += length
    total = t
    print(f"total {total:.1f}s")
    if total > LIMIT:
        raise SystemExit(f"the film runs {total:.1f}s, over the {LIMIT:.0f}s limit: cut words in video/script.md")

    (BUILD / "list.txt").write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts), encoding="utf-8")
    run(["-f", "concat", "-safe", "0", "-i", str(BUILD / "list.txt"), "-c", "copy", str(BUILD / "video.mp4")])
    (BUILD / "audio.txt").write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in audio), encoding="utf-8")
    run(["-f", "concat", "-safe", "0", "-i", str(BUILD / "audio.txt"), "-c", "copy", str(BUILD / "voice.wav")])
    (BUILD / "captions.srt").write_text("\n".join(srt), encoding="utf-8")

    if music:
        custom = HERE / "music.mp3"
        if custom.exists():
            run(["-stream_loop", "-1", "-i", str(custom), "-t", f"{total:.3f}", "-ar", "48000", "-ac", "2",
                 "-af", f"afade=t=out:st={total - 3:.3f}:d=3", str(BUILD / "music.wav")])
        else:
            subprocess.run([sys.executable, str(HERE / "music.py"), f"{total:.3f}", "--out", str(BUILD / "music.wav"),
                            *(["--swell", *[f"{s:.3f}" for s in swells]] if swells else [])], check=True)
        # the bed at MUSIC_DB, ducked further whenever the voice speaks, then both summed
        run(["-i", str(BUILD / "voice.wav"), "-i", str(BUILD / "music.wav"), "-filter_complex",
             f"[1:a]volume={MUSIC_DB}dB[m];[m][0:a]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=600[d];"
             "[0:a][d]amix=inputs=2:duration=first:normalize=0[a]", "-map", "[a]", str(BUILD / "mix.wav")])
        mix = BUILD / "mix.wav"
    else:
        mix = BUILD / "voice.wav"

    srt_path = (BUILD / "captions.srt").resolve().as_posix().replace(":", "\\:")
    style = ("FontName=Geist,FontSize=15,PrimaryColour=&H00F5F5F2,OutlineColour=&H66000000,BackColour=&H66000000,"
             "BorderStyle=4,Outline=0,Shadow=0,MarginV=40,Alignment=2")
    run(["-i", str(BUILD / "video.mp4"), "-i", str(mix), "-vf", f"subtitles='{srt_path}':force_style='{style}'",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", "-shortest", str(out)])
    got = duration(out)
    print(json.dumps({"out": str(out), "seconds": round(got, 1), "under_limit": got <= LIMIT, "rows": len(parts)}))


if __name__ == "__main__":
    main(sys.argv[1:])
