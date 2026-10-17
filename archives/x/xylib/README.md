# xylib - x-y data reading library

## Description

xylib is a portable C++11 library (with C bindings) for reading files that
contain x-y data from powder diffraction, spectroscopy and other experimental
methods. It ships the `libxy` library and the `xyconv` command-line converter.

Supported formats include plain text/CSV, pdCIF, Siemens/Bruker UXD/RAW,
Philips UDF/RD, PANalytical XRDML, Rigaku DAT, Canberra MCA/CNF, Vamas,
WinSpec SPE, Bruker SPC, XSYG and many more.

## Version

- Latest compiled version: 1.6

## Build Information

- Build system: Autotools
- Compiler: Clang 15
- Platform: OpenHarmony (aarch64)

## Dependencies

- boost (header-only)
- zlib
- bzip2

## Usage

```bash
xyconv input.raw output.txt
```

## License

GNU Lesser General Public License v2.1 or later
