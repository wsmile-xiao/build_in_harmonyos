# dcraw 9.28.0 OpenHarmony adaptation notes

## Source

- Upstream: https://www.dechifro.org/dcraw/
- Archive: https://deb.debian.org/debian/pool/main/d/dcraw/dcraw_9.28.orig.tar.gz
- SHA-256: `3929fe8734db7129431531322d76401517b700cc5bab06f4ba2cd2aa0e303a93`

The CI worker cannot reliably reach the upstream download host, so the
recipe uses Debian's authoritative source mirror. The `dcraw.c` and
`dcraw.1` files in this archive match the upstream 9.28.0 archive; the
mirror archive's SHA-256 is pinned above for integrity verification.

## Build decisions

The release contains `dcraw.c`, documentation, translations, and an
`install` shell script. It has no configure script or Makefile. The upstream
compile command links Jasper, JPEG, and Little CMS, but the source provides a
documented `NODEPS` mode that disables those optional integrations. The recipe
uses that mode and links only libm, leaving no external Conan dependency.

The upstream installer also invokes `/bin/sh`, `iconv`, and `msgfmt`, which
are not required for the package's core executable. The recipe copies the
binary and English man page directly and signs the executable only for OHOS.
