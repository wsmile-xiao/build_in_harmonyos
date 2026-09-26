# RapidJSON

## 简介

RapidJSON 是一个高性能的 C++ JSON 解析器和生成器，提供 SAX 和 DOM 风格的 API。

## OHOS 适配

- Header-only 库，`package_type = "header-library"`，经 CMake install 安装头文件与 CMake 包配置
- CMake 不识别 HarmonyOS 的问题通过 `CMAKE_INSTALL_DIR=lib/cmake/RapidJSON` 显式指定解决
  （上游在非 UNIX/WIN32 平台上留空 install DESTINATION，CMake 4.x 拒绝空目标）
- 上游测试套件（gtest，343 用例 / 29 suites）在 `build()` 内编译运行，
  依赖 gtest/1.17.0（ohpcd registry）；OHOS 测试二进制经 binary-sign-tool 自签名
- 4 个补丁全部针对上游测试构建系统（-Werror/-Weverything、gtest 源查找、
  C++17、`/tmp` 硬编码），库本体头文件零修改

## 依赖

- gtest/1.17.0（仅测试构建；库本体零依赖）

## 功能验证

真机 conan create（OHOS SDK 26.0.0.18 / clang 15.0.4 / aarch64，2026-09-24）：

- 上游 gtest 套件 `unittest`：343/343 passed、0 failed
- test_package：`rapidjson_unit_consumer` + `rapidjson_ohos_portability` 2/2 passed

## 参考

- 官网：https://rapidjson.org/
- GitHub：https://github.com/Tencent/rapidjson
