# 3proxy 0.9.5 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4
- Conan 2.29.1

## Verification

- `bash ci/scripts/preflight_check.sh 3proxy/0.9.5`: exit 0
- `python3 scripts/ohc-run.py recipe-search 3proxy`: exit 0
- `python3 scripts/ohc-run.py conan-verify 3proxy 0.9.5`: exit 0
  (G1 recipe completeness / G2 clean `conan create` / G3 / G4 + L2 smoke / L4 checksec / L5 baseline all PASS)
- `python3 scripts/ohc-run.py finish 3proxy 0.9.5 built`: W3 local CI simulation passed,
  `.ci-result.json` `exit_code=0`
- `python3 scripts/ohc-run.py graph validate`: exit 0

## Upstream tests

The upstream tree is a Makefile family (Makefile.Linux/FreeBSD/Solaris/unix/win/msvc/
watcom/...) with **no `check` or `test` target**, no `tests/` directory and no CI
workflow files. `test_package/MANIFEST.yml` therefore declares
`upstream_tests: []` truthfully instead of inventing a command.

## test_package

1. `3proxy -h` — assert the usage banner contains `3proxy-0.9.5`
   (upstream exits with code 1 after printing usage; that is the documented behaviour).
2. Start an HTTP proxy listener on a non-privileged loop-back port and open a real
   TCP connection to it (retry for at most 15 s), then stop the process.

- Test cases: 2
- Passed: 2
- Failed: 0
- Skipped: 0

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible for
`built` status.
