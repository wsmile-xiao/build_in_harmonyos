# aws-crt-cpp 0.38.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-09
- 编译器: clang++ 15.0.4
- 状态: built (Conan recipe generated and verified)

## 编译步骤
aws-crt-cpp uses CMake with BUILD_DEPS=ON which builds all AWS C runtime
dependencies (aws-c-common, aws-c-io, aws-c-cal, aws-c-http, aws-c-auth,
aws-c-mqtt, aws-c-s3, aws-c-event-stream, aws-checksums, aws-c-sdkutils,
aws-lc, s2n) from source as bundled submodules.

### Key CMake options:
- BUILD_SHARED_LIBS=OFF (static library)
- BUILD_TESTING=OFF (skip tests)
- ENFORCE_SUBMODULE_VERSIONS=OFF (no git repo for version checking)
- CMAKE_SYSTEM_NAME=Linux (OHOS adaptation, see below)

### Source handling:
The GitHub release tarball does NOT include git submodule content.
The Conan recipe downloads each submodule archive separately using
the commit SHA from the v0.38.5 tag.

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure error: "Event Loop is not setup on the platform" | aws-c-io/CMakeLists.txt checks CMAKE_SYSTEM_NAME for "Linux" or "Android" but OHOS is detected as "HarmonyOS" | Set CMAKE_SYSTEM_NAME=Linux in CMakeToolchain (OHOS is Linux-compatible) |
| 2 | Empty submodule directories | GitHub release tarball does not include git submodule content | Download each submodule archive separately in conanfile.py source() |

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan recipe with submodule download support |
| conandata.yml | Source URLs and sha256 for main + 13 submodules |
| test_package/test.cpp | C++ test that initializes AWS CRT runtime |

## 结束
COMPLETED
