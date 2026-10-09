# 测试报告 — reflex 20241231

> **项目**: reflex（REFLEX — Thomas Dickey 维护的 flex 2.5.4 分支）
> **测试日期**: 2026-09-29
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64（clang 15 / OHOS SDK 26.0.0.18）
> **测试类型**: 官方测试套件（`make check` 自举回归）+ 消费者端到端功能测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 8 | 100% |
| 通过 (PASS) | 8 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

> 口径：上游 `make check` 1 条自举断言（实测在默认模式下执行 1 次，另在 6 种表压缩模式下
> 复扫 6 次，全部通过）+ 消费者视角 7 条端到端断言。

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。生成器本体（`bin/reflex`、`bin/reflex++`）、C 运行时库（`lib/librefl.a`）、
C++ 头文件（`include/reFlexLexer.h`）与手册页全部可用；C 与 C++ 两条消费者链路
（生成 → 编译 → 链接 → 运行 → 断言词法流）均实测通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游 C++ 骨架守卫错位（`yy_init_globals`/`yylex_destroy` 落在 non-C++ 区之外） | `reflex++` 生成的全部 C++ 扫描器无法编译 | 🔴 已由补丁 0001 修复 |
| 发布包 `skel.c` 与 `flex.skl` 内容不一致而 mtime 相同 | 补丁落点若选错（`flex.skl`）会导致 `make check` 失败 | 🟡 已由补丁落点 + `os.utime` 修复 |
| 上游 `bigcheck` 首项裸 `-C` 不可用 | 上游目标本身失败，非本包引入 | 🟢 已在 manifest/notes 记录并排除 |
| CI worker 上 `config.status` 对自建临时目录写入 EACCES（TMPDIR 落在 HMDFS） | 间歇竞态：本地四道门禁全绿；同一代码一次失败（#65023）一次通过（#65046） | 🔴 已由补丁 0002 + `_pin_tmpdir()` 从根因修复 |

### 2.3 可用功能清单

```
✅ reflex            — C 扫描器生成器（版本 2.5.4 / 20241231）
✅ reflex++          — C++ 模式入口（安装期创建的符号链接已随包发布）
✅ lib/librefl.a     — C 运行时静态库（提供 main() 与 yywrap()，导出符号已用 llvm-nm 实证）
✅ include/reFlexLexer.h — C++ 基类声明（FlexLexer / yyFlexLexer）
✅ share/man/man1/reflex.1 — 上游手册页
⚠️ make bigcheck     — 上游目标本身失败（裸 -C 选项解析缺陷），已改用 6 种压缩模式复扫替代
```

### 2.4 已知限制

1. C++ 消费者必须以 stdout 形式调用（`reflex++ -t foo.l > foo.cc`）；`-o` 形式会丢失
   `#include <reFlexLexer.h>` 序言行（上游行为，非本包引入）。
2. `make check` 是「自举回归」（证明生成器能稳定复现自己的扫描器），并不覆盖消费者可用性；
   消费者可用性由本包新增的 7 条端到端断言覆盖。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| 上游 `make check`（自举回归） | 用刚构建的生成器重新生成 `scan.l` → `scan.c`，与发布包 `initscan.c` 逐字节比对 | ✅ PASS |
| 上游 `make COMPRESSION=<m> check` × 6 | `-Ce` / `-Cm` / `-f` / `-Cfea` / `-CFer` / `-l` 六种表压缩模式下重复自举回归 | ✅ PASS ×6 |
| T1 `version` | `reflex --version` 同时含 `2.5.4`（谱系）与 `20241231`（补丁级） | ✅ PASS |
| T2 `cxx-version` | `reflex++ --version` 可用（安装期符号链接随包发布） | ✅ PASS |
| T3 `header` | `include/reFlexLexer.h` 同时声明 `FlexLexer` 与 `yyFlexLexer` | ✅ PASS |
| T4 `library` | `lib/librefl.a` 为合法 ar 归档（`!<arch>` 魔数）且导出 `yywrap` | ✅ PASS |
| T5 `manpage` | `share/man/man1/reflex.1` 已安装且非空 | ✅ PASS |
| T6 `c-scanner`（端到端） | `reflex` 生成 C 扫描器 → `clang -I inc src -L lib -lrefl` 编译链接 → 运行 → 断言 `NUM:42,ID:alpha,NUM:7,ID:_b9` | ✅ PASS |
| T7 `cxx-scanner`（端到端） | `reflex++ -t` 生成 C++ 扫描器（首行 `#include <reFlexLexer.h>`）→ `clang++ -std=c++17 … -lrefl` → 运行 → 断言同一词法流 | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| `make bigcheck`（首项裸 `-C`） | 上游本版选项解析器会把紧随裸 `-C` 的独立参数当作压缩后缀，报 `./flex: unknown -C option '/'`；属上游缺陷，非平台相关。已用其余 6 种模式替代复扫，并在 `test_package/MANIFEST.yml` 记录 |

---

## 四、关键问题分析

### 问题1: 生成的 C++ 扫描器全部无法编译（上游骨架守卫错位）

