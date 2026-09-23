# CCfits

CCfits is the official NASA HEASARC object-oriented C++ interface to the
cfitsio library for reading and writing FITS (Flexible Image Transport
System) data files.

## Compilation

- Version: 2.7
- License: CFITSIO (NASA/GSFC unpublished-work license, see `License.txt`
  installed under `licenses/`)
- Dependencies: cfitsio/4.6.4 (transitive: zlib)
- Build System: CMake (upstream also ships autotools; CMake is used here for
  consistency with cfitsio on this platform)

## OpenHarmony Adaptation

- Platform: OpenHarmony / HarmonyOS PC, aarch64 (os=OHOS profile)
- Compiler: Clang 15.0.4 (libc++, C++17 toolchain, upstream requires C++11)
- Dependency resolution: upstream probes cfitsio exclusively through
  pkg-config (`PKG_CHECK_MODULES`); the recipe regenerates dependency `.pc`
  files with Conan `PkgConfigDeps` and injects `PKG_CONFIG_PATH` in the
  build environment, because the cfitsio package's own `cfitsio.pc` carries
  a stale packaging-time absolute prefix (see notes.md and knowledge draft
  DRAFT-ccfits-2.7-stale-pc-prefix-regen)
- No patches required (CMake build succeeds without source modifications)

## Status

- Built: 2.7 (this archive)
- Build Date: 2026-09-05
- Artifacts: `lib/libCCfits.a` (default static; `shared` option produces
  `lib/libCCfits.so`, no SONAME) and `include/CCfits/` public headers

## Testing

- Upstream test: the `cookbook` example program (the only upstream CTest
  entry, `-DTESTS=ON`), run on device against `file1.pha` — exit 0, writes
  and reopens atestfil/btestfil/ctestfil FITS files
- Consumer test: `test_package/test_ccfits.cpp` — real API write/reopen/read
  round-trip, 7 assertions, all passing (see `reports/conan-create.log`)
