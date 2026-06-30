# geeqie

Geeqie is a lightweight GTK3 image viewer.

## Description

Geeqie is a fast, lightweight image viewer that supports browsing through directories, image collections, and metadata viewing. It uses the GTK3 toolkit and supports the Broadway (HTML5) backend for OHOS rendering.

## Homepage

https://www.geeqie.org/

## License

GPL-2.0

## Versions

| Version | Status | Build Date |
|---------|--------|------------|
| 2.7     | built  | 2026-05-25 |

## Build Notes

- Uses meson build system on HarmonyOS
- Requires GTK3 3.24.49 (Broadway backend only, no X11/Wayland dependency)
- Requires cairo 1.18.4 with gobject support enabled
- Most optional features disabled (exiv2, heif, webp, pdf, lua, etc.)
- No source code modifications needed — geeqie compiles cleanly on OHOS
- Required creating symlinks for libpng.so, libfribidi.so, libepoxy.so

## Dependencies

| Dependency | Version | Notes |
|------------|---------|-------|
| GTK3       | 3.24.49 | Broadway backend only |
| cairo      | 1.18.4  | gobject enabled |
| glib       | 2.88.0  | |
| pango      | 1.50.14 | |
| harfbuzz   | 14.2.0  | |
| gdk-pixbuf | 2.42.12 | |

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- geeqie 2.7
```