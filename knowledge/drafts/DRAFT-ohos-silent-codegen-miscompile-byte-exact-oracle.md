# 优化构建会静默改变后端机器码（VEX/EVEX 编码错误）；须靠字节级上游对照发现

> DRAFT · contributor_id: `frj__` · 2026-10-03 · 来源：uasm 2.57 OHOS aarch64 适配（PR #14452）

## 错误特征（可粘贴的真实日志）

**没有编译告警**，但同一份源码在 `-O2` 与 `-O0` 下生成的**机器码字节不同**，且 `-O2` 的是错的。
以 uasm 自身（汇编器）在 OHOS aarch64 为例：

```text
# c4 ... 是 VEX 前缀；下面两组是同一输入、仅优化级别不同
$ uasm -q -bin v.asm ; od -An -tx1 -N5 v.BIN
-O2 构建:  c4 e2 59 8c f0      # VPMASKMOVD xmm6,xmm4,<寄存器>（错，误把 [rcx] 当 xmm0 且多一字节 disp）
-O0 构建:  c4 e2 59 8c 31      # VPMASKMOVD xmm6,xmm4,[rcx]（对）
$ uasm -q -bin v.asm ; od -An -tx1 -N6 v.BIN    # 另一条
-O2: c4 e2 69 45 d6 00   -O0: c4 e2 c9 45 d4
```

传统 x86 指令（`mov`/`add`/内存寻址）在两种优化级别下都正确，只有 **CodeGenV2 路径的
AVX/VEX 指令**出错——所以“编译过、大部分用例过”极具欺骗性。

## 触发条件（平台 / 阶段 / 代码模式）

- 平台：OHOS aarch64 + clang 23（其他编译器/架构是否命中需各自实测）。
- 构建：开启优化（`-O2`）；`-O0` 正常。
- 代码模式：存在类型双关 / 共用体别名 / 未定义行为（UB）的后端代码；
  只影响经过该代码路径的指令族（此处为 CodeGenV2 的 VEX/EVEX）。

## 根因分析（机制 + 实测数字）

`codegenv2.c` 大量使用共用体/指针类型双关来拼装前缀与位移。在 `-O2` 下，优化器按
严格别名/UB 规则重排，导致 `BuildVEX`/`BuildMemoryEncoding` 的结果被错误合并，
输出的 VEX 编码不是“少一个字节”就是“把内存操作数当寄存器”。关键对照：

| 变量 | 结果 |
|---|---|
| `-O2` | `vpmaskmovd xmm6,xmm4,[rcx]` → `c4 e2 59 8c f0 00`（错） |
| `-O2 -fno-strict-aliasing` | 仍错（**不足以修复**） |
| `-O0` | `c4 e2 59 8c 31`（对，与上游期望一致） |

即：这不是“优化更强所以更对”，而是优化放大了源码 UB；`-fno-strict-aliasing`
只覆盖严格别名这一种，其他 UB 仍在。

## 解决方案

**推荐**：对“输出机器码/编码”的工具，把**上游期望产物当 oracle 做逐字节比对**，
并在 aarch64 上先用 `-O0` 构建（或定位 UB 后修正源码）。

```sh
make CFLAGS="-O0 ..."           # uasm：-O0 后 CodeGenV2 44/44 与上游字节一致
<runner> <uasm> regress oracle  # 逐字节比对上游 regress/exp/<cat>/
```

**禁止做法（看起来能过但其实错）**：

1. 只凭“能编译 + 大部分用例通过（传统指令）”就在 `-O2` 下发版——静默机器码错误会传下去。
2. 自写一个简化/近似的测试当 oracle——覆盖不到完整指令矩阵，正是它掩盖了 `-O2` 差异。
3. 以为加 `-fno-strict-aliasing` 就够——实测对该后端代码不足。

**验证命令**：见上（同一 `.asm` 在 `-O2`/`-O0` 下 `od` 前 5–6 字节对比）。

## 通用性证据

- **上游语料**：uasm `regress/CodeGenV2/` 44 个 AVX/EVEX 用例，`-O2` 下 30/44 不符、
  `-O0` 下 44/44 与上游期望逐字节一致；`plain_bin` 同类 VEX 用例（`avx_2`/`avx_3`/`clmul` 等）
  亦仅因该机制失败。
- **同一 oracle 同时抓出另一类缺陷**：LP64 位移语义错误（见
  `DRAFT-ohos-lp64-unsigned-long-32bit-semantics`）也是靠同一套字节级对照才发现——
  佐证“字节级上游 oracle”对后端工具的通用价值。

## 查重反证

- `miscompile`、`误编译`、`strict-aliasing`、`类型双关`、`type punning`、`优化器`
  在 `knowledge/graph/index.tsv` 与 `knowledge/drafts/` 均 **0 命中**。
- 相近条目 `DRAFT-clang-o2-unobservable-alloc`（gperftools，`-O2` 消除不可观察的
  `new/delete` 使 hook 计数为 0）：机制是 **优化删除“无副作用”的分配调用**，
  修法是补 `-fno-builtin`；本条是 **优化把后端编码算错**，修法是字节级 oracle + `-O0`/修 UB。
  两者可分别用“hook 计数是否触发”与“输出字节是否等于上游”区分。

## 证据（PR / 分支 / 配方 / 日志）

- 分支 `feat/uasm-2.57`，PR #14452，head `2c48e54`。
- 构建参数见 `archives/u/uasm/2.57/conanfile.py`（`CFLAGS` 含 `-O0`）。
- 真机日志：`regress-oracle.log`（`MODE=oracle / TOTAL run=477 pass=469 fail=8`）。

## 元信息

- authors：`frj__ <241250055@smail.nju.edu.cn>`
- contributor_id：`frj__`；`draft: true`
