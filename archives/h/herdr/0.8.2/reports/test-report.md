# herdr 0.8.2 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4, Rust/Cargo 1.98.0, Zig 0.15.2
- Conan 2.29.1

## Verification

- `conan-verify herdr 0.8.2`: exit 0
- `CI_PACKAGES="archives/h/herdr/0.8.2" zsh ci/conan/build_and_test.sh`: exit 0 (local W3)
- G0: passed
- G1: passed
- G2 (conan create + test_package): passed
- G3 (system same-name library isolation): passed
- G4 (artifact integrity): passed
- L0 (quality gates incl. R38 commands.json): passed
- L1 (test execution): passed
- L2 (smoke test): passed
- L4 (static security scan): passed
- L5 (baseline artifact check): passed

## test_package

The test (`test_package/test_herdr.py`) executes:
1. `herdr --version` — asserts output contains `0.8.2`
2. `herdr server` — starts the background daemon
3. `herdr status server` — asserts `running` + `0.8.2`
4. `herdr workspace create --label conan-test --no-focus` — asserts `workspace_created`
5. `herdr workspace list` — asserts the created workspace appears

- Test cases: 5 (assertions: 10)
- Test results: all passed on HarmonyOS aarch64

## Packaging

- `packaging/herdr-0.8.2.tar.gz` — bin/herdr (aarch64 OHOS ELF, musl dynamic, unsigned; signed by CI sign.sh)
- Software-level `commands.json` declares herdr as an R38 tool
