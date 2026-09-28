# DRAFT-fixed_point_arith-0.0-git9b5da0fa97-inline-gated-api-defines-injection: 头文件门控的 inline 公开 API —— Conan 配方必须通过 cpp_info.defines 注入门控宏

> Contributor: pc4-47 | Status: Draft | Updated: 2026-09-27
> Source: fixed_point_arith 0.0-git9b5da0fa97 适配（Path B 知识库扩展）
> 对应：`knowledge/drafts/DRAFT-fixed_point_arith-0.0-git9b5da0fa97-inline-gated-api-defines-injection.kv`

## 现象

fixed_point_arith（C 固定点运算库，Q 格式 + 向量 + 四元数）的公开 API 头文件
`include/fixed_point/fixed_point.h` 中，全部函数声明都位于

```c
#ifdef FXP_C99_INLINE
#include "inline/fixed_point.h"
#endif
```

之后（同构的 vector.h / quaternion.h 亦然）。即：**消费者不定义 `FXP_C99_INLINE`
该头文件就"只有宏和类型、没有任何函数声明"**。上游 Makefile 默认以
`-DFXP_C99_INLINE` 编译库本身（`CPPFLAGS += -DFXP_C99_INLINE`），README 亦把
`-DFXP_C99_INLINE` 作为默认用法（LTO 场景除外）。

若 Conan 配方的 `package_info()` 不把它带给消费者，消费者 test_package 里
`#include "fixed_point/fixed_point.h"` 后调用 `f_add()` / `f_mul()` / `q_rot()`
会得到**隐式声明/链接失败**，且错误信息与库无关，极难定位。

## 根因

这类库把 "inline 定义对外可见" 与 "C99 inline 语义" 用同一个宏门控：
- 库编译时定义宏 → `_FXP_INLINE_KW` 展开为 `inline`，`FXP_DECLARATION` 产生
  `extern inline`（C99）声明/定义，符号进入静态库（`nm` 可见 T 符号）；
- 消费者未定义宏 → 头文件整体跳过声明区，编译器对任何公开 API 调用都报
  "implicit declaration"（C89/C99 警告+链接失败）。

问题的本质是**公开 API 的存在性本身由编译宏决定**，且上游默认开启该宏。
Conan 配方作为库的使用契约，必须把"上游默认编译参数"完整传递给消费者，
否则包在语义上是不完整的。

## 解决方案

在配方 `package_info()` 中注入门控宏（与上游默认一致）：

```python
def package_info(self):
    self.cpp_info.defines = ["FXP_C99_INLINE"]   # 与上游 Makefile 默认 -DFXP_C99_INLINE 一致
    self.cpp_info.libs = ["fixed_point"]
```

要点：
1. **注入值必须与上游库编译时使用的值一致**（对 fixed_point_arith 是 `FXP_C99_INLINE`）；
   不一致会造成声明/符号语义分裂。
2. 若上游库按 LTO（不定义该宏）构建，则消费者也不应注入；配方应同步关闭。
3. 消费者测试（test_package / test_ohos）因此只需包含公开头文件即可编译运行，
   测试迁移性由配方契约保证——这也解释了为何 test.c 无需自行 `#define FXP_C99_INLINE`。

配套测试写法（Q1.15 固定点断言，见 C4）：
- 用上游常量 `FRAC_1_V`（=32767，非 32768）代替裸字面量，避免 int16 溢出
  （`32768` 隐式转换后变 `-32768`，断言莫名其妙失败）；
- 链式乘法/旋转有 ±1~2 LSB 舍入，用 `CLOSE(a,b,tol)` 容差断言；
- 用"两次旋转回到原点"这类不变量兜底验证，而不是只验证单次精确值。

## 验证

- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...` 通过；
- test_package/test.c 仅公开头文件 + 公开 API（f_add/f_neg/f_mul/f_to_df/df_to_f、
  v_add/v_sub、q_conj/q_rot），13 断言全绿；
- test_ohos/run_ohos_test.py T5 真实固定点计算（7 断言）+ T1/T2/T4 机器检查全 PASS；
- 日志：reports/conan-create.log、reports/w3-local-ci.log（W2/W3 通过）。

## 适用边界 / 反例

- **适用**：任何"C 库公开 API 声明位于 `#ifdef <宏>` 内且上游默认定义该宏"的库
  （固定点/向量/矩阵/数学内联函数头是典型）；
  也推广到任何"库头文件行为由编译宏切换、配方须传递上游默认"的情形。
- **反例 / 不适用**：公开声明无条件暴露的普通 C 库（extern 函数头）无需注入；
  若宏是构建期特性探测（如 HAVE_*，E151 场景），属库自身 build 逻辑，不通过
  cpp_info.defines 粗暴注入，否则可能误开启未实现特性。

## 关系

- `similar_to: []`（E151 是构建期特性探测，非消费者声明门控；E392 是 raw-makefile
  配方三要素，同源但不同层）
- `caused_by: []`；`prerequisite_of: []`；`conflicts_with: []`
- `combination_novelty: true`；`boundary_novelty: true`；`test_migration_novelty: true`