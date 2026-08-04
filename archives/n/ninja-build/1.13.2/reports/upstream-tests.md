# ninja-build 1.13.2 upstream test handling

Date: 2026-07-30

## Inventory

- Official upstream CMake/CTest discovers one aggregate test target, `NinjaTest`, built from the upstream `src/*_test.cc` files.
- `configure.py --bootstrap` is an upstream build path, not the full upstream test suite.
- No separate vendored runtime test corpus is included in the 1.13.2 release tarball.

## Executed on OHOS real device

- SSH port: old port `56267`.
- Runner mode: `heavy` with `--try-lock`.
- run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-ninja-build-ninja-build-1.13.2-upstream-ctest-r2-oldport-20260730-001233-30686`
- Command: `ctest --output-on-failure`
- Result: `0/1` official upstream CTest target passed.
- Failure: `NinjaTest` timed out after 25 minutes with repeated `ninja: ppoll: Out of memory` output.

## New-port split rerun

- Date: 2026-07-30.
- SSH port: new port `33332` only.
- Runner mode: `heavy` with `--try-lock`.
- Default `ppoll` run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-ninja-build-ninja-build-1.13.2-upstream-split-r3-newport-20260730-173904-45482`
- `NINJA_FORCE_PSELECT=ON` run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-ninja-build-ninja-build-1.13.2-pselect-localtar-r1-newport-20260730-180749-56401`
- Environment probe run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-ninja-build-ninja-build-1.13.2-env-probe-r2-newport-20260730-182115-62170`
- The default build used upstream CMake with `BUILD_TESTING=ON`; CTest still registered a single aggregate `NinjaTest` entry.
- `ninja_test --gtest_list_tests` expanded the aggregate target to 410 gtest cases in the default `ppoll` build. `SubprocessTest.SetWithLots` exists only when `USE_PPOLL` is enabled.
- Default `ppoll` split result:
  - `SubprocessTest.*-SubprocessTest.SetWithLots`: 9/12 passed, 3 failed.
  - `SubprocessTest.SetWithLots`: timed out after 300 seconds and repeatedly printed `ninja: ppoll: Out of memory`.
  - Full gtest excluding `SubprocessTest.SetWithLots`: 405/409 passed, 4 failed.
- `NINJA_FORCE_PSELECT=ON` result:
  - Built successfully from the verified upstream v1.13.2 tarball copied into the job because direct GitHub download from the worker timed out.
  - `SubprocessTest.SetWithLots`: 0 tests registered, because the upstream test is guarded by `USE_PPOLL`.
  - Full gtest excluding `SubprocessTest.SetWithLots`: 405/409 passed, 4 failed, same failures as the default build.

Failed cases after excluding the `ppoll` stress case:

- `Jobserver.PosixFifoClient`: `mknod(..., S_IFIFO | 0666, 0)` returned `-1`; runner probe showed `mkfifo` and `mknod p` both fail in `$RUN_DIR/tmp` with `Operation not permitted`.
- `SubprocessTest.InterruptChildWithSigHup`: upstream expects `ExitInterrupted` (`130`), but `subproc->Finish()` returned `129`; runner probe showed `/bin/sh -c 'kill -HUP $$'` exits with `129`.
- `SubprocessTest.SetWithSingle`: upstream runs `ls /` as `kSimpleCommand`; runner probe showed `/bin/sh -c 'ls /'` exits `1` with `ls: /: Permission denied`.
- `SubprocessTest.SetWithMulti`: includes `kSimpleCommand` and `id -u`; runner probe showed `ls /` exits `1`, and `id -u` exits `1` with `id: bad uid 20020105`.

## Adapted package verification

- Final package run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-ninja-build-ninja-build-1.13.2-conan-r5-oldport-current-profile-20260730-045514-53751`
- Full ref: `ninja-build/1.13.2#1580ac184f881f486812fa706ef53022:6b129b068851896169fae42d399fa922d239ce8a#3fcaf810f37a99ac7696e1333bcee0d5`
- `conan create + test_package`: PASS.
- The packaged-tool smoke verifies exact `ninja --version`, executes a minimal `build.ninja` graph, validates the produced output, and checks the dry-run path.

## Decision

The recipe keeps `BUILD_TESTING=OFF` for OHOS because the official aggregate `NinjaTest` is not a clean pass on the worker. `NINJA_FORCE_PSELECT=ON` avoids registering the 1025-process `SetWithLots` ppoll stress case, but it does not fix the remaining FIFO, shell command, uid, and SIGHUP-status assumptions. The limitation is documented here and in the PR body; it is not reported as a full upstream test pass.
