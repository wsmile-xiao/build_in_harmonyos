# DRAFT-libmorton-0.2.9-decoding-boundary-recurring-tags

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-08
> Source: libmorton 0.2.9 HarmonyOS PC 适配（版本 bump 自 0.2.12 归档，配方沿用 + 逐 tag 重验）

## 现象（跨 tag 复发）

同一处 2D 32-bit 解码 off-by-one 缺陷，在两个发布 tag 的官方源码中**逐字相同**：

| tag | 发布时间 | `include/libmorton/morton2D.h` 解码循环 |
|---|---|---|
| v0.2.9 | 2022-02-17 | `for (unsigned int i = 0; i <= checkbits; ++i)` |
| v0.2.12 | 2023-05-24 | `for (unsigned int i = 0; i <= checkbits; ++i)`（逐字一致） |

即：上游在两 tag 之间**从未修复**该循环；0.2.12 归档可用的修复来自适配侧补丁
（`patches/0001-fix-m2d-d-for-loop-bound.patch`），不在上游源码内。因此对
header-only 位运算库做"沿用旧配方 + 只换 tag"的迁移时，缺陷会被原样带进新版本，
**必须**逐 tag 重新派发补丁并重跑上游正确性套件。

## 根因

`m2D_d_for` 使用含端点的循环上界，32 位 `morton` 实例上末次迭代执行
shift-by-width（移位到类型自身位宽）未定义行为：

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

当 `uint_fast32_t` 为 4 字节（OHOS aarch64、Windows LLP64）时 `checkbits=16`，
`i=16` 执行 `1 << 32` —— 对 32 位无符号整型是未定义行为，实测污染解码 y 坐标。
64 位 `morton` 变体与 `uint_fast32_t` 为 8 字节的平台（x86-64 SysV）不触发。

## 受影响行为（版本维度）

- **缺陷持续范围**：v0.2.9 与 v0.2.12 两份官方 tarball 均含相同循环。
- **迁移风险**：任何"抄旧版本配方换新 tag"的操作，若不重下 tarball / 重核 sha /
  重跑上游正确性测试，会把该 UB 静默带入（sha 或上游内容差异也会被吞掉）。
- 库为 **header-only**，缺陷即公开头源码，随版本延续。

## 验证证据

- 源码级（本 draft 作者已执行）：
  - `tar -xzOf v0.2.9.tar.gz libmorton-0.2.9/include/libmorton/morton2D.h` →
    `for (unsigned int i = 0; i <= checkbits; ++i) {`（第 260 行）；
  - v0.2.12 官方 tarball 同路径 → 同语句；`diff` 两 tag 此段为空。
- 补丁可应用性：`patch -p1 --dry-run` 在 v0.2.9 官方 tarball 上 APPLY_OK；
  应用后文件中仅剩 `m2D_d_for_ET` 一处含端点循环（该变体 checkbits 由最高位动态
  推导、语义不同，保持不改，与 0.2.12 处理一致）。
- 运行级：conan create 内嵌上游 `libmorton-test`（test/CMakeLists.txt 的
  `libmorton-test` 目标，剔除非可移植的 bmi2/avx512/zen2 变体），在 OHOS aarch64
  CI 实跑 12/12 正确性检查作为本任务的 L1 门禁（与 0.2.12 归档同一套件）。

## 方案（随配方延续的受限补丁）

在 `conandata.yml` 的 `patches` 段声明，对 0.2.9 逐 tag 重新应用：

```diff
-		for (unsigned int i = 0; i <= checkbits; ++i) {
+		for (unsigned int i = 0; i < checkbits; ++i) {
```

只改循环边界，跳过触发 shift-by-width UB 的末次迭代；不触及任何坐标提取逻辑与
测试断言。修复经上游 12/12 正确性测试验证。

## 作用域与维护条件

- 作用域：`m2D_d_for` 32-bit 路径的循环边界；`m2D_d_for_ET`（最高位动态推导
  checkbits）语义不同保持含端点。
- 维护：上游若在后续版本修复此边界，可撤销补丁；补丁由 conandata.yml patches
  段声明、随配方逐 tag 维护。
- 禁忌：不得跳过/篡改上游正确性测试；不得机械拷贝其他版本配方而不逐 tag 重验。
- 本条目侧重**版本延续性**知识（header-only 位运算库 tag 升级不携带修复、
  补丁必须逐 tag 重派）；具体数值级证据见 similar_to 的
  `DRAFT-libmorton-0.2.12-m2d-32bit-decoding-boundary`。
