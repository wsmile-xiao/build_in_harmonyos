# rgbds for OpenHarmony

`rgbds` (Rednex Game Boy Development System) is a free assembly toolchain for
the Nintendo Game Boy and Game Boy Color, providing four command-line tools:
`rgbasm` (assembler), `rgblink` (linker), `rgbfix` (ROM header fixer), and
`rgbgfx` (PNG ↔ Game Boy graphics converter).

## Package details

- Upstream: https://github.com/gbdev/rgbds
- Build system: GNU Makefile (C++20)
- Target: OpenHarmony/HarmonyOS aarch64
- Runtime dependencies: libpng (rgbgfx only)
- Build dependencies: bison (generates the parser sources)

## Versions

| Version | Status |
| --- | --- |
| 1.0.1 | built |
