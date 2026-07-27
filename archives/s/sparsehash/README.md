# sparsehash

Sparsehash 2.0.4 provides memory-efficient C++ `dense_hash_map`,
`dense_hash_set`, `sparse_hash_map`, `sparse_hash_set`, and `sparsetable`
containers. It is a header-only BSD-3-Clause library.

## OpenHarmony package

- Target: OHOS AArch64 with Clang and libc++
- Build system: Conan 2 with a generated CMake harness for upstream tests
- Dependencies: none beyond the C++ standard library
- CMake target: `sparsehash::sparsehash`
- Include trees: `sparsehash/` and legacy-compatible `google/`

The 2.0.4 recipe compiles all seven upstream test programs and a real consumer
test. Cross-build validation proves AArch64 compilation and linkability; target
execution remains a native CI or connected-device requirement.
