# cute_tiled 1.0.0 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 (os=OHOS, arch=armv8)
- Clang 15.0.4 (ci/conan/profiles/ohos-aarch64)
- Conan 2.29.1

## Verification

- `conan-verify cute_tiled 1.0.0`: exit 0
- G1: PASS (recipe completeness)
- G2: PASS (conan create clean build + test_package)
- G3: PASS (no system-name lib isolation issue, header-only)
- G4: PASS (artifacts)
- L2/L4/L5: PASS

## test_package

The test defines TINYTILED_IMPLEMENTATION, loads a real 4x3 JSON map via
tinytiled_load_map_from_file, asserts width/height/layers, frees via
tinytiled_free_map, and prints PASS.

- Test cases: 1
- Passed: 1
- Failed: 0
- Skipped: 0

## OHOS signed runtime

- ELF compiled by OHOS clang-15 (rc=0)
- Signed via framework sign-elf flow (binary-sign-tool), .codesign verified by llvm-readelf
- Post-sign run on the same final ELF path: PASS (4x3 layers=ground, rc=0)

## Result

PASS
