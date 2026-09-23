# cinatra 0.8.9 适配笔记

## 基本信息

- 上游：https://github.com/qicosmos/cinatra（tag 0.8.9，2024-02-23）
- 类型：header-only C++20 HTTP 框架（coro_http_server / coro_http_client / websocket / restful）
- 构建系统：CMake ≥ 3.15（但无 install 规则；上游 CMake 仅用于组织 tests/examples）
- 许可证：Apache-2.0
- 语言预检（R47）：cpp ✅（630 源文件 cpp:628, nodejs:2）

## 官方来源核验（W0）

- tag 0.8.9 存在：`git ls-remote --tags` -> a30136af8a7e5046d4e2d3588ef480db8141dabe
- **GitHub `refs/tags/0.8.9` archive 下载持续 404**（codeload 与 github.com 双路径、多次重试均 404，tag 明明存在）——用 codeload commit-hash URL 替代（`/tar.gz/a30136af...`），内容与 tag 一致，sha256=30d6d65a5b197a69d3e12c1cd092b3f6e9941dbb3886cdc0cb185a433c0502f0
- 上游最新 tag 即 0.8.9（平台任务版本字段 1.8.9 为笔误，taskBranch=feat/cinatra-0.8.9 为准）

## 依赖分析（W0）

| 依赖 | 上游形态 | 适配决策 |
|------|---------|---------|
| asio | vendored include/asio（完整 asio 头） | 随包部署，无需 conan 依赖 |
| async_simple | vendored include/async_simple（qicosmos 同族） | 随包部署，无需 conan 依赖 |
| cmdline | vendored include/cmdline | 随包部署 |
| OpenSSL | 可选（CINATRA_ENABLE_SSL 默认 OFF） | 不启用 |
| zlib | 可选（ENABLE_GZIP 默认 OFF） | 不启用 |
| pthread | 必须 | system_libs |

registry 检查：无外部 conan requires（PF4 依赖闸零依赖通过）。

## 关键适配点

### 1. patches/0001-sched_setaffinity-portable.patch（portability）

`include/cinatra/ylt/coro_io/io_context_pool.hpp` 的 `run()` 在 `#ifdef __linux__`
分支调用 glibc 专有 API `pthread_setaffinity_np(thread, ...)`。OHOS musl：

- 无 `pthread_setaffinity_np`（编译失败：use of undeclared identifier）
- `sched_setaffinity(pthread_native_handle, ...)` 返回 EINVAL（musl pthread_t
  是结构体指针，不是 tid；实测 rc=-1）
- `sched_setaffinity(0, ...)`（0=调用线程自身，POSIX 语义）实测 rc=0 可用

修复（AI review 意见采纳，纯 POSIX 无平台宏）：删除父线程
`pthread_setaffinity_np` 分支，改为 worker 线程函数体内调用
`sched_setaffinity(0, ...)`，对 glibc 与 musl 统一生效——POSIX 语义 0=调用
线程自身，glibc man 文档同样支持。`cpu_affinity_` 默认 false，上游所有
测试/示例均不启用该选项，行为默认不变。首版用 `__OHOS__` 宏区分被 AI review
指出违反 R8（补丁禁止平台条件编译宏），已改为统一 POSIX 实现。

### 2. 上游无 install 规则

上游 CMakeLists.txt 只配置 tests/examples/press_tool，无 `install()`。配方
`package()` 直接 `copy(include/*)` 部署头文件树（保留 vendored asio/async_simple/
cmdline 目录布局，`#include <cinatra/...>` 与 `#include <asio.hpp>` 均可解析）。

### 3. C++20 强制

cinatra 使用 C++20 协程。CI profile cppstd=17，test_package 的 `generate()`
强制 `CMAKE_CXX_STANDARD=20`（async_simple 1.4 同款做法）。gcc 需 `-fcoroutines`
（test_package CMakeLists 已处理），clang 15 C++20 原生支持。

## 测试结果（真实执行，本机=OHOS PC armv8）

上游测试（BUILD_UNIT_TESTS=ON，clang++ 15.0.4 libc++，`-std=c++20`）：

| 目标 | 结果 |
|------|------|
| test_cinatra | 79/79 通过（410 断言） |
| test_corofile | 14/14 通过（103460 断言） |
| test_time_util | 1/1 通过 |
| test_http_parse | 1/1 通过 |
| **合计** | **95/95 全部通过** |

N 口径（上游默认构建注册）：87 TEST_CASE 声明 − 3 DSKIP_TIME_TEST 守卫
（上游宏笔误：CMake 定义的是 SKIP_TIME_TEST，守卫写的是 DSKIP_TIME_TEST，
默认两者都不定义 -> 3 个 time conversion 用例不注册）− 4 CINATRA_ENABLE_SSL
守卫（默认 OFF）− 1 ENABLE_GZIP 守卫（默认 OFF）= 79 注册于 test_cinatra。
单独跑 `--test-case="*inject*"`（INJECT_FOR_HTTP_CLIENT_TEST 定义）也通过。

test_package 消费者测试：coro_http_server 起服 + coro_http_client GET/POST
loopback 往返校验 200/body —— 通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag archive 404 | GitHub archive 服务对该 tag 异常 | codeload commit-hash URL |
| 2 | pthread_setaffinity_np 编译失败 | glibc 专有 API，musl 无 | patch 0001：sched_setaffinity(0,...) 线程内绑定 |
| 3 | 交叉产物无法运行 | 本机即 OHOS，但 ld.so 找不到 libc++_shared.so | LD_LIBRARY_PATH=/system/lib64（scnlib 同款） |
| 4 | doctest 注册数与声明数差 | 宏守卫（SSL/GZIP/DSKIP_TIME_TEST） | 按上游默认构建注册口径如实申报 79+14+1+1=95 |
