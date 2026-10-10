# med 5.0.0 — HarmonyOS PC (aarch64, OHOS) adaptation notes

## What is it
MED-fichier 5.0.0 (Salome mesh/data-exchange format library), CMake-based,
backed by HDF5. Upstream: https://www.salome-platform.org/

## Build choices (OHOS)
- **Build system**: CMake (not autotools).
- **Library produced**: `libmedC` only — the C/C++ API library that consumers
  link against. The Fortran-facing `libmed` / `libmedfwrap` wrappers require a
  Fortran toolchain that is **not** part of the OHOS NDK, so they are skipped
  (MED's `PROJECT(MEDFile C CXX)` makes Fortran optional; without a Fortran
  compiler it prints "No Fortran support" and continues).
- **Options**: `MEDFILE_BUILD_SHARED_LIBS=ON` (or OFF for static),
  `MEDFILE_BUILD_PYTHON=OFF`, `MEDFILE_BUILD_TESTS=OFF`, docs OFF.
- **HDF5**: `hdf5/1.14.6`. MED's finder is pointed at the Conan hdf5 package
  via `-DHDF5_ROOT_DIR=<hdf5 package folder>`.

## Patches
- `patches/0001-relax-hdf5-version-gate-for-1.14.patch`: MED_FIND_HDF5 in
  `config/cmake_files/medMacros.cmake` hard-requires HDF5 MINOR==12; relaxed to
  also accept MINOR==14 (repo only ships hdf5 1.14.x).

## Source download
The Salome file host (`files.salome-platform.org`) returns HTTP 403 to
non-browser User-Agents. `source()` passes a browser UA so the tarball
downloads; CI uses its own mirror fallback for the same URL.

## Upstream tests
MED's own test suite (`tests/`) links the Fortran `libmed` API, which is not
built on OHOS, so `MEDFILE_BUILD_TESTS` is OFF. An equivalent end-to-end
consumer test is shipped in `test_package/` (create a MED file, write a
comment, close, re-open read-only, close) exercising the HDF5 backend through
the C API.

## Status
status: built (verify passed locally; not yet uploaded).
---

**编译结束**: 2026-09-29 23:20
**最终状态**: built
