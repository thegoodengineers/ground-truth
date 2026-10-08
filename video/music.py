"""A procedural ambient bed for the video (numpy, no licence needed): video/build/music.wav.

    python video/music.py SECONDS [--swell 20.5 95.0] [--fade 3]

Slow detuned pads on A, E and C-sharp with a breathing low-pass noise wash, in stereo, with a gentle swell at
each --swell time (the title and the proof) and a fade over the last --fade seconds. assemble.py ducks it under
the voice. To use a CC BY track instead, save it as video/music.mp3 and credit it in the YouTube description.
"""
import sys, wave

import numpy as np

SR = 48000


def pad(t, f, detune=0.4, vib=0.08):
    """Three detuned sines with slow vibrato, softened by their own second harmonic."""
    out = np.zeros_like(t)
    for d in (-detune, 0.0, detune):
        ph = 2 * np.pi * (f + d) * t + 0.6 * np.sin(2 * np.pi * vib * t + d)
        out += np.sin(ph) + 0.25 * np.sin(2 * ph)
    return out / 3.75


def lowpass_noise(n, cutoff_hz, seed=1):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n)
    a = np.exp(-2 * np.pi * cutoff_hz / SR)
    y = np.empty(n)
    acc = 0.0
    for i in range(n):  # one-pole, fine for a few million samples
        acc = a * acc + (1 - a) * x[i]
        y[i] = acc
    return y / (np.abs(y).max() + 1e-9)


def bed(seconds, swells=(), fade=3.0):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    chord = 0.5 * pad(t, 110.0) + 0.35 * pad(t, 164.81, vib=0.05) + 0.25 * pad(t, 277.18, vib=0.11) + 0.3 * pad(t, 55.0, vib=0.03)
    breath = 0.5 + 0.5 * np.sin(2 * np.pi * t / 14.0)  # a 14-second breath
    wash = lowpass_noise(n, 420.0) * (0.12 + 0.1 * breath)
    mix = chord * (0.55 + 0.25 * breath) + wash
    env = np.ones(n)
    for s in swells:  # a 6-second rise to +60% and a slow return
        env += 0.6 * np.exp(-0.5 * ((t - s - 2.0) / 3.0) ** 2)
    env[: int(2 * SR)] *= np.linspace(0, 1, int(2 * SR))
    f = int(fade * SR)
    if f and f < n:
        env[-f:] *= np.linspace(1, 0, f)
    mix *= env
    mix /= np.abs(mix).max() + 1e-9
    left = mix
    right = np.roll(mix, int(0.011 * SR)) * 0.96 + 0.04 * mix  # a little width
    return np.stack([left, right], axis=1) * 0.9


def write(path, stereo):
    data = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def main(args):
    seconds = float(args[0])
    swells = [float(x) for x in args[args.index("--swell") + 1:] if x.replace(".", "").isdigit()] if "--swell" in args else []
    fade = float(args[args.index("--fade") + 1]) if "--fade" in args else 3.0
    out = args[args.index("--out") + 1] if "--out" in args else "video/build/music.wav"
    write(out, bed(seconds, swells, fade))
    print(f"{seconds:.1f}s of ambient bed -> {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
