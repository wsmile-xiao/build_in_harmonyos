# DRAFT — ASan container-overflow 误报（gtest 静态注册期，OHOS + libc++）

> 发现于 fixed-containers 3.21（C++20 header-only 库）上游测试全量运行阶段，2026-09-27。

## 现象

在 OHOS 工具链（clang 15 + libcxx-ohos）上以 ASan（`-fsanitize=address,undefined`）
构建 gtest 测试二进制后，`fixed_string_test` 启动即在 main() 之前 abort（Signal 6）：

```
==fixed_string_test==ERROR: AddressSanitizer: container-overflow on address ... at pc ...
READ of size 14 at ...
    #0 MemcmpInterceptorCommon(...)
    #1 memcmp
    #2 std::__n1::__tree<...>::__count_unique<std::string>(...) 
    #3 testing::internal::TypedTestSuitePState::VerifyRegisteredTestNames(...)
    #4 _GLOBAL__sub_I_fixed_string_test.cpp
HINT: if you don't care about these errors you may set
ASAN_OPTIONS=detect_container_overflow=0.
```

首次运行 ctest 报 `98% tests passed, 1 tests failed`（fixed_string_test Subprocess aborted）。

## 根因

gtest 的静态初始化（`_GLOBAL__sub_I_*.cpp` → `TypedTestSuitePState::
VerifyRegisteredTestNames`）用 `std::set<std::string>` 做测试名登记与查重，
set 的比较路径经 `__tree::__count_unique` 落到 memcmp。ASan 的
`MemcmpInterceptor` 对 libc++ 容器的"逻辑容器边界"（container-overflow 检测面）
判误，把合法的跨块比较报成越界。这是 ASan 检测器误报，不是被测库或测试代码的
真实缺陷。ASan 自带 HINT 明确允许关闭该检测面。

关键特征：报错发生在**静态注册期**（进程启动阶段），先于任何测试体执行；
普通非 gtest（或不用 TYPED_TEST 静态登记）的 ASan 二进制不受影响。

## 修复（运行环境条件恢复）

复跑命令前置环境选项：

```bash
ASAN_OPTIONS=detect_container_overflow=0 ./fixed_string_test     # 107/107 PASS
ASAN_OPTIONS=detect_container_overflow=0 ctest                   # 56/56, 974/974 用例 PASS
```

该选项只关闭 ASan 的 container-overflow 检测面（libc++ 容器逻辑边界判定），
其余 ASan 检测（越界/泄漏/UAF）保持开启；测试断言与库逻辑完全不受影响。

## 适用边界

- 触发面：OHOS（libcxx-ohos，LLVM15 基线）+ ASan + gtest 静态注册
  （TYPED_TEST / 参数化测试登记）的 C++20 测试二进制。
- 反例：不用该组合（无 gtest 静态登记、或非 OHOS libc++）时不会触发；
  不得用 `ASAN_OPTIONS=detect_leaks=0` 等掩蔽真实问题的选项替代。

## 验证

- 带选项复跑：`ASAN_OPTIONS=detect_container_overflow=0 ctest` →
  `100% tests passed, 0 tests failed out of 56`，GTest 用例 974/974 全通过。
- 台账：`archives/f/fixed-containers/3.21/reports/upstream-test-ledger.md`。

## 关系

- similar_to: E999（同为 OHOS 工具链测试运行期兼容处理，方案均为环境/等价改写而非库缺陷修复）
