# Burst 3.1.1 upstream test baseline

- Date: 2026-09-09
- Source: official `v3.1.1` release archive, SHA-256 `ee58c7b98ca1709dd452b9ba46cb4c91fc0b2952edd020ed5bc2d600b3edeae7`
- Framework: doctest 2.5.2
- Command: `conan create archives/b/burst/3.1.1 -pr:h=default -pr:b=default --build=missing` (the recipe invokes CMake target `check`)
- Result: PASS
- Test cases: 724 passed, 0 failed, 0 skipped
- Assertions: 1,036 passed, 0 failed

The source tree contains 96 C++ test translation units. The framework-reported 724 logical cases are used as the canonical count because doctest expands template cases beyond the 638 literal `TEST_CASE` macro occurrences.

The baseline build used the repository's full Boost 1.90.0 headers and doctest 2.5.2. Those substitutions address Apple arm64 host compatibility only; no Burst source or test file was modified.