**现象**：
```
use of undeclared identifier 'yy_current_buffer'
use of undeclared identifier 'yy_c_buf_p'
use of undeclared identifier 'yy_init'
use of undeclared identifier 'yy_start'
use of undeclared identifier 'yyin'
use of undeclared identifier 'yyout'
（共 10 处，编译器另误建议 yy_nxt）
```

**根因分析**：
骨架数组把 C-only 的 `static int yy_init_globals(void)` 与 `int yylex_destroy(void)`
排在 non-C++ 守卫区块（骨架标记 `%-` … `%*`）**之外**。C++ 模式下这些全局名是
`yyFlexLexer` 的成员，文件作用域不存在 → 引用失败。

**解决方案**：
补丁 `patches/0001-skel.c.patch`（+3 行，`patch_type: bugfix`，非平台专用）插入
`%-` / `%*` 标记把两函数包回 non-C++ 区。C 路径输出逐字节不变，故自举回归不受影响。

### 问题2: 补丁必须打在 `skel.c` 且依赖 mtime 确定性

**现象**：
把补丁打在 `flex.skl` 上后 `make check` 失败，diff 显示
`yy_c_buf_p = NULL`（重新生成）与 `yy_c_buf_p = (char *) 0`（`initscan.c`）不一致。

**根因分析**：
发布包内 `skel.c` 与 `flex.skl` 内容不一致却 **mtime 相同**（均为 `2025-01-01 05:56`）。
mtime 相等时 make 不触发 `skel.c: flex.skl` 规则 ⇒ 真正生效的构建输入是发布版
`skel.c`（与 `initscan.c` 一致，用 `(char *) 0`），`flex.skl` 是陈旧旁支。

**解决方案**：
补丁打 `skel.c`；并在 `build()` 内 `os.utime(skel.c, None)` 强制其比 `flex.skl` 新，
防止 `mkskel.sh` 在增量/并行构建下回写覆盖补丁。

### 问题3: CI 上 `config.status` 写不进自建临时目录（本地四道门禁全绿，间歇复现）

**现象**：
```
./config.status: line 244: /storage/Users/currentUser/.cache/tmp/cslDeidH/subs.sed: Permission denied
./config.status: line 365: /storage/Users/currentUser/.cache/tmp/cslDeidH/subs.frag: Permission denied
./config.status: line 553: .../cslDeidH/out: Permission denied
./config.status: line 690: .../cslDeidH/undefs.sed: Permission denied
grep: install-man: No such file or directory
```
`configure` 的全部探测都通过，只有 `config.status` 段失败（构建 #65023 / worker CI-015）。

**性质：间歇竞态，不是必现缺陷**：
- 同一 PR 的 #65046（worker CI-003）在**修复前的同一份代码**上通过，步骤全 ✅；
- 该 PR 首轮 #65021 失败于 `git-clone`（`cannot exec 'git-remote-https'`），属 worker
  基础设施问题，**未跑到 `config.status`**，不能作为"同点复现"的证据。

故应描述为"时序相关的间歇竞态（HMDFS 权限元数据生效延迟）"：重试可能偶然通过，但根因真实存在。

**根因分析**：
`config.status` 用 `umask 077 && mktemp -d -q "$TMPDIR/csXXXXXX"` 自建临时目录后**立刻**往里
重定向写文件。CI worker 上该进程继承的 `TMPDIR` 落在 **HMDFS 用户卷**（`$HOME/.cache/tmp`，
非 worker 自身导出的 `/data` 路径），HMDFS 新建目录的属主/权限元数据尚未对该调用者生效 →
第一次写入即 EACCES。本地 `TMPDIR` 恰好在 `/data` 缓存上，故本地全绿、无法复现。

**解决方案**（从根因消除，不依赖时序）：
1. 补丁 `patches/0002-configure-hmdfs-tmpdir.patch`（`patch_type: portability`）：去掉
   `umask 077` 依赖，并在临时目录创建后显式 `chmod 700 "$tmp" 2>/dev/null || true`
   （`mktemp -d` 本就申请 `0700`，只是让权限位确定生效；该行随 heredoc 一并进入生成的
   `config.status`，实测生效于 `config.status:239`）。
2. recipe `_pin_tmpdir()`：`configure` 前把 `TMPDIR`/`TMP`/`TEMP` 钉到经
   「建目录 → 立刻写入 → 回读」探针验证的可写根（优先非 HMDFS 的
   `/data/storage/el2/base/cache`）；候选全不过时保留原值并告警。
   实测日志：`Using usable TMPDIR=/data/storage/el2/base/cache`。
3. `test_package/test_reflex.py` 的 `_workdir()` 同样探针化（生成物、`.o` 与链接产物都放那里）。

---

## 五、测试环境

```
reflex 20241231 (REFLEX — Dickey 的 flex 2.5.4 分支)
clang version 15 (OHOS SDK 26.0.0.18)
configure: --prefix=/ --build=aarch64-linux-ohos --host=aarch64-linux-ohos \
           --disable-shared --enable-static
tool_requires: bison/3.8.2, diffutils/3.12
package_type: static-library (R26)
conan create reflex/20241231@ohpcd/stable -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

---

*报告生成时间: 2026-09-29*
