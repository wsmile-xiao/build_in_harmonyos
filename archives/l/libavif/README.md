# libavif

AV1 Image File Format (AVIF) library.

## Description

libavif is a library for encoding and decoding AVIF image files. It supports the AV1 codec for high-quality image compression.

## Dependencies

- aom (3.9.1+) - AV1 codec for encoding and decoding

## Compilation

Build system: CMake

Key configuration options:
- `-DAVIF_CODEC_AOM=SYSTEM` - Use system-installed aom codec
- `-DAVIF_LIBYUV=OFF` - Disable libyuv (optional)

## Version Status

| Version | Status | Date |
|---------|--------|------|
| 1.4.1 | built | 2026-05-27 |

## Notes

- Requires aom codec for AVIF encoding/decoding
- libyuv is optional and can be disabled if not available