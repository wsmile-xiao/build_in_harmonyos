# udns

udns 是 Michael Tokarev 开发的、小型异步/同步（sync/async）stub DNS 解析库 `libudns`。它既能同步解析（类 `gethostbyname`），也能在回调/事件循环模型中异步查询，并原生解析常见 DNS RR 类型（A/AAAA/PTR/MX/TXT/SRV/NAPTR/DNSBL/RHSBL 等），无需应用层手工解析原始 DNS 报文。

## 功能概述

- 同步与异步双接口 DNS stub 解析库
- 原生解析多种 RR 类型，避免引入完整 libresolv / BIND
- 轻量、线程安全、内存分配克制
- `dns_init`/`dns_submit_*`/`dns_resolve_*`/`dns_ioevent` 等完整 API

## OHOS 适配

本适配基于官方 0.6 上游（2024-07-26 发布），在 HarmonyOS PC (aarch64) 上 native 编译 `libudns.a`（静态库），关键适配点（详见 `0.6/notes.md`）：

- **自研 configure**：udns 自带 autoconf 风格 configure 脚本（`configure` + `configure.lib`），**不接受**标准 GNU autoconf 的 `--prefix`/`--host` 等选项，仅支持 `--enable/--disable-ipv6` 与 `--help`；因此不能直接复用 `Autotools(self).configure()`，须手动就地运行 `configure` + `make staticlib`
- **R33**：编译器由 `AutotoolsToolchain` 生成的 conanbuild env 提供（读取 `$CC` 环境变量），`self.run()` 中不裸用 `${CC}` 等 shell 变量
- **无 install 目标 / 无 VPATH**：udns 的 `Makefile` 不含 `install` 目标、`SRCS` 为裸文件名（不支持 out-of-source/VPATH 构建），故就地构建后由 `package()` 手动 stage `libudns.a` 与 `udns.h`
- **无测试套件**：上游源码审计确认无任何自动化测试（无 `check`/`test` 目标、无 `tests/` 目录）；`test_package` 承担消费者视角实质性验证（11 项断言，调用真实 `libudns` API）

## 依赖关系

- **编译依赖**：无（纯 C 库，仅需系统 libc / POSIX socket 接口）
- 示例工具 `dnsget`/`rblcheck`/`ex-rdns` 本适配不打包（保持库级最小产物）

## 参考资料

- 官网: https://www.corpit.ru/mjt/udns.html
- 源码: https://www.corpit.ru/mjt/udns/udns-0.6.tar.gz
- 许可证: LGPL-2.1-or-later
