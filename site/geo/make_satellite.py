"""The ground under the 3D city: a real Sentinel-2 image of Delhi, from the Registry of Open Data on AWS.

    python site/geo/make_satellite.py [--size 2048] [--out site/geo/delhi_satellite.jpg] [--region src/regions/delhi.json]

Finds the newest cloud-free Sentinel-2 L2A scenes over the region's bounding box through the Earth Search STAC
API (Element 84, over the public `sentinel-cogs` bucket), reads just the overview each scene needs from its
true-colour Cloud-Optimised GeoTIFF (a few MB per tile, not the 100 MB file), warps the tiles onto the plain
lat/lon grid the scene uses (1 unit = 100 m, x east, z south) and writes one JPEG plus a .json sidecar with the
bounds and the credit line. No key, no tile server at runtime: the image is vendored with the site.

Credit: Contains modified Copernicus Sentinel data (year), processed by Element 84 / Sinergise, via the Registry of
Open Data on AWS. Free to use with that line.
"""
import argparse, datetime as dt, json, math, os, sys, urllib.request

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.transform import from_bounds
from PIL import Image

STAC = "https://earth-search.aws.element84.com/v1/search"


def search(bbox, max_cloud=8, since="2025-01-01"):
    body = {"collections": ["sentinel-2-l2a"], "bbox": bbox, "limit": 200,
            "datetime": f"{since}T00:00:00Z/{dt.date.today().isoformat()}T23:59:59Z",
            "query": {"eo:cloud_cover": {"lt": max_cloud}}, "sortby": [{"field": "properties.datetime", "direction": "desc"}]}
    req = urllib.request.Request(STAC, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        feats = json.load(r)["features"]
    best = {}  # one scene per MGRS tile: the newest with the least cloud among the newest few
    for f in feats:
        tile = f["properties"].get("grid:code") or f["id"].split("_")[1]
        if tile not in best:
            best[tile] = f
    return best


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=2048)
    ap.add_argument("--out", default="site/geo/delhi_satellite.jpg")
    ap.add_argument("--region", default="src/regions/delhi.json")
    ap.add_argument("--pad", type=float, default=0.08, help="degrees of margin around the region's bounding box")
    a = ap.parse_args(args)
    region = json.load(open(a.region, encoding="utf-8"))
    (lat0, lat1), (lon0, lon1) = region["bbox"]["lat"], region["bbox"]["lon"]
    lat0, lat1, lon0, lon1 = lat0 - a.pad, lat1 + a.pad, lon0 - a.pad, lon1 + a.pad
    # the scene's plane: x east and z south, in units of 100 m; keep the image's pixels square in those units
    kx = 111320 * math.cos(math.radians((lat0 + lat1) / 2)) / 100
    kz = 110540 / 100
    w_units, h_units = (lon1 - lon0) * kx, (lat1 - lat0) * kz
    width = a.size if w_units >= h_units else round(a.size * w_units / h_units)
    height = a.size if h_units >= w_units else round(a.size * h_units / w_units)
    dst_transform = from_bounds(lon0, lat0, lon1, lat1, width, height)
    mosaic = np.zeros((3, height, width), dtype=np.uint8)
    filled = np.zeros((height, width), dtype=bool)

    scenes = search([lon0, lat0, lon1, lat1])
    if not scenes:
        sys.exit("no cloud-free Sentinel-2 scene found")
    years, used = set(), []
    for tile, f in sorted(scenes.items()):
        href = f["assets"]["visual"]["href"]
        print(f"{tile}: {f['properties']['datetime'][:10]}, cloud {f['properties']['eo:cloud_cover']:.1f}%  {href.split('/')[-1]}")
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
            with rasterio.open(href) as src:
                # read an overview close to the output resolution (about 10980 px per 110 km at full res)
                scale = max(1, int(src.width / (width * 1.6)))
                out_shape = (3, src.height // scale, src.width // scale)
                data = src.read(out_shape=out_shape, resampling=Resampling.average)
                src_transform = src.transform * src.transform.scale(src.width / out_shape[2], src.height / out_shape[1])
                part = np.zeros_like(mosaic)
                reproject(data, part, src_transform=src_transform, src_crs=src.crs, dst_transform=dst_transform,
                          dst_crs="EPSG:4326", resampling=Resampling.bilinear, src_nodata=0, dst_nodata=0)
        has = part.max(axis=0) > 0
        take = has & ~filled
        mosaic[:, take] = part[:, take]
        filled |= take
        years.add(f["properties"]["datetime"][:4])
        used.append({"tile": tile, "date": f["properties"]["datetime"][:10], "cloud": f["properties"]["eo:cloud_cover"], "id": f["id"]})
    print(f"covered {100 * filled.mean():.1f}% of the box with {len(used)} tiles")

    img = Image.fromarray(np.moveaxis(mosaic, 0, -1), "RGB")
    # a touch of contrast and a lift in the shadows: Sentinel true colour is flat and dark over a city
    arr = np.asarray(img).astype(np.float32) / 255
    arr = np.clip((arr - 0.02) * 1.25, 0, 1) ** 0.9
    img = Image.fromarray((arr * 255).astype(np.uint8), "RGB")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    img.save(a.out, "JPEG", quality=82, optimize=True, progressive=True)
    credit = f"Contains modified Copernicus Sentinel data {'/'.join(sorted(years))}, processed by Element 84 and Sinergise, via the Registry of Open Data on AWS"
    json.dump({"bounds": {"lat": [lat0, lat1], "lon": [lon0, lon1]}, "width": width, "height": height, "scenes": used,
               "credit": credit, "licence": "Copernicus Sentinel data: free, full and open access; the credit line is required"},
              open(os.path.splitext(a.out)[0] + ".json", "w", encoding="utf-8"), indent=1)
    print(f"{width}x{height} -> {a.out} ({os.path.getsize(a.out) / 1e6:.2f} MB); {credit}")


if __name__ == "__main__":
    main(sys.argv[1:])
