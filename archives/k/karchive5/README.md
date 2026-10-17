# karchive5

KDE Frameworks 5 archive library — the `libKF5Archive.so` shared library
providing the `KArchive` / `KZip` / `KTar` / `KAr` / `KRcc` archive classes,
the `KArchiveDirectory` / `KArchiveFile` entry model, and the
`KCompressionDevice` / `KFilterBase` transparent compression filters
(gzip, bzip2, xz/LZMA and zstd).

This is the **KF5 (Qt5) line**, tracking the 5.116.0 release under the
`karchive5` package name, distinct from the KF6 `karchive` archives
(6.x, Qt6).

## Versions

- 5.116.0 — KF5 line, depends on qt5-qtbase/5.15.2.2.

## OHOS adaptation

- `QT_MAJOR_VERSION=5` keeps the project on the Qt5 code paths;
  `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (HarmonyOS is not in the upstream list).
- `KF_SKIP_PO_PROCESSING=ON`: the published qt5-qtbase ships no
  LinguistTools, so `ecm_install_po_files_as_qm(poqm)` must not run.
- SONAME emission: HarmonyOS is not mapped to the Linux CMake platform, so
  `CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG` is undefined and the produced
  `.so` would lack `DT_SONAME` (W3 CI L5 gate). The recipe sets the soname
  flag plus `CMAKE_PLATFORM_NO_VERSIONED_SONAME`.
- All four compression backends are enabled (no functionality is compiled
  out): zlib (upstream `TYPE REQUIRED`), bzip2 (`TYPE RECOMMENDED`), xz via
  LibLZMA, and zstd via `pkg_config`. `config-compression.h` ends up with
  `HAVE_BZIP2_SUPPORT=1`, `HAVE_XZ_SUPPORT=1`, `HAVE_ZSTD_SUPPORT=1`.
- `zlib/1.3.1.1` is pulled in with `force=True`: qt5-qtbase pins
  `zlib/1.3.1`, whose published `libz.a` is a **non-PIC** static archive and
  cannot be linked into the shared `libKF5Archive.so` on AArch64
  (`relocation R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC`).
  `1.3.1.1` is the same upstream version rebuilt with `-fPIC`
  (as recorded by E541 / E533).
- The compression backends are resolved by CMake's own `FindZLIB` /
  `FindBZip2` / `FindLibLZMA` modules. Because `conan_toolchain.cmake`
  force-sets `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`, a generated
  `CMAKE_PROJECT_INCLUDE` file flips it back to `OFF` so the Find modules
  (which define the canonical `ZLIB::ZLIB` / `BZip2::BZip2` /
  `LibLZMA::LibLZMA` targets and the uppercase `*_FOUND` variables upstream
  reads) win over the CMakeDeps configs.
- The published `zstd/1.5.7` ships a non-relocatable `libzstd.pc`
  (`prefix=/usr/local`). The recipe defines the `PkgConfig::LibZstd` imported
  target and `LibZstd_FOUND` against the Conan package before the project's
  probe runs.
- ECM 6.26 is a `tool_requires`; `ecm/6.26.0` satisfies
  `find_package(ECM 5.116.0)` (minimum-version semantics, same as the
  sibling ki18n5 / kimageformats5 recipes).

## Upstream tests

`BUILD_TESTING=ON` builds and runs the upstream autotest suite:

| # | CTest case | Result |
|---|-----------|--------|
| 1 | `karchivetest` | Passed |
| 2 | `kfiltertest` | Passed |
| 3 | `deprecatedtest` | Passed |
| 4 | `klimitediodevicetest` | Passed |
| 5 | `kcompressiondevicetest` | Passed |

5/5 passed, 0 failed, 0 skipped.

The upstream `tests/` directory (`kartest`, `ktartest`, `krcctest`,
`kziptest`, `k7ziptest`) contains **standalone helper executables**: its
`CMakeLists.txt` only calls `ecm_mark_as_test()` and registers no
`add_test()`, so upstream itself does not run them under CTest. They were
executed manually against real archives on the target and all exit 0.

A test-only shared-mime-info database is generated under the build folder and
exposed through `XDG_DATA_DIRS` for the test run. `KTar` selects its
compression filter via `QMimeDatabase`; the OHOS system MIME database knows
`application/x-compressed-tar`, `application/x-bzip-compressed-tar` and
`application/x-xz-compressed-tar` but has **no zstd entry**, so `.tar.zst`
would resolve to `application/octet-stream` and `KTar` would silently write
an uncompressed tar. The generated database adds the compressed-tar types
(zstd included) without touching the packaged library.
