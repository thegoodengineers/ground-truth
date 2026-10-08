"""Site smoke test (Playwright, Chromium).

Serves site/ with sample/data/ via a local HTTP server, then:
  1. Loads the page – no JS console errors.
  2. Verifies the freshness line and proof stats contain numbers.
  3. Runs the demo tour (?demo=1) and checks all milestones are reached.
  4. Clicks a monitor chip and verifies the panel shows three checks.
  5. Repeats 1–4 with --disable-webgl to exercise the no-WebGL fallback.

Run:
    pytest tests/site/smoke.py
"""
import http.server
import os
import pathlib
import re
import threading

import pytest

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent.parent
SITE = ROOT / "site"
DATA = ROOT / "sample" / "data"


class _Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def translate_path(self, path):
        # /data/... -> sample/data/..., everything else -> site/...
        if path.startswith("/data/"):
            return str(DATA / path[6:])
        return str(SITE / path.lstrip("/"))


@pytest.fixture(scope="module")
def base_url():
    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def _smoke(page, url):
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(url, wait_until="networkidle", timeout=30_000)
    # freshness line present and non-empty
    fresh = page.locator("#fresh").text_content(timeout=5_000)
    assert fresh and fresh.strip() and fresh != "–", f"freshness empty: {fresh!r}"
    # proof stats are numbers
    for sel in ("#stat-flag", "#stat-watch", "#stat-ok"):
        txt = page.locator(sel).text_content(timeout=3_000)
        assert txt and re.search(r"\d", txt), f"{sel} not a number: {txt!r}"
    # no JS errors
    assert not errors, f"console errors: {errors}"


def _tour(page, url):
    """Run the demo tour and assert all milestones complete."""
    page.goto(f"{url}/?demo=1", wait_until="networkidle", timeout=30_000)
    page.wait_for_function("window.__milestones && window.__milestones.some(m => m.name === 'tour:end')",
                           timeout=60_000)
    milestones = page.evaluate("window.__milestones.map(m => m.name)")
    for m in ("tour:start", "tour:physics", "tour:chart", "tour:history", "tour:end"):
        assert m in milestones, f"milestone missing: {m}"


def _panel(page, url):
    """Click the first monitor chip and verify the panel shows three checks."""
    page.goto(url, wait_until="networkidle", timeout=30_000)
    chip = page.locator("#areas button").first
    chip.click()
    page.wait_for_selector(".checks li", timeout=10_000)
    checks = page.locator(".checks li").count()
    assert checks == 3, f"expected 3 check rows, got {checks}"


@pytest.mark.parametrize("webgl", [True, False], ids=["webgl", "no-webgl"])
def test_smoke(base_url, playwright, webgl):
    args = [] if webgl else ["--disable-webgl"]
    launch_kwargs = {"args": ["--no-sandbox", "--disable-dev-shm-usage", "--enable-unsafe-swiftshader"] + args}
    if os.environ.get("CHROMIUM_PATH"):
        launch_kwargs["executable_path"] = os.environ["CHROMIUM_PATH"]
    browser = playwright.chromium.launch(**launch_kwargs)
    ctx = browser.new_context()
    page = ctx.new_page()
    try:
        _smoke(page, base_url)
        _panel(page, base_url)
    finally:
        ctx.close()
        browser.close()


def test_tour(base_url, playwright):
    launch_kwargs = {"args": ["--no-sandbox", "--disable-dev-shm-usage", "--enable-unsafe-swiftshader"]}
    if os.environ.get("CHROMIUM_PATH"):
        launch_kwargs["executable_path"] = os.environ["CHROMIUM_PATH"]
    browser = playwright.chromium.launch(**launch_kwargs)
    ctx = browser.new_context()
    page = ctx.new_page()
    try:
        _tour(page, base_url)
    finally:
        ctx.close()
        browser.close()
