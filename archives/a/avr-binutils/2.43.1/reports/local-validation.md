# Validation: avr-binutils 2.43.1

Date: 2026-08-17

## Local preflight

- Official release archive downloaded from ftp.gnu.org.
- SHA256 matched conandata.yml.
- Python AST parsing passed for the recipe and test_package.
- YAML parsing passed for conandata.yml, manifest.yaml, and MANIFEST.yml.
- Both unified diffs passed `git apply --check` against the release source.
- Conan 2.29.1 inspect and export passed.
- Conan source downloaded, verified, extracted, and applied both patches.
- The OHOS/AArch64 profile dependency graph resolved with no external package
  dependencies.
- The makeinfo fallback passed a local version-response and pre-generated Info
  copy test.

## True-device shadow CI

- Runner mode: `heavy --try-lock`, global single-package lock acquired.
- Runner exit code: 0.
- Duration: 586.4 seconds.
- Tested recipe commit: `025ba666fdac38d42d5feefa534388111a3b22ca`.
- Shadow commit: `66a185f1b5dfc310b5a6ba52b891201a9c70a88a`.
- Run directory: `$HOME/ohos-test-runs/codex-avr-binutils-shadow-ci-r5-2244-20260817-134800-3191`.
- Shadow directory: `$HOME/ohos-users/codex/avr-binutils-2.43.1-2244-9516d63741/ohpc-ci-shadow/runs/codex-avr-binutils-shadow-ci-r5-2244-20260817-134800-3191`.
- G0 and L0 passed.
- L1 passed: Conan create, six official libiberty checks, and test_package ran.
- L2 passed for 16 packaged AVR commands.
- L5 passed with packaged `bin/` content.
- The destructive negative test passed after removing package bin/lib content.
- Package test assembled and linked ATmega328P code, emitted Intel HEX, and
  verified AVR ELF architecture, symbols, and size.
- L4 emitted a non-blocking patch scanner warning.

Package reference produced by the successful run:

```text
avr-binutils/2.43.1#45300c6178b07e91be3c6de056feb1bc:6b129b068851896169fae42d399fa922d239ce8a#7d790831c1885bedf94edf6a75212017
```

## Test counts and pass rates

Pass rates below count only tests that actually ran. Unexecuted tests are
reported separately and are never counted as passed.

| Test scope | Executed | Passed | Pass rate | Result |
| --- | ---: | ---: | ---: | --- |
| Upstream `libiberty` checks (`make -C libiberty check`) | 6 | 6 | 100% | Passed |
| Packaged AVR command checks | 16 | 16 | 100% | Passed |
| Conan `test_package` end-to-end scenario | 1 | 1 | 100% | Passed |
| Package-content negative ownership gate | 1 | 1 | 100% | Passed |
| Required CI gates (G0/L0/L1/L2/L5) | 5 | 5 | 100% | Passed |
| Full upstream DejaGNU target matrix | 0 | 0 | N/A | Not executed: `runtest` is not available in the configured Conan remote |

The upstream source contains 25,185 testsuite files and 372 DejaGNU driver
scripts. The six no-DejaGNU `libiberty` checks above are the complete upstream
subset executable in the current single-package environment. Running the
remaining target matrix requires a separately adapted/published DejaGNU and
Expect toolchain; it is intentionally not mixed into this avr-binutils PR.