# abnfgen 0.21 adaptation notes

## Source and build system

The official release archive is downloaded from quut.com and verified with its
published SHA256. It is an Autotools C project and already contains
`configure` and `Makefile.in`; no Autotools regeneration is needed.

## Dependencies

The program only uses the C/POSIX runtime and declares no Conan dependency.

## Tests

The recipe invokes the upstream `make check` target. Version 0.21 does not
ship an upstream test suite, so the consumer test validates an ABNF grammar,
generates three files, and verifies that every generated value matches it.

## Validation state

Validated on a HarmonyOS aarch64 real device:

- `ci/scripts/preflight_check.sh abnfgen/0.21` passed (exit 0, no dependencies to check).
- `scripts/ohc-run.py conan-verify abnfgen 0.21` passed all gates G0–G4 (exit 0), and marked the recipe publishable.
- `CI_PACKAGES="archives/a/abnfgen/0.21" zsh ci/conan/build_and_test.sh` passed with a 100% pass rate and a confirmed L1e negative test.
- The consumer `test_package/test_abnfgen.sh` actually ran and executed 5 functional assertions against the packaged `abnfgen` binary.
- The upstream `make check` target was invoked by the recipe; the upstream 0.21 release tarball ships no test cases, so the upstream test-case count is 0.
- All 5 consumer functional assertions passed: ABNF grammar validation, generation of 3 output files, output file count is 3, every output value is one of xy/xyxy/xyxyxy, and the test script exits 0.
