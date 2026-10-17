# 数值插值/拟合类判据的「包含性契约」+ 三类不该进断言的派生值

> Draft: `DRAFT-SPLINE-INCLUSION-CONTRACT-AND-DERIVED-VALUE-TRAPS`
> Stem: `spline-1.2-inclusion-contract-and-derived-value-traps` — 与同 stem 的 `.kv` 成对
> 实例：spline 1.2 / aspline（`archives/s/spline/1.2`，PR !9xxx）

## 基本信息

- **ID**: `DRAFT-SPLINE-INCLUSION-CONTRACT-AND-DERIVED-VALUE-TRAPS`
- **严重度**: 3（正反两面：既是判据技法，也是三类假失败的来源）
- **类别**: test-design, false-fail, coverage, ci-gate
- **触发工具**: ci（L1 测试执行验证）
- **阶段**: testing

## 一、正向：把手册里的"契约句"直译成判据

数值工具（插值、拟合、平滑、重采样）的输出是一大串浮点数，很容易被认为
"只能靠 golden 向量验证"。但这类工具的手册里通常写着一句**契约**：

> **aspline**: "It produces a similar set … and **includes the input set** on standard output."

直译成判据：**每个输入点 (x, y) 都必须出现在输出中**。这条完全自闭合，不需要任何
期望表，且直击最核心的语义（插值曲线必须过给定点）。

```c
/* P1 输入点包含性 */
for (j = 0; j < n_input; j++) {
    int found = 0;
    for (q = 0; q < lines; q++) {
        double x, y;
        if (!get_point(buf, q, &x, &y)) continue;
        if (fabs(x - XS[j]) < 1e-9 && fabs(y - YS[j]) < 1e-6) { found = 1; break; }
    }
    expect(found, "输入点出现在输出中", "");
}
```

实测（y=x²，5 个输入点）：

```
  [PASS] 全部 5 个输入点都出现在输出中（实际命中 5 个）
  [PASS] 首点 x == 输入最小 x (0)
  [PASS] 末点 x == 输入最大 x (4)
  [PASS] 首末 y 与输入端点一致 (0 / 16)
```

### 配套：常量保持性（从反方向锁住）

输入全为同一常量 `y = c` 时，**任何**正确的插值器都必须输出恒为 `c`
（两点间是直线段，两端相等 → 恒等）。这是一条极强的数值不变量：

```c
for (k = 0; k < 3; k++) {                  /* c ∈ {5, 0, -3.25} */
    for (j = 0; j < lines; j++) {
        get_point(buf, j, &x, &y);
        if (fabs(y - c) > 1e-9) { bad = 1; break; }
    }
    expect(lines > 0 && !bad, "常量保持性", "");
}
```

```
  [PASS] 常量保持性：y=5 的全部 101 行输出仍为 5
  [PASS] 常量保持性：y=0 的全部 101 行输出仍为 0
  [PASS] 常量保持性：y=-3.25 的全部 101 行输出仍为 -3.25
```

★ P1 保证"**过给定点**"，P2 保证"**不改动已确定的值**"。二者对任意输入规模成立。

## 二、负向：三类"派生值 / 未验证假设"绝不能进断言

本包落地时**三次全部真实踩中**。

### ① `argv[0]` 派生的程序名

用法行与版本串里的程序名取自 `argv[0]` 的 **basename**：

| 调用 | 输出 |
| --- | --- |
| `/tmp/aspline -h` | `usage: aspline …` |
| `/tmp/vf/spline -h`（被复制成 `<包名>`） | `usage: spline …` |
| `-V` | `spline version 1.2` ← **不是** `aspline version 1.2` |

**本地验证时二进制叫 `aspline`，测试把包内二进制复制成 `<包名>` 后就变了名**，
于是 3 条断言在 qemu 上直接挂：

```
[FAIL] -V: 输出含 "aspline version 1.2" — 实际输出: spline version 1.2
[FAIL] --version: 输出含 "aspline version 1.2" — 实际输出: spline version 1.2
[FAIL] -a 缺参打印用法: 输出含 "usage: aspline"
```

**改法**：只断言与程序名无关的部分。

```c
expect_contains("-V", buf, "version 1.2");                    /* ✅ */
expect_contains("-h", buf, "[-hv][-a [xstep]][-l llimit]…");  /* ✅ */
```

同类派生值：绝对路径、时间戳、PID、临时目录名、hostname、随机数。

### ② 想当然的单调性

`-n N` 的语义是"大约 N 个区间"，但**输出必须包含输入点**，所以当 N 要求的区间数
少于输入点数时无法再压缩 —— 行数**不随 N 单调**：

| `-n` | 2 | 3 | 4 | 5 | 10 | 20 |
| --- | --- | --- | --- | --- | --- | --- |
| 输出行数 | 5 | **7** | **5** | 9 | 14 | 21 |

`-n 3 → 7 行` 而 `-n 4 → 5 行`。断言单调性会假失败：

```
  [FAIL] -n 输出行数随 n 单调不减
```

**改法**：断言两条真实成立的属性，并只在**稳定区间**断言精确值。

