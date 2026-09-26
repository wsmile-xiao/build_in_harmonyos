# libfishcamp 1.2 adaptation notes

## Summary

`libfishcamp` is the Fishcamp Starfish camera driver library, shipped as a single
subproject inside the INDI 3rdparty monorepo
(`github.com/indilib/indi-3rdparty`, tag `v2.2.4`). This adaptation vendors the
3 C source files and the LGPL license directly from the official `raw.githubusercontent.com`
host (PF7/R39 compliant) and builds a self-contained library that depends only on
`libusb-1.0`. The INDI framework is **not** required to build or use it.

## Source

- Version: `1.2` (maps to upstream INDI 3rdparty `v2.2.4`, the release that
  contains the `libfishcamp` subproject).
- Vendored files (official `raw.githubusercontent.com/indilib/indi-3rdparty/v2.2.4/libfishcamp/`):
  - `fishcamp.c` (sha256 `f5c3d7cd20edb4b338968ec27bf442512b859ca7a86e790c44df1c20b2d1c79f`)
  - `fishcamp.h` (sha256 `c9caf318352a090ecb67a3b4db324c67e690cca41bb9c6bac2d87322bc81f2e8`)
  - `fishcamp_common.h` (sha256 `ad8cf6c592172de2df8063daeda4e4fbff570af11797bba7ac9cf6c03606441d`)
  - `COPYING.LIB` (sha256 `20cf5be7deab6ff1440e83fea7e3de2592c210b942247c6a509b48bfb7ce8f72`)
- The upstream `libfishcamp` directory also ships `CMakeLists.txt` and `FindINDI.cmake`,
  both of which pull in the full INDI framework. These are **not** used; a minimal
  replacement `CMakeLists.txt` is provided via `exports_sources`.

## INDI decoupling

`fishcamp.c` is the only file that references INDI. Its single coupling is the
`INDI_UNUSED(x)` macro (from `indimacros.h`). The patch
`patches/0001-drop-indi-dependency.patch` removes `#include "indimacros.h"` and
defines `INDI_UNUSED` locally. No `libindi` library functions are used, so no
INDI dependency is needed. The patch text is neutral (no "HarmonyOS" wording),
so it does not trip the PF5 copyright/branding scan.

## Dependencies

- `libusb/1.0.27` — the only real build/runtime dependency. Found via CMakeDeps
  (`find_package(libusb-1.0)`, imported target `libusb-1.0::libusb-1.0`).

## Build

- `cmake_layout` (Conan 2.29.1 places `cmake_layout` in `conan.tools.cmake`).
- `source()` uses `download()` (not `get()`), because the vendored files are
  plain `.c`/`.h`/`.LIB` files; `get()` always unzips and would raise
  `BadZipFile`.
- `exports_sources = "CMakeLists.txt"` places the replacement build script into
  the source folder automatically (Conan 2 merges `export_sources_folder` and
  `source_folder` for a local `conan create`).
- `CMakeLists.txt`: `find_package(libusb-1.0)`, `add_library(fishcamp ...)`,
  links `libusb-1.0::libusb-1.0` **PUBLIC** (fishcamp's public header
  `fishcamp_common.h` includes `<libusb.h>`), installs `fishcamp.h` +
  `fishcamp_common.h` and the static/shared lib.

## test_package

- `test_package/conanfile.py`: `requires(self.tested_reference_str)`,
  `generators = "CMakeDeps","CMakeToolchain"`, `layout()` = `cmake_layout`.
- `test_package/src/test_fishcamp.c` exercises the public API with a custom
  `CHECK` macro (no `<cassert>`, because Release builds define `NDEBUG` and
  strip `assert`): `fcUsb_setSimulation(1)`, `fcUsb_setLogging(0)`, and
  `fcUsb_GetNumCameras()` returning `0`. All three tested functions only mutate
  global driver state and never touch libusb or hardware, so the test runs
  safely on the aarch64/OHOS host.
- `MANIFEST.yml` declares 3 assertions (upstream has no test suite, `N=0`).

## OHOS build-environment notes (host: aarch64 / openharmony)

- `TMPDIR`: `/tmp` is read-only, so `build()` points `TMPDIR`/`TMP`/`TEMP` at the
  HMBS task temp dir (`/data/storage/el2/base/cache`), which is writable and
  supports `mkfifo`. This is needed both for clang temp files and for make's
  parallel jobserver.
- Parallel make (`-jN`) triggers a silent clang failure on this host's
  jobserver, so the build is forced serial (`cmake.build(build_tool_args=["-j1"])`).
- `package_info()`: the CMake consumer name is set via
  `cmake_file_name="fishcamp"` / `cmake_target_name="fishcamp::fishcamp"` so
  `find_package(fishcamp)` resolves; `cpp_info.requires = ["libusb::libusb"]`
  (repo-standard form for the flat libusb package) propagates libusb to
  consumers.
---

**编译结束**: 2026-09-23 22:47
**最终状态**: published
