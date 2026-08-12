# abduco 0.6 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4
- Conan 2.29.1

## Verification

- `conan-verify abduco 0.6`: exit 0
- `CI_PACKAGES="archives/a/abduco/0.6" zsh ci/conan/build_and_test.sh`: exit 0
- L0: passed
- L1: passed
- L1e R34 negative test: passed
- L2: skipped by the script's platform smoke-test rule
- L4: passed
- L5: passed

## test_package

The test executes `abduco -v`, asserts exit code 0, and asserts that the
output contains `abduco-0.6`.

- Test cases: 1
- Passed: 1
- Failed: 0
- Skipped: 0

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible for
published status.
