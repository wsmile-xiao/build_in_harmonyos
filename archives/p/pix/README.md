# Pix

Pix is an image viewer and organizer from Linux Mint, forked from gthumb.
It supports viewing, organizing, and basic editing of images.

## Dependencies
- GTK3
- glib 2.0
- libpng
- zlib
- lcms2 (optional)
- libraw (optional)
- librsvg (optional)

## OpenHarmony Adaptation
- x11, xapp, gsettings-desktop-schemas made optional (not available on OHOS)
- itstool not available, help documentation build skipped
- 3 patches applied for meson build system adaptation
