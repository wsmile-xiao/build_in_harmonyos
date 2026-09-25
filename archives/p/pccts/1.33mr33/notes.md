# pccts 1.33mr33 适配笔记

## 编译环境
- 构建系统: makefile（**非单构建根**，见「编译步骤」）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 / clang++ 15.0.4（`aarch64-unknown-linux-ohos`，OHOS SDK 26.0.0.18）
- 状态: built

## 编译步骤

上游**没有单一构建根**：根 `makefile` 的默认目标 `pccts` 只是一串
`@ (cd ./X; $(MAKE) CC="$(CC)" COPT="$(COPT)")`，真正干活的四个子目录 makefile
**各自硬编码** `CC=cc`、`COPT=-O`（sorcerer 为 `COPT=-g`），且**全树无 configure、
无 install 目标**。故配方 `build()` 自写按依赖序的构建步骤：

| 序 | 子目录 | 产物 | 依赖 |
|---|---|---|---|
| ① | `antlr/` | `bin/antlr` | — （必须最先，后续生成器靠它） |
| ② | `dlg/` | `bin/dlg` | 依赖 ①（`parser.dlg` → `scan.c` 生成） |
| ③ | `sorcerer/`（其 `all` 再递归 `sorcerer/lib`） | `bin/sor` + 支持对象 | 依赖 ①②（`sor.g` → `sor.c`/`parser.dlg`/`scan.c`） |
| ④ | `support/genmk` | `genmk` | 无依赖，最后 `mv` 进 `bin/` |

`bin/` 必须先 `mkdir`（①②③ 都 `mv` 进它）。**注入点是 `COPT`**：四个子目录 makefile
全部把它拼进 `CFLAGS`，是唯一能一次覆盖到 `sorcerer/lib` 的开关。OHOS 无 `cc`/`gcc`
⇒ 必须显式 `CC=clang`（实测默认 `make` 打完 banner 后即因 `cc` 缺失而无产物）。

安装按 Debian `debian/install` 权威参照：4 个可执行 → `bin/`、`h/*.[hc]`+`h/*.cpp` → `include/`、
`sorcerer/h/*.h` 与两个支持源 → `include/sorcerer/`。

关键事实：
- **无硬依赖**：全树无外部 `-l`、无 `pkg-config`、无 `AC_CHECK_LIB`；`conan list -r=ohpcd` rc=0
  （5860 recipes 可达），无需前置包（W0-2 ✅）。
- **无 bootstrap**：`antlr/`、`dlg/`、`sorcerer/` 自带预生成 `.c`/`.dlg`/`tokens.h`，无自举环节。
- **产物形态**：4 个可执行 + `h/` 头（生成的 parser 要 include 它们）；`sorcerer/lib`
  **只编 `.o` 不归档**，上游不产 `.a`/`.so` ⇒ 包内 `cpp_info.libs` 为空属预期，非缺产物。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sorcerer/lib/sorlist.c:35` → `varargs.h:11: error: "Please use <stdarg.h> instead of <varargs.h>"` | 这两文件头部只有 `<stdio.h>`/`<setjmp.h>`，**缺 `#include "pcctscfg.h"`** ⇒ 其中 `#ifdef __STDC__ → #define PCCTS_USE_STDARG` 不生效 ⇒ 掉进 `#else <varargs.h>` 分支；clang 15 shim 直接 `#error`。同目录 `astlib.c`/`sstack.c` 带了该头故正常 | **补 `#include "pcctscfg.h"`**（补丁 0001/0002，与同目录对齐）。配方层 `-DPCCTS_USE_STDARG` 经 `COPT` 注入亦可（探针 E 实测 0 error），但补丁是单文件级根因修复，按「分歧取更严一侧」取补丁 |
