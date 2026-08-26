# Parson 1.5.3 HarmonyOS PC adaptation

## Upstream

- Repository: https://github.com/kgabis/parson
- Version: 1.5.3
- Commit: `ba29f4eda9ea7703a9f6a9cf2b0532a2605723c3`
- License: MIT
- Source: `parson.c` and `parson.h`
- Third-party dependencies: none

Upstream does not publish releases or tags. The recipe pins the commit whose source,
CMake, Meson and package metadata all identify version 1.5.3.

## Build

The recipe compiles `parson.c` directly with the HarmonyOS Clang toolchain and creates
`libparson.a`. The package contains the static library, public header and license.
Only libc and libm are used.

## Compatibility adjustment

No source patch is required. The upstream C89 test command uses `-pedantic-errors`.
HarmonyOS SDK `math.h` implements `isnan` and `isinf` with `ULL` constants, which Clang
reports as a C89 extension. The two strict C targets therefore add `-Wno-long-long`;
the library source remains unchanged.

## Upstream tests

All upstream targets are retained and executed on HarmonyOS after ELF signing:

1. `test`: strict C89 suite
2. `testcpp`: C++ compatibility suite
3. `test_hash_collisions`: strict C89 suite with `PARSON_FORCE_HASH_COLLISIONS`

Each target reports 349 passed assertions and zero failures, for 1047 upstream
assertions in total. Each run also checks 536 injected allocation-failure positions.
These injection positions are internal iterations, not separately counted test cases.

## Consumer test

One consumer executable links the packaged `libparson.a` through `parson::parson` and
verifies parsing, typed access, dot notation, mutation, compact serialization, schema
validation, deep copy equality and invalid JSON rejection. It is counted as one
consumer test boundary rather than inflating each assertion into a separate case.
