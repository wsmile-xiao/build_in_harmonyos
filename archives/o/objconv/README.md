# objconv

**Object file converter for x86 and x86-64 platforms**

## Overview
objconv is a versatile object file converter that supports conversion between multiple object file formats used on different platforms. It can convert between:

- **COFF/PE** (Windows)
- **OMF** (Windows, Borland)
- **ELF** (Linux, BSD, Unix)
- **Mach-O** (Mac OS X)

## Features
- Format conversion between major object file formats
- Disassembly support (MASM, NASM, YASM, GAS syntax)
- Symbol table manipulation
- Section header analysis
- Relocation table handling

## Usage
```bash
objconv -f<format> inputfile [outputfile]
```

### Common Options
- `-fXXX`: Output format (PE, COFF, ELF, OMF, MACHO)
- `-fasm`: Disassemble file
- `-dXXX`: Dump file contents (f: headers, h: sections, s: symbols, r: relocations)
- `-nu`: Change symbol name underscores

## Build Method
objconv uses a simple build process without configure/make:
```bash
unzip source.zip
clang++ -o objconv -O2 *.cpp
```

## Version History
- **2.57** (2026-05-14): Fixed problem with comdat records in omf2asm.cpp

## Author
Agner Fog

## License
GNU General Public License v. 3

## Homepage
https://agner.org/optimize/#objconv

## OpenHarmony Compatibility
objconv 2.57 has been successfully compiled and tested on OpenHarmony HongMeng Kernel 1.12.0 (aarch64).

### Build Notes
- No platform-specific patches required
- Simple compilation with clang++
- Binary size: ~815K

### Availability
Precompiled package: `objconv-2.57-ohos-aarch64.tar.gz`