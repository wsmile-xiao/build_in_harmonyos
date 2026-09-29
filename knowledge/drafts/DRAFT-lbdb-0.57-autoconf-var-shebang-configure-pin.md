# DRAFT-lbdb-0.57-autoconf-var-shebang-configure-pin: autoconf `#! @VAR@` 模板把构建机解释器路径烧进交付脚本

> 状态——草稿（未过主编）。触发事件——`archives/l/lbdb/0.57` 适配 HarmonyOS PC（平台任务 8043，B 机真机实测）。
> 结构化字段见同名 `.kv`。

## 症状 / 错误特征

```
$ head -1 <pkg>/libexec/munge
#! /data/service/hnp/bin/gawk -f          # 构建机当场探测出来的路径
$ head -1 <pkg>/bin/nodelist2lbdb
#! /data/service/hnp/bin/perl
sh: bad interpreter: /data/service/hnp/bin/perl: no such file or directory   # 换机/换 PATH 之后
```

上游用 `*.in` 模板分发命令面脚本，首行写成占位符：

```
$ grep -h '^#!' lbdb-0.57/*.in | sort | uniq -c
     30 #! @SH@
      3 #! @PERL@
      1 #! @PERL@ -w
      2 #! @AWK@ -f
```

configure 的 `AC_SUBST` 在生成时把 `@VAR@` 替换成 **AC_PATH_PROG 当场按 PATH 顺序探到的构建机绝对路径**。
"可移植的模板"于是在交付物里变成机器绑定路径——换机、换用户、换 PATH 即整片 `bad interpreter`。
lbdb 0.57 的面——45 枚 `*.in` 中 36 枚带 `#! @VAR@`，交付 20 枚脚本，其中未处理时至少 5 枚机器绑定
（4 枚 perl + 1 枚 gawk）。

## 根因与"能不能钉"的判据（本条目的新增价值）

常见直觉是"往 configure 传 `SH=/bin/sh AWK=/bin/awk PERL=...` 就完事了"。**实测这是错的**——
能不能钉取决于上游有没有把探测块包在 `if test "x$VAR" = x ; then … fi` 里：

| VAR | 上游写法（lbdb configure.ac 原文） | 命令行钉值的结果 | config.log 读数 |
|---|---|---|---|
| `SH` | 三段探测（bash → ksh → `AC_PATH_PROG(BINSH, sh)`）**每段外面都有** `if test "x$SH" = x ; then` | 三段全短路，顺带躲掉 `$BASH -posix`（本机 bash 是 harmonybrew 用户专属路径） | `SH='/bin/sh'` ✅ 生效 |
| `AWK` | `AC_PATH_PROG(AWK, awk, NONE)` 展开为**无条件赋值** `AWK=$ac_cv_path_AWK`（生成的 configure 第 5611 行），其后 `NAWK/GAWK/MAWK` 三段专用探测逐个覆盖（`if test "x$GAWK" != "xNONE" ; then AWK="$GAWK"`；中间那句 `AWK="$AWK"` 是自赋值空操作） | 必被吃掉 | `AWK='/data/service/hnp/bin/gawk'` ❌ 不生效 |
| `PERL` | `AC_PATH_PROG(PERL, perl, …)`（configure 第 7702 行 `PERL=$ac_cv_path_PERL`） | 本机 `/usr/bin/perl`、`/bin/perl` 均 MISSING，**没有可移植的 FHS 目标可钉**（钉了＝装了跑不了） | `PERL='/data/service/hnp/bin/perl'` ⤳ 只能交付期改 |

一手对照（同一次 `conan create`，构建树＝归一前、包目录＝归一后）：

```
BUILD lbdbq            #! /bin/sh                          <- @SH@ 被 configure 钉住了
BUILD munge            #! /data/service/hnp/bin/gawk -f    <- @AWK@ 钉失败，机器绑定
PKG   lbdbq            #! /bin/sh
PKG   munge            #! /bin/awk -f                      <- 交付期归一救回来
PKG   nodelist2lbdb    #! /usr/bin/env perl                <- 交付期归一（PERL 无 FHS 可钉）
```

## 方案（三层，主次不能颠倒）

1. **主案——交付期按 basename 归一**（conanfile `package()` 遍历 `bin/`、`libexec/`）：
   首行不是 `#!` 的（ELF）跳过，只补可执行位；是 `#!` 的按**解释器 basename** 映射，并保留原 tail
   （`-f`/`-w` 的语义不丢）——

   | basename | 归一为 |
   |---|---|
   | `sh` / `ash` / `dash` | `#! /bin/sh`（带原 tail） |
   | `bash` / `ksh` | `#! /bin/sh`（**前提**——先实测 toybox ash 能吃脚本用到的语法；本包实测 `[[ ]]`、数组、命名函数、`${v//o/0}`、`[ x == y ]`、`local` 全支持） |
   | `perl` | `#! /usr/bin/env perl`（本平台无 `/usr/bin/perl`，perl 在 PATH 上的 hnp） |
   | `awk` / `gawk` / `mawk` / `nawk` | `#! /bin/awk -f` |

   按 basename 映射比"整行 sed 替换"稳，因为 `$BASH -posix` 这类带参数的探测结果会落进同一张表。
2. **第一道（选做，不得当依赖）——configure 命令行只钉有守卫的**（本包 `SH=/bin/sh`）。
   生效与否**必须回读 config.log**判定；钉不住（AWK 型）或无可钉目标（PERL 型）就交给第 1 层。
