# MozJPEG 4.1.1

MozJPEG is adapted as a static-first CMake library for OHOS/armv8.

- The recipe uses the official `v4.1.1` source archive and its verified SHA256.
- `WITH_SIMD=OFF` avoids the unavailable NASM tool while retaining all codec
  functionality.
- PNG input support is enabled through `libpng/1.6.58`, with `zlib/1.3.1.1`.
- The upstream CTest suite runs during `build()`; device validation passed all
  108 of 108 cases.
- The consumer test encodes and decodes a one-pixel JPEG in memory, asserting
  JPEG framing, dimensions, and successful scanline decoding.

**编译结束**: 2026-07-30

**最终状态**: built
