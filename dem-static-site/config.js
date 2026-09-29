// Edit this file to point at your generated Cloud Optimized GeoTIFFs (COGs).
// Requirements for each COG (see README.md "COG generation" section):
//   - Reprojected to EPSG:3857 (Web Mercator) — maplibre-cog-protocol does not reproject.
//   - Single-band elevation/difference data, ideally LERC-compressed with a NaN/nodata value set.
//   - Hosted somewhere that supports HTTP Range requests (GCS, S3, Cloudflare R2, etc.).
window.DEM_CONFIG = {
  // Base URL where the 3 COG files are hosted. Re-uses the same public GCS bucket
  // pattern as potree-static-site/index.html (see gcs-cors.json for the CORS config).
  cogBaseUrl: 'https://storage.googleapis.com/uas-viz/dem_tifs',

  // Initial map view — update to center on your AOI.
  center: [-120.0, 39.0],
  zoom: 12,

  // One entry per raster. `colorRamp` names come from the ColorBrewer/CARTOColor
  // cheatsheet: https://labs.geomatico.es/maplibre-cog-protocol/color-cheatsheet.html
  layers: [
    {
      id: 'pre',
      label: 'Pre-treatment DEM',
      file: 'pre_treatment.tif',
      colorRamp: 'BrewerYlGn9',
      min: 1400,
      max: 2200,
      reverse: false,
    },
    {
      id: 'post',
      label: 'Post-treatment DEM',
      file: 'post_treatment.tif',
      colorRamp: 'BrewerYlGn9',
      min: 1400,
      max: 2200,
      reverse: false,
    },
    {
      id: 'diff',
      label: 'Difference (Post \u2212 Pre)',
      file: 'difference.tif',
      colorRamp: 'BrewerRdBu11',
      min: -5,
      max: 5,
      reverse: true, // reversed so gain (positive) reads blue and loss (negative) reads red
    },
  ],
};
