Tested on HarmonyOS PC (OHOS 6.0, aarch64) with conan 2.29.1 + clang 15.

## Upstream

- Name: orcania
- Version: 2.3.3
- Tag: `v2.3.3` (commit ffc8b55d09a3488f4f6be38034b33bc64bf8b0ce)
- URL: https://github.com/babelouest/orcania
- License: LGPL-2.1-or-later (LICENSE file)

## Build system

CMake 3.5+ upstream, C99. Upstream CMake options:

- BUILD_SHARED / BUILD_STATIC (mutually exclusive; default BUILD_SHARED=ON)
- BUILD_BASE64URL (default ON)
- BUILD_ORCANIA_TESTING (default OFF; needs Check; on Linux/OHOS upstream also
  hard-requires Subunit)
- WITH_STRSTR (default OFF)

This recipe produces the static archive (BUILD_SHARED=OFF / BUILD_STATIC=ON)
that downstream consumers link directly.

## Runtime vs. test-build dependencies

- **Runtime**: orcania depends only on libc (headers `orcania.h` +
  generated `orcania-cfg.h`, one static lib).
- **Test-build stage**: the unmodified upstream CTest suite needs the
  Check framework. The recipe pulls `check/0.15.2` from ohpcd as a **test-only**
  (`test_requires`) dependency — available while building/running the upstream
  tests, never propagated to consumers, not part of the package_id. The same
  pattern is used by the repo precedent `archives/l/libwbxml/0.11.10`.

## Why upstream tests are enabled (rule 4)

Upstream v2.3.3 ships 4 CTest test programs (`str_test`, `split_test`,
`memory_test`, `pointer_list_test`) in `test/`, built with `BUILD_ORCANIA_TESTING=ON`.
They are registered as EXCLUDE_FROM_ALL and executed here inside `conan create`
(via `ctest`), so the official tests genuinely pass 4/4 on OHOS aarch64.

The OHOS `check/0.15.2` package is self-contained (its `libcheck` needs no
Subunit), and all 4 upstream `test/*.c` only `#include <check.h>`. Upstream
CMake nevertheless hard-requires `find_package(Subunit REQUIRED)` and links
`Subunit::Subunit` on non-Win/non-Apple platforms (a legacy Debian-era default).
Because no subunit package exists on ohpcd and the tests do not need it, a
minimal **portability** patch makes Subunit optional on OHOS while leaving the
4 `add_test()` registrations, all test sources and every assertion untouched.

## Patches

- `0001-ohos-subunit-optional.patch` (portability, CMakeLists.txt only):
  1. `find_package(Subunit REQUIRED)` -> `find_package(Subunit)`
  2. append `Subunit::Subunit` to `TEST_LIBS` only `if (SUBUNIT_FOUND)`.

Upstream `test/*.c` are never modified. `BUILD_ORCANIA_TESTING` is enabled at
configure time in `build()` and the 4 EXCLUDE_FROM_ALL executables are built
explicitly before `ctest` runs.

## Notes

The orcania header is shipped as `orcania.h` and the configure step also emits
`orcania-cfg.h`. Both are public and exposed via cpp_info.includedirs. The
upstream unit tests compile against the in-tree static lib and link the Conan
`check` package through orcania's own `cmake-modules/FindCheck.cmake`, seeded
with the Conan check prefix (`CHECK_INCLUDE_DIR` / `CHECK_LIBRARY`); no host
/usr/lib same-name library is used.

`build()` deliberately does **not** pass `CMAKE_PREFIX_PATH` for check: the
Conan toolchain sets `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`, so `find_package(Check)`
would otherwise resolve in CONFIG mode to the installed `check-config.cmake`
(target `Check::check`, variable `Check_FOUND`), skip orcania's bundled module
(`Check::Check` / uppercase `CHECK_FOUND`) and drop the whole CTest tree. With no
config discoverable, `find_package` falls back to MODULE mode and the bundled
module consumes the two seeds above (configure log: `-- Found Check: .../libcheck.a`).
---

**编译结束**: 2026-09-23 21:04
**最终状态**: built
