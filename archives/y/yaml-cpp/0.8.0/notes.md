# yaml-cpp 0.8.0 — Adaptation Notes

> Archive created: 2026-04-26
> Last updated: 2026-08-25
> Status: Conan recipe adapted

## Basic Info
| Item | Value |
|------|-------|
| Software | yaml-cpp |
| Version | 0.8.0 |
| Build System | CMake |
| Source | https://github.com/jbeder/yaml-cpp/archive/refs/tags/0.8.0.tar.gz |
| sha256 | fbe74bbdcee21d656715688706da3c8becfd946d92cd44705cc6098bb23b3a16 |

## Build Steps

### Phase 1: Environment
- [x] init-build completed, source downloaded and extracted
- [x] Dependencies checked (none required)

### Phase 2: Compilation
- [x] cmake configure (with CMAKE_POLICY_VERSION_MINIMUM=3.5)
- [x] make build — 100% success, libyaml-cpp.a produced
- [x] make install — headers, cmake config, pkgconfig, library installed

### Phase 3: Conan Recipe
- [x] conanfile.py adapted from 0.9.0 recipe
- [x] conandata.yml with correct sha256
- [x] test_package/ with functional test (parse/sequence/map/round-trip/emitter)
- [x] conan-verify passed

## Key Adaptation Points

1. **CMake 4.x compatibility**: yaml-cpp 0.8.0 has `cmake_minimum_required(VERSION 3.4)`,
   which CMake 4.x rejects. Fixed by setting `CMAKE_POLICY_VERSION_MINIMUM=3.5` in the
   CMakeToolchain.

2. **OHOS platform support**: Same pattern as 0.9.0 — set `cmake_system_name=OHOS`,
   `cmake_system_processor=aarch64`, `CMAKE_INSTALL_LIBDIR=lib`.

3. **Code signing**: Shared library option supported with OHOS code-signing helpers
   (llvm-objcopy + binary-sign-tool). Default build is static.

4. **No YAML_CPP_MAIN_INCLUDE**: Unlike 0.9.0, 0.8.0 does not have this CMake option.

## Source Modifications
None — yaml-cpp 0.8.0 builds cleanly on OHOS without patches.

## Deliverables
- conanfile.py
- conandata.yml
- test_package/conanfile.py
- test_package/CMakeLists.txt
- test_package/test.cpp
- test_package/MANIFEST.yml

---

**编译结束**: 2026-08-25
**最终状态**: built (Conan recipe adapted, conan-verify PASS, W3 local CI PASS)

