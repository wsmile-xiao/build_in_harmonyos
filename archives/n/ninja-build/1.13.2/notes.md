# ninja-build 1.13.2

## Summary

- Upstream source: https://github.com/ninja-build/ninja/archive/refs/tags/v1.13.2.tar.gz
- SHA256: `974d6b2f4eeefa25625d34da3cb36bdcebe7fbce40f4c16ac0835fd1c0cbae17`
- Dependencies: none.
- Build output: `bin/ninja` or `bin/ninja.exe`.

## Local Build Notes

Windows local source bootstrap was verified with MinGW:

```text
python configure.py --bootstrap --platform=mingw --host=mingw
ninja.exe --version
1.13.2
```

The first bootstrap attempt failed at final link because MinGW could not create
temporary files under the user Temp directory. Redirecting `TMP` and `TEMP` to a
writable workspace path fixed it.

## 2026-07-28 Local Verification

- `py_compile` for recipe and test package: PASS.
- `conan inspect archives/n/ninja-build/1.13.2`: PASS.
- `conan export archives/n/ninja-build/1.13.2`: PASS.
- Windows/MinGW `conan create` with `test_package`: PASS.

## 2026-07-30 OHOS Real Device Verification

- SSH port: old port `56267`.
- Conan job: `/storage/Users/currentUser/ohos-users/codex-a/ninja-build-1.13.2-oldport-r1`.
- Runner command used an isolated `CONAN_HOME`, a job-local OHOS profile, `--mode heavy`, and `--try-lock`.
- `conan create + test_package`: PASS.
  - run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-ninja-build-ninja-build-1.13.2-conan-r5-oldport-current-profile-20260730-045514-53751`
  - profile: `ohos-aarch64-current`
  - full ref: `ninja-build/1.13.2#1580ac184f881f486812fa706ef53022:6b129b068851896169fae42d399fa922d239ce8a#3fcaf810f37a99ac7696e1333bcee0d5`
  - L0/L1/L2/L4/L5: pass.
  - `test_package` verifies `--version`, executes a minimal `build.ninja` graph, and then checks dry-run reports no work.
- One rerun before the final pass failed during CMake compiler detection because the shared OHOS profile pointed at stale `/data/service/hnp/bin/clang++`.
  - run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-ninja-build-ninja-build-1.13.2-conan-r4-oldport-current-bytes-20260730-045239-52707`
  - The final r5 run used a job-local profile with `/storage/Users/currentUser/usr/local/bin/clang-15`.
- Additional manual packaged-tool smoke before folding it into `test_package`: PASS.
  - run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-ninja-build-ninja-build-1.13.2-tool-smoke-r1-oldport-20260730-004112-42377`
  - Result: `ninja` executed a minimal `build.ninja` graph and then reported `ninja: no work to do.` on dry-run.
- Upstream CTest attempt: 0/1 PASS.
  - run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-ninja-build-ninja-build-1.13.2-upstream-ctest-r2-oldport-20260730-001233-30686`
  - CTest discovered 1 test, `NinjaTest`.
  - `NinjaTest` timed out after 25 minutes with repeated `ninja: ppoll: Out of memory` output.
  - This is recorded as an OHOS upstream-test limitation; the recipe keeps `BUILD_TESTING=OFF` and relies on the focused packaged-tool smoke in `test_package`.
- New-port split upstream rerun:
  - Default `ppoll` run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-ninja-build-ninja-build-1.13.2-upstream-split-r3-newport-20260730-173904-45482`
  - `NINJA_FORCE_PSELECT=ON` run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-ninja-build-ninja-build-1.13.2-pselect-localtar-r1-newport-20260730-180749-56401`
  - Environment probe run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-ninja-build-ninja-build-1.13.2-env-probe-r2-newport-20260730-182115-62170`
  - CTest still discovers one aggregate `NinjaTest`; gtest expands it to 410 cases in the default `ppoll` build.
  - Default `ppoll`: `SubprocessTest.SetWithLots` timed out after 300 seconds with repeated `ninja: ppoll: Out of memory`; full gtest excluding that stress case ran 409 cases with 405 pass / 4 fail.
  - `NINJA_FORCE_PSELECT=ON`: `SubprocessTest.SetWithLots` is not registered because it is guarded by `USE_PPOLL`; full gtest excluding it still ran 409 cases with 405 pass / 4 fail.
  - Remaining failures are environment/platform assumptions: FIFO creation via `mknod(S_IFIFO)` is not permitted in run tmp, `/bin/sh -c 'ls /'` returns permission denied, `id -u` returns `bad uid 20020105`, and `/bin/sh -c 'kill -HUP $$'` returns 129 while upstream expects 130.
