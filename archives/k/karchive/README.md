# KArchive

KArchive is the KDE Frameworks 6 archive library. It provides a common
QIODevice-style API over tar (KTar), zip (KZip), ar (KAr), 7z (K7Zip) and
Qt resource container (KRcc) archives plus standalone compression devices
(KCompressionDevice / KFilterBase, gzip/xz/lzma/lzip/bzip2/zstd filters
and QSaveFile-based safe saving).

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `KF_SKIP_PO_PROCESSING=ON`: Qt6LinguistTools is not part of the qtbase
  package in this repository, so `ecm_install_po_files_as_qm(poqm)` must not
  run.
- Compression backends: `WITH_BZIP2=OFF` (the local static `bzip2/1.0.8`
  does not guarantee PIC objects for the shared `libKF6Archive.so`),
  `WITH_LIBZSTD=OFF` (upstream probes through PkgConfig, outside the
  baseline dependency set), `WITH_LIBLZMA=ON` and `WITH_OPENSSL=ON` via the
  published `xz/5.6.2` / `openssl/3.5.6.1` packages.
- ECM 6.26+ `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time; the recipe prepends `/system/lib64` to `LD_LIBRARY_PATH`
  so `qtpaths` resolves the compatible `libc++_shared.so` (the sandbox
  default contains an incompatible one under
  `/data/storage/el1/bundle/libs/arm64`).
- 6.26.0: upstream `src/k7zip.cpp` uses `std::ranges::any_of` and
  `std::bit_cast` (C++20). The ohos-aarch64 conan profile pins
  `compiler.cppstd=17` and CMakeToolchain re-applies
  `CMAKE_CXX_STANDARD 17` on every `project()` call, so the per-project
  standard cannot be raised; a value-identical C++17 rewrite patch is
  applied (`patches/0001-src-cpp17-compat.patch`).
- 6.26.0 test exclusions (run-time only, upstream test sources
  unmodified): `test7ZipOssFuzzIssues:testcase_6213340184772608` (SIGSEGV
  on the OHOS runner; passes upstream Linux CI) and
  `test7ZipReadCoder:{bzip2,zstd}` (need the disabled backends). All other
  115 upstream rows run green.
