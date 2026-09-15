# 路径 B 知识库扩展申请：手写 config.h 必须与 config.h.in 完全 parity，并显式处理可选依赖探测

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#6865 cpmtools 2.23
- **关联 PR**：`!9383`（`feat/cpmtools-2.23`，配方 PR）
- **知识草稿**：`knowledge/drafts/cpmtools-2.23-handwritten-config-h-parity-with-config-h-in.kv` / `.md`
- **草稿 ID**：`DRAFT-CPMTOOLS-HANDWRITTEN-CONFIG-H-PARITY-WITH-CONFIG-H-IN`
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/cpmtools-2.23`）提交
- **申请日期**：2026-09-10

## 一、为什么这是"可跨仓库复用的知识"

本仓库大量包的上游是 autotools 项目，而 tarball **普遍只带 `config.h.in` 不带
`config.h`**，同时几乎每个 C 文件都会 `#include "config.h"`。因此"绕过 configure
直编"时**每个人都得手写一次 config.h** —— 而绝大多数人的第一版都会漏掉配对的
`#include` 块，得到 9 个"看起来像源码不兼容 clang"的错误，进而朝错误方向排查。
本条给出**一行判据**（错误符号是否集中在标准 POSIX 头的东西上 / `grep -cE '^#include' config.h`）
与**四行式写法**，可直接被后续任何同类配方套用；并附一个同源陷阱（可选依赖探测静默跳过）。

## 二、症状与最小复现

```
cpmfs.c:806:38: error: use of undeclared identifier 'LONG_MAX'
cpmfs.c:1546:14: error: use of undeclared identifier 'O_RDONLY'
cpmfs.c:2036:21: error: incomplete definition of type 'struct utimbuf'
cpmfs.c:2034:6: error: conflicting types for 'cpmUtime'
9 errors generated.
```

`O_RDONLY`（fcntl.h）、`LONG_MAX`（limits.h）、`struct utimbuf`（utime.h）—— 全是
标准 POSIX 头里天经地义存在的东西。**出现这种组合就是"头文件没进来"**。

根因：`config.h.in` 里宏与 `#include` 是**成对**的：

```c
#undef HAVE_FCNTL_H
#ifdef HAVE_FCNTL_H
#include <fcntl.h>          /* ← 包含动作在 config.h 内部 */
#endif
```

第一版手写 config.h 只补了 `#define HAVE_FCNTL_H 1`，**漏了配对的 include 块**。

自检：`grep -cE '^#include' config.h` → 为 0 即命中本条。

## 三、方案（可复用）

对每个要开启的能力宏写**四行**（而不是一行）：

```c
#define HAVE_FCNTL_H 1
#ifdef HAVE_FCNTL_H
#include <fcntl.h>
#endif
```

- 带上 `config.h.in` 尾部的固定片段（`_POSIX_PATH_MAX` 兜底、`extern char **environ;`）；
- 生成后自检 include 行数 > 0；
- 上游 `CPPFLAGS` 里的**字符串字面量宏**（`-DDISKDEFS=\"…\"`、`-DFORMAT=\"…\"`）
  一并写进 config.h —— 规避 cmd.exe 与 POSIX sh 的引号差异，且保证所有 TU 一致可见。

补齐后 cpmtools **零源码改动**直接编译通过。

## 四、同源陷阱：可选依赖探测的静默跳过（本包一并命中）

`configure.in`：

```m4
dnl Check for curses. If not found, don't build fsed.cpm
AC_CHECK_LIB(curses, printw, FSED_CPM=fsed.cpm LIBS="-lcurses $LIBS", FSED_CPM=)
```

`Makefile.in`：`ALL = cpmls … fsck.cpm $(FSED_CPM)`

探测失败 → `FSED_CPM` 置空 → **ALL 里静默少一个产物**，configure 不报错不警告。
直编时必须**显式决定**：

| 方案 | 结果 |
|---|---|
| 提供依赖（`requires = "ncurses/6.6"`，制品仓已发布） | 8 个工具全交付 |
| 不提供但**显式声明缺口** | 7 个核心工具（**本包选择**） |
| 不提供也**不声明** | CI 全绿但产物静默缩水 —— 「假完整」，禁止 |

本包交付 **7 个核心工具**（`cpmls` `cpmrm` `cpmcp` `cpmchmod` `cpmchattr`
`mkfs.cpm` `fsck.cpm`），**不含 `fsed.cpm`**（交互式全屏编辑器，需 ncurses）。
该缺口已在 `conanfile.py` 顶部、`notes.md`、`MANIFEST.yml`、PR 正文四处显式声明，
并给出补齐路径（打开 `requires` + config.h 追加两个宏 + 注入 ncurses 头/库路径）。

## 五、验证证据

| 项 | 证据 |
|---|---|
| 首轮失败 | `conan create`：9 个 error，全部为 `undeclared` / `incomplete type` / `conflicting types` |
| 修复后 | 补齐 include 块后 **退出码 0**、`Package created`、test_package 编译通过，**源码零改动** |
| 产物 | 7 个工具均为 ELF64/AArch64，NEEDED 仅 libc.so（未引入 ncurses） |
| 自检命令 | `grep -cE '^#include' config.h` > 0 |

## 六、查重声明

- **E392**（raw makefile 三陷阱：BadZipFile / compiler_executables / make cwd）：不涉及 config.h。
- **E532**（CMake `if(WIN32)/elseif(UNIX)/else()` 不识别 HarmonyOS）：CMake 平台分支，与本条无关。
- 正式库以 `config.h.in` / `HAVE_FCNTL_H` / `O_RDONLY undeclared` 检索无相关条目。

## 七、请评审确认

1. 是否认可本条目为**路径 B（贡献创新，10 分候选）**评审对象？
2. 「可选依赖探测静默跳过」是否建议纳入 `docs/ADAPTATION_GUIDE.md`，并要求
   所有直编配方在 notes.md 中**显式列出与上游 Makefile/configure 的产物集合差异**？
3. 本包选择"不提供 ncurses、显式声明缺口"是否被认可为合规处置（而非"少构建一个工具"）？
   若评审倾向于必须补齐 `fsed.cpm`，我们可按 notes.md 给出的路径补一轮。
