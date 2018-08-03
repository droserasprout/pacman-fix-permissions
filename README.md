# pacman-fix-permissions
Small Python script to fix broken Arch Linux filesystem permissions

usage: pacman-fix-permissions [-h] [-a | -p [names [names ...]] | -f
                              [paths [paths ...]]]

optional arguments:
  -h, --help            show this help message and exit
  -a, --all             process all installed packages (default)
  -p [names [names ...]], --packages [names [names ...]]
                        list of package names to process
  -f [paths [paths ...]], --filesystem-paths [paths [paths ...]]
                        list of filesystem paths to process

