# wmmp

> Window Maker dockapp MPD (Music Player Daemon) client that displays playback status in a 64x64 X11 window.

## Introduction

wmmp (WMmp) is a Window Maker dockapp client for MPD written in C:

- Single X11 client executable (`WMmp`), builtin window creation via `dockapp.c`
- MPD protocol client embedded as source (`src/libmpdclient.c`, vendored upstream — not a separate dependency)
- Uses the XShape extension (`<X11/extensions/shape.h>`, libxext) and XPM icons (`<X11/xpm.h>`, libxpm)
- Links `-lX11 -lXext -lXpm`
- Build system: CMake

Upstream: https://github.com/yogsothoth/wmmp (tag `0.12.6`), GPL-2.0-or-later.

## OHOS Adaptation Notes

1. **CMake >= 4 policy floor**: upstream `cmake_minimum_required(VERSION 2.8)` is rejected by CMake 4. The policy minimum must be passed on the command line (`cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})`) — a toolchain-file `-D` comes too late because `cmake_minimum_required` runs before `project()` includes the toolchain.
2. **CMake does not know HarmonyOS**: E092 — the recipe injects the OHOS platform handling expected by the conan toolchain (known-risk item declared in the recipe).
3. **`find_package(X11)` mapping**: upstream relies on CMake's built-in X11 discovery. The recipe generates a `FindX11.cmake` module (via `cmake.configure` `CMAKE_MODULE_PATH` injection) that maps `X11_INCLUDE_DIR` / `X11_LIBRARIES` / `X11_Xpm_LIB` / `X11_Xext_LIB` onto the Conan X11 stack (`libx11` + `libxext` for XShape + `libxpm`).
4. **Full-graph include aggregation**: `X11/X.h` and other core headers live in `xorgproto`, not `libx11` — the recipe aggregates include directories over the whole dependency graph, not only direct requires.
5. **HMDFS link reliability (E524 family / R49)**: `make`/`lld` stat/open of `.so` files inside the conan cache (foreign uid) is intermittently denied. The recipe copies the three dependency libraries into `<build>/conan_link_libs` and links via `-L` against that copy.
6. **OHOS packaging**: `llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1`; `patchelf --remove-rpath` applied to the packaged binary.
7. **Headless consumer check**: `WMmp -v` / `-h` are handled by `parse_arguments()` before any X11 display is opened and exit 0, so the consumer test needs no X server.

## Dependencies

- libx11/6.4.0 (force)
- libxext/6.4.0 (force)
- libxpm/3.5.17 (force)
- (transitive) libxcb, libxau, libxdmcp, xtrans, xorgproto

## Upstream Tests

Upstream ships **no automated test suite** (no `tests/` directory, no `enable_testing()`/`add_test()` in CMakeLists, no ctest entry). The only executable entry points are `WMmp -v` (prints version, exit 0) and `WMmp -h` (prints usage, exit 0). The HarmonyOS-specific consumer test in `test_package/wmmp_consumer.c` executes the signed `WMmp` binary on-device via `popen()` and verifies both outputs — see `notes.md` (R51 declaration).
