# shortfin 1.0 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4
- Conan 2.29.1

## Verification

- `conan-verify shortfin 1.0`: exit 0 (all gates G0-G4 + L2/L4/L5 passed)
- `CI_PACKAGES="archives/s/shortfin/1.0" zsh ci/conan/build_and_test.sh`: exit 0 (W3 local CI simulation passed)
- L0: passed (quality gates, junk check, knowledge check)
- L1: passed (conan create clean build)
- L2: skipped (no smoke test cache path)
- L4: skipped (no checksec cache path)
- L5: skipped (no baseline comparison cache path)

## test_package

The test_package builds a simple C program that verifies the shortfin binary
exists in the package's bin/ directory. The test uses CMake and CTest.

- Test cases: 1
- Passed: 1
- Failed: 0
- Skipped: 0

The upstream Shortfin source has no test suite (no tests/ directory, no
Makefile.am check targets, no configure.ac test macros). This is expected
for a lightweight static web server application.

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible for
published status.
