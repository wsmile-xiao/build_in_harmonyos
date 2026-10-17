# sparse-map 0.7.0 适配笔记

## 编译环境

- 构建系统: CMake（header-only 库）
- 编译日期: 2026-09-03
- 编译器: `/data/service/hnp/bin/clang++` 15.0.4，目标 `aarch64-unknown-linux-ohos`
- 状态: built（尚未进行 release upload）

## 编译步骤

1. 下载官方 `v0.7.0.tar.gz`，SHA-256 为
   `b603a24f596f95a06ec1d437f4cb928c2647cf9bc73b751ac6fb82deb7863d98`。
2. 用 Conan `CMakeToolchain` 配置上游 CMake 工程；OHOS 配置使用
   `CMAKE_SYSTEM_NAME=Linux` 和 `CMAKE_SYSTEM_PROCESSOR=aarch64`。
3. `cmake --build <build> -j1` 后执行 `cmake --install <build>`，安装头文件和
   `tsl-sparse-map` CMake 配置包。
4. 上游 `tests/` 的原始 CMake 配置要求 `Boost::unit_test_framework`。设备上
   `conan install boost/1.84.0 --build=never` 找不到 OHOS arm64 的 Boost/zlib
   二进制，原始配置也因此报告缺少 `Boost_INCLUDE_DIR` 和
   `unit_test_framework`。配方不添加运行时依赖，而是下载并校验 Boost 1.86.0
   源码头文件，在 build 目录生成只替换入口头文件的 `main.cpp`，并用 clang++
   编译全部 6 个上游测试源文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CMake 测试配置失败 | `tests/CMakeLists.txt` 依赖 `Boost::unit_test_framework`，而 OHOS 设备没有兼容的 Boost/zlib Conan 二进制 | 将 Boost 作为 test-only 源码归档，编译 header-only Boost.Test；不增加包运行时依赖 |
| 2 | CMake 将 OHOS 识别为未知系统 | 设备 CMake 4.1.2 不内置 OHOS 系统名 | Conan toolchain 设置 `CMAKE_SYSTEM_NAME=Linux`，OHOS 处理器设置为 `aarch64` |

## 源码修改

无补丁。只在 build 目录生成 Boost.Test 的 header-only 入口文件，未修改上游源码。

## 依赖版本

- 运行时依赖：无（header-only）
- 测试源码依赖：Boost 1.86.0，SHA-256
  `1bed88e40401b2cb7a1f76d4bab499e352fa4d0c5f31c0dbae64e24d34d7513b`
- Conan：2.29.1；CMake：4.1.2；GNU Make：4.4.1

## 验证结果

```text
上游 OHOS arm64 Boost.Test：Running 156 test cases...
上游结果：*** No errors detected，退出码 0
Conan test_package：sparse_map_consumer 运行成功，1/1，退出码 0
最终命令：conan create ... -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
最终构建使用 CMake `-- -j20 -j1`，末尾 `-j1` 确保设备端串行执行。
```

## 注意事项

- `upstream_test_count` 必须保持为实际 Boost.Test 输出的 156，不能按宏定义数量统计。
- 该库的 CMake 包名/目标名是 `tsl-sparse-map` / `tsl::sparse_map`，不是 Conan 名 `sparse-map`。
- 只将 Boost 作为测试源码下载，避免把不可用的 OHOS Boost/zlib 预编译包带入运行时依赖图。
