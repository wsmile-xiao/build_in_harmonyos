# cpdb-libs 1.2.0 适配笔记

## 编译环境

- 构建系统: Autotools（autoreconf 自举自 git-archive 源码包）
- 编译日期: 2026-09-25
- 编译器: HarmonyOS Clang 15.0.4 (aarch64-linux-ohos, via conan profile)
- Conan: 2.29.1 with `os=OHOS`, `os.version=6.0`, `arch=armv8`
- 状态: built

## 编译步骤

1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...`
2. source() 从官方 GitHub archive 下载 v1.2.0（tag v1.2.0 无 dist 资产，只有 git archive，不包含生成 configure）
3. build() 应用 4 个补丁后，用 tool_requires automake/1.18 + libtool/2.5.4 自举 `autoreconf -fi`，再 configure+make+make check
4. 测试: 上游 v1.2.0 无自动化测试（无 tests/ 目录、无 TESTS/check_PROGRAMS、无 ctest），make check 空跑通过；
   消费者 test_package 实际调用公开 API 12 项断言全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 前端库 lib/Makefile.am 链接 `-lcups` 且 frontend_helper.h include `<cups/cups.h>`，cups 不在 ohpcd registry | v1.2.0 仅用 CUPS 的 PWG 介质名表做 `pwg_to_readable`/`readable_to_pwg` 双向转换（只在 `print_option` 调试输出中用到） | 补丁移除 `-lcups` 链接、移除 cups 头 included，两函数改为原样返回输入（passthrough），API 签名不变 |
| 2 | 消费者测试 Signal 11 崩溃 | `get_absolute_path()` 对 `~` 前缀调用 `getpwuid()` 在其返回 NULL（无 passwd 库的沙箱/OHOS 环境）后未判空即解引用 `passwdEnt->pw_dir` | 补丁增加 `passwdEnt` 判空并 fallback 到 `getenv("HOME")`；该函数用于展开 `~/.CPD-print-settings` |
| 3 | git archive 源码包无 configure/Makefile.in | 上游 v1.2.0 未生成 dist tarball，GitHub 自动归档只有 .ac/.am | recipe `build_requirements()` 增加 `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")`（registry 已发布），build() 用 `autogen.sh`/`autoreconf -fi` 自举 |
| 4 | gdbus-codegen 生成接口代码 | SDK 副本 shebang 固定 `/usr/bin/python3` 不可用，且 profile PATH 优先级覆盖 GLib bin | generate() 设 `GDBUS_CODEGEN` 环境变量 = `LD_LIBRARY_PATH= <python> <glib>/bin/gdbus-codegen`（同 2.0-b5 方案），补丁使 Makefile 规则走 `$(GDBUS_CODEGEN)` |
| 5 | config.status 0700 临时目录在 HMDFS 不可写 | Autoconf 生成脚本用 umask 077 创建 0700 confXXXXXX 目录，HMDFS 构建用户无法写入 | generate() 把 TMPDIR/TMP/TEMP 指向 build_folder/tmp（OHOS 分支） |
| 6 | make check 需要显式 shell | Automake 默认经 /bin/bash shebang 执行测试脚本 | 上游 v1.2.0 无测试脚本，make check 空跑；无此问题（2.0-b5 的 LOG_COMPILER 处理不适用于 1.2.0） |

## 源码修改

- `0001-lib-Makefile.am.patch`: 移除 `-lcups` 链接；GDBus 生成规则改为 out-of-source 安全（`$(srcdir)/interface/...`）且代码生成器可覆盖（`$(GDBUS_CODEGEN)`，默认 gdbus-codegen 不变）。
- `0002-lib-frontend_helper.h.patch`: 移除 `#include <cups/cups.h>`。
- `0003-lib-frontend_helper.c.patch`: `pwg_to_readable`/`readable_to_pwg` 改为 passthrough（无 CUPS 表时原样返回输入），函数签名与调用契约不变。
- `0004-lib-common_helper.c.patch`: `get_absolute_path()` 对 `getpwuid()` NULL 返回值判空，失败时 fallback `$HOME`，仍失败返回 NULL。

## 依赖版本

- `glib/2.88.3`（transitive_headers/transitive_libs）
- 构建工具（tool_requires）: `automake/1.18`、`libtool/2.5.4`
- 传递: libffi/3.5.2、pcre2/10.47、proxy-libintl/0.5、zlib/1.3.2
- HarmonyOS 系统库: pthread、m、crypt

## 上游测试清点

| 测试入口 | 类型 | 数量 | 实际结果 |
|----------|------|------|----------|
| (无) | — | 0 | v1.2.0 无 tests/ 目录、Makefile.am 无 TESTS/check_PROGRAMS、无 ctest 注册；demo/ 的 print_frontend.c、pickle_test.c 为样例程序（独立 Makefile，非 automake 测试），make check 为空跑通过 |

`make -n check` 空跑验证无任何测试目标；台账见 reports/knowledge-candidate-ledger.md（C06）。

## 验证结果

```text
Upstream Automake suite: no automated tests declared (0/0)
HarmonyOS consumer test: PASS (12 assertions, real CPDB frontend/settings/public API calls)
Package contents: libcpdb-libs-common, libcpdb-libs-frontend, public headers,
                  pkg-config files
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libcpdb-libs-common.so*` | CPDB 公共库（GLib/GIO/GIOUnix） |
| `lib/libcpdb-libs-frontend.so*` | CPDB 前端库（依赖 common, pthread/m/crypt） |
| `include/` + `include/cpd-interface-headers/` | 公开头文件（backend/frontend interface、common/frontend helper） |
| `lib/pkgconfig/cpdb-libs-{backend,common,frontend}.pc` | pkg-config 元数据 |

## 注意事项

- v1.2.0 的 frontend D-Bus 交互需会话总线；无总线时 `get_new_FrontendObj` 仍可创建对象（connection=NULL），
  但 `connect_to_dbus` 需要真实 session bus 才能真正发现打印后端（与本版本 NOTICE 一致）。
- PWG 介质名可读转换在本适配中为 passthrough（OHOS 无 CUPS 表）；若未来接入 CUPS 后端需恢复对应实现。

## 编译结束

cpdb-libs 1.2.0 的 HarmonyOS/AArch64 构建、上游空测试套件核验、消费端 API 测试、归档门禁均已完成。

**编译结束**: 2026-09-25
**最终状态**: built
