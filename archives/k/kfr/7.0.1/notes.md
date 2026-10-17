# kfr 7.0.1 - HarmonyOS PC adaptation notes

## Upstream
- Repo: https://github.com/kfrlib/kfr
- Tag: `7.0.1` (note: 7.x tags dropped the `v` prefix)
- Source: `https://codeload.github.com/kfrlib/kfr/tar.gz/refs/tags/7.0.1`
- SHA256: `42b36126f2af8719eff6f26e87e9f155816bc3bb110376e4747ba5de536c2cce`
- License: GPL-2.0-only
- Build system: CMake (`cmake_minimum_required(VERSION 3.16)`), `cxx_std_20`

## Relationship to the 3.0.8 recipe (sibling already merged by another team)
3.0.8 needed two patches. For 7.0.1 only ONE is still relevant:

- C++17 vs C++14 + `inline constexpr` on variable-template specialisations ->
  **gone**: 7.0.1 mandates C++20, so specialisations are implicitly inline and the
  duplicate-symbol link error cannot occur. The old `sincos.hpp` table is removed
  and `fp_precision_limit` is already `constexpr inline` upstream.
- x86-only `-mstackrealign` gate -> **gone**: the flag no longer appears in 7.0.1.
- `SKIP_TESTS`/`ENABLE_DFT`/`CPU_ARCH` -> renamed `KFR_SKIP_TESTS`/`KFR_ENABLE_DFT`/
  `KFR_ARCH`; `generic` remains a valid non-x86 architecture.
- absmin/absmax signed-overflow UB backport -> **already upstream** (`IsNotMinInt`
  is in `tests/unit/simd/min_max.cpp`).
- libstdc++ on OHOS -> **still needed** (patch 0001): the STD_LIB guard covers only
  iOS/Android, and CMake does not model `Platform/HarmonyOS`, so its system name is
  not a usable trigger. The patch adds a `KFR_LINK_LIBSTDCXX` cache switch (empty
  STD_LIB when defined and OFF); the recipe passes `KFR_LINK_LIBSTDCXX=OFF` so OHOS
  deterministically avoids `-lstdc++` (the profile already selects `-stdlib=libc++`).

## CMake / Conan knobs used
- `ENABLE_TESTS=ON`, `ENABLE_EXAMPLES=OFF` (7.0.1 auto-enables examples with tests)
- `KFR_ENABLE_DFT=ON`, `KFR_SKIP_TESTS=OFF` (keeps `add_test()` registration)
- `KFR_ARCH=generic`; `KFR_ENABLE_MULTIARCH` is force-disabled upstream on non-x86,
  so there is no runtime IFUNC dispatch to worry about.
- `BUILD_SHARED_LIBS=OFF` (upstream only emits static archives).

## CTest
`enable_testing()` lives in `tests/CMakeLists.txt`, so ctest runs from
`<build>/tests`. It registers TWO binaries on this build: `all_tests` (Catch2
unit suite: `tests/unit/**` + `dft_test.cpp`, 203 cases) and `audio_test`
(22 cases). Both passed; `100% tests passed out of 2`.

## Boost.Math note
`KFR_USE_BOOST_MATH` defaults ON and CMake FetchContent clones boostorg/math from
github during configure. On the reference device this one-time clone was slow
(several minutes under load=20) but succeeded and is cached in the private
CONAN_HOME. It is not a Conan requirement, so the recipe's dependency list stays
empty.

## Status
`conan create` exit 0 (package 885d6d4f2d1935229411dd8a58da12f5a7eb00eb).
Upstream suite on device: **225/225 Catch2 test cases passed** (2/2 ctest binaries),
source `TEST_CASE` macro count 229. HarmonyOS consumer test: **12/12 passed**.
# Source fetch reliability

The initial CI attempt failed while applying the PR diff because it contained
the 12.9 MB source tarball as a binary patch. The recipe now fetches the pinned
release from the single GitHub codeload URL in `conandata.yml`; Conan verifies
the unchanged SHA-256 during download. The source archive is not committed in
the PR, so worker checkout no longer has to apply a large binary patch.

After switching to the URL fetch, a fresh HarmonyOS `conan create` completed
with exit 0. CTest passed both registered tests; Catch2 reported 203 `all_tests`
and 22 `audio_test` cases (225/225 total). The consumer package passed 12/12.
