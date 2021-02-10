# pacman-fix-permissions

Find and fix wrong filesystem permissions on Arch Linux instance without needing to reinstall every package.

Pro tip: use [lostfiles](https://archlinux.org/packages/community/any/lostfiles/) as a companion tool to find files pacman doesn't know about.

## Installation

### From [AUR](https://aur.archlinux.org/packages/pacman-fix-permissions)

```shell-script
# replace with your favourite AUR helper
yay -S pacman-fix-permissions
```

### Local

```shell-script
# install required dependencies only and build package
DEV=0 make install
make build
# or prepare dev environment and run all checks
make
```

## Usage

```
usage: pacman-fix-permissions [-h] [-a | -p [NAME ...] | -f [PATH ...]]

optional arguments:
  -h, --help            show this help message and exit
  -a, --all             process all installed packages (default)
  -p [NAME ...], --packages [NAME ...]
                        list of package names to process
  -f [PATH ...], --filesystem-paths [PATH ...]
                        list of filesystem paths to process
```
