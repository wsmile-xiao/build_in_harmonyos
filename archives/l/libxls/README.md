# libxls

libxls is a C library for reading legacy binary Excel `.xls` files.

## Versions

- `1.6.3`: HarmonyOS PC arm64 adaptation using Autotools and Conan.

## Configuration

The package builds the static `libxlsreader` library and the `xls2csv` command-line tool. It has no external Conan dependencies; character conversion uses the iconv implementation available from the platform C library.
