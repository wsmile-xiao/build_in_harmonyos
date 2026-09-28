# 输出不可逆的工具用结构不变量做判据，而不是抄 golden 向量

> Draft: `DRAFT-LETTERIZE-STRUCTURAL-INVARIANT-CONSUMER-TEST`
> Stem: `letterize-1.6-structural-invariant-consumer-test` — 与同 stem 的 `.kv` 成对
> 实例：letterize 1.6（`archives/l/letterize/1.6`，PR !9xxx）

## 基本信息

- **ID**: `DRAFT-LETTERIZE-STRUCTURAL-INVARIANT-CONSUMER-TEST`
- **严重度**: 3（判据质量问题——决定 CI 绿灯是否等价于真覆盖）
- **类别**: test-design, coverage, ci-gate
- **触发工具**: ci（L1 测试执行验证）
- **阶段**: testing

## 问题：把"不可逆"误读成"只能硬编码"

对**枚举型 / 组合型**工具（输入 → 一组候选），常见写法是：

```c
/* ❌ 78 行输出里只断言了 1 行 */
expect(strstr(out, "adg") != NULL, "letterize 234");
```

三个结构性缺陷：

| 缺陷 | 说明 |
| --- | --- |
| 覆盖极低 | 一条断言只覆盖 78 行里的一行，其余 77 行不校验 |
| 可能自我固化 bug | 期望值若从一次**错误**运行结果反抄，bug 被固化成"期望行为"，绿得稳定 |
| 组合爆炸时退化为空壳 | 10 位号码 246 行，人工列举不可行 → 干脆只测"能跑、有输出" |

**不可逆 ≠ 无约束**。只要输出必须满足某种结构不变量，就能写出覆盖**全部**输出行的
自闭合判据，不需要任何期望值。

## 方案：逐行校验结构不变量

letterize 的输出有两条硬约束：

| 不变量 | 内容 | 为什么必然成立 |
| --- | --- | --- |
| **P1 长度守恒** | 每行助记词长度 == 输入长度 | 逐位 1:1 映射，任何长度漂移都是实现缺陷 |
| **P2 键位约束** | 第 i 位输出字符要么 == 输入字符（非 2-9 位原样透传），要么 ∈ 该键位字母集合 | 美式电话键盘映射的定义 |

```c
static const char *g_keypad[10] = {
    "0", "1", "abc", "def", "ghi", "jkl", "mno", "prs", "tuv", "xyz"
};

static int line_ok(const char *line, const char *input, char *why, size_t whycap)
{
    size_t i, n = strlen(input);
    if (strlen(line) != n) {                       /* P1 */
        snprintf(why, whycap, "行 \"%s\" 长度 %zu ≠ 输入长度 %zu", line, strlen(line), n);
        return 0;
    }
    for (i = 0; i < n; i++) {
        unsigned char in = input[i], out = line[i];
        if (in >= '2' && in <= '9') {              /* P2 */
            if (!strchr(g_keypad[in - '0'], out)) {
                snprintf(why, whycap, "第 %zu 位：输入 '%c' 映射到 \"%s\"，输出却是 '%c'",
                         i, in, g_keypad[in - '0'], out);
                return 0;
            }
        } else if (out != in) {
            snprintf(why, whycap, "第 %zu 位：非数字键输入 '%c' 应原样透传，输出却是 '%c'",
                     i, in, out);
            return 0;
        }
    }
    return 1;
}
```

## 五个实现要点

### ① 违规信息必须自带定位

不能只打印"属性不成立"。要报出**第几行第几位、输入字符、允许集合、实际字符**：

```
[FAIL] 逐位映射属性 (P1/P2) 全部行成立 — 第 0 位：输入 '2' 映射到 "ABC"，输出却是 'a'
```

### ② 属性成立时也要打印**校验了多少行**

```c
snprintf(label, sizeof(label), "逐位映射属性 (P1/P2) 全部 %d 行成立", seen);
expect(seen > 0, label, "");
```

日志差异：

```
  [PASS] 逐位映射属性 (P1/P2) 全部 246 行成立     ← 真覆盖
  [PASS] 逐位映射属性 (P1/P2) 全部 0 行成立       ← ★ 假绿来源，必须能区分
```

### ③ 字母集合的**大小写必须与被测输出一致**

首版判据写成大写 `"ABC"`，实测 6 个用例全 FAIL：

```
[FAIL] 逐位映射属性 (P1/P2) 全部行成立 — 第 0 位：输入 '2' 映射到 "ABC"，输出却是 'a'
```

这是**判据自身的缺陷**，不是程序缺陷。修法是把集合改为小写 `"abc"`；同时保留一条
golden 首行断言（`adg`）来锚定大小写约定——这样下次约定变化时，golden 断言会先报，
而不是让属性判据产生一串难以定位的 FAIL。

### ④ golden 断言降级为**辅助锚点**，主体是属性

保留的 golden 部分只有：

- 非空行数（`234`→13、`2275`→19、`5551234`→78、`5551234567`→246、`12`→3、
  `0000000`→1、`1-800-555`→18、`1`→1）
- 首行（`adg` / `aarj` / `jjj1adg` / `jjj1adgkop` / `1a` / `0000000` / `1-t00-jjj` / `1`）

它们锚定**词表过滤行为**（行数会随词表变化），而属性覆盖**每一行的每一位**。
两者互补：golden 少而稳，属性广而自闭合。

### ⑤ 属性判据同样遵守既有规范

`expect()` 计数而非 `assert()`（NDEBUG 下 assert 会被整体编译掉）· `popen` 内存
直读不落盘（OHOS `/tmp` 只读）· `pclose==-1 || !WIFEXITED || code∈{126,127} ||
code>=128` 判"跑不起来" · 循环读到 EOF 再 `pclose`。

## 实测结果

```
── letterize "234"          → 13 行,  首行 adg,          逐位映射属性全部 13 行成立
── letterize "2275"         → 19 行,  首行 aarj,         逐位映射属性全部 19 行成立
── letterize "5551234"      → 78 行,  首行 jjj1adg,      逐位映射属性全部 78 行成立
── letterize "5551234567"   → 246 行, 首行 jjj1adgkop,   逐位映射属性全部 246 行成立
── letterize "12"           → 3 行,   首行 1a,           逐位映射属性全部 3 行成立
── letterize "0000000"      → 1 行,   首行 0000000,       逐位映射属性全部 1 行成立
── letterize "1-800-555"    → 18 行,  首行 1-t00-jjj,    逐位映射属性全部 18 行成立
── letterize "1"            → 1 行,   首行 1,             逐位映射属性全部 1 行成立
=== 汇总: 34 通过, 0 失败 ===
```

属性判据共校验 **353 行**输出的每一位，且不含任何完整词表副本。

## 与"往返一致性"的分工

| 判据类型 | 适用 | 依赖 |
| --- | --- | --- |
| **往返一致性**（`DRAFT-LUNAR-ROUNDTRIP-PROPERTY-CONSUMER-TEST`） | 可逆转换（encode/decode） | 被测程序自证 |
| **结构不变量**（本条） | 不可逆但有约束的输出（枚举/展开） | 约束的数学定义 |

两者都不依赖外部对照表。

## 参考实现

`archives/l/letterize/1.6/test_package/test_letterize.c` — 34 条断言
（8 组输入的属性判据 + 行数/首行锚点 + 空输入用例）
