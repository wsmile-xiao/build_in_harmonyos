# libicns

libicns is a library for manipulating Apple ICNS icon files: reading, writing,
and converting the icon formats used by macOS, including the PNG-compressed
and RLE-packed element types from 16×16 up to 1024×1024.

The package builds the official SourceForge 0.8.1 release. The library is
LGPL-2.1-or-later; the three command-line tools it installs
(`icns2png`, `icontainer2icns`, `png2icns`) are GPL-2.0.

## OHOS adaptation

- Builds the official release tarball with its generated Autotools files.
- Recognizes the native `aarch64-unknown-linux-ohos` triplet in the bundled
  2012-era GNU config scripts (patched `config.guess`/`config.sub`).
- Disables the optional Jasper/OpenJPEG JPEG-2000 backends for deterministic
  builds; libpng remains the only dependency.
- Uses package-relative pkg-config metadata and omits the obsolete `.la` file.
- Runs the upstream `make check` target and real installed-package API tests.

## Dependencies

- `libpng/1.6.58.2` supplies the PNG encode/decode backend declared by
  `libicns.pc`.

## Command-line tools

Installed under `bin/` and declared in `commands.json`:

- `icns2png` — convert ICNS files to PNG images
- `icontainer2icns` — extract ICNS from iContainer files
- `png2icns` — build ICNS files from PNG images

## References

- https://sourceforge.net/projects/icns/
- https://en.wikipedia.org/wiki/Apple_Icon_Image_format
