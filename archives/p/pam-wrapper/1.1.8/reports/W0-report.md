# pam-wrapper 1.1.8 W0 and source-analysis report

## W0 result

Status: dependency resolved with separately adapted `linux-pam/1.7.2`.

`pam-wrapper` requires a PAM implementation at build and runtime:

- headers: `security/pam_appl.h`, `security/pam_modules.h`,
  `security/pam_ext.h`
- libraries: `libpam`, optionally `pam_misc`

No PAM implementation recipe was present in this repository checkout during the
initial W0 pass, so `linux-pam/1.7.2` was adapted first under issue #1765 and is
now used as the hard dependency for this package.

Upstream tests require `cmocka >= 1.1.0`. `cmocka/2.0.2` is available from the
`ohpcd` remote for the OHOS CI profile and resolves as a non-visible Conan test
requirement. `linux-pam/1.7.2` is available as the hard runtime dependency.

## Source analysis

- Upstream tarball:
  `https://ftp.samba.org/pub/cwrap/pam_wrapper-1.1.8.tar.gz`
- SHA256:
  `6549c0b3e41d1ebe0c94a1be63c25eec918191462b602ab6f47d4a5fa709c3e4`
- Build system: CMake
- Main options: `UNIT_TESTING`, `PICKY_DEVELOPER`
- Default prepared package mode: `with_upstream_tests=True`, `UNIT_TESTING=ON`

Important files inspected:

- `CMakeLists.txt`: top-level CMake project and CTest/cmocka hook
- `ConfigureChecks.cmake`: PAM header/library and libc capability checks
- `src/CMakeLists.txt`: builds `pam_wrapper` and `pamtest`
- `src/modules/CMakeLists.txt`: builds `pam_matrix`, `pam_get_items`,
  `pam_set_items`, and `pam_chatty`
- `src/python/python3/CMakeLists.txt`: Python extension is conditional on
  Python development files
- `tests/CMakeLists.txt`: registers cmocka and Python tests when enabled

## Prepared artifacts

- `conanfile.py`
- `conandata.yml`
- `test_package/conanfile.py`
- `test_package/CMakeLists.txt`
- `test_package/test_pam_wrapper.c`
- `test_package/MANIFEST.yml`
- `manifest.yaml`
- `notes.md`

The test package performs a real consumer exercise: it pre-creates a
`pam_matrix` service and passdb, loads `libpam_wrapper.so`, and calls
`run_pamtest()` from `libpamtest`.

`test_package/test_pam_wrapper.c` was rechecked against the official
`pam_wrapper-1.1.8` source. In the non-DOXYGEN build path,
`run_pamtest()` passes `sizeof(test_cases) / sizeof(test_cases[0])` to
`_pamtest()`, and `src/libpamtest.c` iterates with `tcindex <
num_test_cases`. The test array is bounded by that explicit count.

## OHOS real-device result

Run:
`/storage/Users/currentUser/ohos-test-runs/codex-pam-wrapper-pam-wrapper-pam-wrapper-1.1.8-r3-conan5-20260806-132958-13395`

- L0: pass
- L1: pass, `test_package` executed and printed
  `pam-wrapper libpamtest authentication check passed`
- L2: skip, no `bin/` directory
- L4: pass, patch scan clean
- L5: pass, library artifacts present

Runtime note: `pam_wrapper` copies `PAM_WRAPPER_SERVICE_DIR` during
`LD_PRELOAD` initialization, before `main()`, so test service files are created
by `test_package/conanfile.py` before launching the executable.

The verification job used a clean `main` clone where `linux-pam/1.7.2` is
tracked by the repository; no local `conan export archives/l/linux-pam/1.7.2`
step was used.

Upstream test run:
`/storage/Users/currentUser/ohos-test-runs/codex-pam-wrapper-upstream-20260807-144624`

- Default `conan create`: pass
- CTest inventory: 1 target (`test_pam_wrapper`)
- CMocka result: 23/23 cases passed
- Consumer `test_package`: pass
- Repository CI: L0/L1/L4/L5 pass; L2 skip (no `bin/`)
- CTest log SHA256:
  `9660199e69663db0bcced0d4bf802d3d6e318219030ecad4e731bd7806c9ed87`
- Repository CI log SHA256:
  `a181e7753188788ad47bd24a4196d2d68e47208a377d4949a9ba3370283d59c7`
- `ohc-run.py conan-verify`: overall pass; G0/G1/G2/G3 passed, with
  cache-path-dependent L2/L4/L5 skipped by that wrapper and covered by the
  repository CI instead

## Next commands

The repository-level command used for validation was:

```sh
CI_PACKAGES="archives/p/pam-wrapper/1.1.8" zsh ci/conan/build_and_test.sh
```
