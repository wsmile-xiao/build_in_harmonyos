# Build Test Report — libcprime 2.3.0

## Build Information

| Field | Value |
|-------|-------|
| Software | libcprime |
| Version | 2.3.0 |
| Build System | CMake (via patch from QMake) |
| Platform | HarmonyOS PC (aarch64) |
| Compiler | clang/clang++ |
| Dependencies | qtbase/6.11.1 |
| Patches | 0001-add-cmake-build.patch, 0002-qt6-compat.patch |
| Status | Built |

## Build Process

1. Downloaded source tarball from GitHub (sha256 verified)
2. Applied 0001-add-cmake-build.patch — creates CMakeLists.txt with Qt6 integration
3. Applied 0002-qt6-compat.patch — fixes 4 Qt5-to-Qt6 API issues
4. Configured with CMake (Qt6 cmake paths injected via conan_cmakedeps_paths.cmake)
5. Built shared library `libcprime` (lib cprime)
6. Installed to package folder: lib/libcprime.so, include/cprime/*.h, share/coreapps/theme/
7. ELF signing applied to shared library for OHOS

## Test Results

### Upstream Tests

No upstream test suite exists in the libcprime repository.

### Test Package

| Test | Description | Result |
|------|-------------|--------|
| test_libcprime | Creates QCoreApplication, calls CPrime::Variables::CC_CoreApps_ConfigDir(), CC_CoreApps_BookMarkFile(), checks CPrime::AppsName enum | PASS |

Assertions: 3

### Environment

- QT_QPA_PLATFORM=offscreen for headless execution
- LD_LIBRARY_PATH set to include qtbase and libcprime lib directories

## Verification Command

```bash
conan create archives/l/libcprime/2.3.0/conanfile.py \
  -pr:h=$SKILL_ROOT/ci/conan/profiles/ohos-aarch64 \
  -pr:b=$SKILL_ROOT/ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## Known Issues

- Source URL uses branch archive (master) rather than a tagged release, as upstream
  does not publish version tags. SHA256 is pinned for reproducibility.
