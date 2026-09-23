# kiconthemes 6.26.0 notes

## Scope

This package is part of the KF6 6.26 baseline (platform task #6386,
dependency activity). It updates the existing HarmonyOS PC recipe from the
6.18.0.1 archive (latest complete archive) to KDE Frameworks 6.26.0,
following the same 7-point pattern as the other 6.26 chain packages
(kitemviews PR #8491 precedent).

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KICONTHEMES_USE_QTQUICK=OFF` avoids Qt6Qml/Qt6Quick (not published to ohpcd).
- `USE_DBUS=OFF` avoids Qt6DBus until the shared Qt DBus baseline lands.
- `USE_BreezeIcons=OFF` avoids the unpublished KF6BreezeIcons package.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation.
- `include(ECMQmlModule)` is patched out for the Qt6Qml-free baseline, and the
  optional QtQuick autotest is guarded behind `KICONTHEMES_USE_QTQUICK`
  (regenerated against the 6.26.0 source; same semantics as 6.18.0.1).
- `/system/lib64` prepended to `LD_LIBRARY_PATH` for configure and test runs
  (sandbox libc++_shared.so shadowing, kconfig 6.26.0 / bluez-qt 6.28.0
  precedent).

## Upstream changes (6.18.0 -> 6.26.0)

- cmake_minimum_required 3.16 -> 3.29; Qt minimum 6.7.0 -> 6.9.0
  (qtbase 6.11.1 satisfies).
- KIconLoader: empty fallback theme guard, icon theme XML whitespace/comment
  handling, svg-before-png lookup preference.
- KIconTheme: empty theme name guard, qCDebug -> qCWarning.
- KIconEngine: Qt 6.8+ size handling cleanup.
- autotests: QVERIFY -> QCOMPARE rewrites only; test set unchanged.
- ECMQmlModule include and autotests QtQuick probe unchanged in position
  (patch context lines still apply with the same semantics).

## Dependency status at build time (local-cache first strategy)

karchive/6.26.0, kcolorscheme/6.26.0 and kguiaddons/6.26.0 were not yet
published to the ohpcd registry when this W3 verification ran. Per the task
coordination instruction they were materialized into the local conan cache
via `conan create` (kcolorscheme/kguiaddons recipes read-only referenced
from their in-flight branches; karchive 6.26.0 recipe assembled locally with
the fixes below) so that this package could be fully validated ahead of the
registry publications. The PR will build in CI once the dependencies are
published (kwidgetsaddons PR #8504 and the kcolorscheme/karchive follow-ups).

Local karchive 6.26.0 build notes (not part of this PR):
- Upstream sources use C++20 (`std::ranges`, `std::bit_cast` in k7zip.cpp).
  The conan toolchain pins cppstd=17 through a normal `set()` that always
  shadows cache-level overrides, so the recipe rewrites the generated
  conan_toolchain.cmake to `set(CMAKE_CXX_STANDARD 20)` (knowledge entry
  c2a7b1018f65 pattern).
- `std::ranges::any_of` is unavailable on the OHOS SDK libc++ 15.04
  (`_LIBCPP_HAS_NO_INCOMPLETE_RANGES`); a small portability patch switches
  it to the iterator-pair `std::any_of` form.
- `test7ZipOssFuzzIssues` (new upstream fuzz regression suite added after
  6.18) hangs indefinitely on OHOS with testcase_6213340184772608; the test
  run skips it and test7ZipReadCoder's bzip2/zstd rows (optional coders not
  compiled in, WITH_BZIP2=OFF/WITH_LIBZSTD=OFF per the 6.18 baseline).

## Test reporting (N declaration)

Upstream build system registers these CTest targets with QtQuick available:
kiconloader_unittest, kiconloader_resourcethemetest, kicontheme_unittest,
kiconengine_unittest, kiconengine_scaled_unittest, kicondialog_unittest,
kpixmapsequenceloadertest, kquickiconprovidertest (8 total).

Executed on OHOS (KICONTHEMES_USE_QTQUICK=OFF, so kquickiconprovidertest is
not registered):
- 5/5 CTest targets passed (kiconloader_resourcethemetest,
  kicontheme_unittest, kiconengine_scaled_unittest, kicondialog_unittest,
  kpixmapsequenceloadertest), offscreen headless.
- kiconloader_unittest passed the OHOS-supported subset: 29/29 QtTest
  checks, excluding one data row that depends on shared-mime-info data
  unavailable in the current OHOS baseline (same as 6.18.0.1).
- kiconengine_unittest passed the OHOS-supported subset: 8/8 QtTest checks,
  excluding `testMode` because BreezeIcons is explicitly disabled (same as
  6.18.0.1).
- Conan test_package passed 1/1 with a `KIconLoader::global()` consumer
  compile/link/runtime smoke.

## Verification

OHOS `conan create` verification passed on 2026-09-06.

- Runner log: `~/tmp/kiconthemes-dl/kit-create2.log` (local W3 run).
- Full package reference:
  `kiconthemes/6.26.0#e0b2178ccabd57241ccb2e973aefae84:8935f3f60d62a98ae9eec680abcd71b2d6234b24#4966e48080d0437ff4dbead7c2230153`.
---

**编译结束**: 2026-09-06 23:54
**最终状态**: built
