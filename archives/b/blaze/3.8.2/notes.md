# Blaze 3.8.2 adaptation notes

## Package model

Blaze is header-only. The recipe copies the upstream `blaze/` directory to
`include/blaze` and exports `Blaze::Blaze` for CMake consumers.

## Upstream validation

`build()` compiles and executes the upstream
`blazetest/src/mathtest/vectors/dynamicvector/ClassTest.cpp` with the compiler
declared by the Conan profile. The test verifies DynamicVector operations and
exits non-zero on failure.

The 3.8.2 tarball can retain a `blaze-3.8.2/` source directory. The recipe
detects that directory before locating headers and upstream test sources.

The upstream test includes private Blazetest headers as
`<blazetest/mathtest/...>`, so its compile command includes both the source root
and `<source-root>/blazetest`.

## OpenHarmony validation

On OHOS aarch64, the upstream DynamicVector ClassTest and the installed-package
consumer CTest both completed successfully on 2026-07-28.