| 2 | `h/pccts_iostream.h:7` → `'iostream.h' file not found`（testcpp 多例） | 该头 `#ifdef PCCTS_USE_NAMESPACE_STD` 有保护，但 `pcctscfg.h` **只消费不定义**该宏 ⇒ 走 `#else` 老头分支 | C++ 侧测试统一 `-DPCCTS_USE_NAMESPACE_STD`（探针 G：3/13 → 11/13） |
| 3 | `testcpp/2,3/MyLexer.cpp:8` → `'iostream.h' file not found` | **不经过** `pccts_iostream.h`，直接 `#include <iostream.h>`，宏救不到 | 补丁 0011/0012：`<iostream.h>` → `<iostream>` + `using namespace std;`（文件用 `cerr`） |
| 4 | `testcpp/13/test.cpp:31` → `'stream.h' file not found` | `test.g` 内嵌 `#include <stream.h>`；**全文 0 处流符号使用**，纯冗余 | 补丁 0010：删除该行 |
| 5 | `sorcerer/testcpp` 5 例 → `test.cpp:37: error: a type specifier is required for all declarations` | `.sor`/`main.cpp` 内嵌 K&R 式 `main()` 缺返回类型，C++ 不允许隐式 int；`-fpermissive`/`-std=gnu++98` 均无效（探针 H 实测） | 补丁 0003–0007：`main()` → `int main()` |
| 6 | `support/rexpr` → `static declaration of 'rexpr'/'match' follows non-static declaration` | `rexpr.h` 声明非 static、`rexpr.c` 定义 static；且 `test.c` 需外部调用 `rexpr()` | 补丁 0009：去 `static` |
| 7 | `support/rexpr` → `make: *** [makefile:7: test] Error 127` | makefile 链接行**硬编码 `cc`**，OHOS 无 cc | 补丁 0008：`cc` → `$(CC)` 并补 `CC=cc` 默认值 |
| 8 | 根 `makefile` 默认目标只打 banner、无产物 | 默认目标 `pccts` 是纯 echo 之后才 `cd` 递归；`CC`/`COPT` 不传时子目录各用硬编码默认值 | 配方自写四个子目录的有序构建（见编译步骤表），显式传 `CC`/`COPT` |

## 源码修改

12 个补丁，全部 **portability**（`platform_only: False`，与 Debian 官方 patch 面
`clang.patch`/`gcc-15.patch`/`implicit-declarations.patch`/`copt.patch` 同族），
三处引用一致（`conandata.yml patches:` = `manifest patches_applied:` = `patches/` 实物 = 12）：

| 补丁 | 文件 | 对应问题 |
|---|---|---|
| 0001–0002 | `sorcerer/lib/{sintstack,sorlist}.c` 补 `pcctscfg.h` | 1 |
| 0003–0007 | `sorcerer/testcpp` 5 处 `main()` → `int main()` | 5 |
| 0008 | `support/rexpr/makefile` `cc` → `$(CC)` | 7 |
| 0009 | `support/rexpr/rexpr.c` 去 `static` | 6 |
| 0010 | `testcpp/13/test.g` 删冗余 `<stream.h>` | 4 |
| 0011–0012 | `testcpp/{2,3}/MyLexer.cpp` `<iostream.h>` → `<iostream>` | 3 |

生成方式：修法先在隔离副本逐一探针验证 → 落 `.work` → `track-edit add` 逐文件登记 12 项 →
`refresh-patch --auto`（**tracker 精准模式**，只对追踪文件产补丁，未走 fallback 排除规则）。

## 依赖版本

无外部依赖。工具链 clang/clang++ 15.0.4、GNU Make 4.4.1 —— 均 CI 具备（W0b CI 能力矩阵 ✅）。

## 验证结果

```bash
# 主构建（带 12 补丁，COPT 不带宏）—— 探针 J
make CC=clang COPT="-O2"     # → 0 error；bin/{antlr,dlg,sor,genmk} 全产出

# 四工具真实运行（banner 版本串）
bin/antlr  # Antlr parser generator   Version 1.33MR33
bin/dlg    # dlg  Version 1.33MR33
bin/sor    # Sorcerer - A simple tree-parser generator  Version 13333
bin/genmk  # usage

# 端到端（真实上游 grammar testcpp/1/test.g）
antlr -CC test.g && dlg -C2 -i -CC parser.dlg \
  && clang++ -DPCCTS_USE_NAMESPACE_STD ... -o t   # → t 产出 68096 B
```

上游测试清点与逐项结果见 `reports/test-report.md`。

## 注意事项

- `pcctscfg.h` **只消费** `PCCTS_USE_NAMESPACE_STD`、不主动定义它 ⇒ C++ 侧编译必须显式 `-D`。
- `sorcerer/lib` 只产 `.o`、上游不归档，`cpp_info.libs` 为空是事实不是缺陷。
- 上游 tarball 时间戳 2002-12-12，是「file from the future」类告警的来源，非错误。
- `h/` 内 `.dsp`/`.dsw`/`.bat` 是 MSVC 工程残留，安装时已按扩展名排除。
---

**编译结束**: 2026-09-23 14:22
**最终状态**: built
