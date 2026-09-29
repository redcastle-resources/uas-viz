// Edit this file to point at your generated Cloud Optimized GeoTIFFs (COGs).
// Requirements for each COG (see README.md "COG generation" section):
//   - Reprojected to EPSG:3857 (Web Mercator) — maplibre-cog-protocol does not reproject.
//   - Single-band elevation/difference data, ideally LERC-compressed with a NaN/nodata value set.
//   - Hosted somewhere that supports HTTP Range requests (GCS, S3, Cloudflare R2, etc.).
window.DTM_CONFIG = {
  // Plain raster XYZ basemap (CARTO Positron, no API key required) rendered
  // as a flat MapLibre style — no vector fragments, no 3D terrain/buildings,
  // and (unlike Mapbox GL JS's "Standard" style) no globe projection to fight
  // with at low zoom. Light/muted tiles keep the color-ramp overlays legible.
  basemapStyle: {
    version: 8,
    sources: {
      basemap: {
        type: 'raster',
        tiles: [
          'https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=cb1_43mw_1_b625104a56feb28a35a62b18',
        ],
        tileSize: 256,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      },
    },
    layers: [{ id: 'basemap', type: 'raster', source: 'basemap' }],
  },

  // Base URL where the COG files are hosted. Re-uses the same public GCS bucket
  // pattern as potree-static-site/index.html (see gcs-cors.json for the CORS config).
  cogBaseUrl: 'https://storage.googleapis.com/uas-viz/cogs',

  // Map centered on the AOI footprint 
  center: [-89.514280, 37.799070],

  zoom: 17.5,

  // One entry per raster. `colorRamp` names come from the ColorBrewer/CARTOColor
  // cheatsheet: https://labs.geomatico.es/maplibre-cog-protocol/color-cheatsheet.html
  // min/max below were measured from each hosted COG's actual valid-pixel
  // range (excluding nodata) via rasterio over /vsicurl/.
  // The two AOI5 DTMs and two AOI6 DTMs share a range so pre/post are visually comparable.
  // Layers that share a `group` key are toggled together in the panel as a single
  // checkbox (e.g. AOI5 + AOI6 pre-treatment hillshades); `groupLabel` names that checkbox.
  layers: [
    {
      id: 'pre_gumridge5_hillshade',
      label: 'Pre-treatment Hillshade',
      group: 'pre_hillshade',
      groupLabel: 'Pre-treatment Hillshade (AOI 5 + 6)',
      file: '2025/GumRidge5_DTM_Hillshade.tif',
      colorRamp: 'BrewerGreys9',
      min: 0,
      max: 254,
      reverse: true,
    },
    {
      id: 'pre_gumridge6_hillshade',
      label: 'Pre-treatment Hillshade',
      group: 'pre_hillshade',
      groupLabel: 'Pre-treatment Hillshade (AOI 5 + 6)',
      file: '2025/GumRidge6_DTM_Hillshade.tif',
      colorRamp: 'BrewerGreys9',
      min: 0,
      max: 254,
      reverse: true,
    },
    {
      id: 'post_gumridge5_hillshade',
      label: 'Post-treatment Hillshade',
      group: 'post_hillshade',
      groupLabel: 'Post-treatment Hillshade (AOI 5 + 6)',
      file: '2026/AOI5_DTM_Hillshade.tif',
      colorRamp: 'BrewerGreys9',
      min: 0,
      max: 254,
      reverse: true,
    },
    {
      id: 'post_gumridge6_hillshade',
      label: 'Post-treatment Hillshade',
      group: 'post_hillshade',
      groupLabel: 'Post-treatment Hillshade (AOI 5 + 6)',
      file: '2026/AOI6_DTM_Hillshade.tif',
      colorRamp: 'BrewerGreys9',
      min: 0,
      max: 254,
      reverse: true,
    },
    {
      id: 'diff_gumridge5',
      label: 'Difference (Post \u2212 Pre)',
      group: 'diff',
      groupLabel: 'Difference (AOI 5 + 6)',
      file: 'difference/AOI5_Difference26_25.tif',
      colorRamp: 'BrewerRdBu11',
      // Symmetric around 0 (actual range was -0.69/+1.68) so "no change" renders mid-ramp.
      min: -1.7,
      max: 1.7,
      reverse: true, // reversed so gain (positive) reads blue and loss (negative) reads red
      unit: 'm',
    },
    {
      id: 'diff_gumridge6',
      label: 'Difference (Post \u2212 Pre)',
      group: 'diff',
      groupLabel: 'Difference (AOI 5 + 6)',
      file: 'difference/AOI6_Difference26_25.tif',
      colorRamp: 'BrewerRdBu11',
      // Symmetric around 0 (actual range was -0.88/+1.38) so "no change" renders mid-ramp.
      min: -1.4,
      max: 1.4,
      reverse: true, // reversed so gain (positive) reads blue and loss (negative) reads red
      unit: 'm',
    },
  ],
};
