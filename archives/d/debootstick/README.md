# debootstick

> Turn a chroot environment into a bootable live image.

## Introduction

debootstick generates a bootable live image from any Debian/Ubuntu filesystem
tree (debootstrap chroot or docker export). The embedded system is ready to
use with no installation step, stays fully upgradable (kernel and bootloader
included), and supports BIOS/UEFI PCs as well as Raspberry Pi boards.

## OHOS adaptation

- **Build system**: plain Makefile (`install-tool` target only). `all` and
  `clean` are empty; there is no configure script and no compilation.
- **Shell**: the script uses `#!/bin/bash`. HarmonyOS PC has no `/bin/bash`,
  so the recipe and its tests always invoke it via the `CONFIG_SHELL` bash
  (`/data/service/hnp/bin/bash` fallback), never by direct exec.
- **Install layout**: upstream installs to `/usr/sbin/debootstick` plus
  `/usr/share/debootstick` (scripts, disk-layouts). The recipe relocates to
  `bin/debootstick` plus `share/debootstick`, and additionally places copies
  of `scripts/` and `disk-layouts/` beside the binary so the upstream
  `DBSTCK_DIR` fallback (`CURRENT_DIR`) keeps working without patches.
- **Privileges**: creating real images requires root, loop devices, parted,
  grub and a Debian chroot, so consumer tests only exercise headless CLI
  paths (`--version`, `--help`, `--help-os-support`, error paths) plus data
  file presence checks. No image is built during tests.
- **Upstream tests**: the upstream tree ships no test suite (see
  `test_package/MANIFEST.yml` audit). The recipe adds consumer smoke tests.

## Dependencies

No build or runtime Conan dependencies (pure shell).

## Functional verification

```bash
debootstick --version   # prints: debootstick 2.9
debootstick --help      # prints usage, exits 0
```

## References

- Upstream repository: https://github.com/drakkar-lig/debootstick
- Project site: https://drakkar-lig.github.io/debootstick
- Debian source: https://tracker.debian.org/pkg/debootstick
