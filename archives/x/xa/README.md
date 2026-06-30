# xa (xa65)

xa is a high-speed, two-pass portable cross-assembler for the 8-bit 6502/65C02/65816/65802 microprocessors.

## Description

xa (xa65) is a 6502/65816 assembler that supports:
- 6502, 65C02, and 65816 instruction sets
- Multiple output formats (o65 object files, raw binary)
- Linker (ldo65) and relocator (reloc65) tools
- File information (file65), CBM BASIC listing (printcbm)
- CPK archive unpacker (uncpk)

## Version History

- **2.4.1** (2024-11): Built on OHOS/aarch64 with clang, status: built

## Dependencies

None (standalone C project)

## Build System

Plain Makefile (no configure script)

## Build Configuration

- CC: clang
- LD: clang
- CFLAGS: -fPIC -O2 -g
- LDFLAGS: -lc
- DESTDIR/PREFIX override for staging installation
