# iqueue 2.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: published

## 编译步骤

1. `init-build iqueue 2.2`：官方 tag v2.2 归档（SHA-256 e13d921b…24d3e），双轨解压至 `$TMPDIR/builds/iqueue-2.2.{orig,work}`。
2. `lang-preflight`：detected=c（c↔cpp 兼容族，通过）。
3. 本地编译：`make -j1 makedir iqueue`（仅构建库目标 bin/iqueue.a；上游 `all` 目标含测试二进制，其 malloc_stats 在 OHOS 不可用）。
4. `conan-init` 生成配方，手工改写 conanfile.py 为纯 Makefile 驱动（无 configure 脚本）。
5. `conan-verify`：8 道门禁全部通过（G0-G4 + L2/L4/L5）。
6. 上游测试：补丁后 `make test` 全绿，12/12 独立测试函数、371 断言，退出码 0。
7. 鸿蒙专项测试 test_ohos：多生产者/消费者真实场景，16 项断言全部 PASS。
8. 消费者用例 test_package：new/trysend/tryrecv/delete 公开 API 流程 PASS。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 首次失败：make 找不到 Makefile | basic_layout 下 make 在 build 目录运行，源码在 source_folder | build() 加 `cwd=self.source_folder` |
| 2 | 上游 test 二进制链接失败：undefined malloc_stats | malloc_stats 是 glibc 扩展，OHOS libc（musl 系）无此符号 | 补丁 0001：`#ifdef __linux` → `#if defined(__linux) && defined(__GLIBC__)`，走上游自带回退 |
| 3 | 上游测试挂起（timeout） | new_iqueue((uint32_t)-1) 的 aligned_capacity 为 uint32_t，64 位下左移到 2^32 溢出为 0 死循环 | 补丁 0002：改为 size_t，超大容量返回 EINVAL |
| 4 | 上游测试 test.c:953 断言失败 | clearsignal_iqsignal 返回 uint32_t，64 位下 size_t 循环 i≥2^32 必然不等 | 补丁 0003：循环计数改 uint32_t |
| 5 | test_package CMake 报 Library not found | 上游归档名为 iqueue.a（无 lib 前缀），CMakeDeps 查找 libiqueue.a | package() 用 shutil 复制并重命名为 libiqueue.a |

## 源码修改

- 无（上游源码仅通过 patches/ 最小补丁修正平台可移植性问题，不直接修改）。
---

**编译结束**: 2026-09-23 04:50
**最终状态**: published
