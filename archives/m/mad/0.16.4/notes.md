# Adaptation Notes — mad (libmad) 0.16.4

## Software
- **Name**: mad (also known as libmad)
- **Version**: 0.16.4
- **Description**: MAD is a high-quality MPEG audio decoder library
- **License**: GPL-2.0-or-later
- **Source**: https://codeberg.org/tenacityteam/libmad
- **SHA256**: 0f6bfb36c554075494b5fc2c646d08de7364819540f23bab30ae73fa1b5cfe65

## Build System
- **Type**: CMake (tenacityteam fork uses cmake, NOT the original sourceforge autotools)
- **CMakeLists.txt**: cmake_minimum_required(VERSION 3.1.0)

## Build Configuration
- `CMAKE_POLICY_VERSION_MINIMUM=3.5` — CMake 4.x removed compat with < 3.5
- `OPTIMIZE=ACCURACY` — optimize for accuracy over speed (matches upstream packaging)
- `BUILD_SHARED_LIBS=OFF` — R26: system same-name library, static to avoid /lib pollution

## Compilation
- **Compiler**: clang 15.0.4 (aarch64)
- **CFLAGS**: -fPIC -O2
- **Build result**: libmad.so (shared, exploratory) → conan recipe builds static (R26)
- **Dependencies**: none (only libc.so)
- **Installed files**: lib/libmad.so, include/mad.h, lib/pkgconfig/mad.pc, lib/cmake/mad/*

## Issues Encountered
1. **Codeberg IP block**: Codeberg blocked our IP (HTTP 429). Resolved by obtaining tarball from openEuler Gitee mirror (gitee.com/src-openeuler/libmad).
2. **CMake 4.x compat**: CMakeLists.txt declares `cmake_minimum_required(VERSION 3.1.0)` which CMake 4.1.2 rejects. Fixed with `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`.
3. **check_env crash**: ohc-run.py init-build crashed in check_env() due to missing autoconf binary. Workaround: manually created .build-context file.
4. **Build system detection**: conan-init guessed "autotools" from URL. Manually corrected conanfile.py to use CMake.

## Test
- `ctest`: No tests defined (library-only project, no upstream test suite)
- test_package: Verifies mad.h includability and mad_stream_init/finish linkage

## Knowledge Graph
- No new error patterns requiring drafts (all issues were straightforward configuration matters)
---

**编译结束**: 2026-07-02 16:02
**最终状态**: built
