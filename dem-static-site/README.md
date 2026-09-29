# Lightweight DEM Static Site (MapLibre GL + COG)

A minimal static viewer for comparing 3 raster layers — pre-treatment DEM,
post-treatment DEM, and their difference — using [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/docs/)
with a plain raster XYZ basemap (CARTO Positron, no API key) and the
[`maplibre-cog-protocol`](https://github.com/geomatico/maplibre-cog-protocol)
plugin. No tile server or backend required: the rasters are read directly as
[Cloud Optimized GeoTIFFs](https://cogeo.org/) (COGs) straight from object
storage, using HTTP range requests.

This used to run on Mapbox GL JS with the vector "Standard" style, but that
style defaults to a **globe projection** at low zoom, which fought with the
raster COG overlays and required a Mapbox access token. Switching to
MapLibre GL JS with a flat raster basemap avoids the globe entirely (MapLibre
has no built-in globe projection), needs no token, and keeps the basemap out
of the way of the color-ramp overlays.

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
  -co ZOOM_LEVEL_STRATEGY=UPPER \
  -co OVERVIEWS=IGNORE_EXISTING -co ADD_ALPHA=NO
```

`ZOOM_LEVEL_STRATEGY=UPPER` matters for high-resolution UAS outputs: GDAL's
COG driver has to snap your source pixel size to the nearest Web Mercator
zoom level, and its default (`AUTO`) picks whichever zoom is numerically
closest — which can round *down* and quietly throw away up to half your
resolution. `UPPER` always rounds up instead, so the COG never has coarser
resolution than the source. `tools/convert_tifs_to_cogs.py` already defaults
to `UPPER` for this reason.

Repeat for `post_treatment.tif` and `difference.tif` (difference = post − pre,
computed with `gdal_calc.py` or in your GIS tool of choice before running
`gdalwarp`).

Sanity-check nodata/transparency before uploading:

```bash
gdalinfo pre_treatment.tif | grep -E 'NoData|Mask Flags|Pixel Size'
```

To confirm the COG actually preserved native resolution, compare `Pixel Size`
above (in the source's original CRS units) against the source raster's own
`gdalinfo`, and check the zoom level the browser stops sharpening at —
`maplibre-cog-protocol` derives the raster source's `maxzoom` directly from
the COG's finest image resolution (`zoom = log2(40075016.686 / (256 *
pixel_size_m))`). Zooming in further than that is expected to look blocky:
MapLibre GL JS is upsampling the highest-resolution tile available, the same
as any fixed-resolution raster pyramid — there is no more real detail to
show past that point.

## 2. Host the COGs

Upload the 3 files to public object storage that supports HTTP Range requests
(GCS, S3, Cloudflare R2, etc.) — reusing the same bucket/pattern already used
for point clouds in `potree-static-site/` is simplest:

```text
gs://uas-viz/dem_tifs/pre_treatment.tif
gs://uas-viz/dem_tifs/post_treatment.tif
gs://uas-viz/dem_tifs/difference.tif
```

If you want a small helper script to convert the rasters to COGs and upload
them to GCS in one step, use:

```powershell
python ..\tools\convert_and_upload_cogs.py .\data -d gs://uas-viz/dem_tifs
```

If you already have COGs and only want to upload them, use the upload helper:

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

- `basemapStyle` — an inline MapLibre style object. Defaults to a plain
  raster XYZ basemap (CARTO Positron, no API key required); swap in any
  other raster tile source or a full vector style URL if you want a
  different look, but avoid globe-projected styles (see the note above).
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

- Multiple layers can be shown at once using the checkboxes. The opacity
  slider controls the most recently enabled visible layer.
- The base map uses a plain raster XYZ basemap (CARTO Positron, no API key,
  no globe projection) defined inline as a MapLibre style object in
  `config.js` (`basemapStyle`). Raster overlays are added on top with no
  slot/ordering system needed since the basemap has no labels or 3D
  fragments — see `js/app.js` if you want to swap in a different basemap.

## Nodata masking

All 6 hosted COGs (`2025/GumRidge5_DTM.tif`, `2025/GumRidge6_DTM.tif`,
`2026/AOI5_DTM.tif`, `2026/AOI6_DTM.tif`,
`difference/AOI5_Difference26_25.tif`, `difference/AOI6_Difference26_25.tif`)
are float32 with `nodata = NaN` (verified via `rasterio` over `/vsicurl/`),
matching the `--nodata nan` default in `tools/convert_tifs_to_cogs.py`.

No extra config is needed to mask these out: `maplibre-cog-protocol` reads
the `GDAL_NODATA` TIFF tag from each COG automatically and renders any pixel
matching that value (here, `NaN`) as fully transparent (`alpha = 0`) before
handing tiles to MapLibre — see `cogProtocol`/`vB`/`lI` in
[`maplibre-cog-protocol`'s bundle](https://unpkg.com/@geomatico/maplibre-cog-protocol/dist/index.js).
If a future raster is missing/incorrect nodata, re-run
`gdal_edit.py -a_nodata nan your_raster.tif` (or re-export with
`tools/convert_tifs_to_cogs.py`, whose default `--nodata` is `nan`) before
uploading — no changes to `config.js`/`js/app.js` are required for masking.
