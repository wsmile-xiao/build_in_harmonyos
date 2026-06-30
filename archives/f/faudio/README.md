# FAudio

FAudio is an XAudio2 reimplementation that focuses solely on the developing FNA
games. It is a cross-platform audio library providing the XAudio2 API on
non-Windows platforms.

- **Homepage**: https://fna-xna.github.io/
- **Source**: https://github.com/FNA-XNA/FAudio
- **Build system**: CMake
- **License**: zlib license

## Compiled versions

| Version | Status | Date |
|---------|--------|------|
| 26.05 | built | 2026-05-26 |

## Notes

- FAudio depends on SDL2 for platform abstraction
- The library provides XAudio2-compatible API (XACT3, F3DAudio, etc.)
- No executables are produced - FAudio is a shared library only