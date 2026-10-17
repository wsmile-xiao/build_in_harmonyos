# wmSolar (wmsolar)

> Window Maker/X11 dockapp that displays the solar system viewed from top (90 deg. heliocentric).

## Introduction

wmSolar is a Window Maker dockapp (formerly on dockapps.org) written in C/C++:

- Pure astronomy math: VSOP87 planetary data (Vsop/Lunar/Pluto/RiseSet/AstroOps)
- X11 dockapp front-end with XPM icon (`wmSolar_master.xpm` + `wmSolar_mask.xbm`)
- Produces a single `wmSolar` executable, linking `-lXpm -lX11 -lXext -lm`

Upstream: https://github.com/engerim42/wmsolar (tag 1.1), GPL-2.0.

## OHOS Adaptation Notes

1. **Hand-written Makefile**: no `configure`; `CC=g++` compiles both `.c` and `.cpp` sources in C++ mode. The Conan recipe injects dependency include/lib paths through the Makefile's `INCDIR`/`LIBDIR`/`LIBS` variables.
2. **C++17 compatibility**: `Lunar.h::SYNODIC_MONTH` changed from `static const double` to `static constexpr double` (C++17 requires constexpr for in-class static float/double member initializers).
3. **Plain char signedness**: OHOS arm64 defaults plain `char` to `unsigned`; the lunar/pluto coefficient tables (`LunarTerms1/2`, `PlutoCoeffs`) store -1/-2, so the fields were changed from `char` to `signed char`.
4. **Missing math.h**: `Vsop.cpp` uses `cos()` without including `<math.h>`; added the include for clang.
5. **CRLF source tree**: the upstream tarball ships CRLF line endings; patches are generated preserving CRLF so GNU `patch --dry-run` passes against the untouched sources.
6. **Build/link toolchain**: OHOS SDK `lld` needs `.../ohos/native/llvm/lib` on `LD_LIBRARY_PATH` (for libxml2.so.16) at link time.
7. **Runtime smoke test**: no X server on OHOS; `test_package` asserts the binary loads its Xpm/X11/Xext dependency chain and reaches `XOpenDisplay` (expected failure: "can't open display"). `LD_LIBRARY_PATH` includes `/system/lib64` for `libc++_shared.so`.

## Dependencies

- libxpm/3.5.17
- libx11/6.4.0
- libxext/6.4.0.1

## References

- https://github.com/engerim42/wmsolar
- GPL-2.0