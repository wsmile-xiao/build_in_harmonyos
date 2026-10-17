# kpackage 6.18.0.2 notes

## Scope

kpackage/6.18.0.2 is the version-suffixed release (R37) of the verified
recipe-layer repair for consuming `karchive/6.19.0`. Version 6.18.0.1's
corrected recipe revision could not be published because the registry rejects
multiple recipe revisions under the same version (HTTP 409); 6.18.0.2 is the
user-selected governed non-destructive publication path. The old 6.18.0.1
artifact is untouched.

## Historical provenance

- Upstream source: kpackage 6.18.0
  (`https://download.kde.org/stable/frameworks/6.18/kpackage-6.18.0.tar.xz`,
  SHA-256 `1bc2e43bf2239dc20e836b70877631e103057fb14a9467290c76fa45ff02870e`).
- 6.18.0.1 carried the original OHOS adaptation (R01/R07, merged via PR #6997)
  plus the R09/R10 recipe-layer repair (R8-compliant) that could not be
  published under the same version.
- 6.18.0.2 carries forward only the already reviewed and R8-compliant
  recipe-layer repair (no platform conditional macros, no upstream patch
  changes, no `#ifdef __OHOS__` in knowledge/patches).

## Adaptations carried forward (recipe layer, R8 compliant)

- `KF_IGNORE_PLATFORM_CHECK=TRUE`, `KF_SKIP_PO_PROCESSING=ON`,
  `USE_DBUS=OFF`, `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON`,
  `BUILD_TESTING=ON`, serial make (OHOS HMDFS mkfifo EPERM).
- Dependencies: `qtbase/6.11.1`, `karchive/6.19.0`, `kcoreaddons/6.18.0`,
  `ki18n/6.18.0`, `openssl/3.5.6.1`, `ecm/6.26.0` (tool).
- CMake path layer fix: conan_cmakedeps_paths.cmake now prepends
  zlib/1.3.1.1 and openssl package root/lib/cmake/include, and zstd
  lib/pkgconfig onto PKG_CONFIG_PATH; adds `-L<zlib/zstd libdir> -lz -lzstd`
  to CMAKE_SHARED_LINKER_FLAGS / CMAKE_EXE_LINKER_FLAGS for the static
  libKF6Archive.a transitive link.
- Relocatability (R05/R07): libKF6Package.so DT_NEEDED has no
  `.conan2`/`.cache` machine-private path.

## Verification

- Clean dependency graph resolves `karchive/6.19.0`, `zlib/1.3.1.1`,
  `zstd/1.5.7`, `openssl/3.5.6.1`.
- conan create rc=0; upstream CTest 8/8 (plasmoidpackagetest excluded per
  R01 baseline hang); test_package 2/2; conan-verify G0-G4/L2/L4/L5 PASS.
- Isolated consumer `kpackage/6.18.0.2 + karchive/6.19.0` build/link/run PASS.

## R14 验证账本 (6.18.0.2, OHOS aarch64)

- 命令: `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同`
  → rc=0；configure: Found ZLIB libz.a 1.3.1 / OpenSSL libcrypto.a 3.5.6 /
  libzstd 1.5.7
  → 日志: `$HOME/tmp/kpackage-r14-create.log`
- 上游 CTest (autotests, `ctest -E "^plasmoidpackagetest$"`): 8/8 Passed
  1 fallbackpackagetest(0.06) 2 packagestructuretest(0.08)
  3 querytest(0.40) 4 testfallbackpackage-appstream(0.10)
  5 testpackage-appstream(0.11) 6 testpackage-nodisplay-appstream(0.08)
  7 testpackagesdep-appstream(0.14) 8 testpackagesdepinvalid-appstream(0.10)
  → "100% tests passed, 0 tests failed out of 8"
  plasmoidpackagetest: R01 基线挂起（-E 排除，未运行不计通过）
- OHOS 专测: test_package/test_ohos_adaptation（PackageLoader + Package +
  PackageJob::install 走 KArchive 提取 + KPluginMetaData）随 test_package
  2/2 Passed（test_kpackage 0.04 + test_ohos_adaptation 0.15）
- test_package RELOCATABILITY OK: libKF6Package.so 无 .conan2/.cache 私有路径

## R14 conan-verify + 可重定位审计

- `ohc-run.py conan-verify kpackage 6.18.0.2` → rc=0，G0/G1/G2/G3/G4
  + L2/L4/L5 全 PASS → 可标 published
  → 日志: `$HOME/tmp/kpackage-r14-conan-verify.log`
- DT_NEEDED/RPATH/RUNPATH 审计（R14 readelf）:
  libKF6Package.so DT_NEEDED = libzstd.so.1, libKF6CoreAddons.so,
  libKF6I18n.so, libQt6Core.so.6, libc++_shared.so, libc.so
  → 机器私有路径(.conan2/.cache)计数 0（R05/R07 保持）
---

**编译结束**: 2026-09-02 15:41
**最终状态**: built
