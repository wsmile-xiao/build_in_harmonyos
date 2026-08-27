# lua-rapidjson 0.6.0 编译笔记

## 编译环境
- 平台: OpenHarmony NEXT (musl libc)
- 编译器: clang 15
- 构建系统: CMake
- Conan: 2.29.1 (OHOS 适配版)

## 源码
- URL: https://github.com/xpol/lua-rapidjson/archive/refs/tags/v0.6.0.tar.gz
- SHA256: eaf053b745fdf89364f5d1416086265788489c0cae424c34f664b311df112b85

## 依赖
- lua/5.4.8 (Conan 制品仓已发布)
- RapidJSON: 内嵌于源码，无需外部依赖

## 问题与方案

### 问题1: CMake 不识别 HarmonyOS 为 UNIX 平台
- **根因**: CMake 不为 HarmonyOS 设置 UNIX 变量，导致 CMakeLists.txt 的 `if(UNIX)` 分支不被执行，平台被标记为 "unsupported"
- **方案**: 补丁修改 `if(UNIX)` 为 `if(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`

### 问题2: cmake_minimum_required(VERSION 2.8) 与 CMake 4.x 不兼容
- **根因**: CMake 4.x 移除了对 < 3.5 版本的支持
- **方案**: 补丁修改 `cmake_minimum_required(VERSION 2.8)` 为 `VERSION 3.5`

### 问题3: -march=native 不适合交叉编译
- **根因**: `-march=native` 在 CI 环境中可能产生不兼容的指令
- **方案**: 补丁移除 `-march=native` 标志

### 问题4: lua.hpp 缺失
- **根因**: lua conan 包只包含 C 头文件 (lua.h, lauxlib.h, lualib.h)，不包含 C++ 封装头文件 lua.hpp
- **方案**: 在 build() 方法中生成 lua.hpp 文件，并在补丁中添加 `${CMAKE_CURRENT_SOURCE_DIR}` 到 include_directories

### 问题5: 动态符号解析失败
- **根因**: HarmonyOS 动态链接器不默认导出主可执行文件的符号，导致 rapidjson.so 无法解析 lua_type 等 Lua API 符号
- **方案**: 补丁修改 `if (WIN32)` 为 `if (WIN32 OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`，使 MODULE 库在 HarmonyOS 上直接链接 liblua.a

## 验证结果
- conan create: PASS (干净构建成功)
- G1-G4 全部通过
- L2/L4/L5 安全/基线检查通过
- test_package: PASS (5 项测试: 加载模块、解码、编码、数组、null)

## 补丁
- patches/0001-fix-platform-detection-and-march-native.patch

---
**编译结束**: 2026-08-27
**最终状态**: built (conan-verify PASS, CI upload 待 PR 合并后触发)
---

**编译结束**: 2026-08-27 01:29
**最终状态**: built
