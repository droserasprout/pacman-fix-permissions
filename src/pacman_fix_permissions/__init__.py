#!/usr/bin/python
import argparse
import logging
import re
import tarfile
from os import chmod, getuid, lstat
from os.path import isfile
from subprocess import DEVNULL, PIPE, run

import zstandard as zstd


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
print(args)
if hasattr(args, "packages") and getattr(args, "packages") == []:
    parser.error("You must pass at least one package name when using -p switch")
if hasattr(args, "filesystem-paths") and getattr(args, "f") == []:
    parser.error("You must pass at least one filesystem path when using -f switch")


def zflat(p):
    # this is dirty, fh and reader are never closed.
    fh = open(p, "rb")
    dctx = zstd.ZstdDecompressor()
    reader = dctx.stream_reader(fh)
    return reader


def getTar(pkg):
    def _open():
        p_arch = "/var/cache/pacman/pkg/{}-{}-{}.pkg.tar.xz".format(
            pkg[0], pkg[1], arch
        )
        p_any = "/var/cache/pacman/pkg/{}-{}-{}.pkg.tar.xz".format(
            pkg[0], pkg[1], "any"
        )
        if isfile(p_arch):
            return tarfile.open(p_arch)
        if isfile(p_any):
            return tarfile.open(p_any)

        p_arch = "/var/cache/pacman/pkg/{}-{}-{}.pkg.tar.zst".format(
            pkg[0], pkg[1], arch
        )
        p_any = "/var/cache/pacman/pkg/{}-{}-{}.pkg.tar.zst".format(
            pkg[0], pkg[1], "any"
        )
        if isfile(p_arch):
            return tarfile.open(fileobj=zflat(p_arch), mode="r|*")
        if isfile(p_any):
            return tarfile.open(fileobj=zflat(p_any), mode="r|*")
        return None

    file = open("/etc/pacman.conf", "r")
    pattern = r'Architecture = (.*)'
    for line in file:
        match = re.match(pattern, line)
        if match:
            arch = match.group(1)
    pkg = pkg.split()
    pkgtar = _open()
    if pkgtar is None:
        logger.info("=> {} package is missing, downloading".format(pkg[0]))
        run(["pacman", "-Swq", "--noconfirm", pkg[0]], stdout=DEVNULL)
        pkgtar = _open()
    if pkgtar is None:
        raise Exception(
            "Can't open or download '{}' package, check your internet connection".format(
                pkg[0]
            )
        )
    return pkgtar


def __main__():
    logger.info("==> Upgrading packages that are out-of-date")
    res = run(["pacman", "-Fy"])
    if res.returncode:
        quit()
    res = run(["pacman", "-Syyuuq", "--noconfirm"])
    if res.returncode:
        quit()

    logger.info("==> Parsing installed packages list")
    if hasattr(args, "packages") and args.packages:
        pkgs = (
            run(["pacman", "-Qn"] + getattr(args, "packages"), stdout=PIPE)
            .stdout.decode()
            .rstrip()
            .split("\n")
        )
    elif hasattr(args, "filesystem_paths") and args.filesystem_paths:
        pkgs = [
            " ".join(p.rsplit(" ", 2)[1:])
            for p in run(
                ["pacman", "-Qo"] + getattr(args, "filesystem_paths"), stdout=PIPE
            )
            .stdout.decode()
            .rstrip()
            .split("\n")
            if p
        ]
        if not pkgs:
            quit()
    else:
        pkgs = run(["pacman", "-Qn"], stdout=PIPE).stdout.decode().rstrip().split("\n")

    logger.info(
        "==> Collecting actual filesystem permissions and correct ones from packages"
    )
    paths = {}
    for i in range(len(pkgs)):
        logger.info("({}/{}) {}".format(i + 1, len(pkgs), pkgs[i]))
        pkgtar = getTar(pkgs[i])
        for f in pkgtar.getmembers():
            if f.name not in [
                ".PKGINFO",
                ".BUILDINFO",
                ".MTREE",
                ".INSTALL",
                ".CHANGELOG",
            ]:
                p = "/" + f.name
                if p not in paths:
                    try:
                        old_mode = int(lstat(p).st_mode & 0o7777)
                        new_mode = int(f.mode)
                        if old_mode != new_mode:
                            paths[p] = {"old_mode": old_mode, "new_mode": new_mode}
                    except FileNotFoundError:
                        logger.error("File not found: {}".format(p))

    if paths:
        logger.info("==> Scan completed. Broken permissions in your filesystem:")
        for p in paths.keys():
            logging.info(
                "{}: {} => {}".format(
                    p, oct(paths[p]["old_mode"]), oct(paths[p]["new_mode"])
                )
            )
        logger.info("==> Apply? (yes/no)")
        if input() in ["yes", "y"]:
            for p in paths.keys():
                chmod(p, paths[p]["new_mode"])
            logger.info("==> Done!")
        else:
            logger.info("==> Done! (no actual changes were made)")
    else:
        logger.info("==> Your filesystem is fine, no action required")


if __name__ == "__main__":
    __main__()
