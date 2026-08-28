# astlib 0.9.0 适配笔记

## 编译环境
- 构建系统: cmake (CMakeLists.txt, C++14 upstream bumped to C++17)
- 编译日期: 2026-08-27
- 编译器: clang 15.0.4 / OHOS SDK
- 状态: published

## 编译步骤

1. Download source from GitHub master branch archive
2. Patch CMakeLists.txt files (see Source Modifications below)
3. Install Poco via Conan (`conan install --requires=poco/1.15.3`)
4. Set LD_LIBRARY_PATH for OHOS SDK lld (E132 fix)
5. cmake configure with CMakeToolchain + CMakeDeps
6. Build generator target only
7. Run generator to create spec files (cat*.cpp, entries.cpp, AsterixItemDictionary.cpp)
8. Re-configure cmake to pick up generated spec files
9. Build all targets (libastlib.a, binary2asterix, ast2json)
10. Install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | poco/1.14.2 not published | Registry only has poco/1.15.3 | Use poco/1.15.3 (satisfies >=1.7.0 requirement) |
| 2 | GitHub download timeout | GitHub blocked on device | Use ghfast proxy for init-build; conandata.yml uses official URL (CI handles mirror) |
| 3 | lld linker can't find libxml2.so.16 | E132: OHOS SDK lld needs llvm/lib in LD_LIBRARY_PATH | Set LD_LIBRARY_PATH to include SDK llvm/lib path |
| 4 | CMake policy error (VERSION 3.3) | CMake 4.x removed compat for <3.5 | Add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 5 | is_same_v/is_signed_v not found | Poco 1.15.3 uses C++17 features; project set C++14 | Bump CMAKE_CXX_STANDARD to 17 |
| 6 | Undefined symbol getAsterixSpecifications | aux_source_directory can't find build-time generated spec files | Pre-generate spec files, re-configure cmake |
| 7 | Narrowing conversion errors in cat002 spec | Generated UTF-8 bytes (-62,-80) in char arrays | Add -Wno-narrowing compiler flag |
| 8 | Generator can't find Poco shared libs at runtime | Runtime LD_LIBRARY_PATH missing Poco lib dir | Source conanrun.sh to get Poco lib path |

## 源码修改

Patches applied programmatically via `replace_in_file()` in conanfile.py `source()` method:

### Main CMakeLists.txt
- `set(CMAKE_CXX_STANDARD 14)` → `set(CMAKE_CXX_STANDARD 17)` — Poco 1.15.3 requires C++17
- `find_package(Poco 1.7.0 REQUIRED ... CONFIG PATHS "/opt/rsys/platform" ...)` → `find_package(poco REQUIRED)` — Use Conan CMakeDeps
- `${Poco_LIBRARIES}` → `poco::poco` — Modern CMake target-based linking
- `${Poco_INCLUDE_DIRECTORIES}` → `${poco_INCLUDE_DIRS}` — Conan variable names
- Added `-Wno-narrowing` to CMAKE_CXX_FLAGS — Suppress errors in generated spec files

### astlib/CMakeLists.txt
- Same Poco find_package and variable replacements
- `aux_source_directory(specifications srcs)` → `file(GLOB SPEC_FILES ...)` — Pick up generated files on re-configure

## 依赖版本

- poco/1.15.3 (published in ohpcd registry)

## 验证结果

```bash
# Build output
[  5%] Built target generator
[ 50%] Built target astlib
[ 52%] Built target binary2asterix
[ 54%] Built target ast2json
[100%] Built target astlib_dll

# Products
lib/libastlib.a — 11MB static library
lib/libastlib_dll.a — 11MB static library (identical)
bin/binary2asterix — 6MB executable
bin/ast2json — 6MB executable
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libastlib.a | 11MB | Static library |
| bin/binary2asterix | 6MB | Binary to Asterix converter |
| bin/ast2json | 6MB | Asterix to JSON converter |

## 注意事项

- The project has a build-time code generation step: the `generator` tool creates spec files from XML definitions
- Two-step cmake configure is needed: first build generator, run it, then re-configure
- Poco 1.14.2 specified in task does not exist in registry; 1.15.3 is the only available version
- C++ standard bumped from 14 to 17 due to Poco 1.15.3 dependency
---

**编译结束**: 2026-08-27 10:01
**最终状态**: built
