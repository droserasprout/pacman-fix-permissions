#!/usr/bin/python
import argparse
import logging
import re
from typing import Dict, Tuple, Iterator, Optional
import tarfile
from os import chmod, getuid, lstat
from os.path import isfile
from subprocess import DEVNULL, PIPE, run
from contextlib import contextmanager, AbstractContextManager
import zstandard as zstd

ARCHITECTURE_REGEX = r"Architecture = (.*)"
PACKAGE_PATH_TEMPLATE = "/var/cache/pacman/pkg/{name}-{version}-{arch}.pkg.{format}"
PACKAGE_IGNORE = [
    ".PKGINFO",
    ".BUILDINFO",
    ".MTREE",
    ".INSTALL",
    ".CHANGELOG",
]

__version__ = "1.1.1"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

if getuid():
    logger.error("This script must be run as root.")
    quit()

parser = argparse.ArgumentParser()
mods = parser.add_mutually_exclusive_group(required=False)
mods.add_argument(
    "-a", "--all", action="store_true", help="process all installed packages (default)"
)
mods.add_argument(
    "-p",
    "--packages",
    nargs="*",
    help="list of package names to process",
    metavar="names",
)
mods.add_argument(
    "-f",
    "--filesystem-paths",
    nargs="*",
    help="list of filesystem paths to process",
    metavar="paths",
)
args = parser.parse_args()

if hasattr(args, "packages") and getattr(args, "packages") == []:
    parser.error("You must pass at least one package name when using -p switch")
if hasattr(args, "filesystem-paths") and getattr(args, "f") == []:
    parser.error("You must pass at least one filesystem path when using -f switch")


def _get_arch() -> str:
    arch = None
    with open("/etc/pacman.conf", "r") as file:
        for line in file:
            match = re.match(ARCHITECTURE_REGEX, line)
            if match:
                arch = match.group(1)
                break
    if arch is None or arch == "auto":
        arch = run(["uname", "-m"], stdout=PIPE).stdout.decode().rstrip()
    return arch


def _get_package_path(name: str, version: str, arch: str) -> Optional[str]:
    for _arch in (arch, "any"):
        for _format in ("tar.xz", "tar.zst"):
            package_path = PACKAGE_PATH_TEMPLATE.format(
                name=name, version=version, arch=_arch, format=_format
            )
            if isfile(package_path):
                return package_path
    return None


@contextmanager
def get_package(name: str, version: str, arch: str) -> Iterator[tarfile.TarFile]:

    path = _get_package_path(name, version, arch)
    if path is None:
        logger.info("=> {} package is missing, downloading".format(name))
        run(["pacman", "-Swq", "--noconfirm", name], stdout=PIPE)

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


def __main__():
    arch = _get_arch()
    logger.info("==> Upgrading packages that are out-of-date")
    res = run(["pacman", "-Fy"])
    if res.returncode:
        quit()
    res = run(["pacman", "-Syyuuq", "--noconfirm"])
    if res.returncode:
        quit()

    logger.info("==> Parsing installed packages list")
    if hasattr(args, "packages") and args.packages:
        package_ids = (
            run(["pacman", "-Qn"] + getattr(args, "packages"), stdout=PIPE)
            .stdout.decode()
            .rstrip()
            .split("\n")
        )
    elif hasattr(args, "filesystem_paths") and args.filesystem_paths:
        package_ids = [
            " ".join(p.rsplit(" ", 2)[1:])
            for p in run(
                ["pacman", "-Qo"] + getattr(args, "filesystem_paths"), stdout=PIPE
            )
            .stdout.decode()
            .rstrip()
            .split("\n")
            if p
        ]
        if not package_ids:
            quit()
    else:
        package_ids = (
            run(["pacman", "-Qn"], stdout=PIPE).stdout.decode().rstrip().split("\n")
        )

    logger.info(
        "==> Collecting actual filesystem permissions and correct ones from packages"
    )
    broken_paths: Dict[str, Tuple[int, int]] = {}
    package_ids_total = len(package_ids)

    for i, package_id in enumerate(package_ids):
        logger.info("({}/{}) {}".format(i + 1, package_ids_total, package_id))
        name, version = package_id.split()

        with get_package(name, version, arch) as package:
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
                    logger.error("File not found: {}".format(path))

    if not broken_paths:
        logger.info("==> Your filesystem is fine, no action required")
        return

    logger.info("==> Scan completed. Broken permissions in your filesystem:")
    for path, modes in broken_paths.items():
        old_mode, new_mode = modes
        logging.info("{}: {} => {}".format(path, oct(old_mode), oct(new_mode)))
    logger.info("==> Apply? (yes/no)")
    if input() not in ["yes", "y"]:
        logger.info("==> Done! (no actual changes were made)")
        return

    for path, modes in broken_paths.items():
        old_mode, new_mode = modes
        chmod(path, new_mode)
    logger.info("==> Done!")


if __name__ == "__main__":
    __main__()
