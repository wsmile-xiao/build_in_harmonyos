# PCCTS 1.33mr33：2002 年非单构建根 makefile 工具集在 OHOS/clang15 的四个独立故障点

> Draft: DRAFT-E679-NON-ROOT-MMAKE-VARGARGS-PORTABILITY
> Stem: `E679-draft-PCCTS` — pairs with the same-stem `.kv`
> 软件/版本：pccts 1.33mr33（分支 `feat/pccts-1.33mr33`）

## 基本信息

- **ID**: DRAFT-E679-NON-ROOT-MMAKE-VARGARGS-PORTABILITY
- **严重度**: 2
- **类别**: portability|toolchain|build-system
- **触发工具**: make|clang|clang++
- **阶段**: compilation|link

## 错误特征

编译期（四个**互相独立**的故障点，混看会误判成「工具链不可用」）：

```
# ① CC 硬编码（OHOS 无 cc）——原样 make 打完 banner 就没有产物
make: *** [makefile:7: test] Error 127
/data/service/hnp/bin/clang: error: no such file or directory: 'cc'

# ② 单文件缺 pcctscfg.h → 掉进 <varargs.h> 分支
In file included from sorlist.c:35:
.../clang/15.0.4/include/varargs.h:11:4: error: "Please use <stdarg.h> instead of <varargs.h>"

# ③ 老式 C++ 头（宏保护救不到的两处）
MyLexer.cpp:8:10: fatal error: 'iostream.h' file not found
test.cpp:31:10:  fatal error: 'stream.h' file not found

# ④ K&R 习惯 + 静态性冲突（在 C++ 下炸）
test.cpp:37:1: error: a type specifier is required for all declarations   # main() 缺返回类型
rexpr.c:122:12: error: static declaration of 'rexpr' follows non-static declaration
```

## 为什么不是孤立 bug

四个点分别落在**构建系统结构**、**单文件 include 顺序**、**宏保护覆盖范围**、**语言标准演进**四个层面，
任一层的修法都不能覆盖其余三层；而它们同时出现在**所有 1995–2002 年间、无 configure 的多子目录
makefile 工具集**移植 OHOS 的场景里——这是一类可预检的组合故障，不是单点补丁。

## 根因逐条

### ① 非单构建根 + CC/COPT 硬编码

上游**没有单一构建根**：根 `makefile` 默认目标 `pccts` 只是一串
`@ (cd ./X; $(MAKE) CC="$(CC)" COPT="$(COPT)")`，真正干活的四个子目录 makefile
**各自硬编码** `CC=cc`、`COPT=-O`（sorcerer 是 `COPT=-g`），且**全树无 configure、无 install**。
OHOS 只有 `clang`/`clang++`，`cc`/`gcc` 均不存在 ⇒ 原样 `make` 打完 banner 即无产物，
子目录 `cc ...` 直接 `Error 127`。

依赖顺序必须自己读出来（`bin/` 要先 `mkdir`，①②③ 都 `mv` 进它）：

| 序 | 子目录 | 产物 | 依赖 |
|---|---|---|---|
| ① | `antlr/` | `bin/antlr` | — （生成器，必须最先） |
| ② | `dlg/` | `bin/dlg` | 依赖 ①（`parser.dlg` → `scan.c`） |
| ③ | `sorcerer/` → `sorcerer/lib` | `bin/sor` + 支持对象 | 依赖 ①②（`sor.g` → `sor.c`/`parser.dlg`/`scan.c`） |
| ④ | `support/genmk` | `genmk` | 无依赖，最后手工 `mv` 进 `bin/` |

**注入点是 `COPT`**：四个子目录 makefile 全部把它拼进 `CFLAGS`，是唯一能一次覆盖
`sorcerer/lib` 的开关（`CC` 命令行传即可）。

### ② 单文件缺 `pcctscfg.h`（本条最高价值）

`sorcerer/lib/{sorlist,sintstack}.c` 头部只有 `<stdio.h>`/`<setjmp.h>`，
**缺 `#include "pcctscfg.h"`**——而 `PCCTS_USE_STDARG` 正是由 `pcctscfg.h` 在
`__STDC__` / `__USE_PROTOS` / `__cplusplus` 三条件下定义的。缺头即掉进
`#else <varargs.h>` 分支，clang 15 的 `varargs.h` 是 shim，直接 `#error`。

对照证据：**同目录 `astlib.c`/`sstack.c` 带了该头故编译正常** ⇒ 这是
**单文件级 include 缺失，不是全局配置问题**。两条等价修法：

- 补一行 `#include "pcctscfg.h"`（与同目录对齐，本任务取此，走 refresh-patch）；
- 或配方层 `COPT` 注入 `-DPCCTS_USE_STDARG`（实测同样 0 error）。

