#!/usr/bin/env python3
"""Convert GeoTIFFs to COGs and upload them to GCS in one step.

This wraps the existing converter and uploader scripts so a single command can
prepare COGs and publish them to a gs:// prefix. If ``--output-dir`` is not
provided, the converted files are written to a temporary folder that is cleaned
up automatically after upload.

Example:

    python tools/convert_and_upload_cogs.py D:\\FY26\\uas\\cogs -d gs://uas-viz/cogs
    python tools/convert_and_upload_cogs.py dem_sources/ -o out -d gs://uas-viz/cogs --overwrite
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_DESTINATION = "gs://uas-viz/cogs"
DEFAULT_RESAMPLING = "bilinear"
DEFAULT_OVERVIEW_RESAMPLING = "average"
DEFAULT_COMPRESSION = "LERC"
DEFAULT_MAX_Z_ERROR = "0.1"
DEFAULT_TARGET_SRS = "EPSG:3857"
DEFAULT_CONTENT_TYPE = "image/cog"
DEFAULT_CACHE_CONTROL = "public, max-age=31536000, immutable"

CONVERTER_SCRIPT = Path(__file__).with_name("convert_tifs_to_cogs.py")
UPLOADER_SCRIPT = Path(__file__).with_name("upload_cogs_to_gcs.py")


def status(message: str) -> None:
    print(message, flush=True)


def gcloud_path() -> str | None:
    resolved = shutil.which("gcloud")
    if resolved:
        return resolved

    if sys.platform.startswith("win"):
        candidate_roots = []
        for env_var in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
            base_dir = os.environ.get(env_var)
            if base_dir:
                candidate_roots.append(
                    Path(base_dir) / "Google" / "Cloud SDK" / "google-cloud-sdk" / "bin"
                )

        for root in candidate_roots:
            for candidate_name in ("gcloud.cmd", "gcloud.bat", "gcloud"):
                candidate = root / candidate_name
                if candidate.exists():
                    return str(candidate)

    return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert GeoTIFFs to COGs and upload them to a Google Cloud Storage prefix."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Input .tif/.tiff files or directories to scan recursively.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        help="Directory to write intermediate COGs into. Defaults to a temporary folder.",
    )
    parser.add_argument(
        "-d",
        "--destination",
        default=DEFAULT_DESTINATION,
        help=f"Destination gs:// prefix for uploads (default: {DEFAULT_DESTINATION}).",
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
        default=None,
        help=(
            "Override the output nodata value. By default, the source raster's "
            "nodata value is used when present; otherwise nan is used."
        ),
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
        help="Replace existing local outputs and destination objects.",
    )
    parser.add_argument(
        "--content-type",
        default=DEFAULT_CONTENT_TYPE,
        help=f"Content-Type metadata to apply during upload (default: {DEFAULT_CONTENT_TYPE}).",
    )
    parser.add_argument(
        "--cache-control",
        default=DEFAULT_CACHE_CONTROL,
        help=(
            "Cache-Control metadata to apply during upload "
            f"(default: {DEFAULT_CACHE_CONTROL})."
        ),
    )
    parser.add_argument(
        "--acl",
        default=None,
        help="Optional ACL to set during upload, for example public-read.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print upload actions without running gcloud storage cp.",
    )
    return parser.parse_args(argv)


def run_script(script: Path, arguments: list[str]) -> int:
    command = [sys.executable, str(script), *arguments]
    completed = subprocess.run(command)
    return completed.returncode


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if not args.destination.startswith("gs://"):
        print("error: destination must start with gs://", file=sys.stderr)
        return 2

    if gcloud_path() is None:
        print(
            "error: gcloud is not available; install the Google Cloud SDK or add gcloud to PATH",
            file=sys.stderr,
        )
        return 2

    if args.output_dir:
        output_root = Path(args.output_dir)
        cleanup = None
    else:
        cleanup = tempfile.TemporaryDirectory(prefix="uas_viz_cogs_")
        output_root = Path(cleanup.name)
        status(f"using temporary output folder {output_root}")

    try:
        convert_arguments = [
            *args.inputs,
            "-o",
            str(output_root),
            "--target-srs",
            args.target_srs,
            "--compression",
            args.compression,
            "--resampling",
            args.resampling,
            "--overview-resampling",
            args.overview_resampling,
            "--max-z-error",
            args.max_z_error,
        ]
        if args.nodata is not None:
            convert_arguments.extend(["--nodata", args.nodata])
        if args.overwrite:
            convert_arguments.append("--overwrite")

        status(f"converting COGs into {output_root}")
        result = run_script(CONVERTER_SCRIPT, convert_arguments)
        if result != 0:
            return result

        upload_arguments = [
            str(output_root),
            "-d",
            args.destination,
            "--content-type",
            args.content_type,
            "--cache-control",
            args.cache_control,
        ]
        if args.acl:
            upload_arguments.extend(["--acl", args.acl])
        if args.overwrite:
            upload_arguments.append("--overwrite")
        if args.dry_run:
            upload_arguments.append("--dry-run")

        status(f"uploading COGs from {output_root} to {args.destination}")
        result = run_script(UPLOADER_SCRIPT, upload_arguments)
        if result != 0:
            return result

        return 0
    finally:
        if cleanup is not None:
            cleanup.cleanup()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))