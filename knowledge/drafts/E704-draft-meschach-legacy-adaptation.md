# meschach 1.2b 老项目适配三连修（草稿 E704）

- **来源**：meschach 1.2b OHOS 移植（任务卡 8812），W0 编译探针 + 配方阶段实测
- **日期**：2026-09-24
- **证据**：`archives/m/meschach/1.2b/notes.md` 问题表 #1–#4；`$TASK_DIR/w0/w0-compile-probe.txt`、`$TASK_DIR/oos-build/cfg.log`

## 三条失败面

### ① complex.h 探针撞名内建 typedef（编译期确定性错误）

configure 用 `AC_HEADER_CHECK(complex.h)` 探测系统头并写 `HAVE_COMPLEX_H`，
`machine.h` 随即 `#include <complex.h>`。C99 起 `complex` 是宏（`≡ _Complex`），
把 meschach 自带的 `typedef struct { Real re,im; } complex;`（`zmatrix.h:41`，
使用面 23 文件）展开坏：

```
./zmatrix.h:41:10: error: expected ';' after struct
```

**Debian 官方同判同修**：`meschach_1.2b-13.configure.diff:4602-4605` 原文注释
「No no no no no! Meschach does NOT support complex.h, which uses a completely
different definition of complex numbers and has a different meaning for keyword
"complex"! Drew Parsons, 2001」，`##AC_HEADER_CHECK(complex.h, ...)`。

**取舍**：符号面核对显示 `<complex.h>` 唯一 include 点是 `machine.h:122`
（守卫 `#ifdef HAVE_COMPLEX_H`）⇒ configure 侧断源即整链规避，
`zmatrix.h` 与 23 个使用文件**零改动**；反向改 typedef 面 delta 大且偏离 Debian 已审修法。

### ② all 目标绕过 SPARSE/COMPLEX 守卫宏（缺 --with-all 必炸）

`makefile.in:68` 的 `all` 无条件依赖 `part3 zpart`，而 `TYPE_SPMAT` 等常量只在
`SPARSE`/`COMPLEX` 下声明（`meminfo.h:55,58`），两宏仅由 `--with-all`
（`configure.in:66-67 AC_WITH(all,...)`）定义 ⇒ 默认 configure 下
`sparse.c` 报 `use of undeclared identifier 'TYPE_SPMAT'` ×20。
**配方固定 `./configure --with-all`，Debian rules 同口径。**

### ③ epsilon 探针反引号缺 ./ 前缀（rc=0 假绿面）

`AC_DEFINE_UNQUOTED(D_MACHEPS,\`macheps\`)` 执行无 `./` 前缀的探针程序，
设备 PATH 不含 cwd ⇒ **静默不执行**、configure 仍 rc=0，但 `D_MACHEPS`/`M_MAX_INT`
生成**空宏**写进 machine.h（`oos-build/machine.h:182` 实证；原树 configure 日志
`maxint: inaccessible or not found` ×4）。补丁改 `` `./macheps` ``、`` `./maxint` ``。

## 修复（配方三件套）

1. `patches/0001-configure.patch` + `patches/0002-configure.in.patch`：两侧成对
   移除 complex.h 探针（Debian 同款判词）+ 探针补 `./` 前缀；`strip: 1`，对原树
   `patch -p1 --dry-run` 实测 APPLIES_OK。
2. `conanfile.py build()`：in-source（epsilon 探针不带 $srcdir，out-of-source 必产
   空宏）、`./configure --with-all`、CFLAGS 在 configure 期与 make 调用行**各钉一次**
   （本型 makefile `CFLAGS = -O` 是字面量非 `@CFLAGS@`，configure 期传不进 make）。
3. 产物 `meschach.a` 重命名 `libmeschach.a`；12 头落 `include/meschach/`
   （Debian `/usr/include/meschach` 同口径）；makefile 无 install 目标 → 手工 package。

## 复现

```bash
printf '#include <complex.h>\n#include "zmatrix.h"\n' > "$HOME/tmp/meschach-1.2b/coll-probe.c"
clang -fsyntax-only -I "$HOME/tmp/meschach-1.2b/oos-src" "$HOME/tmp/meschach-1.2b/coll-probe.c"
# 期望：zmatrix.h:41:10: error: expected ';' after struct（rc=1）
# 对照：去掉 complex.h include → rc=0
```

## 禁行

- `#undef complex` 局部消宏：依赖 include 顺序，先 zmatrix.h 后 complex.h 的 TU 仍撞名。
- 改 zmatrix.h typedef 名：波及 23 文件、偏离 Debian 已审修法（备选，仅 configure 不可改时）。

> 提交后回填 source_commit；晋升需人工/AI 评审改名 `E704.kv` 移入 `knowledge/graph/` 并登记 index.tsv。
