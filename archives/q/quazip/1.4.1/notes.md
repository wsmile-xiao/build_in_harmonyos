# QuaZip 1.4.1 adaptation notes

## Version identity

- Task platform version: quazip 1.4.1 (Issue #2220, points race)
- Upstream project: QuaZip, tag v1.4 (there is no upstream v1.4.1 tag;
  1.4.1 is the Conan adaptation version for this repository, matching the
  previous 1.4 -> 1.4.1 bump made while updating the qt5-qtbase dependency)
- Archive: archives/q/quazip/1.4.1, Conan ref quazip/1.4.1

## Build environment

- Target: OpenHarmony aarch64 (os=OHOS, arch=armv8, clang 15)
- Build system: CMake
- Dependencies: qt5-qtbase/5.15.2.2 and zlib/1.3.1

## Adaptation

The upstream project uses find_package(Qt5 COMPONENTS Core). The recipe maps
the Conan Qt package to the upstream Qt5 CMake package name while preserving
the generated Qt component targets. Bzip2 support is disabled because it is not
needed for the upstream ZIP coverage.

CMakeDeps does not export the Qt5::moc and Qt5::rcc executable targets, so the
recipe supplies the Conan-provided tools through CMAKE_AUTOMOC_EXECUTABLE and
CMAKE_AUTORCC_EXECUTABLE. The Qt5 runtime directory is applied only while
running CTest.

The recipe declares the canonical checksum-verified GitHub source URL. If that
download is unavailable, it clones the GitCode mirror and checks out the
verified upstream v1.4 commit `566fa496649b8cb09018b497575bb3bf2977965f`.

## Tests

The recipe enables and runs upstream qztest through CTest. The consumer test
creates a ZIP archive, writes an entry, reopens it and verifies the payload.
The root-directory extraction case performs a POSIX runtime check and is skipped
only when the test environment does not permit writing to `/`; no platform
conditional-compilation macro is introduced. The remaining upstream cases and
the consumer test are executed on the target device; results are recorded in
manifest.yaml after the real run.
---

**编译结束**: 2026-08-16 09:35
**最终状态**: built
