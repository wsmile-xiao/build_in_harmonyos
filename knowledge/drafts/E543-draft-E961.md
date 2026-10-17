# E543 — Widen uniform_int_distribution to int for narrow integer types on libc++

## 症状

```
__random/uniform_int_distribution.h:162:5: error: static assertion failed due to
requirement '__libcpp_random_is_valid_inttype<char>::value':
IntType must be a supported integer type
```

libstdc++（GCC、Linux 上 Clang 默认）下同一源码编译通过。

## 根因

libc++ 按 [rand.req.dist] 的 IntType 要求加 `static_assert`（`__libcpp_random_is_valid_inttype`）：只接受
`short/int/long/long long` 及其 unsigned 变体；`char/signed char/unsigned char/char8_t` 在编译期被拒绝。
libstdc++ 不做该检查，因此“上游在 GCC 上能编过”不代表 libc++ 可用。

## 已验证方案（libasd 1.5.6 test_read_binary_as / test_write_as_binary）

小整型把分布加宽为 `int` 并回转，值域与语义不变：

```cpp
using dist_type = std::uniform_int_distribution<
    typename std::conditional<(sizeof(T) < sizeof(int)), int, T>::type>;
dist_type distro(std::numeric_limits<T>::min(), std::numeric_limits<T>::max());
return static_cast<T>(distro(rng));
```

验证：libasd 6/6 上游 Boost.Test 在 OHOS PC 设备全部通过（见归档 reports/upstream-boost-test-ctest.log）。

## 适用边界与反例

- 仅适用于 [min(T),max(T)] 能被 int 覆盖的窄整型；`sizeof(T) >= sizeof(int)` 时保持 `T`。
- 与 E321 不同：E321 是运行期伪随机字节序列跨标准库不一致（mt19937_64 输出标准指定但分布映射实现定义）；
  本条是编译期类型拒绝。两者常在同一批上游测试中先后出现。

## 禁止

- 换 `-stdlib=libstdc++` 掩盖（破坏目标平台 ABI，CI 无法复现）。
- 删除受影响测试用例（静态分母缩水且无理由）。
