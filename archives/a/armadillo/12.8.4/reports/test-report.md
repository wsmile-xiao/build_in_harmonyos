# armadillo 12.8.4 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64
- Clang 15.0.4
- Conan 2.29.1

## Verification

- `conan-verify armadillo 12.8.4`: exit 0
- `CI_PACKAGES="archives/a/armadillo/12.8.4" zsh ci/conan/build_and_test.sh`: exit 0
- L0: passed
- L1: passed (test_package executed by conan create)
- L1e R34 negative test: passed (test genuinely depends on armadillo)
- L2: skipped (no bin/ directory — library package)
- L4: passed (patches clean)
- L5: passed (lib/ has content)

## test_package

The test exercises armadillo matrix and vector operations including:
- Matrix creation (randu), addition, multiplication, transpose
- Element access
- Special matrices (zeros, ones, eye)
- Vector operations (sum, norm, min, max, dot)
- Matrix accumulation (accu)

- Test cases: 1
- Passed: 1
- Failed: 0
- Skipped: 0

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible for
published status.