3. **验收（必做）——test_package 全量 shebang 扫描断言**：逐枚取已安装包 `bin/*`、`libexec/*` 的首行，
   解释器路径命中 `*/storage/Users/*|*/data/service/*|*/.harmonybrew/*|*/usr/local/*|/usr/bin/perl*|*bash*`
   即判失败；**并断言扫描到的脚本数 > 0**（本包断言 `scanned 20 installed scripts`），
   否则 "0 offenders" 可能只是什么都没扫到＝假绿。

本包落地读数——`SUMMARY lbdb consumer: total=10 passed=10 failed=0`，其中 A5/A6 两个 perl 交付脚本
rc=255 / rc=2（**不是 127、不是 `No such file or directory`**，即解释器已解析）、A7 offenders=0、A8 扫描数 20。

## 禁止

- ⛔ **只向 configure 传 `VAR=value` 就收工**——AWK/PERL 两类必被漏掉（实测）。
- ⛔ 把 bash 型 shebang 归一成 `#!/bin/bash`，或赌平台装了 bash（本平台 `/bin/bash`、`/usr/bin/bash` 均 MISSING）。
- ⛔ 不做逐枚首行扫描、只凭 `rc=0` 或 `ls` 宣称 shebang 已可移植。
- ⛔ 为凑绿把脚本从 `bin/`、`libexec/` 删掉（缩命令面＝虚假适配，且会撞 CI 结构检查与 L0k 声明面差集）。
- ⛔ 与"configure 自身的驱动解释器"混淆——HNP bash 在非 `/` 目录 `getcwd` 被拒，
  那是 `CONFIG_SHELL`/`SHELL` 的事（E129/E551/autoconf269-config-shell 家族），不解决交付脚本首行。

## 适用范围 / 不适用

- 适用——任何用 autoconf `*.in` 模板分发命令面、模板首行为 `#! @VAR@` 的包（同族还常见 `#! @PYTHON@`）。
- 不适用——CMake/meson `configure_file` 生成的脚本（替换源不同）；上游脚本首行**本就写死**的字面 shebang
  （那是 E049/E037/date/libgctp 的场景）；纯 ELF 产物。
- 风险/代价——归一只改首行、不动脚本体，故若某脚本实际依赖 bash 特性而 toybox ash 不支持，
  归一会把"启动即死"变成"跑到一半才死"；所以第 1 步的 `bash→/bin/sh` 必须先做语法能力实测，
  第 3 步的 round-trip 断言（本包 A9）负责兜住语义。

## 查重账（整仓 `knowledge/` 检索，B 机 `~/qzy/主理-74-lbdb-0.57`，2026-09-27 22:25–22:28）

| 命令 | 命中 |
|---|---|
| `grep -rl lbdb knowledge/{graph,doc,drafts,draft}` | 0 / 0 / 0 / 0 |
| `grep -ic lbdb knowledge/graph/index.tsv` | 0 |
| `grep -rl '@SH@' knowledge` / `'@PERL@'` / `'@AWK@'` | 0 / 0 / 0 |
| `grep -rl '@PYTHON@' knowledge` | 3（E465 嵌入式 python launcher、kea meson configure_file——均非 shebang 替换语境） |
| `grep -rli 'AC_PATH_PROG' knowledge` | 8（无一涉及交付脚本 shebang） |
| `grep -rl 'SH=/bin' / 'AWK=/bin' / 'PERL=/usr/bin' knowledge` | 0 / 0 / 0 |
| `grep -rli 'offender' / '机器绑定' / 'basename.*归一' knowledge` | 0 / 0 / 0 |
| `grep -rli 'shebang' knowledge`（家族面） | 102 个文件 |
| `grep -rli 'shebang.*hardcoded' knowledge` | 3（E049 的 doc/graph/index 三件，即 E049 自身） |
| `grep -rli "jigit\|mkjigsnap" knowledge`（配方注释里引的先例） | 0 |

**与最接近条目的边界**——

- `E049 shebang-portable-fix`——机制是"生成器程序（automake `gen-all.pl`）把解释器路径**硬编码**进产物"，
  处方是"事后 sed 改已装脚本 + 让生成器输出 env 形式"。它**不含** `@VAR@ 模板由 configure 填实`这条产生路径，
  没有"哪些 VAR 钉得住"的判据（`if test "x$VAR" = x` 守卫 vs `VAR=$ac_cv_path_VAR` 无条件赋值），
  也没写 configure 传参与交付期归一的主次关系与全量扫描断言 ⇒ 按 `手册/03 §6.2⑦` "症状相同但用既有条目
  没写的另一条解法＝create"，本条按新增申报。
- `E037 shebang-fix`——前提是"鸿蒙没有 `/usr/bin/env`"，本机实测 `/usr/bin/env` 存在（toybox），前提不符。
- `DRAFT-ohos-perl-script-package-conan-adaptation`——纯 Perl 脚本包，改字面 shebang + 补 PERL5LIB。
- `DRAFT-date-3.0.3-ohos-bash-shebang` / `DRAFT-8207-libgctp-automake-log-compiler-no-bin-bash`——
  测试辅助脚本的字面 shebang（后者用 `LOG_COMPILER=/bin/sh` 绕过），不经 autoconf 模板替换。
- `DRAFT-ohos-configure-ac-cv-path-tool-override`——用 `ac_cv_path_*` 钉工具是为解决头文件/库搜索路径，
  与交付脚本首行无关。
