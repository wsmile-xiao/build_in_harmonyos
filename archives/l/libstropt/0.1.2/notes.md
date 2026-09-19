# libstropt 0.1.2 适配笔记

## 编译环境

- 目标系统：HarmonyOS 6.0 PC aarch64
- 构建系统：CMake
- 编译器：Clang 15.0.4
- Conan：OHOS 适配版 2.29.1
- 编译日期：2026-09-18
- 状态：built（本地验证通过，未上传）

## 上游与源码完整性

- 官方仓库：https://github.com/rd235/libstropt
- 官方标签：`0.1.2`，commit `e026a7eaf07dc169d8b8365958e7c96e8869848c`
- 官方标签包 SHA256：`49a3f89fd80bd2a4dc3dd60adce84e99d0fb857146d733d6de525ae44c4b2e72`
- Debian 原始源码记录的 `libstropt_0.1.2.orig.tar.gz` 大小与 SHA256 和官方标签包一致。

## 编译步骤

1. `source()` 下载并校验官方 0.1.2 标签包。
2. `apply_conandata_patches()` 应用版本元数据和内存流可移植性补丁。
3. `CMakeToolchain` 生成 HarmonyOS 原生工具链配置。
4. CMake 构建并安装单一未版本化 `libstropt.so`、公开头文件、pkg-config 文件和手册页。
5. Conan `test_package` 编译、链接并运行两个消费者测试程序。

## 适配问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 0.1.2 标签构建出的库和 pkg-config 版本显示为 0.0.1 | 上游 `CMakeLists.txt` 的 `project(VERSION)` 未随标签更新 | 通过自动生成的 `0001-CMakeLists.txt.patch` 修正为 0.1.2 |
| 2 | 真机上 `stropt2buf()` 返回全零空缓冲，消费者测试第 13 项失败 | OHOS musl 的 `fmemopen()`/`open_memstream()` 写路径未产生数据 | `0002-stropt.c.patch` 用两遍长度计算和有界内存写入替代内存流，保持 API 及截断安全性 |
| 3 | 真机构建只有 `libstropt.so` 且 ELF 无 `DT_SONAME` | HarmonyOS 对 CMake 4.1 是未知平台，未定义 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` | 注入 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` 和 `-Wl,-soname,`，避免 HMDFS 版本软链并生成可重定位 SONAME |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：只修正 CMake 项目版本，不引入平台宏，不改变 API 或运行逻辑。
- `patches/0002-stropt.c.patch`：以标准 C 的长度计算、`malloc()` 与有界 `memcpy()` 替代内存流；这是跨 libc 的可移植修复，不引入 `__OHOS__` 平台分支。
- 库解析主体为纯 C/POSIX 实现，在 HarmonyOS musl 上无需平台条件分支。

## 依赖版本

无第三方依赖；仅使用 HarmonyOS libc。CMake、Clang 和 Conan 是构建工具，不作为运行时依赖传播。

## 上游测试账本

- 静态清点：发布包共 14 个文件；无 `tests/`、`test/` 目录，无测试源文件，无 `enable_testing()`、`add_test()`、`TESTS` 或 `check` 目标。
- 动态清点：干净 CMake 配置和构建成功，`ctest -N` 输出 `Total Tests: 0`，`ctest --output-on-failure` 输出 `No tests were found`。
- 上游实测测试数：0；不存在可跳过或可删减的上游测试。

## 新增测试

- `test_libstropt.c`：16 个断言，覆盖 `stropt`、`stroptx`、`stropt2buf`、`stropt2str` 全部公开 API，包括参数、引号、转义、注释、自定义分隔符、空字段、换行标签和删除标签。
- `test_libstropt_ohos.c`：5 个鸿蒙特有断言；编译期强制 `__OHOS__` 与 aarch64，运行期验证 64 位小端 ABI、OHOS musl 解析行为，以及修复后的固定/动态缓冲字符串重建。
- 合计 21 个新增断言，严格不少于上游实测的 0 个测试，且包含独立鸿蒙特有测试。

## 交付物

- `lib/libstropt.so`，真机 ELF SONAME `libstropt.so`（避免 HMDFS 版本软链）
- `include/stropt.h`
- `lib/pkgconfig/stropt.pc`，版本 `0.1.2`
- `share/man/man3/stropt*.3`
- `licenses/COPYING`

## 注意事项

- 本库不是 HarmonyOS 系统同名库，按赛事规则保留上游共享库产物，不创建 `commands.json`。
- 上游没有自动化测试；测试数量按实际清点和执行结果申报为 0，新增测试不冒充上游测试。
- 状态为 `built`，因为本任务明确禁止上传、提交或创建 PR。

---

**编译结束**: 2026-09-18 04:00 UTC
**最终状态**: built
