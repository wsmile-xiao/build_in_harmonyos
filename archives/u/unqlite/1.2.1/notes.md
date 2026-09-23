# unqlite 1.2.1 适配笔记

## 编译环境

- 构建系统：上游 CMakeLists.txt（静态库 unqlite + install lib/include，要求 CMake >= 3.10）
- 编译日期：2026-09-18
- 编译器：Conan OHOS profile 提供的 clang（clang 15.0.4，target aarch64-unknown-linux-ohos）
- 状态：built

## 版本与源码

上游 tag `1.2.1`（无 `v` 前缀，https://github.com/symisc/unqlite），官方 tarball
`https://github.com/symisc/unqlite/archive/refs/tags/1.2.1.tar.gz`，
SHA256 `3cd5f638cdea014af4879d9ba4f088c92f5cf885051c5ced3dde1ef8a62fac9c`。
tarball 内容：amalgamation `unqlite.c` + `unqlite.h`、分文件源码 `src/`、
顶层 `CMakeLists.txt`、`samples/`（9 个演示程序 + demovfs）、README、
CHANGELOG.md（Release 1.2.1 于 2026-04-30，简化 SyMemBackend 池路径、
CMake 现代化为 >= 3.10、修复 <3.5 兼容）、LICENSE（BSD-2-Clause，
Symisc）。无 Makefile、无 configure、无 tests/ 目录。

## 适配方式

标准 CMake 库配方（与 1.1.9 同型）：`package_type = "library"`，构建上游
静态库 `unqlite`，`cmake.install()` 安装 libunqlite.a 与 unqlite.h；
`cpp_info.libs = ["unqlite"]`，声明 `cmake_file_name=unqlite` /
`cmake_target_name=unqlite::unqlite`。上游仅提供静态库形态（CMakeLists
硬编码 STATIC）：配方声明 shared 选项以满足 Conan library 包规范，并在
validate() 中拒绝 shared=True；fPIC 由选项控制。
1.2.1 的 CMakeLists 因 `include(CTest)` 会在 BUILD_TESTING=ON 时把
samples/ 演示程序注册为 add_test；配方 build 内显式设 BUILD_TESTING=OFF，
避免演示程序（部分依赖数据文件）参与包构建；演示程序的注册情况在
MANIFEST.yml 与双口径台账中如实列出，不作为独立上游用例。
CMake >= 4 需命令行 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（toolchain file
set 太晚），沿 1.1.9 已验证做法保留。

## 上游测试（双口径台账，见最终回报）

- source_declared_total：0（无断言型独立测试用例）。清点证据：tarball 无
  tests/ 目录；CMakeLists 无 add_test 注册到真实测试程序，仅注册 samples/
  演示程序；samples/*.c 全部零断言（grep -c assert == 0），属于 API 演示，
  明确不属于独立上游用例，但逐项列台账。
- CTest 演示注册项（非独立用例）：`unqlite_test_example_1..6`、
  `unqlite_test_example_unqlite_huge`、`_unqlite_mp3`、`_unqlite_tar`、
  `unqlite_test_example_unqlite_demovfs`，共 10 项，逐项列出并标注
  “演示程序，零断言，不计入上游用例”。
- 行为验证由消费者测试承担：test_unqlite.c 驱动真实 KV 引擎
  （unqlite_open(":mem:") → kv_store → kv_fetch 长度与取回 → kv_delete →
  NOTFOUND，6 项断言）+ Jx9 文档存储（unqlite_compile → vm_config 输出
  消费者 → vm_exec → db_create/db_store/db_fetch_all 过滤回调 → 保留
  age>=30 记录，6 项断言），共 12 项全部通过；test_unqlite_ohos.c 磁盘
  文件持久化语义 12 项（创建/写入/commit/关闭/重开读回/删除/重开确认），
  合计 24 项断言全部通过。

## 消费者测试

`test_package/test_unqlite.c`：12 项断言（KV 6 + Jx9 6），编译链接已安装包，通过公开
头文件 unqlite.h/target unqlite::unqlite 使用库，覆盖 KV 引擎与 Jx9 文档
存储两个有业务意义的公开 API 调用路径，全部通过。

## 依赖

无（self-contained ANSI C）。

## 路径判断

候选知识：unqlite 1.2.1 上游版本演进（CMake 现代化 + SyMemBackend 池路径
简化）与 1.1.9 配方兼容。1.1.9 已按路径 A 交付且配方同型；1.2.1 无新增
需要跨库复用的技术增量。知识库扩展路径 B 评估在知识台账与七轴查重中
展开（见最终回报）。
---

**编译结束**: 2026-09-18 03:12
**最终状态**: built
