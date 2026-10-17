# SPIRV-Cross 1.4.341.0 adaptation notes

## Result

- Target: OHOS 6.0, armv8, clang 15 profile
- Date: 2026-07-16
- Status: `built`
- Source changes: none

## Implementation

The recipe builds all static SPIRV-Cross backends, the C API, and the
`spirv-cross` command-line tool. Optional upstream tests are disabled because
they require external shader toolchain dependencies; consumer-level functional
tests are supplied instead.

The OHOS SDK uses the `std::__n1` libc++ ABI namespace. Selecting its dedicated
`libcxx-ohos` headers is required so compiled objects match the SDK libraries.

## Validation

`conan create` completed successfully. The test constructs a valid minimal
compute SPIR-V module, parses it through `spirv_cross_c.h`, generates GLSL, then
writes the module and converts it again with the installed CLI. Both outputs
contain a generated `void main` function.
