# Opus

Opus is a low-latency, royalty-free audio codec for speech and music.

## Versions

### 1.4

- Build system: Meson
- Libraries: `libopus.so` when shared, `libopus.a` when static
- Public headers: `opus.h`, `opus_defines.h`, `opus_types.h`,
  `opus_multistream.h`, and `opus_projection.h`
- Conan CMake target: `Opus::opus`
- pkg-config module: `opus`

The shared package uses one unversioned `libopus.so` on OpenHarmony PC.

### 1.5.2

- Build system: CMake
- Pure audio codec library with no external Conan dependencies
- Enables `OPUS_BUILD_SHARED_LIBRARY` for the shared variant

## Reference

- https://opus-codec.org/
