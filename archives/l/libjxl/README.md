# libjxl

JPEG XL image format reference implementation.

## Description

JPEG XL is a modern image format that provides:
- 60% size reduction at equivalent subjective quality compared to JPEG
- Fast, parallelizable decoding and encoding
- Progressive decoding, lossless compression, and animation support
- Reversible transcoding of existing JPEG with 22% size reduction
- Support for high-quality applications including wide gamut, higher resolution/bit depth/dynamic range

## Homepage

https://github.com/libjxl/libjxl

## Build System

CMake

## Dependencies

- **Required**: cmake, pkg-config, brotli
- **Optional**: libgif, libjpeg, libopenexr, libpng, libwebp

## Tools Provided

- `cjxl`: JPEG XL encoder
- `djxl`: JPEG XL decoder
- `jxlinfo`: JPEG XL file info tool