```c
if (lines < n_input)     ge = 0;      /* 行数 ≥ 输入点数 */
if (lines > 2 * n + 2)   ranged = 0;  /* "approx. n intervals" 的合理上界 */
expect(ge && ranged, "-n 行数在 [输入点数, 2n+2] 内", "");
expect(count_lines(buf) == 21, "-n 20 时输出 21 行（20 个区间）", "");
```

### ③ 上游并未定义的错误退出码

`-a` 缺参数时，上游打印 `option requires an argument: a` **与用法块**，但
**退出码仍是 0**。把"错误路径必须非 0 退出"写进断言会假失败：

```
  [FAIL] -a 缺少参数时非 0 退出码
```

**改法**：断言"报错信息 + 用法块 + 未因信号终止"，并把实测退出码打印留痕。

```c
rc = run_capture("-a", buf, sizeof buf);
printf("     [INFO] -a 缺参时实测退出码 = %d\n", rc);
expect(rc >= 0, "-a 缺参未导致进程异常终止", "");
expect_contains("-a 缺参", buf, "option requires an argument");
expect_contains("-a 缺参打印用法", buf, "[-hv][-a [xstep]]");
```

## 三、判别清单（写数值/CLI 判据前过一遍）

| 准备写进断言的东西 | 是否安全 | 处置 |
| --- | --- | --- |
| 输入点必须出现在输出中 | ✅ 契约 | 直接断言 |
| 常量输入 → 常量输出 | ✅ 不变量 | 直接断言 |
| x 递增 / 行列数关系 / 端点一致 | ✅ 结构 | 直接断言 |
| **程序名 / 路径 / 时间 / PID** | ❌ 环境派生 | 只断言与名字无关的部分 |
| **"参数变大输出必变多"** | ❌ 未验证的单调性 | 改断言上下界 + 稳定区间精确值 |
| **错误路径必非 0 退出** | ⚠️ 需实测 | 先测再定；若为 0 则断言"报错 + 未崩溃"并留痕 |

## 四、实测结果

```
=== aspline (spline 1.2) 消费者测试 ===
  [PASS] 全部 5 个输入点都出现在输出中（实际命中 5 个）
  [PASS] 常量保持性：y=5 的全部 101 行输出仍为 5
  [PASS] 常量保持性：y=0 的全部 101 行输出仍为 0
  [PASS] 常量保持性：y=-3.25 的全部 101 行输出仍为 -3.25
  [PASS] 输出 x 严格递增
  [PASS] -n 各档输出行数均不少于输入点数 (5)
  [PASS] -n 各档输出行数不超过 2n+2（手册：approx. n intervals）
  [PASS] -n 20 时输出 21 行（20 个区间）
  === 汇总: 51 通过, 0 失败 ===
```

## 五、可套用范围

| 工具/场景 | 包含性契约 | 常量保持性 |
| --- | --- | --- |
| 插值 / 拟合（aspline、plotutils spline、gnuplot 平滑） | 曲线过给定点 | ✅ |
| 重采样 / 抽稀 | 端点与关键点保留 | 常量输入→常量输出 |
| 图像缩放 / 卷积 | — | 单色图必须保持单色 |
| 单位换算 / 坐标变换 | 恒等变换点 | 零点保持 |
| 排序 / 归一化 | 元素集合不变（置换） | 常量数组不变 |
| 无损压缩 | 往返一致 | — |

★ 通用原则：**先找手册里的契约句（includes / preserves / exact for / …），把它
翻译成属性判据；再把所有由 `argv[0]`、环境、时间派生的值从断言里剔出去，并把
"想当然"的规律（单调性、退出码语义）先用一次实测证实再写死。**

## 六、与本批次其它判据的关系

| 判据 | 适用 | 参考 |
| --- | --- | --- |
| 往返一致性 | 可逆转换 | `DRAFT-LUNAR-ROUNDTRIP-PROPERTY-CONSUMER-TEST` |
| 结构不变量 | 不可逆但输出有约束 | `DRAFT-LETTERIZE-STRUCTURAL-INVARIANT-CONSUMER-TEST` |
| 两段式调用 | 有状态的修改类工具 | `DRAFT-PAXCTL-MUTATE-THEN-READ-SEPARATE-INVOCATIONS` |
| 干跑 + 独立历法 | 输出与当前时刻相关 | `DRAFT-SNOOZE-TIMELESS-DRYRUN-CALENDAR-CROSSCHECK` |
| 合成夹具 + 往返属性 | 解析结构化二进制输入 | `DRAFT-UNYAFFS-SYNTHESIZED-FIXTURE-ROUNDTRIP` |
| 本地环境能力不得固化 | 行为依赖内核/平台能力 | `DRAFT-PRCTL-PLATFORM-CAPABILITY-TIERED-ASSERTIONS` |
| **包含性契约 + 派生值禁忌**（本条） | 数值插值/拟合/重采样 | — |

## 七、参考实现

- `archives/s/spline/1.2/test_package/test_spline.c` — 51 条断言
- `archives/s/spline/1.2/test_package/conanfile.py` — scratch 目录构造与传参
