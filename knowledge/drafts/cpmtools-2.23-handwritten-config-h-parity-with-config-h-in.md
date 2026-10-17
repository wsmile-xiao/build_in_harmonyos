# 手写 config.h 必须与 config.h.in 完全 parity（能力宏与 `#include` 成对）

> Draft: `DRAFT-CPMTOOLS-HANDWRITTEN-CONFIG-H-PARITY-WITH-CONFIG-H-IN`
> Stem: `cpmtools-2.23-handwritten-config-h-parity-with-config-h-in` — 与同 stem 的 `.kv` 成对
> 实例：cpmtools 2.23（PR !9383，首轮 9 个 error 全部源于此）

## 基本信息

- **ID**: DRAFT-CPMTOOLS-HANDWRITTEN-CONFIG-H-PARITY-WITH-CONFIG-H-IN
- **严重度**: 2
- **类别**: conan, autotools, cross-compile, config-h
- **触发工具**: conan
- **阶段**: build

## 错误特征

```
cpmfs.c:722:57: error: use of undeclared identifier 'DISKDEFS'
cpmfs.c:806:38: error: use of undeclared identifier 'LONG_MAX'
cpmfs.c:848:30: error: use of undeclared identifier 'INT_MAX'
cpmfs.c:1546:14: error: use of undeclared identifier 'O_RDONLY'
cpmfs.c:1675:15: error: use of undeclared identifier 'O_WRONLY'
cpmfs.c:2034:6: error: conflicting types for 'cpmUtime'
cpmfs.c:2036:21: error: incomplete definition of type 'struct utimbuf'
9 errors generated.
```

**注意这些符号的共同点**：`O_RDONLY`（fcntl.h）、`LONG_MAX`/`INT_MAX`（limits.h）、
`struct utimbuf`（utime.h）—— 都是"标准 POSIX 头里天经地义存在的东西"。
出现这种组合，几乎可以立刻判定：**该头文件根本没被包含**，而不是"编译器不认"。

## 可复现问题

上游 tarball 里 **没有 `config.h`**（只有 `config.h.in`），而 cpmtools 的
**每个** C 文件第 2 行都是 `#include "config.h"`：

```
cpmchattr.c:2:#include "config.h"
cpmfs.c:2:#include "config.h"
...
device_posix.c:2:#include "config.h"
```

`config.h.in` 的结构是：

```c
#undef HAVE_FCNTL_H
#ifdef HAVE_FCNTL_H
#include <fcntl.h>          /* ← 包含动作在 config.h 内部！ */
#endif

#undef HAVE_LIMITS_H
#ifdef HAVE_LIMITS_H
#include <limits.h>
#endif
/* …每一组都是"宏 + #include"成对… */
```

**第一版手写的 config.h 只写了 `#define HAVE_FCNTL_H 1` 等宏定义，漏掉了配对的
`#include` 块** → 宏确实定义了，但头文件从未被包含 → 上述 9 个 error。

自检一行：

```bash
grep -cE '^#include' config.h      # 为 0 即说明只补了宏、没补 include 块
```

## 根因分析

autoconf 生成的 `config.h` 不是"纯宏开关文件"，而是**宏 + 条件包含的复合体**。
绕过 configure 直编时，很多人的心智模型是"把 `#undef` 换成 `#define` 就行"，
于是漏掉 include 块。由于症状伪装成"上游老代码不兼容 clang 15"，
排查者容易去改源码、加 `-Wno-*`、甚至打补丁——**方向全错**。

实测：补齐 include 块后，cpmtools **零源码改动**直接编译通过。

## 方案（可复用步骤）

1. 列出 `config.h.in` 里全部能力宏（`grep -nE '^(#undef|#define|#ifdef|#include|#endif)' config.h.in`）；
2. 对每个要开启的宏，写**四行**，而不是一行：

   ```c
   #define HAVE_FCNTL_H 1
   #ifdef HAVE_FCNTL_H
   #include <fcntl.h>
   #endif
   ```

3. 把模板尾部的固定片段原样带上（`_POSIX_PATH_MAX` 兜底、`extern char **environ;` 等）；
4. **生成后自检**：`grep -cE '^#include' config.h` 必须 > 0；
5. 上游通过 `CPPFLAGS` 注入的**字符串字面量宏**（`-DDISKDEFS=\"$(DISKDEFS)\"`、
   `-DFORMAT=\"$(DEFFORMAT)\"`）**也放进 config.h** —— 既省去跨 shell 引号转义
   （cmd.exe 与 POSIX sh 行为不同），又保证所有 TU 一致可见。

参考实现：`archives/c/cpmtools/2.23/conanfile.py` 的 `CONFIG_H` 常量
（6 组成对 include + `DISKDEFS`/`FORMAT` 定义）。

## 同类陷阱（本包一并命中，可作对照）

同一个包里的**可选依赖探测静默跳过**：`configure.in` 用
`AC_CHECK_LIB(curses/ncurses, printw, FSED_CPM=fsed.cpm …)` 决定是否构建第 8 个工具，
探测失败时 `FSED_CPM` 置空、`Makefile` 的 `ALL` 里**静默少一个产物**，
configure 不报错不警告。直编时若既不提供依赖、也不声明缺口，就会得到
"CI 全绿但产物静默缩水"的假完整。本包选择**显式声明缺口**（交付 7 个核心工具，
`fsed.cpm` 不构建），并在 conanfile 顶部、notes.md、MANIFEST.yml、PR 正文四处写明。

## 边界与查重

- **E392**（raw makefile 配方三陷阱：BadZipFile / compiler_executables / make cwd）：
  均不涉及 config.h。
- **E532**（上游 CMake `if(WIN32) elseif(UNIX) else()` 不识别 HarmonyOS）：
  讲的是 CMake 平台分支，与本条的 autoconf config.h 无关。
- 正式库以 `config.h.in` / `HAVE_FCNTL_H` / `O_RDONLY.*undeclared` 检索无相关条目。

## 关联

- 配方 PR：**!9383**（cpmtools 2.23 适配 HarmonyOS PC，分支 `feat/cpmtools-2.23`）
- 平台任务：#6865（cpmtools 2.23）
- 本 Issue 与 PR 双向关联；草稿经主编审核后由 promote 流程转入正式知识库。
