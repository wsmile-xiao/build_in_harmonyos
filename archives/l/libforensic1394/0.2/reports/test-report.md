# libforensic1394 0.2 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device (HongMeng Kernel 1.12.0)
- Clang 15.0.4 (OHOS SDK 26.0.0.18), CMake 4.1.2, Conan 2.29.1
- Build: native aarch64, `shared=False` default (static library)

## Verification

- `conan-verify libforensic1394 0.2`: exit 0. Its own gates all passed:
  G0, G1, G2, G3, G4 plus the verify harness's L2/L4/L5 probes
  (`reports/conan-verify-report.json`, verdict PASS).
- `CI_PACKAGES="archives/l/libforensic1394/0.2" zsh ci/conan/build_and_test.sh`:
  exit 0. Package-side results from that script:
  - L0: passed (structure, test sources, MANIFEST.yml, recipe/data syntax)
  - L1: passed — test_package executed; L1e R34 negative test confirmed the
    consumer binaries genuinely link and call the packaged library
  - L2 (script smoke test): skipped — the package installs no `bin/`
    executables (library only)
  - L4: passed
  - L5: passed — `lib/` contains the installed library

## Upstream test suite

Upstream 0.2 ships **no test suite**: the published release tarball has no
`tests/` directory, `CMakeLists.txt` has no `enable_testing()`/`add_test()`
and there is no Makefile `check` target; the same holds for the upstream
master branch. Source inventory evidence is recorded in `../notes.md`.
Upstream test count is therefore 0/0 (no runnable entry point).

## test_package (installed-package consumer tests)

Two programs are built against the installed package and executed:

| Program | What it verifies | Checks | Result |
|---|---|---|---|
| `forensic1394_api_surface` | all 24 exported functions bind with their header-declared signatures (forced relocations), the public result-code to string table, `FORENSIC1394_CSR_SZ`, out-of-range result codes | 37 | PASS |
| `forensic1394_bus_lifecycle` | documented bus lifecycle without FireWire hardware: alloc, user-data round trip, device enumeration (NULL-terminated empty list, `ndev == 0`), `enable_sbp2` I/O-error path, repeated destroy | 9 | PASS |

- Test cases: 2
- Assertions: 46
- Passed: 2 (46/46 assertions)
- Failed: 0
- Skipped: 0

Hardware note: the device has no FireWire controller (`/dev/fw*` absent), so
the consumer tests assert the documented no-hardware behaviour
(`forensic1394_get_devices` returns a non-NULL empty list with `*ndev = 0`,
`forensic1394_enable_sbp2` returns `FORENSIC1394_RESULT_IO_ERROR`). Device
enumeration and memory access against a real peer cannot be exercised in CI;
the code paths for those are covered by the API-surface relocations plus the
lifecycle assertions, not by a fabricated pass.

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible for
published status.
