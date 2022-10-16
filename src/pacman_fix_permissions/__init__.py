#!/usr/bin/python
"""Fix broken filesystem permissions"""
import argparse
import logging
from pathlib import Path
import re
import sys
import tarfile
from contextlib import contextmanager
from os import chmod
from os import getuid
from os import lstat
from os.path import isfile
from subprocess import PIPE
from subprocess import run
from typing import Dict
from typing import Iterator
from typing import Optional
from typing import Tuple

import zstandard as zstd

ARCHITECTURE_REGEX = r"Architecture = (.*)"
PACKAGE_PATH_TEMPLATE = "/var/cache/pacman/pkg/{name}-{version}-{arch}.pkg.{format}"
PACKAGE_IGNORE = [
    ".PKGINFO",
    ".BUILDINFO",
    ".MTREE",
    ".INSTALL",
    ".CHANGELOG",
    # NOTE: unable to chmod
    "boot/amd-ucode.img",
]

__version__ = "1.1.2"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

if getuid():
    logger.error("This script must be run as root.")
    sys.exit(1)

parser = argparse.ArgumentParser(prog="pacman-fix-permissions")
mods = parser.add_mutually_exclusive_group(required=False)
mods.add_argument(
    "-a", "--all", action="store_true", help="process all installed packages (default)"
)
mods.add_argument(
    "-p",
    "--packages",
    nargs="*",
    help="list of package names to process",
    metavar="NAME",
)
mods.add_argument(
    "-f",
    "--filesystem-paths",
    nargs="*",
    help="list of filesystem paths to process",
    metavar="PATH",
)
parser.add_argument(
    "-c", "--clean", action="store_true", help="clean up package cache after processing"
)
parser.add_argument(
    "-v", "--version", action="version", version=f"%(prog)s {__version__}"
)
cli_args = parser.parse_args()

if getattr(cli_args, "packages", None) == []:
    parser.error("You must pass at least one package name when using -p switch")
if getattr(cli_args, "filesystem-paths", None) == []:
    parser.error("You must pass at least one filesystem path when using -f switch")


def _get_arch() -> str:
    """Get system architecture from pacman.conf or from uname if not set explicitly."""
    arch = "auto"
    with open("/etc/pacman.conf", "r") as file:
        for line in file:
            match = re.match(ARCHITECTURE_REGEX, line)
            if match:
                arch = match.group(1)
                break
    if arch == "auto":
        result = run(
            ("uname", "-m"),
            check=True,
            stdout=PIPE,
        )
        arch = result.stdout.decode().rstrip()
    return arch


def _get_package_path(name: str, version: str, arch: str) -> Optional[str]:
    """Get path to package stored in pacman cache."""
    for _arch in (arch, "any"):
        for _format in ("tar.xz", "tar.zst"):
            package_path = PACKAGE_PATH_TEMPLATE.format(
                name=name, version=version, arch=_arch, format=_format
            )
            if isfile(package_path):
                return package_path
    return None


@contextmanager
def get_package(
    name: str, version: str, arch: str, clean: bool = False
) -> Iterator[tarfile.TarFile]:
    """Open package from pacman cache, download it if missing."""

    downloaded = False
    path = _get_package_path(name, version, arch)
    if path is None:
        logger.info("=> %s package is missing, downloading", name)
        run(
            ("pacman", "-Swq", "--noconfirm", name),
            check=True,
        )
        downloaded = True

    path = _get_package_path(name, version, arch)
    if path is None:
        raise Exception

    if path.endswith("xz"):
        with tarfile.open(path) as package:
            yield package
    elif path.endswith("zst"):
        dctx = zstd.ZstdDecompressor()
        with open(path, "rb") as file:
            with dctx.stream_reader(file) as reader:
                with tarfile.open(fileobj=reader, mode="r|*") as package:
                    yield package
    else:
        raise Exception("Unknown package format")

    if downloaded and clean:
        logger.info("=> %s package downloaded, cleaning up", name)
        Path(path).unlink()


def __main__():
    arch = _get_arch()
    logger.info("==> Upgrading packages that are out-of-date")
    run(
        ("pacman", "-Syu", "--noconfirm"),
        check=True,
    )

    logger.info("==> Parsing installed packages list")
    selected_packages = getattr(cli_args, "packages", [])
    selected_paths = getattr(cli_args, "filesystem_paths", [])
    if selected_packages:
        result = run(
            ("pacman", "-Qn", *selected_packages),
            check=True,
            stdout=PIPE,
        )
        package_ids = result.stdout.decode().strip().split("\n")
    elif selected_paths:
        result = run(("pacman", "-Qo", *selected_paths), check=True, stdout=PIPE)
        output = result.stdout.decode().strip().split("\n")
        package_ids = [" ".join(line.split()[-2:]) for line in output]
    else:
        result = run(
            ("pacman", "-Qn"),
            check=True,
            stdout=PIPE,
        )
        package_ids = result.stdout.decode().strip().split("\n")
    if not package_ids:
        raise Exception("No packages selected")

    logger.info(
        "==> Collecting actual filesystem permissions and correct ones from packages"
    )
    broken_paths: Dict[str, Tuple[int, int]] = {}
    package_ids_total = len(package_ids)

    for i, package_id in enumerate(package_ids):
        logger.info("(%i/%i) %s", i + 1, package_ids_total, package_id)
        name, version = package_id.split()

        with get_package(name, version, arch, cli_args.clean) as package:
            for file in package.getmembers():
                if file.name in PACKAGE_IGNORE:
                    continue

                path = "/" + file.name
                if path in broken_paths:
                    continue

                try:
                    old_mode = int(lstat(path).st_mode & 0o7777)
                    new_mode = int(file.mode)
                    if old_mode != new_mode:
                        broken_paths[path] = (old_mode, new_mode)
                except FileNotFoundError:
                    logger.error("File not found: %s", path)
                    # TODO: Suggest to reinstall package

    if not broken_paths:
        logger.info("==> Your filesystem is fine, no action required")
        return

    logger.info("==> Scan completed. Broken permissions in your filesystem:")
    for path, modes in broken_paths.items():
        old_mode, new_mode = modes
        logging.info("%s: %s => %s", path, oct(old_mode), oct(new_mode))
    logger.info("==> Apply? [Y/n]")
    if input().lower() in ["no", "n"]:
        logger.info("==> Done! (no actual changes were made)")
        return

    for path, modes in broken_paths.items():
        old_mode, new_mode = modes
        chmod(path, new_mode)
    logger.info("==> Done!")


if __name__ == "__main__":
    __main__()
