# libgff 2.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-15
- 编译器: clang/clang++ 15.0.4 (OHOS aarch64, Conan 2.29.1)
- 状态: built

## 编译步骤

上游 CMake 工程（`project(gff)`）无条件构建静态库与手动工具，无 configure/generate 开关需要传参：

```bash
conan create archives/l/libgff/2.0.0 -pr:h=ohos-aarch64
```

配方要点：
- `cmake_layout()` + `CMakeToolchain`/`CMakeDeps`；只注入 `CMAKE_POSITION_INDEPENDENT_CODE`（上游把 `-O3 -Wall -D_FILE_OFFSET_BITS=64` 写死在 CMakeLists 里，不重复追加）。
- 上游 `add_library(${PROJECT_NAME} STATIC ...)` 硬编码 STATIC，故 `package_type = "static-library"`、不暴露 `shared` 选项。
- 打包阶段显式拷贝：`include/`（.h/.hh）、`libgff.a`、`BoostLicense.txt`；不调用 `cmake.install()`（上游 install 规则把 `${CMAKE_INSTALL_PREFIX}` 写进 DESTINATION，且 install 的 cmake config 与 Conan 的 CMakeDeps 重复，无益）。
- `package_info()`: `libs = ["gff"]`（target 名 `gff`，产物 `libgff.a`），Linux/OHOS 补 `m`、`pthread`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 管线 `build` 自动生成的配方是 autotools 模板（`AutotoolsToolchain` + `--enable-static`） | 首稿模板选择未识别 CMake 工程 | 按 2.6 节改为 CMake 配方（`CMakeToolchain` + `cmake_layout`），见 conanfile.py |
| 2 | `conan-init` 生成的 `conandata.yml` sha256 为占位符 `REPLACE_WITH_ACTUAL_SHA256` | 生成器不自动算哈希 | 由官方 tarball 实测填入 `7656b194…a99c`（设备与本机两侧下载同值） |

## 依赖版本

无编译依赖（上游自包含，仅用 libc/libstdc++）。

## 上游测试清点（R51）

- v2.0.0 release tarball 顶层：`.gitignore BoostLicense.txt CMakeLists.txt Readme.md include libgffConfig.cmake.in src`。
- `CMakeLists.txt` 无 `enable_testing()` / `add_test()` 注册项 → 上游静态测试数 **N_static = 0**。
- `src/TestGFFParse.cpp` 为需外部 GFF 输入的手动工具（`Usage: TestGFFParse input`），未注册为测试目标，且 tarball 未随附示例注释数据 → 无法作为上游自动化测试执行。
- 因此本包以真实消费者测试补位（见 `test_package/`）。

## 验证结果

```bash
# 设备侧（OHOS aarch64）
conan create archives/l/libgff/2.0.0 -pr:h=ohos-aarch64
# 消费者测试 test_libgff：解析内联 GFF3（gene/mRNA/exon），
# 断言转录本 ID=tx1、基因 ID=gene1、exon 数=2、属性 ID/Parent 可读 → 全部通过
```

## 注意事项

- 上游 `CMakeLists.txt` 覆盖了 CMake 内建变量 `PROJECT_SOURCE_DIR`（改成 `<src>/src`），调试路径类问题时不要按标准语义理解。
- `-D_FILE_OFFSET_BITS=64` 与 `-O3` 由上游 CMakeLists 硬编码，交叉编译不受影响。
---

**编译结束**: 2026-09-16 00:00
**最终状态**: built
