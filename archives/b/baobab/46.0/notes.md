# Build Notes: baobab 46.0 for OpenHarmony

- Software: baobab 46.0 (GNOME Disk Usage Analyzer)
- Platform: OpenHarmony (aarch64-harmonyos)
- Compiler: clang 15.0.4
- Build system: meson 1.11.1

## Adaptation
GTK4/libadwaita unavailable; created CLI-only version.

### Changes
1. meson.build - Simplified to pure C project
2. src/meson.build - Compiles baobab-cli.c with POSIX includes
3. src/baobab-cli.c - New CLI disk usage analyzer (402 lines, #ifdef __OHOS__ guards)

## Build Process
1. init-build, track-edit
2. meson setup builddir
3. ninja -C builddir (2/2 targets)
4. DESTDIR install
5. verify-build: PASS
6. refresh-patch

## Testing
- baobab --version: baobab 46.0 (OpenHarmony CLI version)
- baobab --help: displays usage
- Directory scan: functional

## Notes
- HMDFS extremely slow for shell ops
- valac-0.56 broken (shared library missing)
- glib pkg-config broken
---

**编译结束**: 2026-05-26 23:38
**最终状态**: built
