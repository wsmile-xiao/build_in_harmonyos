# lexd 1.3.5：没有 HFST 也能复核 ATT transducer 的 gold（DP 成员判定）

> Draft: DRAFT-LEXD-135-ATT-GOLD-VERIFIER-WITHOUT-HFST
> Stem: `DRAFT-lexd-1.3.5-att-gold-verifier-without-hfst` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-LEXD-135-ATT-GOLD-VERIFIER-WITHOUT-HFST
- **严重度**: 2
- **类别**: testing|transducer|att|hfst|finite-state|pkg-config|missing-dependency
- **触发工具**: conan|python3|make
- **阶段**: testing

## 错误特征

上游 `make check` 的正例部分在 OHOS/CI 上必然失败：

```
hfst-txt2fst: command not found
make: *** [Makefile:66: out-plain/test-alt.lexd.txt.strings.check] Error 1
```

清点依赖确认这不是「环境没装」而是「制品仓没有」：

```bash
conan download "hfst/*" -r=ohpcd --only-recipe   # Found 0 pkg/version recipes
conan download "foma/*" -r=ohpcd --only-recipe   # Found 0 pkg/version recipes
```

按 R41 这属于外部阻塞，但**不等于**放弃判定：这套 oracle 并不依赖 HFST 的内部
实现，只依赖 AT&T 格式的三个可解析约定。

## 根因分析

上游判定管线（`tests/feature/Makefile`）：

```make
$(O)/%.lexd.txt.strings: $(O)/%.lexd.txt
	hfst-txt2fst $< | hfst-fst2strings -X obey-flags -c 10 | LC_ALL=C sort -u > $@
$(O)/%.strings.diff: $(O)/%.strings %.strings.gold
	diff -U0 $^ > $@; [ $$? != 2 ]
```

可解析的约定只有三条：

1. 每行 `in_state out_state [in_label out_label] weight`，标签可缺省（= epsilon）；
   末段「单状态 + 权重」行声明 final state。
2. `@0@` 是空标签。
3. `-X obey-flags` 的语义：把 `@X.Y@` 形式的 flag diacritic 当**元数据**，
   不算字面字符。

掌握这三点就能自己判定「某条 gold 串是否被转换器接受」。

### 三个必须避开的坑

**① 不要枚举全部路径。** 直觉做法是 DFS 枚举所有接受的字符串再查表，但 lexd 的
`test-disjoint-opt` / `test-pattern-independence` 在 `minimize` 变体下路径数
组合爆炸——实测把 python 进程 OOM 掉（rc=137，`Killed`）。必须改成**成员判定**。

**② gold 是子集，不是全集。** 上游用 `hfst-fst2strings -c 10` 做计数截断，
只保留出现 ≥10 次的串，因此「实际可接受串」⊋ gold。断言写成相等会得到
**111/216 的假失败**（每个夹具都会报「produced-only」差异）。正确方向是
`gold ⊆ 实际集合`。

**③ 空 gold 不能当失败。** `test-empty.lexd`（空词典）的 gold 是 0 字节，lexd
正确输出 0 字节且退出码 0。若沿用「输出为空即失败」的通用规则，会得到
**6/216 的假失败**（6 个 flag 变体各一次）。空 gold 的正确断言是
「不接受任何串」。

## 复现与定位

```bash
# 1) 确认工具缺失是「未发布」而非「没装」
command -v hfst-txt2fst hfst-fst2strings || echo "HFST absent"
conan download "hfst/*" -r=ohpcd --only-recipe

# 2) 清点 gold 规模（= 断言规模）
wc -l tests/feature/*.strings.gold | tail -1     # lexd: 132 行 gold
# 断言数 = 每变体 132 行 + 1 条空 gold 断言 = 133，x 6 变体 = 798

# 3) 跑自带校验器
python3 test_package/att_check.py <bin/lexd> test_package/data /tmp/r.txt
# att_check: 798 gold assertions over 216 fixture-variant combinations OK
```

### 读取器要点

**解析**：三种行都可能只有 2 个 tab 分段，不能只看字段数——

| 行形态 | 判定 | 处理 |
|--------|------|------|
| `0\t1\ta\ta\t0.000000\t` | ≥5 字段 | 转移 `(in=0, out=1, in_label=a, out_label=a)` |
| `5\t6` | 2 字段且都是整数 | epsilon 转移（**不是** final state！） |
| `0\t0.000000` | 末段单状态行 | final state |

**flag diacritic 不可见**：`@0@` 与所有 `^@[A-Z][A-Za-z0-9.]*@$` 在左右两侧都
当作「不产生字符」。否则 `-f/--flags` 变体的 surface 串会带上
`@U.F.B@` / `@P.D.C@` 之类元数据而全量 mismatch。

**按位置索引的 DP 成员判定**（不枚举路径）：

```
dp[i] = {(state, 右侧已拼串)}   # 恰好吃掉 surface 前 i 个字符后可达的状态集
dp[0] = {(0, "")}
for i in 0..len(left):
    # ① 在位置 i 上做 epsilon/flag 的不动点闭包
    repeat until no change: 对 (st, r) ∈ dp[i] 的每条不可见边，加入 (out, r + 可见右侧)
    # ② 消耗可见标签
    for (st, r) ∈ dp[i]: 若 left.startswith(label, i) → dp[i+len(label)] += (out, r + 可见右侧)
命中 ⟺ dp[len(left)] 中存在 (final_state, right)
```

复杂度 `O(len(left) × |E|)`，对指数级路径数免疫。多字符标签（`1`、`1b`）由
`startswith(label, i)` 天然处理。

**两种渲染都要接受**：gold 行含 `:` → 按 `left:right` 判定；不含 `:` → 按纯
surface 判定（HFST 在转移左右标签相同时只打印一侧）。

## 解决方案

`test_package/att_check.py`（约 200 行，无第三方依赖）：

```
att_check: 798 gold assertions over 216 fixture-variant combinations OK
att_check: ELF64 AArch64 (OHOS aarch64) target confirmed for lexd
```

**仍然要跑能跑的**：`make -C tests/feature LEXD_TEST_FLAGS='<flags>' check-neg`
只依赖 lexd 的退出码，6 个 flag 变体 × 2 个负例 = **12 次真实执行全部通过**；
把 216 次正例排除写进 `HMBS_UPSTREAM_TEST_RESULT`（`skipped=216` + `reason`
说明缺 HFST/Foma），不允许静默跳过（R51）。

## 适用边界

- 适用于「上游测试把 ATT/VRT/FST 输出交给外部 FST 工具比对 gold，而该工具未
  发布」的所有包；判据是上游测试 Makefile 里出现 `hfst-*` / `foma` / `hfst2txt`。
- **不等于**复现了 HFST：`-c 10` 的计数截断语义无法在无 hfst 时复刻，所以断言
  是包含关系。若将来 HFST 被适配，可直接用上游 `make check` 替换本校验器。
- 转换器若使用多字符标签 + 位置无关的 `@L.F@` 之类非标准标记，需要按实际
  标记形态调整 `is_invisible()` 的正则。

## 关联

- 本条目来自 lexd 1.3.5（Apertium 词典编译器）HarmonyOS PC aarch64 适配。
- 同族可复用包：hfst-twolc 系列、apertium 的 transducer 子测试。
- 与 R51（上游测试三步法）、R41（外部依赖止损但不放弃验证）配套。
