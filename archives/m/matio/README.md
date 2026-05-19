# matio

MATIO is a C library for reading and writing MATLAB MAT files.

## Description

MATIO provides a C interface for reading and writing MATLAB MAT files. It supports MAT file versions 4, 5, and optionally 7.3 (with HDF5).

## Homepage

https://sourceforge.net/projects/matio/

## License

BSD-2-Clause

## Versions

| Version | Status | Build Date |
|---------|--------|------------|
| 1.5.23  | built  | 2026-05-19 |

## Build Notes

- Uses CMake build system on HarmonyOS (autotools has temporary directory permission issues)
- Disabled MAT73 and HDF5 support for simpler compilation
- Static library build to avoid LLVM linker symbol file format issues
- Requires config.guess modification for HarmonyOS detection

## Dependencies

None (standalone library, optionally zlib for compression)

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- matio 1.5.23
```