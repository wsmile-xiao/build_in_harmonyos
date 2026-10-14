# utf8proc 2.11.3

## Package

- Upstream: https://github.com/JuliaStrings/utf8proc
- Source archive: https://github.com/JuliaStrings/utf8proc/archive/v2.11.3.tar.gz
- Build system: CMake
- OHOS target: armv8

## Tests

- Upstream CMake defaults `UTF8PROC_ENABLE_TESTING` to `Off`; the recipe explicitly enables it and runs CTest with `--no-tests=error`.
- The upstream CMake configuration registers 10 CTest cases on OHOS/Linux. It downloads `NormalizationTest.txt` and `GraphemeBreakTest.txt` from unicode.org during configuration, so that host must be reachable in CI.
- The test package supplies decomposed `e` + combining acute to `utf8proc_map`, then checks the 3-byte NFC output `Aé`.
- The upstream Makefile test path was previously skipped because its test-data generation requires Julia. The CMake test path now enables the upstream suite, but passing results still require confirmation from the target CI run.

## Validation status

The recipe and metadata have not yet been validated by a successful target CI run for this revision. Do not mark this version as built until CI confirms the package build, upstream tests, and test package all pass.
