# klibc-dash

klibc 内嵌的 **dash**（Debian Almquist Shell）——klibc 源码树 `usr/dash` 组件的独立打包。

## 这是什么

- 上游工程：**klibc**（minimalistic libc subset for use with initramfs），
  <https://www.kernel.org/pub/linux/libs/klibc/>
- 本包目标：klibc 2.0.14 源码树内 `usr/dash`（内嵌 dash 快照，`usr/dash/README.dash`
  记录同步自 dash.git changeset `46abc8c6d8a5e9a5712bdc1312c0b6960eec65a4`）。
- 版本号口径：`2.0.14` = klibc 发行版本（`usr/klibc/version`），**不是** dash 自己的
  版本号（`usr/dash/config.h` 中 `PACKAGE_VERSION "0.5.7"` 是 kbuild 静态 config.h 的
  历史快照值，不随同步更新）。
- 产物：`bin/sh`，静态自包含（klibc libc 静态链接），已做 OHOS 代码签名（`.codesign`），
  用作 initramfs / 早期用户空间的 POSIX `/bin/sh`。

> 不是 Debian 的 `dash` 包，也不是独立 dash 工程（后者见本仓 `archives/d/dash-shell`）。

## 使用方式

```bash
conan install --requires=klibc-dash/2.0.14 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<同 profile>
# 或
conan require 后在生成的环境中直接使用 bin/sh：
$(conan cache path klibc-dash/2.0.14)/bin/sh -c 'echo hello'
```

`bin/sh` 是**静态** ELF，无运行时库依赖（不依赖 OHOS musl 动态加载器）。

## 依赖

强制第三方依赖 **0 个**：dash 依赖的 klibc libc（`usr/klibc` → `libc.a`）由**同一
tarball** 提供并静态链接（同源树内组件，非独立 Conan 包）。构建期依赖内核 UAPI 头
（由 OHOS SDK sysroot 提供）、clang/llvm-* 工具链与 perl。

## OHOS 适配要点（详见 2.0.14/notes.md）

| # | 问题 | 处理 |
|---|------|------|
| 1 | klibc 无 GNU install，不能 `make install`（E098） | Conan copy 手动打包 |
| 2 | OHOS asm UAPI 头在 `aarch64-linux-ohos/asm`（非 `asm-arm64`），且 HMDFS 符号链接受限 | patch 0001（`KLIBCASMDIR` + `cp -rf`） |
| 3 | OHOS 内核头用 `_KERNEL__NSIG` 而非 `_NSIG` | patch 0002 |
| 4 | HMDFS 不支持硬链接（E079） | patch 0003（共享库 soname `ln`→`cp`） |
| 5 | 根 `Kbuild` 的 `all` 会连带构建 kinit/utils/gzip | patch 0004（只建 scripts/basic + usr/klibc + usr/dash） |
| 6 | `usr/dash/mktokens` 硬编码 `/tmp` 写临时文件，OHOS `/tmp` 只读（E002） | patch 0005（`${TMPDIR:-/tmp}`） |
| 7 | 架构标志不能走 `EXTRA_KLIBCCFLAGS` 命令行变量（会覆盖 dash 的 config.h/配置宏） | 把 `--target=` / `-m <emu>` 写进 `CC` / `LD` 的内容 |
| 8 | OHOS 要求可执行 ELF 带 `.codesign`，否则内核拒绝 exec（E077） | package() 内 `binary-sign-tool -selfSign 1` |
| 9 | 上游 `malloctest3` 在 clang `-Os/-O1/-O2` 下被折叠为必失败（`malloc(0)!=NULL` 假设） | patch 0006：该单文件 `-fno-builtin`（源码/断言不动，保留 -Os） |
| 10 | 上游 `testrand48` 硬编码 `return 1`（打印型样例、无断言） | patch 0007：`return 1` → `return 0`（纳入退出码统计） |

## 上游测试

- `usr/dash` 组件自身**无自动化测试**（无 `tests/` 目录、无注册；dash 的 `tests/` 在
  导入 klibc 时未包含）。
- 上游树内唯一的自动化测试入口是 `make test` → `usr/klibc/tests`（39 个用例，即 dash
  静态链接的 klibc libc 的测试套件），已在配方 `build()` 中构建 + 逐个执行并记录：
  **39/39 通过（100%）、0 失败、0 跳过、无漏测**。
- Debian 打包期 dash 冒烟入口 `usr/dash/static/sh -c "exit"`，已在配方 `build()` 执行（rc=0）。
- 上游用例修改说明（2 处，均在 `usr/klibc/tests/` 测试侧，产品代码未改）：
  ①`malloctest3` 单文件加 `-fno-builtin`（clang `-Os` 把 `malloc(0) != NULL` 折叠为真，
  与 klibc `malloc(0)` 返回 NULL 的语义冲突；反汇编实证 + 退出码对照见 test-report.md §3）；
  ②`testrand48.c` 硬编码 `return 1` → `return 0`（打印型样例、无断言）。
- 覆盖口径：上游每用例有 static/shared 两种形态（78 二进制全部构建成功）；static 39 个
  100% 执行；shared 39 个在 OHOS 上结构性不可执行（PT_INTERP=`/lib/klibc-<hash>.so`，
  `/lib -> /system/lib` 为只读系统分区）。

实测结果与逐项用例清单见 `2.0.14/notes.md` 与 `2.0.14/reports/`。