> 判据：看到 `varargs.h` 的 `#error` **不要**去改编译标准或关 warning——
> 先查该文件是否 include 了 `pcctscfg.h`，与同目录兄弟文件对照即可 30 秒定位。

### ③ `PCCTS_USE_NAMESPACE_STD` 只被消费、不被定义

`h/pccts_iostream.h` 有 `#ifdef PCCTS_USE_NAMESPACE_STD` 保护，但 `pcctscfg.h`
**只 `#ifdef` 它、从不 `#define` 它** ⇒ C++ 侧必须显式 `-D`。
而 `testcpp/{2,3}/MyLexer.cpp` **绕过该头**直接 `#include <iostream.h>`、
`testcpp/13/test.g` 内嵌 `#include <stream.h>`（该内嵌 main 全文 **0 处流符号使用**，纯冗余）——
**宏救不到，只能补丁**。

实测：加 `-DPCCTS_USE_NAMESPACE_STD` 使 testcpp 由 **3/13 → 11/13**，余下 3 例才需补丁。

### ④ K&R 与静态性冲突（两分支都要改）

- `sorcerer/testcpp` 五处内嵌 `main()` 缺返回类型 → `a type specifier is required`，
  **`-fpermissive` / `-std=gnu++98` 均无效**（clang 不再允许隐式 int）。
- `support/rexpr`：`rexpr.h` 非 static 声明 vs `rexpr.c` static 定义。
  ⚠️ **`#ifdef __USE_PROTOS` 与 `#else` 两个分支都必须改**——`rexpr.c` 不 include
  `pcctscfg.h` 故 `__USE_PROTOS` 未定义、实际走 `#else` K&R 分支；只改一支实测仍报同样错误。

## 推广价值

- 凡「根 makefile 只做 cd 递归 + 子目录硬编码 CC/COPT + 无 configure/install」的工具集
  （PCCTS 家族 antlr/dlg/sorcerer/genmk 及其派生项目），配方一律自写按依赖序的构建步骤。
- 安装无现成目标时，按上游发行版 `debian/install` 口径手工 copy 是权威参照
  （本任务据此确定：4 可执行 → `bin/`、`h/*.[hc]`+`h/*.cpp` → `include/`、
  `sorcerer/h/*.h` → `include/sorcerer/`，排除 `.dsp/.dsw/.bat` IDE 残留）。
- 上游 `sorcerer/lib` **只编 `.o` 不归档** ⇒ 包内 `cpp_info.libs` 为空是**预期**，不是缺产物。

## 复现命令（设备可直接执行）

```sh
. "$HOME/tmp/pccts-1.33mr33/env.sh"
W="$WORKSPACE_ROOT/tmp/builds/pccts-1.33mr33.work"
O="$WORKSPACE_ROOT/tmp/builds/pccts-1.33mr33.orig"

# 1) 主构建（带补丁、COPT 不带宏）→ 应 0 error 且 4 产物
make -C "$W" CC=clang COPT='-O2' -j1 && ls "$W"/bin/{antlr,dlg,sor,genmk}

# 2) 编辑数自证：等于人工登记的编辑数即干净；多出的即被重新生成的产物
diff -rq "$O" "$W" | grep '^Files' | wc -l        # 期望 12

# 3) 只有这一步证明「补丁是根因修复」：带 12 补丁、不注入任何宏仍 0 error
```

⚠️ **跑完上游测试后必须执行第 2 步**：`test4/SimpleTreeParser.cpp`、`test7/stdpccts.h`
这类文件在 `.orig` **存在**但会被 antlr/sor **重新生成**，若不 `cp` 自 `.orig` 恢复，
`refresh-patch --auto` 会把它们当编辑 → 补丁数由 12 漂到 14 → 编号整体后移
→ **`conandata.yml` 的 `patch_file` 引用错位**（原 `0009-rexpr` 变成指向别人的文件名），
配方随即不可构建。同理：**`pr.diff` 为 0 字节时** `junk_check` 的 `-s` 判据不成立，
退化为全仓扫描，JC6 会把上游主线几百个包误判成本 PR ⇒ 必须**先 commit 再 finish**。

## 关联

- 配方：`archives/p/pccts/1.33mr33/{conanfile.py,conandata.yml,manifest.yaml,notes.md}`
- 补丁：`archives/p/pccts/1.33mr33/patches/0001`–`0012`（均 `portability`、`platform_only: False`）
- 上游测试证据：`archives/p/pccts/1.33mr33/reports/test-report.md`（26 例，24 通过）
- 权威参照：Debian `pccts_1.33MR33-6.6` 的 `debian/rules` 与 5 个 patch（同族端口性问题）
