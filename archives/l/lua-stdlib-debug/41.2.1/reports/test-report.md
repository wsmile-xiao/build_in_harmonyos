# Test Report — lua-stdlib-debug 41.2.1

## Build Test

- Build system: autotools
- Build result: ✅ PASS
- Build command: `./configure && make -j1`

## Conan Test Package

- Test: Load `std.debug` module via lua interpreter
- Result: ✅ PASS
- Output: `std.debug loaded successfully`

## Verification

- conan-verify: ✅ PASS (G1-G4, L2/L4/L5)
- W3 local CI: ✅ PASS (setup.sh + build_and_test.sh)

## Test Date

2026-08-22
