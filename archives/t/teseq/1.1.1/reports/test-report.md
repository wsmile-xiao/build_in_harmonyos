# teseq 1.1.1 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device (HarmonyOS 6.1.0.117)
- OHOS SDK clang 15.0.4 (aarch64-unknown-linux-ohos), OHOS SDK 26.0.0.18
- Conan 2.29.1 (OHOS-adapted), profile `ohos-aarch64-device`
- Build: GNU autotools (configure + make), in-source

## Verification

- `python3 scripts/ohc-run.py clean-verify teseq 1.1.1`: exit 0 (patches alone give a
  clean configure + make + make install of both binaries; no recipe-side workaround)
- `python3 scripts/ohc-run.py conan-verify teseq 1.1.1 --profile ohos-aarch64-device`: exit 0 (G0–G4 PASS)
- `CI_PACKAGES="archives/t/teseq/1.1.1" zsh ci/conan/build_and_test.sh`: exit 0 (W3 local CI)
- L0: passed
- L1: passed
- L1e R34 negative test: passed
- L2/L4/L5: passed (executable-only package, no cache path)

## Upstream tests (make check, run during `conan create` on the device)

| Suite | Command | Cases | Passed | Failed | Skipped |
| --- | --- | --- | --- | --- | --- |
| teseq shell suite | `tests/run-tests` | 28 | 28 | 0 | 0 |
| reseq shell suite | `tests/run-tests -r` | 28 | 28 | 0 | 2 (harness `run_reseq=false`, counted as pass) |
| sequence exercise | `exercise-seqs` | - | OK ("Results: All runs look okay.") | 0 | 0 |
| libcheck unit tests | `check-TESTS` | 2 programs | 2 (7 + 3 individual checks) | 0 | 0 |

The two libcheck tests (`src/test-ringbuf`, `src/test-inputbuf`) are compiled and
executed because the recipe declares `check/0.15.2` as test_requires and
publishes it through PkgConfigDeps; without `check` upstream would silently skip
them (`AM_CONDITIONAL DO_CHECK_TESTS`).

```
RUNNING TESEQ TESTS ... Ran 28 total tests / Passed: 28 / Failed: 0
RUNNING RESEQ TESTS ... Ran 28 total tests / Passed: 28 / Failed: 0
Results: All runs look okay.
# TOTAL: 2  # PASS: 2  # FAIL: 0
```

## test_package

Consumer-side regression (teseq publishes command-line tools only, no
compile-time API); 13 `self.run` assertions:

1. `bin/teseq` and `bin/reseq` exist and are executable
2. `teseq --version` reports `GNU teseq 1.1.1`
3. `teseq --help` and `reseq --help` expose `--timings`
4. `ESC[1mBOLD ESC[0m` input is decoded with an `SGR` description line and the
   literal `BOLD` text is preserved
5. `reseq decoded roundtrip.bin` + `cmp` proves the byte-exact round trip
6. the fuzz regression input `ESC!!DEL` fixed in 1.1.1 exits promptly (RC=0)

- Assertions: 13
- Passed: 13
- Failed: 0

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible for
published status.
