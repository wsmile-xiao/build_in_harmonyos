# apache-arrow 24.0.0 adaptation closure summary

## Current Scope

The PR remains a basic Apache Arrow C++ consumer package plus Path B evidence.
It does not claim full Apache Arrow upstream test-suite completion.

The stable package scope is:

- `ARROW_IPC=ON`
- `ARROW_COMPUTE=ON`
- `ARROW_CSV=ON`
- `ARROW_FILESYSTEM=ON`
- `ARROW_JSON=ON`

Heavy modules are still outside the regular recipe:

- Parquet
- Dataset / Acero
- Flight
- ORC
- Gandiva
- CUDA

Parquet and Dataset/Acero were tested as separate upstream CTest evidence, not
as enabled recipe guarantees.

## Closed Evidence

- shared Conan create: passed on isolated HarmonyOS device.
- static Conan create: passed on isolated HarmonyOS device.
- enhanced `test_package`: 15 observable assertions.
- largest CTest expansion: 81/89 target passed.
- Parquet focused subset: 11/11 target passed.
- Dataset/Acero focused subset: 26/26 target passed.
- P1 IO/filesystem after test-runtime relink: 248/248 tests passed.
- low-risk increment: 627 passed, 14 skipped.
- compute-on focused subset: 12 target passed, 3272 passed, 25 skipped.

## 89 Target Closure

The original 8 failures in the 81/89 range were narrowed to known categories:

- `arrow-array-test`: GTest `/tmp` capture issue; passes after `TEST_TMPDIR` /
  `TMPDIR` migration with 1038 passed, 1 skipped.
- `arrow-io-file-test`: passes after `0003` file-IO edge fix and test-runtime
  relink, 50/50.
- `arrow-filesystem-test`: passes after `0003` filesystem path fix and
  test-runtime relink, 198/198.
- `arrow-buffer-test`: non-OOM subset 45/45; remaining OOM resize cases are
  allocator/extreme allocation semantics.
- `arrow-misc-test`: non-OOM subset 180/180; remaining OOM/Reallocate cases are
  allocator/extreme allocation semantics.
- `arrow-stl-test`: non-OOM subset 44/44; `allocator.TestOOM` expects
  `std::bad_alloc` but OHOS did not throw.
- `arrow-compute-scalar-cast-test`: `TZDIR` support narrows it to 105/106; the
  remaining case is a historical DST/tzdb expectation difference.
- `arrow-compute-scalar-temporal-test`: full run 46 passed, 1 skipped, 7 failed;
  filtered known timezone/DST differences pass 46, skip 1.

## Reproduction Scripts

Added scripts:

- `scripts/ohos_arrow_relink_tests.py`
- `scripts/ohos-run-upstream-ctest.sh`
- `scripts/ohos-probe-upstream-modules.sh`
- `scripts/ohos_extract_tar_no_links.py`

The script entry points were checked on the HarmonyOS device with `--help`.
The shell scripts avoid heredocs because the device `sh` may create temporary
files under read-only `/tmp`.

## ORC / Flight Boundary

ORC inventory:

- representative target: `arrow-orc-adapter-test`
- dependency expansion: ORC, protobuf, zlib
- isolated cache currently has Boost / GoogleTest but no reusable ORC /
  protobuf / zlib source cache
- first probe RUN_DIR:
  `/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-orc-probe-v1-20260726-224750-37131`
- first probe result: 1200 second timeout, exit code 124, while configuring
  Protobuf through FetchContent

Flight inventory:

- representative target: `arrow-flight-internals-test`
- additional targets include Flight integration, SQL and ODBC tests
- dependency expansion: gRPC, protobuf, re2, zlib, OpenSSL
- also requires service-style test handling, ports or sockets
- v2 probe RUN_DIR:
  `/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-flight-probe-v2-20260727-040342-62286`
- v2 result: gRPC tarball download completed, but extraction failed because the
  current device filesystem rejects symlink/hardlink creation
- mitigation: pre-extracted gRPC 1.46.3 with link entries copied as regular
  files/directories, 12 links copied
- v3 probe RUN_DIR:
  `/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-flight-probe-v3-20260727-042031-3517`
- v3 result: passed gRPC source extraction, then hit Flight static-linkage
  requirement
- v4 probe RUN_DIR:
  `/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-flight-probe-v4-20260727-043233-9482`
- v4 result: static Arrow + pre-extracted gRPC configured, but CMake generate
  failed because `OpenSSL::SSL` and `OpenSSL::Crypto` targets were missing

ORC / Flight heavy probes are intentionally separated from the regular recipe
and should run only when the shared device lock is free.  The Flight probe does
not enter `arrow-flight-internals-test` build/run yet; it currently documents
the gRPC archive-link filesystem gap and the OpenSSL dependency boundary.
