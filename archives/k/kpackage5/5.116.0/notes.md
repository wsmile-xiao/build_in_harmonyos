# kpackage5 5.116.0 - adaptation notes (OpenHarmony PC)

## Upstream identity

- Repository: https://invent.kde.org/frameworks/kpackage (KF5 branch)
- Version: 5.116.0, the final KF5 release
- Source: https://download.kde.org/stable/frameworks/5.116/kpackage-5.116.0.tar.xz
- SHA-256: 5705b185c72b09f19215fa659fc628dc74529bb7d3f649d1fc953ae5a7ebf1be
  (re-downloaded and verified byte for byte)
- Language: C++ (Qt5); `CMakeLists.txt:3` sets KF_VERSION 5.116.0
- Build system: CMake + extra-cmake-modules, tests under CTest

## Dependency that blocked this task

`CMakeLists.txt:47` calls `find_package(KF5Archive 5.116.0 REQUIRED)`.
`karchive5/5.116.0` existed neither in this repository nor on `ohpcd`, so the
project could not be configured at all. It is now an independently delivered
adaptation (`archives/k/karchive5`, device-verified), which unblocks this one.

## Device verification: PASS, 11/11

```
worker   WIN01
sha      313fb726fdfdfaa275a1c88961ced7d94eec035c
status   PASS (exit 0), 205.6 s
ctest    100% tests passed, 0 tests failed out of 11
consumer PASS: KPackage::PackageLoader registry round-trip OK
package  libKF5Package.so + 6 headers + 8 cmake configs
         + 52 .mo catalogues + 3 .desktop + kpackagetool5
```

```
 1/11 plasma-fallbackpackagetest ....... Passed  0.14 sec
 2/11 plasma-packagestructuretest ...... Passed  0.61 sec
 3/11 plasma-plasmoidpackagetest ....... Passed  0.56 sec
 4/11 plasma-rccpackagetest ............ Passed  0.07 sec
 5/11 plasma-querytest ................. Passed  0.61 sec
 6/11 testfallbackpackage-appstream .... Passed  0.15 sec
 7/11 testpackage-appstream ............ Passed  0.18 sec
 8/11 testpackage-nodisplay-appstream .. Passed  0.10 sec
 9/11 testjsonmetadatapackage-appstream  Passed  0.16 sec
10/11 testpackagesdep-appstream ........ Passed  0.15 sec
11/11 testpackagesdepinvalid-appstream . Passed  0.15 sec
```

**All eleven upstream CTest entries run and all eleven pass.** No test is
excluded. `autotests/mockdepresolver` builds `mockhandler` but registers no
test, so it contributes none.

An earlier revision of this recipe excluded `plasma-plasmoidpackagetest` with
`-E`, on the strength of a comment inherited from the KF6 kpackage recipe
claiming it hangs on this runner. That claim was not true here: run with no
exclusion and a per-test `--timeout 180`, it passes in 0.56 s. Excluding a
test asserts something about the platform, so it is no longer asserted -
`ctest` runs every registered entry, and a wedged test would report as TIMEOUT
rather than hang the build.

## Root cause of the four tests that used to fail

They died at dynamic-load time with

```
Error loading shared library libKF5CoreAddons.so.5: Permission denied
```

which was misleading in every direction. A minimal `dlopen(path, RTLD_NOW)`
probe, printing `dlerror()` instead of trusting the wrapped message, settled
it:

```
dlopen("libKF5CoreAddons.so.5")   FAILED: ... Permission denied
dlopen("libQt5Core.so.5")         OK
dlopen("libQt5DBus.so.5")         OK
dlopen("libKF5Archive.so")        OK
```

The file is present, readable (`head -c 4` returns the ELF magic), carries the
right SONAME, and exports the 74 `KPluginMetaData` symbols being relocated.
What it does not carry is a **.codesign section the OHOS loader accepts**:

    unmodified copy of libKF5CoreAddons.so.5  -> dlopen FAILS (EACCES)
    same bytes, re-signed with binary-sign-tool -selfSign 1 -> dlopen OK

HarmonyOS refuses to map the library and reports the refusal as a permission
error against whichever library it was resolving. The invalid signature is
inside the published `kcoreaddons5` package, which this recipe cannot change,
so the recipe stages copies of the dependency libraries, re-signs them with
`binary-sign-tool`, and puts that directory **first** on `LD_LIBRARY_PATH` -
both for the upstream ctest run and for `test_package`. Ordering matters: with
the dependency lib directories first (as they originally were) the loader
resolved the unsigned original and never reached the signed copy, so signing
alone changed nothing.

