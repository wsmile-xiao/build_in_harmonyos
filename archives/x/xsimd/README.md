# xsimd

C++ wrappers for SIMD intrinsics

## Description

SIMD (Single Instruction, Multiple Data) is a feature of microprocessors that has been available for many years. SIMD instructions perform a single operation on a batch of values at once, and thus provide a way to significantly accelerate code execution.

`xsimd` provides a unified means for using these features for library authors. Namely, it enables manipulation of batches of numbers with the same arithmetic operators as for single values. It also provides accelerated implementation of common mathematical functions operating on batches.

## Adoption

Beyond Xtensor, Xsimd has been adopted by major open-source projects, such as Mozilla Firefox, Apache Arrow, Pythran, and Krita.

## Supported Architectures

- x86: SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2, FMA3+SSE, FMA3+AVX, FMA3+AVX2, AVX512BW, AVX512CD, AVX512DQ, AVX512F
- x86 AMD: FMA4
- ARM: NEON, NEON64, SVE128/256/512
- WebAssembly: WASM
- RISC-V: RISC-V128/256/512

## Compilation Notes

xsimd is a header-only library. No special compilation flags are required for OpenHarmony. The library compiles cleanly with Clang 15.0.4.

## Dependencies

Optional dependency on xtl (for xtl::xcomplex support).

## Homepage

https://github.com/xtensor-stack/xsimd

## License

BSD-3-Clause