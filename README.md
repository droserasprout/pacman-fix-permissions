# pacman-fix-permissions

When updating packages with pacman you could see the following warning:

```text
warning: directory permissions differ on /etc/NetworkManager/system-connections/
filesystem: 600  package: 700
```

This script helps to find and fix wrong filesystem permissions on Arch Linux without reinstalling every package. It downloads package archives and compares directory trees with actual filesystem.

WARNING: It will spend a lot of your internet trafic and storage space!

## Installation

### From [AUR](https://aur.archlinux.org/packages/pacman-fix-permissions)

```shell
# replace with your favorite AUR helper
paru -S pacman-fix-permissions
```

### Local

```shell
make install
source .venv/bin/activate
```

## Usage

```
usage: pacman-fix-permissions [-h] [-a | -p [NAME ...] | -f [PATH ...]] [-c] [-v]

options:
  -h, --help            show this help message and exit
  -a, --all             process all installed packages (default)
  -p [NAME ...], --packages [NAME ...]
                        list of package names to process
  -f [PATH ...], --filesystem-paths [PATH ...]
                        list of filesystem paths to process
  -c, --clean           clean up package cache after processing
  -v, --version         show program's version number and exit
```

___

Pro tip: use [lostfiles](https://archlinux.org/packages/community/any/lostfiles/) as a companion tool to find files pacman doesn't know about.
