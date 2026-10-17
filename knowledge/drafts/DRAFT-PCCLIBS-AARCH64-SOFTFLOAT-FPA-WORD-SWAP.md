# aarch64 软浮点误用 32 位 ARM 宏判断 FPA 双字序 → 双精度算术全错

> Draft: `DRAFT-PCC-LIBS-AARCH64-SOFTFLOAT-FPA-WORD-SWAP`
> 软件/版本：pcc-libs `1.2.0-devel-20211015`（分支 `feat/pcc-libs-1.2.0-devel-20211015`）
> 平台：HarmonyOS PC（aarch64，musl），clang 15，真机原生执行

## 基本信息

| 项目 | 内容 |
|---|---|
| 触发工具 | clang / gcc / make / conan |
| 阶段 | runtime / testing |
| 严重度 | 2（静默数值错误，非崩溃；但覆盖全部双精度运算） |
| 分类 | platform / portability / aarch64 / word-order / softfloat / abi |
| 复用价值 | 任意 32 位 ARM → AArch64 移植的软浮点或位布局代码 |

## 错误特征

无编译期报错。编译、链接、静态审查全部通过，**只有真机运行数值断言才暴露**：

```
addsf3  (单精度加法)  → 正确
adddf3  (双精度加法)  → 错误（垃圾值）
muldf3  (双精度乘法)  → 错误
divdf3  (双精度除法)  → 错误
ltdf2   (双精度比较)  → 恰好正确（见下"为何隐蔽"）
```

pcc-libs 真机实测：`addsf3` 正确而 `adddf3` 错误，是最典型的入手指纹——**单精度对、
双精度错**，直接把怀疑范围锁定到"双精度位模式的字序"。

匹配关键词：softfloat、libgcc soft-float、FPA、word swap、`__VFP_FP__`、`__ARMEB__`、
aarch64 double broken、adddf3 wrong、IEEE754 bit pattern swapped。

## 根因分析

为 32 位 ARM 编写的软浮点实现，用 `__VFP_FP__`（VFP 浮点字序）或 `__ARMEB__`（大端）
判断是否需对 double 做 FPA 风格的 32 位字交换：

```c
#if defined(__VFP_FP__) || defined(__ARMEB__)
#define FLOAT_WORD_ORDER_SWAPPED      /* FPA：高字在前 */
#else
#define FLOAT_WORD_ORDER_NATURAL
#endif
```

这两个宏属于 **armv7/arm32 的 ABI 宏集合**，AArch64 编译器（clang/gcc for aarch64）
**都不定义**。于是 `#if defined(...)` 恒为假 → 误入"需要字交换"分支 → 每个 double
位模式的高 32 位与低 32 位被对调后再参与运算。

本项目命中点：`libsoftfloat/arch/aarch64/aarch64-gcc.h`。

### 为何如此隐蔽（三层掩护）

1. **单精度免疫**：float 只有 32 位，"字交换"是恒等操作，`addsf3`/`mulsf3` 完全正常。
2. **比较函数幸存**：`__ltdf2`/`__gtdf2`/`__eqdf2` 的符号位在高字，交换后仍参与符号
   判定，很多输入下结果碰巧正确。
3. **编译期无痕**：`defined()` 判断是预处理期行为，不产生任何 warning；
   静态审查看到的是"完整且合理"的 `#if/#else` 结构。

结论：**代码审查、编译、乃至单精度测试都无法发现该问题**，必须对双精度做真机数值断言。

## 复现与定位

```bash
# 1) 免费信号：确认目标编译器不定义这两个宏
clang -dM -E -x c /dev/null | grep -E "__VFP_FP__|__ARMEB__|__ARMEL__"
#    aarch64 上无输出 → 源码里所有 defined() 判断必为假
# （对照：armv7 交叉工具链执行同一命令会命中这几个宏）

# 2) 静态排查可疑点
grep -rn "__VFP_FP__\|__ARMEB__\|__ARMEL__" <src>

# 3) 位模式往返（区分"逻辑错"与"字序错"）
#    取 1.5 的 IEEE754 双精度位模式 0x3FF8000000000000；
#    若某运算结果恰为该值的 32 位字对调形态，即确诊字序问题

# 4) 真机数值断言（本次实际采用，唯一可靠的确认手段）
conan create . -pr:h=<profile> -pr:b=<profile> --build='<pkg>/*'
#    → test_package 对 adddf3 / muldf3 / divdf3 / extendsfdf2 / truncdfsf2 数值比对
```

## 解决方案

把 `__aarch64__` 显式加入"自然序（不做 FPA 字交换）"的条件：

```c
#if defined(__VFP_FP__) || defined(__ARMEB__)
#  if !defined(__aarch64__)          /* ← 新增 */
#    define FLOAT_WORD_ORDER_SWAPPED
#  endif
#endif
/* 其余情况保持 NATURAL */
```

**为什么选"排除 aarch64"而不是"补定义缺失的宏"**：

1. `__VFP_FP__`/`__ARMEB__` 表达的是 arm32 ABI 的浮点寄存器字序；AArch64 的 AAPCS64
   本身即自然序。强行 `#define` 会污染同一头文件的其他 include 点。
2. 排除写法最小且局部，只改这一处判断，**不改变任何平台的既有行为**（32 位 ARM 路径
   逐字节不变）。
3. 与同族但不同的另一类修复互补：
   - 本条：治"**错误地认为需要交换**"（宏存在性判断失误）；
   - 另一类：治"**拿不到字序信息**"——编译器不定义 `__FLOAT_WORD_ORDER__` 时，
     回退到 `__BYTE_ORDER__`。

**排查纪律**：先做上面第 1、2 步锁定候选，再上真机断言确认，**不要仅凭代码审查下结论**
（第 3 节的"三层掩护"会让人误判为逻辑 bug 而改错方向）。

## 适用边界

- 命中前提：待移植代码用 arm32 专属宏判断 **double / long double 的字序或位布局**，
  且目标为 AArch64（或任何不定义这些宏的架构）。
- 若代码用 `__BYTE_ORDER__`/`__FLOAT_WORD_ORDER__` 等**通用**宏判断，则不属于本条。
- 若项目确实依赖 FPA 字序（例如与 32 位 ARM 二进制做位级交互），则不能简单改为自然序，
  需在边界处显式转换。
- 测试要求：必须覆盖**双精度**数值路径；仅测单精度或仅做编译验证会漏过本条。

## 关联

- 同族条目：编译器不定义 `__FLOAT_WORD_ORDER__` 时回退 `__BYTE_ORDER__`（符号位读取
  失效，表现为复数例程段错误）。
- 本次同一适配任务的另一条：签入的预生成 `configure` 与实际构建的双改问题。
