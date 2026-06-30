# googletest

Google Testing and Mocking Framework - C++ 测试和模拟框架

## 软件简介

googletest 是 Google 开发的 C++ 测试框架，包含：
- **GoogleTest (gtest)**: C++ 单元测试框架
- **GoogleMock (gmock)**: C++ 模拟对象框架

## 编译版本

| 版本 | 状态 | 编译日期 | 构建系统 |
|------|------|---------|---------|
| 1.15.2 | built | 2026-05-27 | cmake |

## 产物说明

googletest 仅提供静态库，无动态库和可执行文件：
- `libgtest.a`: GoogleTest 核心库
- `libgtest_main.a`: GoogleTest 主入口库
- `libgmock.a`: GoogleMock 核心库
- `libgmock_main.a`: GoogleMock 主入口库

## 使用方式

### 1. 通过预编译包安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- googletest 1.15.2
```

### 2. 在 CMake 项目中使用

```cmake
find_package(GTest REQUIRED)
target_link_libraries(your_target GTest::gtest GTest::gtest_main)
```

### 3. 在 pkg-config 项目中使用

```bash
pkg-config --cflags --libs gtest gtest_main
```

## 特性

- ✅ 无外部依赖
- ✅ 纯 C++ 实现
- ✅ 静态库编译
- ✅ 自动平台检测

## 编译参数

| 参数 | 值 | 说明 |
|------|-----|------|
| CMAKE_INSTALL_PREFIX | ~/usr/local | 安装路径 |
| CMAKE_BUILD_TYPE | Release | 编译类型 |

## 注意事项

1. googletest 仅提供静态库，使用时需链接两个库
2. cmake 会检测平台为 "unknown"，但不影响编译
3. Google 建议从最新 commit 编译，而非固定版本

## 参考链接

- GitHub: https://github.com/google/googletest
- 文档: https://google.github.io/googletest/