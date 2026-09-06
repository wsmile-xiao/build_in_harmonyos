# googletest release-1.12.1 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64)的 conan 包，纯静态库，供 C++ 工程测试链接。

## 出包（鸿蒙 PC CI）

```bash
# 鸿蒙 PC 设备原生编译
conan create . -pr ohos-native
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；stock conan 2 默认不含 OHOS。推荐在 `~/.conan2/settings_user.yml` 的 `os:` 下加一行 `    OHOS:`（非侵入扩展，不改 settings.yml），或使用 OpenHarmonyPCDeveloper 分发的 conan。

## 产物

静态库（`lib/`）：

| 库 | 说明 |
|----|------|
| `libgtest.a` | GoogleTest 核心 |
| `libgtest_main.a` | GoogleTest 默认 main |
| `libgmock.a` | GoogleMock 核心 |
| `libgmock_main.a` | GoogleMock 默认 main |

头文件安装到 `include/gtest/`、`include/gmock/`；同时安装 `GTestConfig.cmake`（find_package(GTest)）与 `gtest.pc`/`gmock.pc`。

## 消费：CMake 工程

```bash
conan install --requires=googletest/release-1.12.1 -pr ohos-native
```

```cmake
find_package(GTest REQUIRED)
target_link_libraries(your_test GTest::gtest GTest::gtest_main)
```

## 消费：裸 g++ 静态链接

```bash
clang++ test.cpp -I ~/usr/local/include -L ~/usr/local/lib \
    -lgmock -lgtest_main -lgtest -lpthread -std=c++14
```

注意链接顺序：gmock_main → gmock → gtest_main → gtest。
