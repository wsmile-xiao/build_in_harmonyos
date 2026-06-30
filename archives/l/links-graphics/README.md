# links-graphics

Links is a text and graphics mode WWW browser with a framebuffer driver for Linux. It supports HTML 4.0, tables, menus, CSS, and various image formats.

## OpenHarmony Notes
- GPM (General Purpose Mouse) is not available on OpenHarmony; the FB driver uses PS/2 mouse input only
- Requires OpenSSL, zlib, libpng, libjpeg, libtiff, libwebp, bzip2, zstd, freetype2, fontconfig

## Version 2.30
- Status: built
- Build system: autotools
- Key patch: conditional GPM support with `#ifdef HAVE_LIBGPM` guards
