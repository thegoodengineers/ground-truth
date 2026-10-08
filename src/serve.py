"""Serve the site from the bucket over HTTPS, with the security headers, from a Lambda function URL.

CloudFront is the intended front (template.yaml, UseCloudFront=true), but a new account can't create distributions
until AWS Support verifies it. Until then this function is the HTTPS origin: GET /path reads `path` from the site
bucket (`/` and `/dir/` read index.html), answers 304 to a matching If-None-Match, gzips text when asked, and sends
the same headers as the CloudFront response headers policy (tests/test_serve.py checks they stay identical).

Environment: SITE_BUCKET (required).
"""
import base64, gzip, mimetypes, os

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; "
       "worker-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
       "upgrade-insecure-requests")
SECURITY_HEADERS = {
    "content-security-policy": CSP,
    "strict-transport-security": "max-age=31536000; includeSubDomains; preload",
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "x-frame-options": "DENY",
    "x-xss-protection": "1; mode=block",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
}
TEXT_TYPES = ("application/json", "application/javascript", "text/javascript", "image/svg+xml", "application/xml")
CACHE = {"vendor/": "public, max-age=604800", "geo/": "public, max-age=86400", "data/": "public, max-age=300"}
DEFAULT_CACHE = "public, max-age=300"
MIN_GZIP = 1024
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/json", ".json")


def key_for(path):
    """The object key for a request path: the directory index for '/' and 'dir/', no leading slash, no '..'."""
    path = path or "/"
    if path.endswith("/"):
        path += "index.html"
    key = path.lstrip("/")
    if ".." in key.split("/"):
        return None
    return key or "index.html"


def content_type(key, stored=None):
    if stored and stored != "binary/octet-stream":
        return stored
    return mimetypes.guess_type(key)[0] or "application/octet-stream"


def cache_control(key, stored=None):
    if stored:
        return stored
    for prefix, value in CACHE.items():
        if key.startswith(prefix):
            return value
    return DEFAULT_CACHE


def response(status, body=b"", headers=None, ctype="text/plain; charset=utf-8", gzip_ok=False):
    h = {**SECURITY_HEADERS, "content-type": ctype, **(headers or {})}
    is_text = ctype.startswith("text/") or any(ctype.startswith(t) for t in TEXT_TYPES)
    if gzip_ok and is_text and len(body) >= MIN_GZIP:
        body = gzip.compress(body, 6)
        h["content-encoding"] = "gzip"
        h["vary"] = "Accept-Encoding"
    if is_text and "content-encoding" not in h:
        return {"statusCode": status, "headers": h, "body": body.decode("utf-8")}
    return {"statusCode": status, "headers": h, "body": base64.b64encode(body).decode(), "isBase64Encoded": True}


def serve(event, get_object):
    """`get_object(key)` -> (body bytes, {"etag", "content_type", "cache_control"}) or None when missing."""
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    if method not in ("GET", "HEAD"):
        return response(405, b"Method not allowed", {"allow": "GET, HEAD"})
    key = key_for(event.get("rawPath", "/"))
    if key is None:
        return response(400, b"Bad request")
    found = get_object(key)
    if found is None:
        return response(404, b"Not found", {"cache-control": "no-store"})
    body, meta = found
    req_headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    etag = meta.get("etag")
    headers = {"cache-control": cache_control(key, meta.get("cache_control"))}
    if etag:
        headers["etag"] = etag
        if req_headers.get("if-none-match") == etag:
            return {"statusCode": 304, "headers": {**SECURITY_HEADERS, **headers}, "body": ""}
    ctype = content_type(key, meta.get("content_type"))
    gzip_ok = "gzip" in req_headers.get("accept-encoding", "")
    return response(200, b"" if method == "HEAD" else body, headers, ctype, gzip_ok)


def handler(event, context):
    import boto3  # in the Lambda runtime; not needed for tests
    s3, bucket = boto3.client("s3"), os.environ["SITE_BUCKET"]

    def get_object(key):
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
        except s3.exceptions.NoSuchKey:
            return None
        return obj["Body"].read(), {"etag": obj.get("ETag"), "content_type": obj.get("ContentType"),
                                    "cache_control": obj.get("CacheControl")}
    return serve(event, get_object)
