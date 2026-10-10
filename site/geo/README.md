# geo

Base geography for the 3D map, so the city draws even without a tile server.

- `delhi_wards.json`: Delhi municipal ward boundaries, simplified for the web.
- `delhi_boundary.json`: the Delhi NCT boundary, simplified.
- `delhi_satellite.jpg` + `.json`: the ground under the 3D city, a cloud-free Sentinel-2 true-colour mosaic of the region (5 Oct 2026, four MGRS tiles) on the plain lat/lon grid the scene uses, made by `make_satellite.py` from the Cloud-Optimised GeoTIFFs on the Registry of Open Data on AWS (`sentinel-cogs`, found through the Earth Search STAC API). Run it again for a newer image or another region (`--region src/regions/<city>.json`). Credit, required: *Contains modified Copernicus Sentinel data 2026, processed by Element 84 and Sinergise, via the Registry of Open Data on AWS.*

Source: [Delhi Municipal Spatial Data](https://github.com/datameet/Municipal_Spatial_Data/tree/master/Delhi) by the [DataMeet India community](http://datameet.org/), licensed [CC BY-SA 2.5 India](http://creativecommons.org/licenses/by-sa/2.5/in/). These simplified files are shared under the same licence.
