# config-loader 1.0 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64
- Clang 15.0.4 (aarch64-linux-ohos)
- Conan 2.29.1
- CMake 4.1.2

## Verification

- `conan-verify config-loader 1.0`: exit 0 (G0/G1/G2/G3/G4 + L2/L4/L5 all passed)
- `conan create archives/c/config-loader/1.0` (ohos-aarch64 profile): exit 0
- W3 local CI simulation (build_and_test.sh): passed after baseline isolation re-verification
- Upstream test suite: `All tests passed (352 assertions in 29 test cases)`, exit 0

## Upstream tests (source-declared ledger)

- 13 user test source files in `test/ut/` (Catch2 BDD style, `SCENARIO` = TEST_CASE alias)
- source_declared_total: 29; configured_executable_total: 29; executed_passed_total: 29
- Passed: 29/29 (100%); failed: 0; uninstantiated: 0
- Full-run evidence: `logs/upstream-test.log` — "All tests passed (352 assertions in 29 test cases)", exit 0

## test_package (consumer + platform tests)

- `test_config-loader` (consumer case): loads a business "order service" JSON
  config through the public API (DEFINE_SCHEMA + loadJSON2Obj), asserts field
  values and the missing-field error path.
- `ohos_platform_test` (HarmonyOS-specific): serialize dump assertion +
  standard-JSON round-trip + YAML backend load on the OHOS target.
- Both registered as CTest; `ctest` reports 100% passed (2/2), exit 0.

## Result

The recipe was verified on a HarmonyOS aarch64 target and is eligible for
published status after the release pipeline uploads the artifact.
