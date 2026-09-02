# DRAFT-libmorton-0.2.12-m2d-32bit-decoding-boundary

> Contributor: pc1-21 | Status: Draft | Updated: 2026-09-01
> Source: libmorton 0.2.12 HarmonyOS PC 适配

## 现象

libmorton 0.2.12 的 2D 32-bit 解码函数 `m2D_d_for` 在编码/解码往返后产生**错误坐标**。
上游正确性测试 "32-bit using methods encode For and decode For" 失败：

```text
x: 00000000000000001011110111001000 (48584)
y: 00000000000000001010010100101101 (42285)
morton: 11001101011100110101100011100010(3446888674)
x_result: 00000000000000001011110111001000 (48584)
y_result: 00000000000000000010010100101101 (9517)   ← y 损坏
32-bit using methods encode For and decode For
Failed
++ ERROR: One of the correctness tests failed.
```

独立最小复现（控制位交错算法对照）确认：encode 正确
（`m2D_e_for` 与控制算法一致、128 随机样本控制解码 0 失败），
损坏完全发生在解码侧 `m2D_d_for`。

## 根因

`m2D_d_for` 使用含端点的循环上界，末次迭代对 32 位 morton 类型执行
**shift-by-width**（移位到类型自身位宽）未定义行为：

```cpp
template<typename morton, typename coord>
inline void m2D_d_for(const morton m, coord& x, coord& y) {
    x = 0; y = 0;
    unsigned int checkbits = sizeof(morton) * 4;          // 32-bit: 16
    for (unsigned int i = 0; i <= checkbits; ++i) {        // i 到 16
        morton selector = 1;
        unsigned int shift_selector = 2 * i;               // i=16 → 32
        x |= (m & (selector << shift_selector)) >> i;      // 1 << 32 (UB)
        y |= (m & (selector << (shift_selector + 1))) >> (i + 1);
    }
}
```

当 `morton` 为 32 位类型（如 aarch64/OHOS 上 `uint_fast32_t` = `unsigned int` 4 字节）时
`checkbits=16`，`i=16` 迭代执行 `1 << 32`——对 32 位无符号整型是未定义行为，
实测污染解码结果。64 位变体（`uint_fast64_t`）不受影响；x86-64 上
`uint_fast32_t` 为 8 字节，因此该缺陷在常见 x86 平台不暴露，仅在
fast 类型为 4 字节的平台上触发。

## 受影响行为

- 所有将 `m2D_d_for` 以 32 位 morton（4 字节）实例化的消费者：2D 32-bit Morton
  解码往返后 y 坐标损坏。
- 库为 **header-only**，缺陷位于公开头文件 `include/libmorton/morton2D.h`。
- 上游测试套件 `test/libmorton_test.cpp` 的正确性段能真实捕获该失败。

## 验证证据（OHOS aarch64，clang 15.0.4）

- 上游测试日志: `/storage/Users/currentUser/tmp/libmorton-src/ohos-test-r03.log`
  SHA256: `7db35fd5bf87863ba47a689dbe9aebe0f5ebc21a19b3f60f6f46093b91e65938`
- 修复前: 2D 32-bit For 往返 Failed；修复后: **12/12 正确性检查 Passed**（exit 0）。
- 最小复现: x=48584, y=42285 → morton=3446888674 → 修复前 `m2D_d_for` 解出
  x=1588361403, y=1（错误）；控制算法解出 x=48584, y=42285（正确）。
- 修复后相同样本解出 x=48584, y=42285；128 随机样本 0 失败。

## 方案（受限移植补丁）

在 `patches/0001-fix-m2d-d-for-loop-bound.patch` 中把循环上界改为不含端点：

```diff
-		for (unsigned int i = 0; i <= checkbits; ++i) {
+		for (unsigned int i = 0; i < checkbits; ++i) {
```

仅改变循环边界，跳过触发 shift-by-width UB 的末次迭代；不修改任何
坐标提取逻辑与测试断言。修复后上游测试 12/12 通过。

## 作用域与恢复/维护条件

- 作用域：仅限 `m2D_d_for` 32-bit 路径的循环边界；`m2D_d_for_ET` 的
  `checkbits` 语义不同（由最高位动态推导），保持含端点不变。
- 维护：上游若在后续版本修复该边界，可撤销此补丁；本补丁以
  `conandata.yml` patches 段声明，随配方一起维护。
- 禁忌：不得跳过/篡改上游正确性测试来规避；不得把修复伪装成通过。
- 未声称任何远端 PR、Issue、CI 或上游发布。