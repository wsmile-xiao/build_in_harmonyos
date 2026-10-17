# kpackage 6.26.0 notes

## Scope

First adaptation of the upstream kpackage 6.26.0 release (KDE Frameworks
6.26) for HarmonyOS PC. Recipe and OHOS patches carried forward from the
proven 6.18.0.2 baseline (PR lineage #6997 -> 6.18.0.1 -> 6.18.0.2).

- Upstream source: kpackage 6.26.0
  (`https://download.kde.org/stable/frameworks/6.26/kpackage-6.26.0.tar.xz`,
  SHA-256 `313cda4a335ecdb67bb8e2fcc15bdeb5970db17d5597282ca655bf97a98abab5`).

## Dependency resolution (W0 findings)

Upstream `CMakeLists.txt` sets `KF_DEP_VERSION "6.26.0"`, i.e.
`find_package(KF6Archive 6.26.0 REQUIRED)`. The ohpcd registry caps at:

- karchive: 6.19.0 (max) -> no 6.26.x published, no in-flight PR (checked
  all 600+ open PRs on 2026-09-05)
- kcoreaddons: 6.26.0 (published)
- ki18n: 6.26.0 (published)
- ecm: 6.26.0 (published, tool_requires)

Resolution: `0001-lower-ecm-and-kf-dep-version.patch` lowers
`KF_DEP_VERSION` to `6.19.0` (knewstuff 6.29.0 precedent,
`archives/k/knewstuff/6.29.0/patches/0001-lower-ecm-and-kf-dep-version.patch`).
kcoreaddons/ki18n are consumed at 6.26.0 (>= the 6.19.0 floor, CMake
version-compatible). This is a recipe-layer decision, not an upstream fork:
no KF6 API gap exists between 6.19 and 6.26 for the surfaces kpackage uses
(verified by the 8/8 upstream CTest pass).

## Adaptations carried forward (recipe layer)

- `KF_IGNORE_PLATFORM_CHECK=TRUE`, `KF_SKIP_PO_PROCESSING=ON`,
  `USE_DBUS=OFF`, `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON`,
  `BUILD_TESTING=ON`, serial make (OHOS HMDFS mkfifo EPERM).
- OHOS patches 0002/0003/0004/0005 regenerated or verified against 6.26.0:
  - 0002 plugin path / XDG data locations: regenerated (upstream
    packageloader.cpp drifted: private include removed, `for (auto &wp)`
    loop form; hunk line numbers moved) - rebased onto 6.26.0 and verified
    with the same patch_ng (strip=0, fuzz=False) engine conan uses.
  - 0003 archive root unsupported fallback: packagejobthread.cpp is
    byte-identical between 6.18.0 and 6.26.0, patch carried unchanged.
  - 0004 targz gzip mime: same file, carried unchanged.
  - 0005 relocatable soname link: CMakeLists hunk context unchanged
    (`${KF_DEP_VERSION}` indirection), carried unchanged.
- CMake path layer fix (conan_cmakedeps_paths.cmake): zlib/openssl/zstd
  roots prepended for karchive/6.19.0's transitive find_dependency calls;
  `-L<zlib/zstd libdir> -lz -lzstd` in linker flags for the static
  libKF6Archive.a transitive link.

## New in 6.26.0 vs 6.18.0 baseline

- `cmake_minimum_required(VERSION 3.29)` (local cmake 4.1.2 satisfies).
- ECM 6.26 `KDEInstallDirs6` runs the qtbase qtpaths host tool during
  configure (`ecm_query_qt -> QT_INSTALL_PREFIX`). The qtpaths binary needs
  the compatible libc++_shared.so; the sandbox LD_LIBRARY_PATH contains an
  incompatible one under /data/storage/el1/bundle/libs/arm64 that shadows it.
  Fix: prepend `/system/lib64` (+ SDK llvm lib) in `_cmake_build_env()` and
  `_library_runtime_env()` (kconfig 6.26.0 / bluez-qt 6.28.0 precedent).
  The same injection was needed in test_package (KF6PackageMacros.cmake
  pulls in KDEInstallDirs at consumer configure time).
- Upstream code changes 6.18 -> 6.26 are small (packageloader.cpp include
  cleanup, package.cpp/packagejob.cpp minor updates, kpackagetool updates);
  all 8 upstream CTest tests pass unmodified (plasmoidpackagetest excluded
  per the R01 baseline hang).

## Verification

- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default
  --build=missing` -> rc=0, clean cache (fresh export, no binary reuse).
- Upstream CTest (autotests, `ctest -E "^plasmoidpackagetest$"`): 8/8 Passed
  (fallbackpackagetest 0.07, packagestructuretest 0.07, querytest 0.49,
  5x appstream 0.07-0.11) -> "100% tests passed, 0 tests failed out of 8".
- test_package: 2/2 Passed (test_kpackage 0.05 + test_ohos_adaptation 0.15).
- test_ohos_adaptation: PackageLoader + Package + PackageJob::install (KArchive
  extraction fallback) + KPluginMetaData all PASS on OHOS.
- RELOCATABILITY OK: libKF6Package.so has no .conan2/.cache machine-private
  path in DT_NEEDED/RPATH/RUNPATH.
- Log: `$HOME/tmp/kpackage-626-create-clean.log`
---

**编译结束**: 2026-09-05 21:45
**最终状态**: built
