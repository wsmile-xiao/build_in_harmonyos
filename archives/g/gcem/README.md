# GCEM

GCE-Math (GCEM) is a C++11 `constexpr` math library for compile-time and
runtime mathematical functions.

## HarmonyOS adaptation

- The upstream v1.18.0 CMake project is used with three narrowly scoped
  portability patches: long-double exponent thresholds, tiny-input sqrt
  scaling, and six OHOS libc oracle skips.
- GCEM is header-only and has no third-party Conan dependencies.
- The package preserves the upstream CMake config and exposes the canonical
  `gcem::gcem` consumer target through Conan metadata.
- The upstream suite has 46 standalone test programs but no CTest registration;
  the recipe builds and runs all 46 programs explicitly, with six visible OHOS
  reference-case skips.

## References

- https://github.com/kthohr/gcem
- https://github.com/kthohr/gcem/releases/tag/v1.18.0
