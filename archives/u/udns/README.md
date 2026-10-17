# udns

udns 是 Michael Tokarev 开发的、小型异步/同步（sync/async）stub DNS 解析库 `libudns`。它既能同步解析（类 `gethostbyname`），也能在回调/事件循环模型中异步查询，并原生解析常见 DNS RR 类型（A/AAAA/PTR/MX/TXT/SRV/NAPTR/DNSBL/RHSBL 等），无需应用层手工解析原始 DNS 报文。

## 功能概述

- 同步与异步双接口 DNS stub 解析库
- 原生解析多种 RR 类型，避免引入完整 libresolv / BIND
- 轻量、线程安全、内存分配克制
- `dns_init`/`dns_submit_*`/`dns_resolve_*`/`dns_ioevent` 等完整 API

## OHOS 适配

本目录覆盖两个已适配版本：

| 版本 | 上游发布 | 状态 | 核心适配点 |
|------|----------|------|-----------|
| 0.5 | 2024-03-09 | built | **需打补丁修复上游 configure 的 inet_pton()/inet_ntop() 探测原型错误**，否则库符号表与自身头文件不一致、消费者 100% 链接失败（详见 `0.5/notes.md`） |
| 0.6 | 2024-07-26 | built | 上游已自行修好上述探测，无需补丁 |

### 0.5（2024-03-09）

- **★ 必须打补丁**：`configure` 判断 libc 是否提供 `inet_pton()`/`inet_ntop()` 的探测程序原型写错（把 `long *` 传给 `inet_pton()` 的 `const char *` 形参，又把 `inet_ntop()` 的 `const char *` 返回值当成 `int main()` 的返回值）。clang 对此报**硬错误**，探测必然失败，而 configure 退出码仍为 0，只在 config.h 里悄悄不写 `HAVE_INET_PTON_NTOP`。`udns_XtoX.c` 因此走入 `#define inet_XtoX_prefix udns_` 回退分支，产出 `udns_ntop()`/`udns_pton()`，而 `udns.h` 声明、库内部 `udns_resolver.c` 调用的都是 `dns_ntop()`/`dns_pton()` —— `libudns.a` 与其随包头文件符号不匹配，**任何消费者链接都必然失败**（`undefined symbol: dns_pton / dns_ntop`）。修复见 `0.5/patches/0001-configure-fix-inet_pton-inet_ntop-probe-prototypes.patch`（回移上游 0.6 的修正探测体）。反向证伪：移除该补丁后 `conan create` 立即以同样的 undefined symbol 失败。
- **0.5 与 0.6 的真实 API 差异**（消费者代码需注意）：`dns_dntop()` 在 0.5 返回 `int`（0.6 返回 `const char *`）；`dns_ntop()` 末参数 0.5 为 `int`（0.6 为 `unsigned`）；`dns_free()` 在 0.5 只接受 `ctx` 且断言 `ctx != NULL && ctx != &dns_defctx`，**不能**用 `dns_free(NULL)`，默认上下文的结果须由 `dns_close(NULL)` 回收（0.6 才扩展为 `dns_free(ctx, result)`）。
- 其余构建要点与 0.6 相同（自研 configure、就地构建、手动打包）。
- 测试：三层共 21 项断言（12 + 8 + 1，层 3 为端到端 pass/fail 门计 1 项），全部真实执行通过；
- 上游源码（0.5，本适配对象。0.6 已在上游修掉本适配器所依赖的 configure 探测缺陷，两者不可互相替代）：
  https://www.corpit.ru/mjt/udns/udns-0.5.tar.gz
  真机 DAYU200（OpenHarmony 6.0.0.47, aarch64）三层亦全部通过，含 rule12「本地 DNS 应答器端到端回环」（设备无外网，用例自带应答器使链路确定性可验，反向证伪：破坏应答 RDATA 后正确判失败并退出码 1）。详见 `0.5/notes.md`。

### 0.6（2024-07-26）

在 HarmonyOS PC (aarch64) 上 native 编译 `libudns.a`（静态库），关键适配点（详见 `0.6/notes.md`）：

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
