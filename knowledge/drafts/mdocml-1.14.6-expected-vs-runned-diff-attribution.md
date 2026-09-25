# 上游测试的「期望文件数」与「实跑 tests run」差额，必须归因到具体文件才能提审

> Draft: DRAFT-MDOCL-1146-EXPECTED-VS-RUNNED-DIFF-ATTRIBUTION
> Stem: `mdocml-1.14.6-expected-vs-runned-diff-attribution` — pairs with the same-stem `.kv`
> 草稿号 **E699**（`knowledge_id.py --claim --task mdocml-1.14.6-2`，回查未占用）

## 基本信息

- **ID**: DRAFT-MDOCL-1146-EXPECTED-VS-RUNNED-DIFF-ATTRIBUTION
- **严重度**: 3
- **类别**: test-count|audit|portability|workflow
- **触发工具**: conan|make
- **阶段**: testing

## 错误特征

rule4 少报红线是「**实测 N > 声明 N**」，但上游测试有三个**互不相等**的计数量纲，
拿错量纲就会在 W4 或外部审查被判少报：

```
输入文件      .in               572
期望输出文件  .out_*           1189   ← 6 个后缀分层
驱动实跑数    tests run        1427   ← regress.pl 自己汇总
```

真正危险的形态是**「期望文件存在但驱动不跑」的静默差额**——
它让声明数与审方独立克隆清点数对不上，而本地一切全绿。

## 根因分析（mandoc / mdocml 1.14.6 实测）

期望 1189 vs 实跑 1427 **本就不同量纲**（`man` 类 244 没有独立期望文件，
它是 `-T man` 产物再以 `-man -T ascii` 回读后与 `.out_ascii` 比对）。
逐类相减后有**两类非零差额**，都能精确定位到文件：

### 差额一：lint 期望 249 vs 实跑 248（差 1 = `mdoc/Xr/args`）

成因是**手写 Makefile 里的注释边界截断了解析**。`mdoc/Xr/Makefile` 第 5 行是：

```make
# OpenBSD only: .Xr target tests cause too much trouble elsewhere
LINT_TARGETS	 = args
```

而上游 `regress/regress.pl` 的 `parse_makefile()` 有这一句：

```perl
last if /^# OpenBSD only/;      # 提前终止整个文件的解析
```

于是写在该注释**之后**的 `LINT_TARGETS` 整段失效 → 该项**被上游有意不注册、不跑**；
期望文件 `mdoc/Xr/args.out_lint`(462B) 与输入 `args.in`(526B) 却都还在树里。
这是**上游有意排除**（注释原文写明 elsewhere 有太多麻烦），不是平台失败。

### 差额二：utf8 期望 26 vs 实跑 21（差 5 = `char/unicode` 未注册项）

成因是**注册面收窄**——`char/unicode/Makefile:9`：

```make
UTF8_TARGETS = ascii invalid man mdoc namediff      # 只注册 5 项
```

但该目录下 `.out_utf8` 有 10 个（ascii / input / invalid / latin1 /
latin1diff / man / mdoc / named / namediff / nogroff）→ 未注册的
**input / latin1 / latin1diff / named / nogroff** 共 5 项有期望文件但不跑。

### 零差额类别

`ascii 565/565`、`tag 28/28`、`html 68/68`、`markdown 253/253` —— 直接记零。

## 解决方案

**主方案**: attribute-every-delta-to-a-concrete-file-before-submission

三步对账，**任何一步对不上都要给出文件名才允许提审**：

1. **分栏清点**：输入文件（`*.in` / `*_test.c` / `TESTS` 列表）与期望输出文件
   （`*.out_*` / golden / expected）**分别计数**，并与驱动程序实跑的
   `tests run` 并列成三行。三者量纲不同，**不得互相替代**，也不得用其中任一个
   去凑任务卡上的约数。
2. **算类内差额**：逐类别（ascii / lint / utf8 / html…）把期望文件数减实跑数；
   零差额直接记零，**非零差额必须给出文件名与成因**。
3. **用「解析口径复算 + 产物集合差集」闭环，不靠肉眼**：
   - 按驱动程序**真实的解析规则**（含注释边界、`SKIP_*` / `*_TARGETS` 显式列举、
     `?=`/`+=` 变量语义）重算注册集；
   - 再与**实跑产物集合**（`*.mandoc_lint` / `*.mandoc_ascii` 等中间产物文件）做
     `comm` **双向差集**；
   - 差集**恰好等于第 2 步给的文件名**才算归因完成。

   本例闭环读数：按 perl 解析口径（含 `last if` 边界）重算 = **248**，
   与实跑产物 248 个 `*.mandoc_lint` 的 `comm -23` / `comm -13` 双向差集
   **恰好只剩 `mdoc/Xr/args` 一项**。

### 方向判据要写进正文

- rule4 红线是**实测 > 声明**（少报）；
- 若声明来自任务卡约数且**大于**实测（本例 1468 vs 1189），方向安全、
  **不存在少报风险**；
- 但**约数不是判据**——判据是实测两栏 + 取数命令（审方可独立复算）；
- 约数与任何实测集合都对不上时，**如实写「差额无对应集合」**，不要硬凑解释
  （本例 1468 与 1427 / 1189 均无对应物理集合，「差额 41 无对应集合」句式保留）。

## 验证

```sh
# 1) 两栏清点
find regress -type f -name '*.in'    | wc -l        # 输入
find regress -type f -name '*.out_*' | wc -l        # 期望
find regress -type f -name '*.out_*' | sed 's/.*\.out_//' | sort | uniq -c

# 2) 实跑读数
grep -E 'tests run|NUMBER OF FAILED' regress.log

# 3) 差额归因闭环（以 lint 为例）
find regress -name '*.out_lint' | sed 's|^\./||;s|\.out_lint$||' | sort > exp.txt
find regress -name '*.mandoc_lint' | sed 's|^\./||;s|\.mandoc_lint$||' | sort > ran.txt
comm -23 exp.txt ran.txt      # → mdoc/Xr/args（期望有、实跑无）
comm -13 exp.txt ran.txt      # → 空（无"实跑但缺期望"）

# 4) 解析口径复算（复刻 regress.pl 的 last if 边界）
for f in $(find regress -name Makefile); do
  awk '/# OpenBSD only/{exit} /^LINT_TARGETS/{sub(/^LINT_TARGETS[ \t]*[?+]?=[ \t]*/,""); print}' "$f"
done | sort | uniq | wc -l    # → 248，与实跑一致
```

## 关联条目

- 与本任务 **E697**（手写 configure 的三个环境缺口）成对：E697 讲
  **测试为什么失败**（19 failed → 0 failed），本条讲**测试数为什么不能直接抄**
  （期望 ≠ 实跑，差额要归因）。
- 与 `references/iron-rules.md` **R51 上游测试三步法**、`pr-audit/SUMMARY.md`
  的 rule4（实测 N > 声明 N 判少报，25% 返工率）同族。
- 上游解析边界的同类形态：`docs/TEST_QUALITY_SPEC.md` 关于「跳过有据」的口径。
