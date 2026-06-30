# Build Notes — mupdf 1.27.2

## Build Date
2026-05-25

## Build System
GNU Makefile (custom, not cmake/autotools/meson)

## Build Configuration
```bash
make -j2 \
  USE_SYSTEM_LIBS=yes \
  USE_SYSTEM_LCMS2=yes \
  USE_SYSTEM_BROTLI=yes \
  mujs=no \
  html=no \
  extract=no \
  HAVE_GLUT=no \
  HAVE_X11=no \
  HAVE_OBJCOPY=no \
  HAVE_LIBCRYPTO=yes \
  prefix=/storage/Users/currentUser/usr/local \
  verbose=yes
```

## Build Duration
~15 minutes (900 seconds)

## Dependencies
| Dependency | Version | Source |
|-----------|---------|--------|
| freetype | 2.13.3 | cmd-pkgs |
| libjpeg-turbo | 3.1.0 | cmd-pkgs |
| zlib | 1.2.13 | system |
| openjpeg | 2.5.0 | cmd-pkgs |
| libpng | 1.6.44 | cmd-pkgs |
| lcms2 | 2.16 | cmd-pkgs |
| brotli | 1.1.0 | cmd-pkgs |
| jbig2dec | 0.20 | manual compile |
| openssl | 3.4.1 | cmd-pkgs |

## Key Issues & Resolutions

### 1. mujs submodule empty
The mupdf tarball includes mujs as a git submodule reference but the actual source files are missing.
Resolution: Downloaded mujs 1.3.5 source and copied regexp.c, regexp.h, utf.c, utf.h, utfdata.h, mujs.h to thirdparty/mujs/.

### 2. ld.lld -b binary not supported
The Makefile's OBJCOPY_CMD uses `ld -r -b binary` to embed fonts, but ld.lld doesn't support this.
Resolution: Set HAVE_OBJCOPY=no to use the hexdump method (scripts/hexdump.sh) for font embedding instead.

### 3. gumbo-parser unavailable
No prebuilt package available for gumbo-parser.
Resolution: Disabled HTML support via html=no (FZ_ENABLE_HTML=0).

### 4. jbig2dec unavailable
No cmd-pkgs prebuilt for jbig2dec.
Resolution: Manually downloaded and compiled jbig2dec 0.20 from source.

### 5. `install` command not available
HMDFS environment lacks the GNU `install` command.
Resolution: Used `busybox install` for manual installation to staging directory.

## Build Output
- libmupdf.a (52 MB) - static library
- libmupdf-pkcs7.a (25 KB) - PKCS7 module
- libmupdf-threads.a (5.7 KB) - threading module
- mutool (36 MB) - command-line tool (mutool version 1.27.2)

## Disabled Features
- JS engine (mujs=no, FZ_ENABLE_JS=0) - regexp still works via embedded mujs code
- HTML engine (html=no, FZ_ENABLE_HTML=0)
- EPUB (FZ_ENABLE_EPUB=0)
- FB2 (FZ_ENABLE_FB2=0)
- MOBI (FZ_ENABLE_MOBI=0)
- Office (FZ_ENABLE_OFFICE=0)
- TXT (FZ_ENABLE_TXT=0)
- DOCX output (FZ_ENABLE_DOCX_OUTPUT=0)
- Barcode (FZ_ENABLE_BARCODE=0)
- GLUT/X11 (HAVE_GLUT=no, HAVE_X11=no)
---

**编译结束**: 2026-05-25 22:35
**最终状态**: built
