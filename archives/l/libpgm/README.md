# libpgm (OpenPGM)

> OpenPGM — an implementation of the PGM reliable multicast transport protocol (RFC 3208).

## 简介

libpgm（OpenPGM）是 PGM（Pragmatic General Multicast，实用通用组播，RFC 3208）可靠组播
传输协议的 C 语言实现。它为组播（及单播）提供可靠的、有序的、无重复的数据投递，广泛用作
ZeroMQ（`pgm`/`epgm` 传输）等消息中间件的底层可靠组播引擎。

库提供引擎生命周期（`pgm_init`/`pgm_shutdown`）、GSI/TSI 全局源标识与传输源标识、
发送窗口（TXW）/接收窗口（RXW）、速率控制、前向纠错（Reed–Solomon）、定时器、套接字与
网络地址处理等 API，公开头文件位于 `include/pgm-5.3/pgm/`。

## OHOS 适配要点

以下为**跨版本通用**的鸿蒙（OHOS）适配要点（版本特定的构建配置见对应版本目录的
`conanfile.py`，编译过程记录见 `notes.md`）：

- **构建系统为 Autotools，且发布包只带 `configure.ac`/`Makefile.am`**：需先 `autoreconf`
  生成 `configure`；autoconf/automake/libtool 由 Conan `tool_requires` 提供（OHOS worker 无
  系统 automake）。
- **`config.guess` 不识别 `uname -s = HarmonyOS`**：2025 版 GNU config.guess 会退回
  `set_cc_for_build` 探针，其 `umask 077 && mktemp -d` 临时目录在 HMDFS 上不可写 →
  构建期为其补 `*:HarmonyOS:*:*` 分支，产出 `aarch64-unknown-linux-ohos` 三元组，并用
  `sh config.guess` / `sh config.sub` 实跑校验（知识条目 **E007**）。
- **`configure` 的 `umask 077` 临时目录在 HMDFS 上建不出**：`config.status` 阶段
  `mktemp -d ./confXXXXXX` 生成 0700 目录对构建用户不可写 → 构建期将 `umask 077` 放宽为
  `umask 022`（知识条目 **E114**）。
- **Autotools + Conan 的 perl 双体系冲突**：conan autoconf/automake 的 perl 脚本 shebang 硬编码
  各自 perl，与 `PERL5LIB` 的 XS 模块树混用会报 `Perl_my_cxt_init: symbol not found` /
  `Cwd ... handshake mismatch` → `PERL=perl` 让全链走平台 perl，并把 `PERL5LIB` 收敛为
  automake/autoconf 两个**纯 Perl** 模块目录（草稿 **DRAFT-6049**）。
- **libtool 必须经 Conan `conanbuild` env**：conan `libtool` 包通过 `buildenv_info` 注入
  `ACLOCAL_PATH`（含 `libtool.m4`）、`LIBTOOLIZE`、`_lt_pkgdatadir`。缺 `ACLOCAL_PATH` 时
  `autoreconf` 的 autom4te trace 找不到 `AC_PROG_LIBTOOL`（打印 “not using Libtool”）而不调用
  `libtoolize`，随后报 `possibly undefined macro: AC_PROG_LIBTOOL`；缺 `_lt_pkgdatadir` 时
  `libtoolize` 报 `$pkgauxdir is not a directory: '//share/libtool/build-aux'`（知识草稿 **E6502**）。
- **x86 内联汇编需平台守卫**：`cpu.c` 的 `__cpuidex`/`_xgetbv` 只被 `#ifndef _MSC_VER` 包住，
  clang 对未使用的静态函数也校验 asm 约束，在 aarch64 上报 `invalid output constraint '=a'` →
  补丁 0001 将其纳入 `#if defined(__i386__) || defined(__x86_64__)` 守卫（**E016**，无平台宏）。
- **上游单测需 `-DSKB_DEBUG`**：上游 SCons 注册的 libcheck 单测必须与库一起用 `-DSKB_DEBUG`
  编译，否则 `pgm_skb_is_valid(NULL)` 返回 TRUE，`txw_unittest` 会段错误而非按预期 SIGABRT。
- **静态 glib 的 gettext 缺口**：上游单测链接 glib 静态库时，OHOS/musl 无 unprefixed
  `gettext` 入口（制品仓 `libintl.so` 只导出 `libintl_*`/`g_libintl_*` 别名）→ 单测 harness 内置
  C locale 恒等 shim（仅用于单测链接，**不进 libpgm 包**，**E107**）。
- **产物为静态库**：仅依赖 libc（pthread/libm/librt 由 configure 探测），不与系统同名库冲突。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libc（pthread/libm/librt） | 系统 | 运行期唯一依赖，由 `configure` 探测 |
| autoconf | 2.72 | 构建工具（`tool_requires`，提供 `autoreconf`） |
| automake | 1.18 | 构建工具（`tool_requires`） |
| libtool | 2.5.4 | 构建工具（`tool_requires`，提供 `libtoolize` + m4 宏） |
| m4 | 1.4.19 | autoconf 传递依赖 |
| check | 0.15.2 | 仅上游单测（`test_requires`） |
| glib | 2.84.0 | 仅上游单测（`test_requires`，+ libffi/pcre2） |

## 功能验证

```bash
# 通过 Conan 消费者的形式链接静态库并调用公开 API 验证：
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# test_package 调用版本三元组 / pgm_gsi_* / pgm_tsi_* / pgm_init / pgm_shutdown 并断言确定性指纹
```

## 参考

- 上游仓库: <https://github.com/steve-o/openpgm>
- 协议标准: RFC 3208 (PGM Reliable Transport Protocol Specification)
- 许可证: LGPL-2.1-or-later
