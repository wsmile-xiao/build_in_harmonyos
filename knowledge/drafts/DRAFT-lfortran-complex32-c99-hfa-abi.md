# DRAFT-lfortran-complex32-c99-hfa-abi（草稿）: LLVM 系编译器复数按值传递 ABI 统一（C99 HFA vs <2 x float> 向量）

> 事件族：aarch64 Linux 上 `float _Complex` 的 C99 ABI 是 HFA（d0,d1 双寄存器），
> 而 LLVM 系语言实现常以 `<2 x float>` 固定向量（单 d 寄存器）声明复数签名 → 实部幸存、虚部错位。
> 本条为 draft，编号由知识库主编确认，禁止直接 promote。

## 基本信息
- **严重度**: 2
- **类别**: abi, codegen, llvm, fortran, portability
- **principles**: P-TOOLCHAIN-001
- **similar_to**: DRAFT-lfortran-runtime-ohos-adaptation（同任务的运行时适配家族）
- **作者**: Hawkninja21
- **来源**: lfortran 0.64.0 适配（2026-09-28，C 类任务，真机验证进行中）

## 错误特征（预期签名）

```
ERROR STOP FAIL: C calling Fortran tests failed      ← bindc_iso_fb_05（bind(c) 按值复数）
C test failed with code: 18                          ← f25_conj 单测（虚部断言）
(14.1014204,0.00000000)                              ← tan((1.5,0.1)) 虚部读不到且随 -O 级非确定
declare <2 x float> @f25_conj(<2 x float>)           ← --show-llvm：签名用了向量
define { float, float } @f25_conj([2 x float] %0)    ← clang 同函数真实 C ABI
```

## 根因分析

1. **ABI 错位的本质**：AAPCS64 把 C99 `float _Complex` 归类为 HFA（Homogeneous Float
   Aggregate，2 个 float 成员）：实参走 `[2 x float]`（d0,d1 双寄存器），返回走
   `{float, float}`。而 lfortran LLVM 后端在「非 Windows、非 macOS_ARM」平台的 5 处
   complex32 签名分支统一用了 `<2 x float>` 固定向量——LLVM 把它当作单 d 寄存器向量。

2. **为何 x86 不暴露、aarch64 必暴露**：x86-64 SysV 对 `{float,float}`、`[2 x float]`、
   `<2 x float>` 三者 SSE 分类相同（都打包进 xmm0 低 64 位）——三种声明在 x86 上
   二进制等价，上游 CI（x86/glibc）永远测不出。aarch64 上向量=单 d 寄存器、HFA=双
   d 寄存器：调用 C 运行时复数数学包装（`_lfortran_ctan` 等 30 个 C99 complex 包装）
   与 bind(c) 按值复数子程序时，d0 低半（实部）幸存，d1（虚部）从未被写入/读取 →
   虚部=垃圾且随优化级非确定（真机实录 0.0/12.92/14.10 三种值）。

3. **上游分支结构**：5 处均为三路分支 `Windows → i64 / macOS_ARM → struct / else →
   vector`。macOS_ARM 分支本来就是 struct（Apple 打包聚合体），说明上游早已意识到
   ARM 上向量不可行——只是把「else」默认当成了 x86。

## 修复模式（可跨库复用）

把 kind-4 复数签名分支的 else 统一为 C99 HFA（与 macOS_ARM 分支逐字一致）：

```cpp
// 返回类型（llvm_utils.cpp get_function_type）
if (platform == Windows) { return_type = i64; }
else { return_type = getComplexType(4); }        // {float, float}

// 按值实参（bind(c) value 属性）
if (platform == Windows) { type = i64; }
else { type = ArrayType::get(FloatTy, 2); }       // [2 x float]

// abi_to_internal（调用外部复数函数后）
if (platform == Windows) { /* i64 → struct 解包 */ }
else { /* 直通，已是 {float, float} */ }
```

- **验证锚点**：目标平台 C 编译器对 `float _Complex` 的 LLVM 签名是唯一权威
  （`clang -S -emit-llvm`），语言实现的声明必须逐类型对齐。
- **回归防护**：x86-64 三种声明 SSE 分类等价 → x86 构建零行为变化（CI 绿即证）。
- **不动**：Windows i64 路径、kind-8（`{double,double}` 结构体已是正确 HFA）、
  SIMD 向量运算（FIXED_VECTOR_TYPE 在非签名场合合法）。

## 适用范围

任何「LLVM 系语言实现用固定向量声明 C 兼容复数类型」的 aarch64 Linux/OHOS 移植：
- Fortran 复数 bind(c) 互操作（flang、lfortran）；
- 复数数学运行时包装（clang 系前端的 complex 内建降级、FFI 按值复数参数）；
- 判别标准 = 平台 C 编译器 `float _Complex` 签名是否 `[2 x float]`/`{float,float}`。

## 验证记录

- 2026-09-28 真机（OHOS 6.0 / aarch64 / musl）：补丁 0006 应用后增量重编译，
  复现测试 15/17 绿——8 条复数数学内建（intrinsics_04s/18c/49/212/264/265/266/295）、
  bindc_iso_fb_01/05（"All tests passed"）、modules_15、F3/F4 测试树适配 4 条全过；
  剩 2 条为文档化排除（musl tgamma 尾差、上游 strlen codegen 缺陷），与 ABI 无关。
- 集成套件全量复跑（llvm + c 双后端）进行中，结果待回填。
