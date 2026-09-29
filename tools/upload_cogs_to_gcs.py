#!/usr/bin/env python3
"""Upload COGs and other raster files to a Google Cloud Storage bucket.

This script is intentionally small and shell-friendly. It walks one or more
files/directories, preserves any directory structure underneath a directory
input, and uploads each file to a gs:// destination prefix.

By default it expects Cloud Optimized GeoTIFFs and sets the uploaded objects'
Content-Type to image/tiff with a long-lived cache policy.

Example:

    python tools/upload_cogs_to_gcs.py cogs/ -d gs://uas-viz/cogs --overwrite
    python tools/upload_cogs_to_gcs.py out/pre.tif out/post.tif -d gs://uas-viz/cogs
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath


DEFAULT_DESTINATION = "gs://uas-viz/cogs"
DEFAULT_CONTENT_TYPE = "image/cog"
DEFAULT_CACHE_CONTROL = "public, max-age=31536000, immutable"
DEFAULT_EXTENSIONS = {".tif", ".tiff"}


def status(message: str) -> None:
    print(message, flush=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload raster files to a Google Cloud Storage prefix."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Input files or directories to upload.",
    )
    parser.add_argument(
        "-d",
        "--destination",
        default=DEFAULT_DESTINATION,
        help=f"Destination gs:// prefix (default: {DEFAULT_DESTINATION}).",
    )
    parser.add_argument(
        "--all-files",
        action="store_true",
        help="Upload every file found, not just .tif/.tiff files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace destination objects if they already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print upload actions without running gsutil.",
    )
    parser.add_argument(
        "--content-type",
        default=DEFAULT_CONTENT_TYPE,
        help=f"Content-Type metadata to apply (default: {DEFAULT_CONTENT_TYPE}).",
    )
    parser.add_argument(
        "--cache-control",
        default=DEFAULT_CACHE_CONTROL,
        help=(
            "Cache-Control metadata to apply "
            f"(default: {DEFAULT_CACHE_CONTROL})."
        ),
    )
    parser.add_argument(
        "--acl",
        default=None,
        help="Optional ACL to set during upload, for example public-read.",
    )
    return parser.parse_args(argv)


def iter_files(source: Path, *, all_files: bool) -> list[Path]:
    if source.is_file():
        if all_files or source.suffix.lower() in DEFAULT_EXTENSIONS:
            return [source]
        return []

    files: list[Path] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        if all_files or path.suffix.lower() in DEFAULT_EXTENSIONS:
            files.append(path)
    return files


def build_destination(destination_prefix: str, relative_path: str | Path) -> str:
    prefix = destination_prefix.rstrip("/") + "/"
    return prefix + PurePosixPath(Path(relative_path).as_posix()).as_posix()


def build_command(executable: str, arguments: list[str]) -> tuple[list[str] | str, bool]:
    if sys.platform.startswith("win") and executable.lower().endswith((".cmd", ".bat")):
        command_line = subprocess.list2cmdline([executable, *arguments])
        return command_line, True
    return [executable, *arguments], False


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


def upload_file(
    source: Path,
    destination: str,
    *,
    gcloud_executable: str,
    content_type: str,
    cache_control: str,
    acl: str | None,
    overwrite: bool,
    dry_run: bool,
) -> None:
    command_arguments = ["storage", "cp"]
    if not overwrite:
        command_arguments.append("--no-clobber")
    if acl:
        command_arguments.extend(["-a", acl])
    command_arguments.extend([
        f"--content-type={content_type}",
        f"--cache-control={cache_control}",
        str(source),
        destination,
    ])

    command, use_shell = build_command(gcloud_executable, command_arguments)

    status(f"upload {source} -> {destination}")
    if dry_run:
        return

    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            shell=use_shell,
        )
    except subprocess.CalledProcessError as error:
        if error.stdout:
            print(error.stdout, file=sys.stderr, end="")
        if error.stderr:
            print(error.stderr, file=sys.stderr, end="")
        print(
            f"error: upload failed for {source} -> {destination} (exit code {error.returncode})",
            file=sys.stderr,
        )
        raise SystemExit(error.returncode) from None

    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if not args.destination.startswith("gs://"):
        print("error: destination must start with gs://", file=sys.stderr)
        return 2

    gcloud_executable = gcloud_path()
    if gcloud_executable is None:
        print(
            "error: gcloud is not available; install the Google Cloud SDK or add gcloud to PATH",
            file=sys.stderr,
        )
        return 2

    uploads: list[tuple[Path, str]] = []
    for raw_input in args.inputs:
        source = Path(raw_input)
        if not source.exists():
            print(f"error: input does not exist: {source}", file=sys.stderr)
            return 2

        if source.is_file():
            if args.all_files or source.suffix.lower() in DEFAULT_EXTENSIONS:
                uploads.append((source, build_destination(args.destination, source.name)))
            continue

        for file_path in iter_files(source, all_files=args.all_files):
            relative_path = file_path.relative_to(source)
            uploads.append((file_path, build_destination(args.destination, relative_path)))

    if not uploads:
        print("error: no matching files found to upload", file=sys.stderr)
        return 2

    for source, destination in uploads:
        upload_file(
            source,
            destination,
            gcloud_executable=gcloud_executable,
            content_type=args.content_type,
            cache_control=args.cache_control,
            acl=args.acl,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))