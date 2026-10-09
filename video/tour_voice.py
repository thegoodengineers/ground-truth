"""The 60-second tour's voice-over: one MP3 per step and language, in site/audio/tour-<lang>-<step>.mp3.

    set ELEVENLABS_API_KEY=<your key>          (Command Prompt; in PowerShell: $env:ELEVENLABS_API_KEY="<your key>")
    python video/tour_voice.py                 # ElevenLabs, English and Hindi, all 7 steps
    python video/tour_voice.py --lang en       # one language
    python video/tour_voice.py --voice <id>    # another ElevenLabs voice (default: Rachel)
    python video/tour_voice.py --engine edge   # the free edge-tts voice instead, no key needed

The key is read from the environment only: never put it in a file, a commit or a chat. The site's tour plays a
step's file and moves on when it ends, so the lines below are the captions, said aloud. A line naming a station
the tour picks at run time (step 3) says "this monitor" instead.
"""
import argparse, asyncio, json, os, sys, urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "site" / "audio"
ELEVEN = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_64"
RACHEL = "21m00Tcm4TlvDq8ikWAM"  # an ElevenLabs default voice; eleven_multilingual_v2 speaks Hindi with it too
EDGE = {"en": "en-IN-NeerjaNeural", "hi": "hi-IN-SwaraNeural"}

LINES = {
    "en": [
        "Fifty-two air-quality monitors across Delhi and the NCR, checked every hour.",
        "Delhi in 3D. Each mast is a monitor. Its column is as tall as its PM 2.5 reading, and the smog is thicker where the air is worse.",
        "This monitor reports readings that can't be real. Its numbers don't add up.",
        "Anand Vihar, hour by hour, against the four stations around it. The shaded band is eleven in the morning to five in the evening.",
        "Jahangirpuri, against its own last three weeks. Worth a look, not proof.",
        "When a station is in doubt, use what the stations around it read right now.",
        "A flag means the numbers don't add up. Not that anyone cheated.",
    ],
    "hi": [
        "दिल्ली और एन सी आर के बावन वायु-गुणवत्ता मॉनिटर, हर घंटे जाँचे जाते हैं।",
        "3D में दिल्ली। हर खंभा एक मॉनिटर है। उसका स्तंभ उसकी पी एम ढाई की रीडिंग जितना ऊँचा है, और जहाँ हवा ज़्यादा ख़राब है वहाँ धुंध घनी है।",
        "यह मॉनिटर ऐसी रीडिंग भेजता है जो असली हो ही नहीं सकतीं। इसके आँकड़े मेल नहीं खाते।",
        "आनंद विहार, घंटे-दर-घंटे, आस-पास के चार स्टेशनों के मुकाबले। रंगी हुई पट्टी सुबह ग्यारह से शाम पाँच बजे तक है।",
        "जहाँगीरपुरी, अपने पिछले तीन हफ़्तों के मुकाबले। देखने लायक, पर सबूत नहीं।",
        "जब किसी स्टेशन पर शक हो, तो आस-पास के स्टेशनों की अभी की रीडिंग इस्तेमाल करें।",
        "फ़्लैग का मतलब है कि आँकड़े मेल नहीं खाते। यह नहीं कि किसी ने धोखा दिया।",
    ],
}


def eleven(text, voice, key):
    body = {"text": text, "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.55, "similarity_boost": 0.75, "style": 0.15}}
    req = urllib.request.Request(ELEVEN.format(voice=voice), data=json.dumps(body).encode(), method="POST",
                                 headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


async def edge(text, lang, path):
    import edge_tts  # in requirements-dev.txt
    await edge_tts.Communicate(text, EDGE[lang], rate="+5%").save(str(path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", nargs="+", default=["en", "hi"], choices=sorted(LINES))
    ap.add_argument("--engine", default="elevenlabs", choices=["elevenlabs", "edge"])
    ap.add_argument("--voice", default=RACHEL, help="ElevenLabs voice id")
    a = ap.parse_args()
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if a.engine == "elevenlabs" and not key:
        sys.exit("Set ELEVENLABS_API_KEY in this terminal first (see the top of this file), or use --engine edge.")
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in a.lang:
        for i, text in enumerate(LINES[lang], 1):
            path = OUT / f"tour-{lang}-{i}.mp3"
            if a.engine == "elevenlabs":
                path.write_bytes(eleven(text, a.voice, key))
            else:
                asyncio.run(edge(text, lang, path))
            print(f"{path.name}  {path.stat().st_size // 1024} KB  {text[:60]}")


if __name__ == "__main__":
    main()
