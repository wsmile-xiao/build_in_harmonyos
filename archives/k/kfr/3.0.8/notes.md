# kfr 3.0.8 - HarmonyOS PC adaptation notes

## Upstream
- Repo: https://github.com/kfrlib/kfr
- Tag: `v3.0.8`
- SHA256: `f61068e8ae401853ca04ac00fe25fff06ef181789fad97c3950c452395c6bc46`
- License: GPL-2.0-only
- Build system: CMake (declares `cmake_minimum_required(VERSION 3.1)`)

## Portability fixes (patches/0001-ohos-aarch64-portability.patch)

### 1. CMake 4.x policy floor (recipe level, DRAFT-E321)
CMake 4.1.2 removes compatibility with `cmake_minimum_required(< 3.5)`.
`tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"` is required
(the variable must exist before the first `cmake_minimum_required()`, so
`tc.variables` - written into `conan_toolchain.cmake` - is too late).

### 2. Duplicate symbols at link time (header patch)
KFR declares explicit specialisations of variable templates in headers:

```
include/kfr/dft/data/sincos.hpp:106    constexpr f64 c_sin_table<f64>[65] = {...};
include/kfr/math/impl/round.hpp:138    constexpr f32 fp_precision_limit<f32> = 16777216.0f;
```

Under C++14 these are not inline, so every translation unit that includes the
header emits a strong definition and `ld.lld` aborts the `all_tests` link:

```
ld.lld: error: duplicate symbol: kfr::data::c_sin_table<double>
ld.lld: error: duplicate symbol: kfr::neon64::intrinsics::fp_precision_limit<float>
```

Fix: build as C++17 (which the OHOS Conan profile already mandates) and add
`inline` to those specialisations. This also removes the ODR violation for
downstream consumers of `libkfr_dft.a`.

### 3. x86-only driver flag
`target_compile_options(kfr INTERFACE -mstackrealign)` is applied to every
non-MSVC/non-IOS build; clang rejects it on aarch64
(`unsupported option '-mstackrealign'`). Gated behind `X86`.

### 4. libstdc++ does not exist on OHOS
`set(STD_LIB stdc++)` makes `kfr` link `-lstdc++`, which is unresolved on
HarmonyOS (libc++ only). libc++ is added by `clang++` automatically.

## CTest
`enable_testing()` lives in `tests/CMakeLists.txt`, so the root build tree has
no `test` target; ctest must be run from `<build>/tests`. That directory
registers a single test, `all_tests`, which is the testo binary containing all
128 `TEST()` cases.

## Status
Build / link / install: PASS.
Upstream suite on device: **126/128 passed, 2 failed (`absmin`, `absmax`)**.
The failing pair are the special-value reduction tests. The suite was left
enabled on purpose - no test was disabled or trimmed.
