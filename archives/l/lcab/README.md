# lcab

`lcab` is a small command-line utility for creating Microsoft Cabinet (`.cab`) archives from files and directories.

- Version: 1.0b12
- License: GPL-2.0-or-later
- Build system: GNU Autotools
- Package type: command-line tool
- Dependencies: none
- Source mirror: https://sources.archlinux.org/other/packages/lcab/

## HarmonyOS adaptation

The upstream POSIX C sources compile for `aarch64-linux-ohos` without platform-specific source changes. The recipe explicitly passes `--host=aarch64-linux-ohos` because the repository's OHOS Conan profile uses the target profile for both host and build contexts. One upstream bugfix patch updates the stale `VERSION` macro from `1.0b11` to `1.0b12`.

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 1.0b12 | built | W3 local CI passed; functional cabinet creation tests passed under qemu-aarch64 |
