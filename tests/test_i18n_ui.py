"""Every phrase app.js passes through tx("...") or tr`...` needs a Hindi entry in i18n.js's UI table; a missing one
shows English in the middle of a Hindi page. This names each phrase that has none."""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "..", "site")


def ui_keys():
    js = open(os.path.join(SITE, "i18n.js"), encoding="utf-8").read()
    block = js[js.index("const UI = {"):js.index("\n  };", js.index("const UI = {"))]
    return {k.replace('\\"', '"') for k in re.findall(r'^\s*"((?:[^"\\]|\\.)*)":', block, re.M)}


def phrases():
    js = open(os.path.join(SITE, "app.js"), encoding="utf-8").read()
    out = {m.replace('\\"', '"') for m in re.findall(r'\btx\("((?:[^"\\]|\\.)*)"\)', js)}
    for body in re.findall(r"\btr`([^`]*)`", js):
        parts = re.split(r"\$\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", body)
        out.add("".join(p + (f"{{{i}}}" if i < len(parts) - 1 else "") for i, p in enumerate(parts)))
    return out - {"..."}  # tr`...` in a comment


def test_every_app_phrase_has_hindi():
    found = phrases()
    assert len(found) > 100
    assert sorted(found - ui_keys()) == []
