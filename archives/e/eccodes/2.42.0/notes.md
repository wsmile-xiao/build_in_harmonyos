# eccodes 2.42.0 adaptation notes

## Scope

- Upstream: ECMWF ecCodes 2.42.0 official source bundle.
- Build system: CMake with bundled ecbuild modules.
- Package scope: core `eccodes` C/C++ library, headers, CMake/pkg-config
  metadata, and installed definitions/samples needed by consumers such as
  Magics.

## Source

- URL: `https://confluence.ecmwf.int/download/attachments/45757960/eccodes-2.42.0-Source.tar.gz?api=v2`
- SHA256:
  `60371b357cb011dee546db2eabace5b7e27f0f87d3ea4a5adde7891371b3c128`

## Configuration

The first dependency package intentionally keeps a narrow dependency surface:

```text
-DENABLE_AEC=OFF
-DENABLE_JPG=OFF
-DENABLE_PNG=OFF
-DENABLE_NETCDF=OFF
-DENABLE_FORTRAN=OFF
-DENABLE_GEOGRAPHY=OFF
-DENABLE_MEMFS=OFF
-DENABLE_EXAMPLES=OFF
-DENABLE_BUILD_TOOLS=OFF
-DENABLE_TESTS=OFF
-DBUILD_TESTING=OFF
-DENABLE_INSTALL_ECCODES_DEFINITIONS=ON
-DENABLE_INSTALL_ECCODES_SAMPLES=ON
```

`ENABLE_AEC=OFF` is explicit because ecCodes 2.42.0 otherwise treats missing
AEC as a configure-time critical error.

## Tests

`test_package` links through Conan's generated `eccodes::eccodes` target and
exercises a real sample-backed API path:

- `codes_get_api_version()`
- `codes_handle_new_from_samples(NULL, "GRIB2")`
- `codes_get_long()` / `codes_set_long()`
- `codes_handle_delete()`

The package exports `ECCODES_DEFINITION_PATH` and `ECCODES_SAMPLES_PATH` in the
run environment so samples/definitions remain discoverable from the Conan
package root. No upstream ecCodes regression-test pass rate is claimed.

## 2026-08-08 native upstream-test mode

- `with_upstream_tests=False` is the package default and retains the narrow
  library-only dependency surface above.
- A native HarmonyOS PC transaction can set `with_upstream_tests=True`; it
  enables build tools, `ENABLE_TESTS`, and `BUILD_TESTING`, then runs CTest
  only when Conan reports that the target is runnable. `ENABLE_EXTRA_TESTS`
  stays disabled because it expands beyond the first-pass feature scope.
- No upstream or consumer test total is implied by this option. The current
  status remains `failed` until the exact candidate runs on the device.
