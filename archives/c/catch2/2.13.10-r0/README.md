# catch2 2.13.10-r0 — OpenHarmony 编译记录

## 基本信息
- 软件: catch2
- 版本: 2.13.10-r0
- 构建系统: cmake
- 目标: ohos-aarch64

## 编译指导
Conan 包名为 `catch2/2.13.10-r0`，通过 `Catch2::Catch2` CMake 目标提供单头文件测试框架。

## 补丁清单
<!-- patches/ 目录中的补丁说明 -->

## 已知限制
<!-- 平台相关限制 -->

## 功能验证
`conan create .` 会编译并运行 `test_package/test_catch2.cpp`。
