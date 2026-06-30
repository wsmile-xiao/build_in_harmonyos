# SVT-AV1

SVT-AV1 (Scalable Video Technology for AV1) is a high-performance AV1 video encoder developed by Intel and AOMediaCodec.

## Description

SVT-AV1 is an AV1-compliant software encoder library targeting production-level media encoding workloads.

## Platform Support

SVT-AV1 can be compiled on OpenHarmony/HarmonyOS ARM64 platform with:
- cmake >= 3.5
- NASM assembler >= 2.14
- clang compiler

## Build System

CMake

## Key Features

- High-performance AV1 video encoding
- Scalable multi-threaded design
- NEON optimization for ARM64 (auto-enabled)
- Advanced SIMD: NEON_DOTPROD, NEON_I8MM
- Shared library with frontend executable
- Preset-based encoding speed control

## Compiled Versions

- **v4.1.0**: Built successfully on OpenHarmony ARM64 (2026-05-27)
  - Compiler: Clang
  - Optimizations: NEON, NEON_DOTPROD, NEON_I8MM
  - Test: Version check passed

## Installation

- Binary: `/usr/local/bin/SvtAv1EncApp`
- Library: `/usr/local/lib/libSvtAv1Enc.so`
- Headers: `/usr/local/include/svt-av1/*.h`

## Usage

```bash
SvtAv1EncApp -i input.y4m -b output.ivf -enc-mode 8
```

## References

- GitLab: https://gitlab.com/AOMediaCodec/SVT-AV1