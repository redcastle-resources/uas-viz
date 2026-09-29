# Lightweight DEM Static Site (MapLibre + COG)

A minimal static viewer for comparing 3 raster layers — pre-treatment DEM,
post-treatment DEM, and their difference — using [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/)
and the [`maplibre-cog-protocol`](https://github.com/geomatico/maplibre-cog-protocol)
plugin. No tile server or backend required: the rasters are read directly as
[Cloud Optimized GeoTIFFs](https://cogeo.org/) (COGs) straight from object
storage, using HTTP range requests.

## Folder layout

```text
dem-static-site/
├── index.html
├── config.js          # <- edit this to point at your 3 COGs
├── css/style.css
├── js/app.js
├── serve.ps1           # local dev only
├── serve_range.py       # local dev only
└── data/                # optional local COGs for dev (gitignored)
```

## 1. Generate the 3 COGs

Each `.tif` **must** be reprojected to `EPSG:3857` (Web Mercator) — this
library does not reproject, and will throw an error otherwise.

For elevation/difference rasters (float data), NaN is the ideal nodata value
and LERC compression gives good browser decode performance:

```bash
gdal_edit.py -a_nodata nan pre_treatment_source.tif

gdalwarp pre_treatment_source.tif pre_treatment.tif -of COG \
  -co TILING_SCHEME=GoogleMapsCompatible \
  -co COMPRESS=LERC -co MAX_Z_ERROR=0.1 \
  -co RESAMPLING=BILINEAR -co OVERVIEW_RESAMPLING=AVERAGE \
  -co OVERVIEWS=IGNORE_EXISTING -co ADD_ALPHA=NO
```

Repeat for `post_treatment.tif` and `difference.tif` (difference = post − pre,
computed with `gdal_calc.py` or in your GIS tool of choice before running
`gdalwarp`).

Sanity-check nodata/transparency before uploading:

```bash
gdalinfo difference.tif | grep -E 'NoData|Mask Flags'
```

## 2. Host the COGs

Upload the 3 files to public object storage that supports HTTP Range requests
(GCS, S3, Cloudflare R2, etc.) — reusing the same bucket/pattern already used
for point clouds in `potree-static-site/` is simplest:

```text
gs://uas-viz/dem_tifs/pre_treatment.tif
gs://uas-viz/dem_tifs/post_treatment.tif
gs://uas-viz/dem_tifs/difference.tif
```

If you want a small helper script for GCS uploads, use:

```powershell
python ..\tools\upload_cogs_to_gcs.py .\data -d gs://uas-viz/dem_tifs
```

The script preserves any subdirectory structure under the local input folder
and sets `Content-Type: image/tiff` plus a long-lived cache policy on each
uploaded object.

The bucket's CORS config (see `potree-static-site/gcs-cors.json`) already
allows `Range`/`Accept-Ranges`/`Content-Range` headers from any origin, so no
CORS changes should be needed if you reuse that bucket.

## 3. Point config.js at your data

Edit `config.js`:

- `cogBaseUrl` — the folder URL from step 2.
- `center` / `zoom` — initial map view over your AOI.
- Each entry in `layers[]` — `file` name, `colorRamp` (see the
  [color ramp cheatsheet](https://labs.geomatico.es/maplibre-cog-protocol/color-cheatsheet.html)),
  and `min`/`max` values that bound your data (elevation range for pre/post,
  a symmetric range like `-5`/`5` for the difference layer).

## Run locally on Windows

COG reads use HTTP Range requests even for local files, so use the bundled
range-supporting server (Python's plain `http.server` does not support Range):

```powershell
cd dem-static-site
./serve.ps1
```

Then open <http://localhost:8080/>.

To test against local files instead of the hosted bucket, drop your `.tif`s in
`data/` and temporarily point `cogBaseUrl` in `config.js` at `./data`.

## Deployment

This folder is deployed alongside the Potree viewer by
`.github/workflows/deploy-pages.yml`, which publishes it to GitHub Pages at
`/dem/` (Potree lives at `/potree/`, with a small landing page at `/`).

## Notes / next steps

- Currently one layer is shown at a time (radio buttons) with an opacity
  slider. A swipe/compare control or side-by-side view would be a natural
  next enhancement.
- The base map style (`https://demotiles.maplibre.org/style.json`) is
  MapLibre's free public demo style — swap for a hosted style (MapTiler,
  Protomaps, etc.) if you need more detail or offline tiles.
