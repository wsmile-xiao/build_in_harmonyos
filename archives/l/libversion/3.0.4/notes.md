# libversion 3.0.4 — Adaptation Notes

## Upstream

- **Repository**: https://github.com/repology/libversion
- **Tag**: 3.0.4
- **Source**: https://github.com/repology/libversion/archive/refs/tags/3.0.4.tar.gz
- **SHA256**: `48c2a4a98b6f220dedd535979f1e9ab83f9bf869e06c0f5e7bb1be6d2e662fee`
- **License**: MIT
- **Language**: C (one utility in C++)
- **Standard**: C99
- **Build system**: CMake ≥ 3.22.1
- **Dependencies**: none

## Products

Upstream always builds BOTH a shared and a static library target
(`OUTPUT_NAME=version` → `libversion.so` / `libversion.a`, link with `-lversion`).

Installed files:
- `lib/libversion.so` / `lib/libversion.a`
- `include/libversion/version.h` (public API)
- `include/libversion/config.h` (generated: version constants)
- `include/libversion/export.h` (generated: export macros via `generate_export_header`)
- `lib/pkgconfig/libversion.pc`
- `lib/cmake/libversion/libversionConfig.cmake` (removed in package() to avoid
  target conflicts with Conan's CMakeDeps)
- `bin/version_compare` (CLI: compare two version strings)
- `bin/version_sort` (CLI: sort version strings from stdin)

`version_explain` is built but NOT installed by upstream.

## API

The public API (from `libversion/version.h`) consists of:

| Function | Signature |
|---|---|
| `version_compare2` | `int version_compare2(const char* v1, const char* v2)` |
| `version_compare4` | `int version_compare4(const char* v1, const char* v2, int v1_flags, int v2_flags)` |

Flags enum:
- `VERSIONFLAG_P_IS_PATCH` (0x1) — treat `p` suffix as patch, not prerelease
- `VERSIONFLAG_ANY_IS_PATCH` (0x2) — treat any suffix as patch
- `VERSIONFLAG_LOWER_IS_PATCH` (0x4) — treat lowercase suffix as patch

Macros:
- `LIBVERSION_VERSION_ATLEAST(x, y, z)` — compile-time version check
- `LIBVERSION_VERSION_MAJOR` / `LIBVERSION_VERSION_MINOR` / `LIBVERSION_VERSION_PATCH`
- `LIBVERSION_NO_DEPRECATED` — disable deprecated API declarations

## Build notes

- No OHOS-specific patches required. Pure C library with no external dependencies.
- The `generate_export_header` mechanism requires `LIBVERSION_STATIC_DEFINE` to be
  defined when consuming the static library. This is handled in `package_info()`.
- Upstream CMake config files are removed in `package()` to prevent target conflicts
  with Conan's CMakeDeps-generated `find_package` files.
- When `shared=False`, both upstream targets become static (due to `BUILD_SHARED_LIBS=OFF`).
  The static target's install overwrites the shared-turned-static target's install,
  resulting in a single `libversion.a`. The `LIBVERSION_STATIC_DEFINE` define is
  propagated to consumers via `cpp_info.defines`.

## R26 (system-name library) check

libversion is NOT present as a system library (`/lib/libversion.so*` not found),
so R26 does not apply and packaging is safe.

## Upstream tests

- **Source files**: 1 (`tests/compare_test.c`); fuzzer `tests/compare_fuzzer.c` exists
  but is not registered with CTest.
- **Executables**: 2 (`compare_test`, `compare_fuzzer`)
- **CTest registered**: 1 (`compare_test`)
- **Assertions**: 229 (error-accumulating `version_test*` calls across 25 test groups)
- **Native run**: 1/1 passed, 0 failed, 0 skipped
