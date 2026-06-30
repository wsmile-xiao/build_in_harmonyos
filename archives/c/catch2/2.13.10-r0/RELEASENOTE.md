# catch2 2.13.10-r0 发布说明

## 软件信息
- **软件名**: catch2
- **版本**: 2.13.10-r0
- **类型**: Header-only C++ 测试框架
- **构建系统**: CMake

## 编译状态
- **状态**: success
- **编译日期**: 2026-05-09

## 安装内容
- 头文件: `include/catch2/catch.hpp` (主头文件)
- 扩展头文件: `catch_reporter_automake.hpp`, `catch_reporter_sonarqube.hpp`, `catch_reporter_tap.hpp`, `catch_reporter_teamcity.hpp`
- CMake 配置: `lib/cmake/Catch2/`
- pkg-config: `share/pkgconfig/catch2.pc`
- 调试辅助: `share/Catch2/gdbinit`, `share/Catch2/lldbinit`

## 使用方法
```cmake
# CMake 项目中使用
find_package(Catch2 REQUIRED)
target_link_libraries(my_test Catch2::Catch2)
```

```cpp
// C++ 代码中使用
#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>

TEST_CASE("example", "[tag]") {
    REQUIRE(true);
}
```

## 编译环境
- 编译器: Clang 15.0.4
- CMake: 4.3.1
- 平台: HarmonyOS (aarch64)

## 注意事项
- catch2 是 header-only 库，无需链接动态库
- 编译时需要 C++11 或更高版本支持
