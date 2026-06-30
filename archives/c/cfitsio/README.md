# CFITSIO

CFITSIO is a library of C and Fortran subroutines for reading and writing data files in FITS (Flexible Image Transport System) data format.

## Compilation

- Version: 4.6.4
- License: CFITSIO License (ISC-like)
- Dependencies: zlib (optional: curl)
- Build System: CMake / Autotools

## OpenHarmony Adaptation

- Platform: aarch64-unknown-linux-ohos
- Compiler: Clang 15.0.4
- Build Mode: CMake (due to autotools permission issues)
- No patches required (CMake build successful without modifications)

## Status

- Published: 4.6.4
- Build Date: 2026-05-21
- Package: cfitsio-4.6.4-ohos-aarch64.tar.gz (10MB)

## Tools

All 8 utility programs built successfully:
- cookbook: FITS file cookbook examples
- fitscopy: Copy FITS files
- fitsverify: Verify FITS format compliance
- fpack: Compress FITS files
- funpack: Uncompress FITS files
- imcopy: Copy FITS images
- smem: Shared memory test
- speed: Performance benchmark

## Notes

- Dynamic library loading: Requires LD_LIBRARY_PATH to include ~/usr/local/lib
- No RPATH set in executables (CMake default behavior)
- Build warnings: sys/fcntl.h redirect warnings (non-critical)
