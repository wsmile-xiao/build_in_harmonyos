# libnsbmp 0.1.7 adaptation notes

## Upstream facts

- **Source**: `https://download.netsurf-browser.org/libs/releases/libnsbmp-0.1.7-src.tar.gz`
- **SHA256**: `5407a7682a122baaaa5a15b505290e2d37df54c13c5edef4b09d12c862d82293`
- **Version**: 0.1.7 (NetSurf BMP/ICO decoding library, MIT license)
- **Homepage**: https://www.netsurf-browser.org/projects/libnsbmp/

## Build system analysis

libnsbmp uses the NetSurf project's own **NSSHARED** build system (`netsurf-buildsystem`), not a standard autotools/cmake/meson project. The upstream `Makefile` does:

```
include $(NSSHARED)/makefiles/Makefile.tools
include $(NSTOOLSDIR)/makefiles/Makefile.subdir
```

`NSSHARED` resolves to `/opt/netsurf/share/netsurf-buildsystem/` on a host where the `netsurf-buildsystem` Debian package is installed. That package is **not available for OHOS**, and NSSHARED is a meta-build tool (not a library), so it cannot be vendored or shipped as a Conan dependency. Standard Conan toolchains (`CMakeToolchain`, `AutotoolsToolchain`) do not apply.

### Patch: 0001-standalone-makefile.patch

Replaces the NSSHARED-`include`d `Makefile` with a self-contained one that reproduces the upstream compile, install and test rules:

- Compiles `src/libnsbmp.c` with the **same warning flags** as upstream (`-Wall -W -Wundef -Wpointer-arith -Wcast-align -Wwrite-strings -Wstrict-prototypes -Wmissing-prototypes -Wmissing-declarations -Wnested-externs -pedantic`), plus `-D_BSD_SOURCE -D_DEFAULT_SOURCE -std=c99`.
- Removes `-Werror`: upstream targets GCC; OHOS clang may emit warnings that differ, and `-Werror` would abort on harmless warnings. This is the only behavioral deviation and is explicitly an OHOS portability fix.
- Builds `libnsbmp.a` (static, matching upstream `COMPONENT_TYPE ?= lib-static`).
- Generates `libnsbmp.pc` from `libnsbmp.pc.in`.
- Builds the two upstream test programs (`test_decode_bmp`, `test_decode_ico`) linking the fresh static lib.
- `check` target invokes the upstream `test/runtest.sh` over the full corpus.

This is a **portability** patch with a real OHOS cause (NSSHARED unavailable), not a workaround for a build bug.

## Dependencies

- **Build-time**: only `netsurf-buildsystem` (the NSSHARED meta-tool) — replaced by the patch, so effectively **none**.
- **Runtime**: `libm` (math, linked by test programs and declared in `package_info.system_libs`).
- No NetSurf library dependencies (unlike libparserutils→libwapcaplet, libnsbmp is a leaf decoder).
- No vendoring of other projects' source.
- No host `/usr/local` library linking.

## Upstream official tests

The release tarball ships a complete upstream test suite:

| Item | Detail |
|------|--------|
| Test runner | `test/runtest.sh` |
| Test programs | `test/decode_bmp.c`, `test/decode_ico.c` |
| BMP corpus | 1070 files (bmpsuite + bmp + afl-bmp + ns-afl-bmp) |
| ICO corpus | 611 files (icons + afl-ico + ns-afl-ico) |
| **Total test data files** | **1681** |
| Entry point | `make check` → `test/runtest.sh build/test_decode_bmp build/test_decode_ico` |

`runtest.sh` decodes every BMP/ICO file through `bmp_analyse`/`bmp_decode` (and the ICO equivalents), writing PPM/PAM output and reporting pass/error counts. It resolves test data paths relative to the source root, so the `check` target must run from `source_folder`.

The recipe runs `make check` inside `conan create`'s `build()` step, so all 1681 upstream tests execute on OHOS.

## Consumer test (test_package)

Embeds a minimal 62-byte 2×1 24-bit BMP (red + green pixels) and exercises the full API: `bmp_create` → `bmp_analyse` → `bmp_decode` → `bmp_finalise`. Asserts:

1. `bmp_create` → `BMP_OK`
2. `bmp_analyse` → `BMP_OK`
3. width == 2
4. height == 1
5. bpp == 24
6. `bmp_decode` → `BMP_OK` and `bmp.decoded == true`
7. pixel0 == red `[FF,00,00,FF]`
8. pixel1 == green `[00,FF,00,FF]`

Pixel layout (`[R,G,B,A]`, 4 bytes/pixel) verified empirically against the built library before writing the checks — matches upstream `test/decode_bmp.c`'s `BYTES_PER_PIXEL = sizeof(uint32_t)` and `write_ppm` convention.

## Validation

- Native clang sanity build: library + test programs compile; probe confirms pixel layout.
- `conan create` on OHOS aarch64 profile: see task #8.
- test_package: see task #8.

---

**编译结束**: 2026-08-25
**最终状态**: built
