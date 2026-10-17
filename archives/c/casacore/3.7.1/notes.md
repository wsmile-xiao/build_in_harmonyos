# Casacore 3.7.1 — Adaptation Notes

## Overview

Casacore is a C++ library for radio astronomy data processing. It provides
core functionality for astronomical data I/O (FITS, Measurement Sets),
coordinate transformations, and image processing.

## Build System

- **Build system**: CMake (minimum 3.14)
- **C++ standard**: C++17
- **Source**: https://github.com/casacore/casacore/archive/refs/tags/v3.7.1.tar.gz

## Dependencies

| Dependency | Version | Required | Notes |
|------------|---------|----------|-------|
| cfitsio | 4.6.4 | Yes (for fits/images/msfits modules) | Conan registry |
| wcslib | 8.4 | Yes (for images module) | Conan registry |
| fftw | 3.3.10 | Yes (for scimath module) | Conan registry |
| openblas | 0.3.28 | Yes (BLAS/LAPACK for scimath) | Conan registry |
| hdf5 | 1.14.6 | Optional (USE_HDF5=ON) | Conan registry |
| readline | 8.3 | Optional (USE_READLINE=ON) | Conan registry |
| flex | 2.6.4 | Yes (tool_requires, for tables) | Conan registry |
| bison | 2.7 | Yes (tool_requires, for tables) | Conan registry |

## Patches

### 0001-disable-fortran-on-ohos.patch

**Problem**: Casacore's CMakeLists.txt includes `scimath_f` (Fortran module) when
MODULE=all, which requires `enable_language(Fortran)`. No Fortran compiler is
available on OHOS/CI.

**Fix**: Remove `scimath_f` from the module list and keep `_usefortran=NO`.
The C++ `scimath` module remains functional without its Fortran counterpart.

**Impact**: The `casa_scimath_f` library target is not built. All other modules
work normally.

### 0002-undef-open64-to-avoid-musl-macro-conflict.patch

**Problem**: OHOS (musl) `fcntl.h` defines `#define open64 open` when
`_LARGEFILE64_SOURCE || _GNU_SOURCE` is defined — and OHOS clang predefines
`_GNU_SOURCE`. Casacore's `DataManager::open64` virtual method (and its
overrides in ISMBase/MSMBase/SSMBase/StManAipsIO/TiledStMan/VirtColEng/
AlternateMans engines) get macro-expanded to `open` inconsistently per-TU
(depending on where `fcntl.h` enters the include order), producing vtable
undefined-symbol link errors (`VirtualColumnEngine::open(u64, AipsIO&)`)
and out-of-line definition mismatches.

**Fix**: Insert `#undef open64` immediately before every open64 member
declaration (headers), definition (.cc files), and the one call site
(`tables/Tables/ColumnSet.cc`). The name then stays uniform in every TU.
Shipped headers keep the `#undef`, so downstream consumers are ABI-safe too.

### 0003-link-lapack-into-scimath-when-fortran-disabled.patch

**Problem**: Upstream links `${LAPACK_LIBRARIES} ${BLAS_LIBRARIES}` only into
`casa_scimath_f` (the Fortran wrapper). With Fortran disabled, `casa_scimath`'s
own Mathematics code (via `MatrixMathLA.h`, which `#define dgetrf dgetrf_` in
f2c style) calls LAPACK directly, leaving `dgetrf_`/`dgetri_` undefined when
linking executables (imagecalc, taql, ...).

**Fix**: Link `${LAPACK_LIBRARIES} ${BLAS_LIBRARIES}` directly into
`casa_scimath` and drop the `casa_scimath_f` reference (also replaces the
former build()-time replace_in_file for this file).

## Build Options (OHOS-specific)

- BUILD_PYTHON3=OFF: No Python on OHOS
- BUILD_PYTHON=OFF: No Python2
- USE_ADIOS2=OFF: ADIOS2 not available
- USE_OPENMP=OFF: Not available on OHOS
- USE_MPI=OFF: Not needed
- USE_STACKTRACE=OFF: `<execinfo.h>` may not be available
- USE_PCH=OFF: Avoid precompiled header issues
- BUILD_DYSCO=OFF: Requires C++20 and libdeflate >= 1.19 (3.7.1 may not have this option)
- ENABLE_RPATH=OFF: Conan manages RPATH
- MODULE=all: Build all C++ modules

## Platform Notes

- `__linux__` is defined on OHOS, so `AIPS_LINUX` is set correctly
- `<linux/nfs_fs.h>` is available on OHOS
- `/proc` filesystem access works for HostInfo
- Pthreads, mmap, fcntl all work on OHOS
- dlmalloc is not used (AIPS_LINUX defined → system malloc)

## Library Targets

The package produces 13 library targets:
casa_casa, casa_mirlib, casa_tables, casa_scimath, casa_measures, casa_meas,
casa_fits, casa_ms, casa_msfits, casa_derivedmscal, casa_lattices,
casa_coordinates, casa_images

(casa_scimath_f is not built due to Fortran patch)

## Build Fixes (2026-09-18 re-verification)

The first submission (2026-09-04) failed local `conan create` with three
OHOS-specific issues; all were root-caused and fixed on 2026-09-18:

1. **`No rule to make target 'm'`** — casacore's FindCFITSIO/FindWCSLIB and
   `casa/CMakeLists.txt` call `find_library(m)`; CMake cannot see the OHOS SDK
   sysroot, and passing bare names (`M_LIBRARY=m`) via cache variables makes
   CMake record them as build-dir-relative FILEPATHs. Fix: resolve the sysroot
   libdir with `clang -print-file-name=libm.a` (see `_sysroot_libdir()` in
   conanfile.py) and expose it via `CMAKE_LIBRARY_PATH`/`CMAKE_INCLUDE_PATH`,
   so `find_library(m/pthread)` finds the real `libm.a`/`libpthread.a`.

2. **open64 macro conflict** — see patch 0002 above; additionally
   `AIPS_NOLARGEFILE` is defined globally (via `tc.preprocessor_definitions`)
   so casacore stops defining `_LARGEFILE64_SOURCE` and stops using the
   fopen64/lseek64 aliases. musl off_t is always 64-bit, no functionality lost.

3. **LAPACK undefined symbols** — see patch 0003 above.

After the fixes, a full local `conan create` (2026-09-18) built all 13 static
libraries, 20 executables, and the test_package (`test_casacore`, 4/4 checks)
passed on-device.

---

**编译结束**: 2026-09-18 08:46
**最终状态**: built (conan create PASS, test_package 4/4)
