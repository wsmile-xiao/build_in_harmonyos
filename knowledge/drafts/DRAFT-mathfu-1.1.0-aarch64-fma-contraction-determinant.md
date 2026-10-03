# DRAFT-mathfu-1.1.0-aarch64-fma-contraction-determinant

- **草稿 ID**: DRAFT-mathfu-1.1.0-aarch64-fma-contraction-determinant
- **来源**: mathfu 1.1.0 HarmonyOS PC（aarch64）适配，上游 Google Test 三套件真跑
- **分类**: aarch64 / clang / floating-point / testing / portability
- **状态**: 本地草稿（pending-editor-review）

## 问题 / 错误签名

mathfu 上游单元测试在 OHOS aarch64（clang 15.0.4 -O2）默认编译下 3 例确定性失败：

```
unit_tests/matrix_test/matrix_test.cpp:377: Failure
Value of: matrix.InverseWithDeterminantCheck(&inverse_matrix)
  Actual: true
Expected: false
[  FAILED  ] MatrixTests.InverseNonInvertible_float_3
[  FAILED  ] MatrixTests.InverseNonInvertible_double_3
[  FAILED  ] QuaternionTests.Inverse
```

同一份源码在 x86_64（gcc/clang）上游 CI 全绿。

## 根因

1. **FMA 收缩默认开启**：aarch64 硬件有 `__ARM_FEATURE_FMA`，clang 默认
   `-ffp-contract=on`，把 `a*b+c` 融合为单步舍入的 FMA 指令
   （`__FP_FAST_FMA=1` 宏实证）。x86 无 FMA 默认收缩，行为分叉由此而生。

2. **测试依赖精确相消**：`InverseNonInvertible` 构造的矩阵 8 个元素为
   `kDeterminantThresholdSmall`、1 个为 `kDeterminantThresholdInverseLarge`，
   数学上两列成比例 → 行列式理论精确为 0。逐项 IEEE 754 舍入下部分积
   **精确相消**为 0；FMA 单步融合改变舍入路径，残留非零值越过
   `1e-7f`/`1e-15` 判定阈值 → 奇异矩阵被误判可逆。
   `QuaternionTests.Inverse`（q·q⁻¹ 与 identity 的容差比对）同理由累积
   舍入路径改变而超差。

3. **上游注释自认边界**：matrix_test.cpp 注释明示该类用例是
   "combination of huge and tiny values" 的精度边界设计——浮点收缩语义
   不受控时必然动摇。

## 最小修复方案

编译测试（及任何依赖精确浮点语义的库代码）时统一加 `-ffp-contract=off`：

```python
# archives/m/mathfu/1.1.0/conanfile.py — build() 直接编译上游测试翻译单元
base_flags = [
    "-std=c++11", "-O2",
    "-ffp-contract=off",   # 恢复 IEEE 754 逐步舍入，精确相消成立
    "-Wall", "-Wextra", "-Werror",
    "-Wno-deprecated-copy-with-user-provided-copy", "-Wno-deprecated-copy",
    "-DMATHFU_COMPILE_WITHOUT_SIMD_SUPPORT",   # vectorial 子模块不在 tarball
]
# OHOS：测试二进制 -static（SDK libc++.so 是链接器脚本，动态链接运行报符号缺失）
```

上游断言**原样保留**，未改任何容差或用例。

## 验证

- 加 `-ffp-contract=off`：vector 180/180、matrix 129/129、quaternion 16/16，
  **325/325 全过**（conan create RC=0，aarch64 原生执行）
- 对照复现：去掉该 flag 重编 → 上述 3 例**必现**失败（确定性，非随机）
- 复现命令：
  ```
  clang++ -std=c++11 -O2 -ffp-contract=off -DMATHFU_COMPILE_WITHOUT_SIMD_SUPPORT \
    -Iinclude -Iunit_tests -isystem <gtest>/include \
    unit_tests/matrix_test/matrix_test.cpp <gtest>/lib/libgtest.a \
    -lpthread -static -o matrix_test && ./matrix_test
  ```

## 降级方案

构建系统不允许动编译 flag 时：将 3 例登记 known_failures（附平台浮点语义
说明，322/325 申报）。下策——丢失真实平台差异的修复证据。禁止放宽断言
容差或删用例。

## 适用范围

所有"精确相消/紧容差往返比对"类浮点测试在 aarch64（FMA 硬件 + clang 默认
收缩）上的移植：矩阵求逆判定、数值恒等式往返、定点/浮点转换比对、ULP 级
golden 对比。同类库：Eigen、glm、cml、osg::Matrix 等线性代数/几何库的
test suite。E401（MLton golden-file）是"平台数学库结果变体"近亲，但那是
libm 差异；本条是**编译器收缩语义**差异，修复点在编译 flag 而非基线文件。
