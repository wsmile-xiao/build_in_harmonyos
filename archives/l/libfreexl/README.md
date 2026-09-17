# libfreexl

libfreexl is a C library for extracting valid data from Excel spreadsheets.
Version 2.0.0 supports legacy BIFF `.xls`, XML-based `.xlsx`, and ODS `.ods` formats.

## Versions

- `2.0.0`: HarmonyOS PC arm64 adaptation using Autotools and Conan.

## Configuration

The package builds the static `libfreexl` library, public header `freexl.h`,
and `freexl.pc`. It depends on `expat` and `minizip` Conan packages;
character conversion uses the iconv implementation available from the platform C library.

## Reference

- Upstream: https://www.gaia-gis.it/fossil/freexl/index
- Source: https://www.gaia-gis.it/gaia-sins/freexl-2.0.0.tar.gz
