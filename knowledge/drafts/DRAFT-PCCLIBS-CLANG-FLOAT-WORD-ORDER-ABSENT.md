# clang 不定义 `__FLOAT_WORD_ORDER__` → `__signbit{l,d}` 读到尾数位 → 复数例程段错误

> Draft: `DRAFT-PCC-LIBS-CLANG-FLOAT-WORD-ORDER-ABSENT`
> 软件/版本：pcc-libs `1.2.0-devel-20211015`（分支 `feat/pcc-libs-1.2.0-devel-20211015`）
> 平台：HarmonyOS PC（aarch64，musl），clang 15（OHOS SDK），真机原生执行

## 基本信息

| 项目 | 内容 |
|---|---|
| 触发工具 | clang（对照 gcc）/ make / conan |
| 阶段 | runtime / testing |
| 严重度 | 2（可致段错误，且符号判定静默出错） |
| 分类 | platform / portability / clang / byte-order / signbit / legacy-c |
| 复用价值 | 任意用编译器内建字序宏做位布局判断、且改用 clang 构建的项目 |

## 错误特征

无编译期报错；表现为**运行时符号判定错误**，进而在复数例程上崩溃：

```
__mulxc3 (long double complex 乘法) → SIGSEGV
__divxc3 (long double complex 除法) → SIGSEGV
__muldc3 (double complex 乘法)      → SIGSEGV
__signbitl(-inf)                    → 取到非 1 的错误结果
```

匹配关键词：`__FLOAT_WORD_ORDER__`、`__BYTE_ORDER__`、signbit、`__signbitl`、
`__signbitd`、mulxc3、divxc3、SIGSEGV、clang vs gcc macro。

## 根因分析

代码用 **GCC 内建宏** `__FLOAT_WORD_ORDER__` 判断浮点字序以定位符号位：

```c
#if __FLOAT_WORD_ORDER__ == __ORDER_LITTLE_ENDIAN__
#  define SIGNBIT_IS_HIGH_WORD   0
#else
#  define SIGNBIT_IS_HIGH_WORD   1     /* 非小端 → 符号位在高字 */
#endif
```

**clang 不定义 `__FLOAT_WORD_ORDER__`**（这是 GCC 的内建宏）。预处理阶段未定义标识符
在 `#if` 中按 **0** 计算，而 `__ORDER_LITTLE_ENDIAN__` 通常为 **1234**（不是 0），
于是 `0 == 1234` 为假 → 恒选 `#else`（"非小端"）分支。

结果：`__signbitl`/`__signbitd` 按错误的分支去取字，读回的是**尾数位**而非符号位。

### 与"FPA 字交换"不同（易混，需二分）

| | 本条 | FPA 字交换条 |
|---|---|---|
| 失效环节 | **取不到**字序信息（宏缺失） | **错误地认为**需要交换（arm32 宏误判） |
| 典型宏 | `__FLOAT_WORD_ORDER__` | `__VFP_FP__` / `__ARMEB__` |
| 表现 | 符号判定错 → 复数例程段错误 | 双精度全部算术返回垃圾（单精度正常） |

两者都静默、都只在运行时暴露，叠加出现时需分别用探针二分。

## 复现与定位

```bash
# 1) 免费信号：确认目标编译器是否定义该宏
clang -dM -E -x c /dev/null | grep FLOAT_WORD_ORDER
#    clang: 无输出（不定义）
gcc   -dM -E -x c /dev/null | grep FLOAT_WORD_ORDER
#    gcc:   __FLOAT_WORD_ORDER__ 1234   ← 有定义，故上游在 gcc 下正常

# 2) 注意枚举值陷阱：__ORDER_LITTLE_ENDIAN__ 通常为 1234，不是 0/1
clang -dM -E -x c /dev/null | grep -E "__ORDER_LITTLE_ENDIAN__|__BYTE_ORDER__"

# 3) 运行时探针（唯一可靠确认）
#    __signbitf/__signbitd/__signbitl: (+1.5)->0, (-1.5)->1, (-0.0)->1, (-inf)->1
#    再调用 __mulxc3 / __divxc3 确认不再 SIGSEGV

# 4) 静态定位
grep -rn "__FLOAT_WORD_ORDER__" <src>
```

## 解决方案

给出**带回退的派生宏**，优先专用宏、缺失时退回更普及的 `__BYTE_ORDER__`：

```c
#if defined(__FLOAT_WORD_ORDER__)
#  define PCC_FLOAT_WORD_ORDER  __FLOAT_WORD_ORDER__
#elif defined(__BYTE_ORDER__)
#  define PCC_FLOAT_WORD_ORDER  __BYTE_ORDER__      /* 浮点跟随字节序 */
#else
#  error "cannot determine float word order"
#endif
```

在比较处统一使用 `PCC_FLOAT_WORD_ORDER`。

要点：

1. **浮点字序在绝大多数平台（含 AArch64 / OHOS）与字节序一致**，因此回退到
   `__BYTE_ORDER__` 是安全且最小的修复。
2. **不要**用 `#ifdef` 直接判"小端"——必须与宏**值**比较（`__ORDER_LITTLE_ENDIAN__`
   为 1234，而非 0/1），否则会写出第二个等价陷阱。
3. 若确有"浮点字序 ≠ 字节序"的平台，在该派生宏处单独特判，不让通用路径承担风险。
4. 排查纪律：先 `-dM -E` 确认宏存在性，再上运行时断言；
   **不要**因为代码里有 `#if/#else` 看似周全就跳过验证。

## 适用边界

- 命中前提：代码用 `__FLOAT_WORD_ORDER__`（或其他**编译器专属**内建宏）判断位布局或
  字序，且缺少 `eliif` 回退；改用 clang 构建即触发。
- 若代码本就使用 `__BYTE_ORDER__` 等跨编译器通用宏，则不属于本条。
- 若项目仅在 gcc 下构建，本条不触发（但属潜在技术债）。
- 测试要求：必须覆盖**符号位**相关入口（`__signbit*`）与复数例程，
  仅跑普通算术断言会漏过。

## 关联

- 同族条目：aarch64 软浮点误用 32 位 ARM 宏 `__VFP_FP__`/`__ARMEB__` 判断 FPA 双字序
  （错误地认为需要交换，双精度算术全错）。
- 本次同一适配任务：签入的预生成 `configure` 与实际构建的双改问题。
