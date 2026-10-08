"""The HTTPS front (src/serve.py): paths, headers, caching, and that it matches the CloudFront policy."""
import base64, gzip, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import serve  # noqa: E402

FILES = {
    "index.html": (b"<!doctype html><h1>Ground Truth</h1>" + b" " * 2000, {"etag": '"abc"'}),
    "app.js": (b"console.log(1)", {"content_type": "application/javascript"}),
    "data/latest.json": (b'{"stations": []}', {"cache_control": "public, max-age=300", "etag": '"d1"'}),
    "og.png": (b"\x89PNG\r\n\x1a\n" + bytes(range(256)), {"content_type": "image/png"}),
}


def get(key):
    return FILES.get(key)


def req(path, **headers):
    return {"rawPath": path, "requestContext": {"http": {"method": "GET"}}, "headers": headers}


def test_root_and_directories_read_index_html():
    assert serve.key_for("/") == "index.html"
    assert serve.key_for("") == "index.html"
    assert serve.key_for("/docs/") == "docs/index.html"
    assert serve.key_for("/app.js") == "app.js"
    assert serve.key_for("/../secret") is None


def test_html_comes_with_every_security_header():
    r = serve.serve(req("/"), get)
    assert r["statusCode"] == 200
    h = r["headers"]
    for name, value in serve.SECURITY_HEADERS.items():
        assert h[name] == value
    assert h["content-type"] == "text/html"
    assert "Ground Truth" in r["body"] and not r.get("isBase64Encoded")


def test_content_types_and_cache_rules():
    assert serve.serve(req("/app.js"), get)["headers"]["content-type"] == "application/javascript"
    assert serve.serve(req("/app.js"), get)["headers"]["cache-control"] == serve.DEFAULT_CACHE
    assert serve.serve(req("/data/latest.json"), get)["headers"]["cache-control"] == "public, max-age=300"
    assert serve.cache_control("vendor/three/three.module.min.js") == "public, max-age=604800"
    assert serve.content_type("x.bin", "binary/octet-stream") == "application/octet-stream"


def test_binary_is_base64_and_text_gzips_when_asked():
    png = serve.serve(req("/og.png"), get)
    assert png["isBase64Encoded"] and base64.b64decode(png["body"]).startswith(b"\x89PNG")
    assert "content-encoding" not in png["headers"]
    z = serve.serve(req("/", **{"accept-encoding": "gzip, br"}), get)
    assert z["headers"]["content-encoding"] == "gzip" and z["headers"]["vary"] == "Accept-Encoding"
    assert b"Ground Truth" in gzip.decompress(base64.b64decode(z["body"]))
    small = serve.serve(req("/app.js", **{"accept-encoding": "gzip"}), get)
    assert "content-encoding" not in small["headers"]  # under MIN_GZIP: not worth it


def test_etag_gives_304_and_missing_gives_404():
    r = serve.serve(req("/", **{"if-none-match": '"abc"'}), get)
    assert r["statusCode"] == 304 and r["headers"]["etag"] == '"abc"' and r["headers"]["x-frame-options"] == "DENY"
    r = serve.serve(req("/nope.txt"), get)
    assert r["statusCode"] == 404 and r["headers"]["cache-control"] == "no-store"
    r = serve.serve({"rawPath": "/", "requestContext": {"http": {"method": "POST"}}}, get)
    assert r["statusCode"] == 405


def test_headers_match_the_cloudfront_policy():
    """One source of truth for the policy: the CloudFront ResponseHeadersPolicy in template.yaml."""
    text = open(os.path.join(HERE, "..", "template.yaml"), encoding="utf-8").read()
    block = text[text.index("SiteHeaders:"):text.index("IngestFunction:")]
    csp = " ".join(re.search(r"ContentSecurityPolicy: >-\n((?:\s+.+\n)+?)\s+StrictTransportSecurity", block)
                   .group(1).split())
    assert csp == serve.CSP
    assert "AccessControlMaxAgeSec: 31536000" in block and "IncludeSubdomains: true" in block and "Preload: true" in block
    assert serve.SECURITY_HEADERS["strict-transport-security"] == "max-age=31536000; includeSubDomains; preload"
    assert re.search(r"ReferrerPolicy: strict-origin-when-cross-origin", block)
    assert serve.SECURITY_HEADERS["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "FrameOption: DENY" in block and serve.SECURITY_HEADERS["x-frame-options"] == "DENY"
    assert re.search(r"Value: " + re.escape(serve.SECURITY_HEADERS["permissions-policy"]), block)
