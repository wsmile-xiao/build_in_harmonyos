# pd-zexy

Pure Data 的 **zexy** 外部对象集 —— 俗称 Pd 界的"瑞士军刀"：列表/符号/消息处理、
时间与随机数工具、文件与 MIDI 辅助、若干 DSP 类，合计约 90 个对象。

构建基于上游随源码 vendored 的 **pd-lib-builder**（`Makefile.pdlibbuilder` 0.7.0），
89 个 `.c` 链成**单一** `zexy.pd_linux`。

| 项 | 值 |
|----|-----|
| 上游 | <https://github.com/iem-projects/pd-zexy>（主站 `git.iem.at/pd/zexy`） |
| 许可证 | GPL-2.0-or-later |
| 产物 | `lib/pd-externals/zexy.pd_linux` + `share/pd-zexy/`（abs/、reference/、tests/） |
| 依赖 | `puredata/0.54.1`（编译期头集 + test_package 的 Pd 宿主） |

## 版本索引

| 版本 | 状态 | 构建系统 | 补丁 | 说明 |
|------|------|----------|------|------|
| [2.4.4](2.4.4/) | published | Makefile (pd-lib-builder 0.7.0) | 0 | 首个 OHOS 适配版本 |

## 依赖

| 依赖 | 用途 |
|------|------|
| `puredata/0.54.1` | **编译期头集**（`m_pd.h` / `s_stuff.h` / `g_canvas.h` … 位于其 `include/pd`） |
| `puredata/0.54.1` | **test_package**：其 `bin/pd` 作为上游回归套件的宿主（`libpd` 包不含内部头，不可用于编译外部对象） |

## OHOS 适配要点

### 1. 构建（与 pd-vbap 同族）

上游 vendored 的 pd-lib-builder 默认 `CC = $(PLATFORM)-cc`，OHOS 只带 `clang`，
故 make 在**编译任何东西之前**就硬失败（`Makefile.pdlibbuilder:764: Command "cc -dumpmachine"
did not return a target triplet`）。配方显式注入编译器（取自
`tools.build:compiler_executables`，R33）与 Pd 头集：

```
make -j1 CC=<clang> PDINCLUDEDIR=<puredata>/include/pd with-lpt=no
```

### 2. `with-lpt=no`：本版本的关键开关（本库独有）

zexy 通过 `$(CPP)` 探测 `<sys/io.h>` 来决定是否编译并口代码（`src/lpt.c`）。
**OHOS sysroot 装了这个头，但 musl 没有 `ioperm`/`inb`/`outb`** —— 探针假阳性，
x86 专属对象被链进同一个 `zexy.pd_linux`。未定义符号在链接期被放行，直到宿主
`dlopen` 做全量重定位时才爆炸：

```
Error relocating ./zexy.pd_linux: ioperm: symbol not found
```

**单产物库「一坏全坏」**：这一个符号让库里全部约 90 个类不可用 —— 上游 36 项回归
首跑仅 13 通过。加 `with-lpt=no`（→ `-DZ_WANT_LPT=0`）后符号精确归零，
回归变为 **32 PASS / 0 FAIL / 4 XFAIL**。**零补丁**，只用上游自带开关。

### 3. 验证方式

- 符号层：`nm -uD <pkg>/lib/pd-externals/zexy.pd_linux | grep -xE 'ioperm|iopl|inb|outb'` → 0 行；
- 端到端：`test_package/` 用 `puredata` 包的 `bin/pd` 跑**上游全套回归**
  （`tests/testrunner.sh`，36 项），断言 `FAIL == 0` 且 `TOTAL >= 36`。

## 产物布局

```
lib/pd-externals/zexy.pd_linux      # Pd 宿主 dlopen 的插件（非可链接库，cpp_info.libs 为空）
share/pd-zexy/                      # zexy-meta.pd 等根级抽象 + abs/ + reference/ + tests/（上游回归套件）
licenses/LICENSE.txt
```

## 相关技能

本库属于 **pd-lib-builder 外部库** 一族（vbap / iemlib / cyclone / iemnet …），
「构建期注入编译器与头集」的通用方法沉淀在配套 PR 的技能 `skills/pd-externals-ohos/`
（同批提交、尚未合入 main；首见 pd-vbap 适配 PR #14210）；
「平台头探针假阳性 → 单产物库整体不可加载」这一新缺口沉淀为知识条目
`knowledge/drafts/E998-draft-B183-pd-external-unresolved-symbol.md`。
