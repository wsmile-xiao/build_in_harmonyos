# gumbo-parser 0.10.1 适配笔记

## 编译环境

- 平台：OpenHarmony / HarmonyOS PC aarch64
- 构建方式：Conan 配方直接调用 clang/llvm-ar
- 编译日期：2026-07-23
- 编译器：clang 15 / clang++ 15
- 状态：built

## 编译步骤

1. 下载官方 `v0.10.1` 源码归档，并以 SHA-256 校验。
2. 下载官方 GoogleTest `release-1.6.0` 归档，填补上游源码归档中未初始化的 `third_party/gtest` 子模块。
3. 用 clang 编译 11 个 C 源文件并用 `llvm-ar` 生成静态库 `libgumbo.a`。
4. 用 clang++ 编译 GoogleTest 与 9 组上游测试源文件；为旧版 GoogleTest 设置 `GTEST_USE_OWN_TR1_TUPLE=1`，避免 OHOS libc++ 缺少 `tr1/tuple`。
5. 运行 `gumbo_test --gtest_color=no`，172/172 个上游测试全部通过。
6. 运行 Conan `test_package` 消费者测试，验证已打包的 `libgumbo.a` 与公开 API。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方源码归档没有 GoogleTest | `third_party/gtest` 是 Git 子模块，tarball 不带子模块内容 | 在 `conandata.yml` 声明并校验官方 GoogleTest `release-1.6.0` 源码，构建时解压到 `gtest/`。 |
| 2 | GoogleTest 1.6.0 找不到 `tr1/tuple` | OHOS libc++ 未提供旧版 libstdc++ TR1 兼容头 | 为上游测试编译添加 `-DGTEST_USE_OWN_TR1_TUPLE=1`，使用 GoogleTest 内置 tuple 实现。 |
| 3 | `autoreconf` 缺少 automake 组件 | CI 环境只有 Autoconf，不含 aclocal/automake/libtoolize | 配方直接编译上游确定的 C 源文件，避免未发布构建工具依赖；上游 GoogleTest 测试仍完整执行。 |
| 4 | Meson 消费测试工具不可用 | CI 环境未安装 Meson | 将 `test_package` 改为直接用 profile 中的 clang 链接 `libgumbo.a`，保留实质 API 测试。 |

## 源码修改

未修改上游 C/C++ 源码或上游测试。配方仅补齐上游声明的 GoogleTest 测试依赖，并使用 clang 直接复现库和测试的编译链接过程。

## 依赖版本

- 运行时/发布库依赖：无，仅使用 libc。
- 测试依赖：GoogleTest `release-1.6.0`，仅在构建时下载，不打包进交付物。

## 验证结果

- 上游 GoogleTest：9 个测试套件、172 个测试，172/172 通过（100%）。
- 消费者测试：1 个测试、5 项实质 API/DOM 断言，1/1 通过（100%）。
- 产物：`lib/libgumbo.a`、`include/gumbo.h`、`include/tag_enum.h`、许可证文件。

## 注意事项

- 交付物为静态库，以避免 OHOS 上的动态链接/RPATH 不确定性。
- `package_info()` 将 CMake 包名/目标声明为 `gumbo` / `gumbo::gumbo`，pkg-config 名声明为 `gumbo`。
- 上游原始 Autotools 构建仍可在工具完整的环境中使用；配方选择直接编译，是为了让现有 OHOS CI 对同一源码与测试集可重复构建。
