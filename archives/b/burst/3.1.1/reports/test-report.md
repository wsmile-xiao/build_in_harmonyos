# Burst 3.1.1 test report

## Counting method

The common unit is a logical test case. For the upstream suite, the doctest runtime report is authoritative; for the standalone consumer executable, each independently described scenario is one case.

## Results

| Environment | Test group | Passed | Failed | Skipped | Assertions | Result |
|---|---|---:|---:|---:|---:|---|
| Apple arm64 baseline | Upstream doctest suite | 724 | 0 | 0 | 1,036 | PASS |
| Apple arm64 Conan lifecycle | Upstream doctest suite | 724 | 0 | 0 | 1,036 | PASS |
| Apple arm64 packaged consumer | API scenarios | 4 | 0 | 0 | 6 | PASS |
| OHOS 6.0 armv8 CI #45099 | Upstream doctest suite | 723 | 1 | 0 | 1,035/1,036 passed | FAIL |

CI #45099 confirms that the prior absolute-path repair works: it configured successfully, compiled all 96 upstream test translation units, linked `burst-unit-tests`, and ran all 724 cases. The only failure was `to_unsigned<char>` (`0 == 128`) because OHOS AArch64 defaults plain `char` to unsigned while that unchanged upstream template case assumes signed `char`. The OHOS suite now compiles with `-fsigned-char` per knowledge E419; final counts remain pending until `/rebuild` verifies the fix.

The OHOS `test_package` stage was not run in CI #45099 because Conan correctly stopped after the upstream suite returned failure; its remote result remains pending.

## Consumer scenarios

1. Sort signed integers through `burst::radix_sort` and compare the exact order.
2. Lazily intersect vector/list/deque ranges through `burst::intersect` and compare `{3, 5, 7}`.
3. Store and retrieve heterogeneous values through `burst::dynamic_tuple`.
4. Evaluate `burst::intpow` in a compile-time assertion.

## Integrity

- Official source SHA-256: `ee58c7b98ca1709dd452b9ba46cb4c91fc0b2952edd020ed5bc2d600b3edeae7`
- Verification command: `conan create archives/b/burst/3.1.1 -pr:h=default -pr:b=default --build=missing`
- Verification rerun date: 2026-09-12
- Clean verification runtime: Conan 2.32.0 with a new isolated Conan home
- Upstream execution: absolute `build/Release/test/burst-unit-tests` path with upstream's original `--report_level=short --color_output` arguments
- No upstream source or test file was modified.
- The package installed 185 public Burst headers.
- Remote CI evidence: build #45099 ran the complete upstream executable and reported 723/724 cases, with only the plain-char signedness assertion failing.
