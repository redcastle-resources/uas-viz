#!/usr/bin/env python3
"""Convert GeoTIFFs to Cloud Optimized GeoTIFFs with GDAL.

This is intentionally small: it uses GDAL to turn a directory of source DEMs
into COGs without needing a separate GUI or tile server. If the Python GDAL
bindings are available, it uses those directly; otherwise it falls back to
the ``gdalwarp`` executable.

Defaults are tuned for the DEM workflow in this repo:
- reproject to EPSG:3857
- write COG output
- use LERC compression
- assume NaN nodata for float elevation rasters

Example:

    python tools/convert_tifs_to_cogs.py input_dem.tif -o out
    python tools/convert_tifs_to_cogs.py dem_sources/ -o out --overwrite
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_RESAMPLING = "bilinear"
DEFAULT_OVERVIEW_RESAMPLING = "average"
DEFAULT_COMPRESSION = "LERC"
DEFAULT_MAX_Z_ERROR = "0.1"
DEFAULT_TARGET_SRS = "EPSG:3857"

try:
    from osgeo import gdal
except ImportError:
    gdal = None


def status(message: str) -> None:
    print(message, flush=True)


def iter_tifs(source: Path) -> list[Path]:
    if source.is_file():
        return [source]
    return sorted(
        path
        for pattern in ("*.tif", "*.tiff")
        for path in source.rglob(pattern)
        if path.is_file()
    )


def convert_tif(
    source: Path,
    output: Path,
    *,
    target_srs: str,
    compression: str,
    nodata: str,
    resampling: str,
    overview_resampling: str,
    max_z_error: str,
    overwrite: bool,
) -> None:
    if output.exists() and not overwrite:
        status(f"skip {source} -> {output} (exists)")
        return

    output.parent.mkdir(parents=True, exist_ok=True)

    status(f"start {source}")
    status(f"write {output}")

    if gdal is not None:
        gdal.UseExceptions()
        warp_options = gdal.WarpOptions(
            dstSRS=target_srs,
            format="COG",
            resampleAlg=resampling,
            srcNodata=nodata,
            dstNodata=nodata,
            creationOptions=[
                "TILING_SCHEME=GoogleMapsCompatible",
                f"COMPRESS={compression}",
                f"MAX_Z_ERROR={max_z_error}",
                f"RESAMPLING={resampling.upper()}",
                f"OVERVIEW_RESAMPLING={overview_resampling.upper()}",
                "OVERVIEWS=IGNORE_EXISTING",
                "ADD_ALPHA=NO",
            ],
        )
        gdal.Warp(str(output), str(source), options=warp_options)
        status(f"done {output}")
        return

    command = [
        "gdalwarp",
        "-of",
        "COG",
        "-t_srs",
        target_srs,
        "-r",
        resampling,
        "-srcnodata",
        nodata,
        "-dstnodata",
        nodata,
        "-co",
        "TILING_SCHEME=GoogleMapsCompatible",
        "-co",
        f"COMPRESS={compression}",
        "-co",
        f"MAX_Z_ERROR={max_z_error}",
        "-co",
        f"RESAMPLING={resampling.upper()}",
        "-co",
        f"OVERVIEW_RESAMPLING={overview_resampling.upper()}",
        "-co",
        "OVERVIEWS=IGNORE_EXISTING",
        "-co",
        "ADD_ALPHA=NO",
        str(source),
        str(output),
    ]

    subprocess.run(command, check=True)
    status(f"done {output}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert one or more GeoTIFFs into COGs using gdalwarp."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Input .tif/.tiff files or directories to scan recursively.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        required=True,
        help="Directory to write COGs into.",
    )
    parser.add_argument(
        "--target-srs",
        default=DEFAULT_TARGET_SRS,
        help=f"Target spatial reference system (default: {DEFAULT_TARGET_SRS}).",
    )
    parser.add_argument(
        "--compression",
        default=DEFAULT_COMPRESSION,
        help=f"COG compression (default: {DEFAULT_COMPRESSION}).",
    )
    parser.add_argument(
        "--nodata",
        default="nan",
        help="Nodata value to set on the output (default: nan).",
    )
    parser.add_argument(
        "--resampling",
        default=DEFAULT_RESAMPLING,
        help=f"Warp resampling method (default: {DEFAULT_RESAMPLING}).",
    )
    parser.add_argument(
        "--overview-resampling",
        default=DEFAULT_OVERVIEW_RESAMPLING,
        help=(
            "Overview resampling method "
            f"(default: {DEFAULT_OVERVIEW_RESAMPLING})."
        ),
    )
    parser.add_argument(
        "--max-z-error",
        default=DEFAULT_MAX_Z_ERROR,
        help=f"COG MAX_Z_ERROR creation option (default: {DEFAULT_MAX_Z_ERROR}).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing outputs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if gdal is None and shutil.which("gdalwarp") is None:
        print(
            "error: neither osgeo.gdal nor gdalwarp is available; install GDAL or add gdalwarp to PATH",
            file=sys.stderr,
        )
        return 2

    output_root = Path(args.output_dir)
    if not output_root.exists():
        output_root.mkdir(parents=True, exist_ok=True)
        status(f"created output folder {output_root}")
    else:
        output_root.mkdir(parents=True, exist_ok=True)

    sources: list[tuple[Path, Path]] = []
    for raw_input in args.inputs:
        source = Path(raw_input)
        if not source.exists():
            print(f"error: input does not exist: {source}", file=sys.stderr)
            return 2

        if source.is_file():
            if source.suffix.lower() not in {".tif", ".tiff"}:
                continue
            sources.append((source, output_root / source.name))
            continue

        for tif in iter_tifs(source):
            relative = tif.relative_to(source)
            sources.append((tif, output_root / relative))

    if not sources:
        print("error: no .tif/.tiff files found", file=sys.stderr)
        return 2

    for source, output in sources:
        convert_tif(
            source,
            output,
            target_srs=args.target_srs,
            compression=args.compression,
            nodata=args.nodata,
            resampling=args.resampling,
            overview_resampling=args.overview_resampling,
            max_z_error=args.max_z_error,
            overwrite=args.overwrite,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))