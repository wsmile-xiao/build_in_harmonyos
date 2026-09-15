# unqlite 1.1.9 适配笔记

## 编译环境

- 构建系统：上游 CMakeLists.txt（静态库 unqlite + install lib/include）
- 编译日期：2026-09-12
- 编译器：Conan OHOS profile 提供的 clang
- 状态：built

## 版本与源码

上游 tag v1.1.9（https://github.com/symisc/unqlite），官方 tarball
`https://github.com/symisc/unqlite/archive/refs/tags/v1.1.9.tar.gz`，
SHA256 `33d5b5e7b2ca223942e77d31112d2e20512bc507808414451c8a98a7be5e15c0`。
tarball 内容：amalgamation `unqlite.c`（1.95MB）+ `unqlite.h`、分文件源码
`src/`、顶层 `CMakeLists.txt`、`example/`（10 个演示程序）、README、LICENSE
（BSD-2-Clause，Symisc）。无 Makefile、无 configure、无测试目录。

## 适配方式

标准 CMake 库配方：`package_type = "library"`，构建上游静态库 `unqlite`，
`cmake.install()` 安装 libunqlite.a 与 unqlite.h；`cpp_info.libs =
["unqlite"]`，声明 `cmake_file_name=unqlite` /
`cmake_target_name=unqlite::unqlite`。上游仅提供静态库形态（CMakeLists 硬编码 STATIC）：配方声明 shared
选项以满足 Conan library 包规范，并在 validate() 中拒绝 shared=True；
fPIC 由选项控制，供下游链接需要。

## 上游测试（四维账本）

- N_static：0。清点证据：tarball 内无 Makefile（无 check/test 目标）、无
  tests/ 目录、CMakeLists.txt 无 add_test/enable_testing、源码树无断言型
  测试程序；`example/` 的 10 个程序（含 demovfs）为 API 演示，无断言型测试逻辑
  （demovfs 仅含内部防御性 assert 守卫），不属于测试边界。上游 CI 配置
  （.travis.yml/.gitlab-ci.yml）仅做编译验证，无测试消费。
- N_registered / N_executed：0（上游无测试可执行）。
- 未执行/跳过：0。
- 行为验证由消费者测试承担：test_unqlite.c 驱动真实 KV 引擎
  （unqlite_open(":mem:") → kv_store → kv_fetch 长度与取回 → kv_delete →
  NOTFOUND），6 项断言全部通过。

## 消费者测试

`test_package/test_unqlite.c`：6 项断言（打开内存库、写入、长度查询、
取回值逐字节比对、删除、删除后 NOTFOUND），全部通过。

## 依赖

无（self-contained ANSI C）。

## 路径 B 判断

判断依据（按 AGENTS §6.2 要求记录）：候选知识主题为"无测试套件库的
消费者行为验证模式"。查重：知识库 E257/E321/E322/E470 覆盖 header-only
配方；无测试库以消费者测试补验证是仓库通行做法（TEST_QUALITY_SPEC 载明），
不构成跨仓库复用的新知识增量。结论：**不走路径 B**，按纯路径 A 交付。
