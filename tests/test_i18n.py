"""The Hindi page dictionary (site/i18n.js) is keyed by the English text of index.html. When that text changes, the
key no longer matches and Hindi visitors silently get English: this test names every key that went stale."""
import html, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "..", "site")


def page_keys():
    js = open(os.path.join(SITE, "i18n.js"), encoding="utf-8").read()
    block = js[js.index("const PAGE = {"):js.index("\n  };", js.index("const PAGE = {"))]
    return [k.replace('\\"', '"') for k in re.findall(r'^\s*"((?:[^"\\]|\\.)*)":', block, re.M)]


def squash(s):
    return re.sub(r"\s+", "", s)


def test_every_hindi_block_still_exists_in_the_pages():
    src = "".join(open(os.path.join(SITE, page), encoding="utf-8").read() for page in ("index.html", "method.html"))
    src = re.sub(r"<(script|style|svg)\b.*?</\1>", "", src, flags=re.S)
    text = squash(html.unescape(re.sub(r"<[^>]+>", "", src)))
    keys = page_keys()
    assert len(keys) > 100
    assert [k for k in keys if squash(k) not in text] == []
