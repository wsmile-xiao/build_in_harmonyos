# aarch64 / HarmonyOS PC long double 尾数超出 ull → 尾数存储拓宽到 unsigned __int128

> 草稿（pending-editor-review）｜源自 wide-integer 1.01 HarmonyOS PC 适配
> 关联 KV：`DRAFT-wide-integer-1.01-long-double-mantissa-storage.kv`

## 问题

在 aarch64（HarmonyOS PC）上编译 wide-integer 上游测试时，`test/test_uintwide_t_edge_cases.cpp`
构造 `uintwide_t(inf_ld)` 触发模板实例化 `detail::native_float_parts<long double>`，命中编译期断言：

```
./math/wide_integer/uintwide_t.h:1985:7: error: static assertion failed due to
requirement 'std::numeric_limits<long double>::digits <=
std::numeric_limits<unsigned long long>::digits':
Error: The width of the mantissa does not fit in unsigned long long
```

## 根因

| 平台 | long double 形态 | 尾数位数 | 是否适配 unsigned long long |
|---|---|---|---|
| x86-64 (Linux/Windows) | 80-bit 扩展精度 | 64 | ✅ 恰好 |
| aarch64 Linux / HarmonyOS PC | IEEE quad | 113 | ❌ 超出 |
| float / double（所有平台） | — | 24 / 53 | ✅ |

库的 float→bigint 转换路径用 `unsigned long long` 固定承接浮点尾数并写死
`static_assert(digits <= 64)`。x86-64 恰好满足；aarch64 上 long double 为
IEEE quad（`LDBL_MANT_DIG=113`），实例化即编译失败。这是平台差异而非库逻辑错误
——上游头文件注释也声明"需验证尾数能放入 unsigned long long"。
即便该构造运行期只处理非有限值（inf 走 `isfinite` 先行分支），模板实例化仍会触发断言。

## 方案

将尾数存储类型从固定 `unsigned long long` 改为按浮点类型 `digits` 条件选择：

```cpp
using mantissa_storage_type =
  typename std::conditional<(std::numeric_limits<FloatingPointType>::digits
                               > std::numeric_limits<unsigned long long>::digits),
                            unsigned __int128,
                            unsigned long long>::type;
```

同时：
1. static_assert 改为对 `mantissa_storage_type` 校验；
2. 归一化位移 `my_mantissa_part |= (1 << (digits-1))` 改用 `mantissa_storage_type`，
   避免 113 位移位在 64 位类型上的未定义行为；
3. `get_mantissa()` 返回类型与成员类型同步为 `mantissa_storage_type`。

float(24)/double(53)/x86-64 long double(64) 不受影响（仍走 ull 分支）；
任何 digits>64 的浮点平台（aarch64 Linux/OHOS、arm64 macOS）自动走 `__int128` 分支。

## 验证

- 环境：OHOS clang 15（`aarch64-unknown-linux-ohos`），`-DWIDE_INTEGER_HAS_LIMB_TYPE_UINT64`
- 补丁后编译全部上游测试通过，运行 **30/30 通过**（exit 0）：
  - `test_uintwide_t`（28 个 run() 测试函数）日志 SHA-256 `5e16466693da1b0a91939bac09e8dd694ab029b7cf189f717c28f26616bf315f`
  - `test_xtra_from_issue_335` 日志 `9f6d29b0b76d8348d6677de434ff451a4b3e8dbdbdc469a0338dd77006db0271`
  - `test_boost_backend_via_test_arithmetic`（No errors detected）日志 `063a32d3d02a8f9581405b89d88f6f330fb3828fed4233d8fc21bfd8732a8dea`
- 鸿蒙专项测试 `HARMONYOS_SPECIFIC_TEST: PASS`（日志 `ce8a199d8629185f835de2768f07d1766e6a4dcd0756224eb49875b00361c308`）
- 消费者用例 `CONSUMER_RESULT=OK`（日志 `f4e6be973aea4e6ca60d20b232b65ebf010a0229422fbaf2b93df3349e6388fe`）
- conan-verify G0-G4/L2/L4/L5 通过；W3 本地 CI 模拟通过（`.ci-result.json` exit_code=0）

## 适用边界与反例

- 适用：任意精度整数库（uintwide_t/decwide_t/boost::multiprecision backend 等）的
  float/long double 构造或转换路径，在 long double 尾数 > 64 位的平台上编译失败。
- 反例/不适用：float 与 double 路径（digits≤53）不受影响；x86-64 上 long double 尾数恰为 64，
  原实现可用；若库禁止改动公共头，可用平台宏关闭 float 互操作（不推荐，会连带关闭精度路径）。

## 查重摘要（七轴）

- exact_duplicate 否 / causal_duplicate 否（E388 为 Boost.Math 数值收敛，因果链不同）
- trigger_overlap 部分（同 aarch64 long double 平台面，错误签名/阶段不同）
- solution_overlap 否 / combination_novelty 是 / boundary_novelty 是 / test_migration_novelty 是
- similar_to: E388, DRAFT-E999-ohos-musl-long-double-double-alias

## 相关链接

- 适配归档：`archives/w/wide-integer/1.01/`（conanfile.py / patches/0001-… / notes.md / reports/）
- 知识候选台账：见适配归档 `reports/knowledge-candidate-ledger.md`（本地验证报告，随任务回报提交）
