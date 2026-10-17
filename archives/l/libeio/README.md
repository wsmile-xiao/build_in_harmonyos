# libeio

libeio 是一个基于线程池的异步 I/O 系统调用封装库（libev 作者 Marc Lehmann
出品）。它把 open/read/write/readdir/stat 等 POSIX 文件系统调用封装为异步
请求，由工作线程池执行，应用通过回调 + 事件循环（eio_poll）消费结果。
纯 C 实现，无第三方依赖，核心文件为 eio.c/eio.h（含 ecb.h/xthread.h 内嵌辅助）。

- Homepage: https://github.com/scunningham/libeio
- Upstream: https://github.com/scunningham/libeio (master, MIT license)
- Version: 1.0（configure.ac `AM_INIT_AUTOMAKE(libeio,1.0)`，官方仓库无 release tag）

## OHOS adaptation

- 构建系统 autotools；官方 master tarball 不含预生成 configure，配方以
  tool_requires（automake/1.18 + libtool/2.5.4）+ autoreconf 生成。
- OHOS config.guess 无法识别 HarmonyOS kernel，配方显式传
  `--build/--host=aarch64-unknown-linux-gnu`（ABI 等价 Linux-ELF；
  libeio.m4 无 AC_RUN_IFELSE，不影响运行时检测）。
- patches/0001-ecb.h.patch：C11 下 `ecb_noreturn` 原展开为 `_Noreturn`
  且置于函数声明尾部（`ecb_inline void f(void) ecb_noreturn;`），现代
  clang 要求 `_Noreturn` 前置，改为 `ecb_attribute((__noreturn__))`。
- 产物：libeio.a / libeio.so.1.0.0，链接标志 `-leio`。
- 上游无测试用例（无 tests 目录、无 TESTS/check_PROGRAMS）；核心 API
  已由鸿蒙专项测试（tests/ohos_test.c）与 test_package 消费者用例实跑验证。
