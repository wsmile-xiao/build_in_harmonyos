# libco 1.0 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15 (OHOS SDK sysroot, musl libc)
- Conan 2.29.1 (OHOS adapted, os=OHOS / aarch64-linux-ohos triplet)

## Verification

- `conan-verify libco 1.0`: exit 0 (G0-G4, L2/L4/L5 all PASS)
- `finish libco 1.0` W3 local CI (`ci/conan/build_and_test.sh` equivalent):
  exit 0 — `Success: 1, Failed: 0, Pass rate: 100.0% (1/1)`
- L0: passed (JC junk check: 0 hits in libco scope)
- L1 test_package: passed
- L2: passed (platform smoke)
- L4: passed (checksec static scan)
- L5: passed (artifact baseline)

## Upstream tests (libco v1.0 has no make check; examples are the test suite)

| Test | Command | Result |
|------|---------|--------|
| example_closure | `./example_closure` | PASS (exit 0) |
| example_cond | `./example_cond` | PASS (exit 0) |
| example_copystack | `./example_copystack` | PASS (exit 0, 100k switches) |
| example_specific | `./example_specific` | PASS (exit 0) |
| example_thread | `./example_thread` | PASS (exit 0, 4 threads x 50k coroutines) |
| example_poll | `./example_poll 127.0.0.1 <port>` | PASS (exit 0) |
| example_echosvr/echocli | server/client pair on loopback | PASS (both exit 0) |

- Test cases: 8 (upstream) + 1 (test_package)
- Passed: 9
- Failed: 0
- Skipped: 0

## test_package

The test executes a real coroutine (R34): `co_create` + 100x
`co_resume`/`co_yield_ct` round-trips, asserts counter == 100 — this drives
`coctx_make` and the new aarch64 `coctx_swap` assembly end-to-end.

- Test cases: 1
- Passed: 1
- Failed: 0
- Skipped: 0

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible for
published status.
