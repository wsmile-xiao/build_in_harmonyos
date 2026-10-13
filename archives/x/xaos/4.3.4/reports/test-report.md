# XaoS 4.3.4 HarmonyOS test report

## Environment

- Target: HarmonyOS 6.0 PC, HarmonyOS HongMeng Kernel 1.12.0, aarch64
- Profile: `ci/conan/profiles/ohos-aarch64`
- Compiler: Clang 15; Conan 2.29.1
- Qt: `qtbase/6.11.1.3`, `qttools/6.11.1.1`
- Display mode: Qt offscreen QPA in an SSH session without an active GUI compositor

## Upstream test inventory

The official XaoS 4.3.4 source has no `tests/` or `test/` directory and registers no CTest cases. The upstream test count is 0; the source and command evidence are in [`upstream-tests.md`](upstream-tests.md).

## Results

| Test | Runs | Passed | Failed | Result |
|---|---:|---:|---:|---|
| Conan G2 `conan create` including `test_package` | 1 | 1 | 0 | PASS |
| W3 `build_and_test.sh` local CI simulation | 1 | 1 | 0 | PASS |
| HarmonyOS native Mandelbrot render and PNG decode | 3 | 3 | 0 | PASS |

The consumer test runs the package's real `bin/XaoS` with `-render`, using `test_package/xaos-smoke.xaf`. The PNG decoder checks chunk structure, zlib data, dimensions of 160×120, and pixel variation. All three device runs produced a valid RGB PNG with at least 1009 unique pixels (23,895 bytes).

After the test script's output and temporary-directory handling were updated, a final `conan test` on the HarmonyOS device resolved recipe revision `453485fa80b39955cc98bd285b4ecd5e` and package revision `06311ee02bf7c13a1f862d4df86af108`; the consumer test passed. A separate cache inspection found an older cached XaoS package that returned `Operation not permitted`; Conan did not select that stale package in the successful test.

Additional CI checks: R34 negative dependency test PASS, L4 patch scan PASS, and L5 executable artifact check PASS. The generic L2 probe skipped because it tries `--version` and `--help`; upstream only recognizes `-help`, prints the help text, and returns 255, so it is not counted as a successful L2 check. This is non-blocking and separate from the successful render test.

## HarmonyOS-specific adaptation verified

The initial device run rejected both the Conan-cached Qt `lrelease` and the installed XaoS ELF with `Operation not permitted`. The recipe now signs a build-local copy of `lrelease` before translation generation and re-signs `bin/XaoS` after CMake installation. The successful on-device rendering test exercises the installed signed executable and validates its actual image output.

## Limitations

Interactive window presentation was not tested because the SSH session had no `DISPLAY`, `WAYLAND_DISPLAY`, or `XDG_RUNTIME_DIR`. The native rendering engine, Qt offscreen plugin path, package runtime libraries, and image output were exercised on-device.

## Evidence

- `conan-verify-report.md`: Conan G0–G3 pass; G4 is explicitly marked not verified because no package ID was available.
- `upstream-tests.md`: source inspection and commands used to establish the upstream test inventory.
- The W3 result and all three HarmonyOS device runs are summarized above; generated runner logs and `.ci-result.json` are not part of the archive.
