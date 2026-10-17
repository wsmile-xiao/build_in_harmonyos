# optional-lite 3.5.0 适配笔记

## 基本信息
- **上游**: https://github.com/martinmoene/optional-lite
- **版本**: 3.5.0
- **许可证**: BSL-1.0 (Boost Software License)
- **类型**: header-only C++ 库 (CMake INTERFACE library)

## 依赖
无任何依赖，仅包含单个头文件 `include/nonstd/optional.hpp`。

## 构建系统
CMake，header-only INTERFACE library。
- `OPTIONAL_LITE_OPT_BUILD_TESTS=ON` 启用上游测试
- 上游测试使用 lest 测试框架 (内置于 test/lest/lest_cpp03.hpp)
- clang 15+ 下 CTest 运行 4 个测试: cpp98/cpp11/cpp14/cpp17

## 安装路径
- 头文件: `include/nonstd/optional.hpp`
- CMake 配置: `lib/cmake/optional-lite/optional-lite-config.cmake`
- CMake 目标: `nonstd::optional-lite`

## OHOS 适配
- 设置 `CMAKE_SYSTEM_NAME=Linux` 规避 E092 (CMake 不识别 OHOS)
- 无需补丁，源码直接编译
