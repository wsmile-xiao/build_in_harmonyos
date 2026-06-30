# sleef

SLEEF (SIMD Library for Evaluating Exact Functions) is a library for evaluating mathematical functions (sin, cos, log, exp, etc.) with SIMD (Single Instruction Multiple Data) instructions.

## Description

SLEEF implements elementary functions in double precision and single precision using SIMD instructions. It is designed to achieve high performance while maintaining accuracy and correctness.

## Key Features

- Supports various SIMD instruction sets:
  - x86: AVX, AVX2, AVX512F
  - ARM: Advanced SIMD (NEON), SVE
- Provides both pure C scalar functions and SIMD vectorized functions
- Compatible with libm and libmvec in GNU libc (sleefgnuabi)
- High accuracy (error bound < 1 ULP for most functions)
- Open source (Boost Software License)

## Build System

- CMake based build system
- Requires C compiler with SIMD support
- Optional: OpenMP for parallel execution

## OpenHarmony Compatibility

Successfully compiled for OpenHarmony/HarmonyOS platform with:
- Platform detection patch for CMAKE_SYSTEM_PROCESSOR="unknown"
- Automatic processor detection via `uname -m`
- SVE (Scalable Vector Extension) support enabled for ARM processors

## Versions

- 3.6.1: Built successfully (2026-06-17)