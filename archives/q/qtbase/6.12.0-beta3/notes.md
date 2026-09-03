# qtbase 6.12.0-beta3 Adaptation Notes

## Source
- Upstream: Qt 6.12.0-beta3 (development release)
- URL: https://github.com/qt/qt5/tree/6.12
- Tarball: qtbase-everywhere-src-6.12.0-beta3.tar.xz
- SHA256: f3824da6358d11da552dfbda21107c666606baac2d283a31d0ee1a052fdcff37
- Source: download.qt.io/development_releases (NOT official_releases - beta)

## Adaptation Strategy
- Based on qtbase/6.11.1.1.1 recipe
- Patches reused from 6.11.1.1.1 (6 HarmonyOS portability patches)
- conanfile.py updated with version string only
- Build configuration identical to 6.11.1.1.1

## Environment Limitation
- Local compilation blocked: OHOS security policy prevents execution of
  unsigned ELF binaries (clang, cmake, ninja all return "Operation not permitted")
- This recipe requires a CI worker with proper binary signing to build
- The conan profile (ohos-aarch64) expects compiler at /data/service/hnp/bin/clang

## Patches (6 total)
1. cmake/QtPlatformSupport.cmake - Treat HarmonyOS as Linux-compatible UNIX
2. mkspecs/harmonyos-clang/ - Add harmonyos-clang Qt mkspec (new files)
3. src/corelib/thread/qthread_unix.cpp + qprocess_unix.cpp - Disable pthread cancel
4. cmake/platforms/Platform/HarmonyOS.cmake - Reuse CMake Linux platform rules (new file)
5. cmake/QtAutoDetectHelpers.cmake - Skip Android autodetection
6. src/corelib/tools/qhash.cpp - Disable ARM AES hash on HarmonyOS

## Dependencies
- openssl/3.5.6.1 (for Qt Network SSL support)

## TODO
- [ ] Verify patches apply cleanly to 6.12.0-beta3 source
- [ ] Run conan create on CI worker to verify build
- [ ] Update to beta4 or final release when available
