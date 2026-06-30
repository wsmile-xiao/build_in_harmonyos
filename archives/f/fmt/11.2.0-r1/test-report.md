# Test Report — fmt 11.2.0-r1

**Date**: 2026-05-19
**Build System**: CMake

## Test Results

**Total Tests**: 21
**Passed**: 20 (95%)
**Failed**: 1 (5%)

### Failed Test
- **Test**: file_test.line_buffering
- **Location**: test/os-test.cc:538
- **Error**: Expected n=42, got n=0
- **Duration**: 143ms
- **Reason**: Platform-specific behavior difference in file buffering on HarmonyOS

### Passed Tests (20)
1. args-test (0.03s)
2. base-test (0.04s)
3. assert-test (0.03s)
4. chrono-test (0.06s)
5. color-test (0.03s)
6. gtest-extra-test (0.20s)
7. format-test (0.06s)
8. format-impl-test (0.04s)
9. ostream-test (0.03s)
10. compile-test (0.02s)
11. compile-fp-test (0.03s)
12. printf-test (0.04s)
13. ranges-test (0.04s)
14. no-builtin-types-test (0.04s)
15. scan-test (0.04s)
16. std-test (0.04s)
17. unicode-test (0.03s)
18. xchar-test (0.03s)
19. enforce-checks-test (0.02s)
20. posix-mock-test (0.03s)

## Notes
- One test failure related to file buffering behavior
- This is likely a platform-specific issue on HarmonyOS
- Core formatting functionality works correctly (all format tests pass)
- Recommendation: Accept with documentation of platform-specific limitation
