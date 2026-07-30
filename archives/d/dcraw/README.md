# dcraw

`dcraw` is a small command-line program for decoding raw digital camera photos.

## OpenHarmony adaptation

- Upstream version: 9.28.0
- Build system: direct compilation of `dcraw.c`
- Dependencies: libc and libm only
- Installed files: `bin/dcraw` and `share/man/man1/dcraw.1`

The upstream `install` script assumes `/bin/sh`, `iconv`, `msgfmt`, and the
optional Jasper/JPEG/Little CMS development libraries. The Conan recipe uses
the self-contained `-DNODEPS` build, which keeps the package dependency-free
and avoids those unavailable build-time tools on the OHOS worker.
