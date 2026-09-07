# DRAFT-icecream-cpp-1.0.0-cpp20-ranges-toolchain-gap — OHOS SDK clang15 libc++ 缺 C++20 std::views 的处理模式

## 问题现象

icecream-cpp 1.0.0 官方上游测试 `test_c++20.cpp` 在 OHOS PC aarch64
（OHOS SDK 26.0.0.18、clang 15.0.4、libcxx-ohos）上编译失败：

```
test_c++20.cpp:32:25: error: expected namespace name
    namespace rv = std::views;
               ~~~~~^
# 后续 6 处均因 rv 未声明连锁报错
```

最小探针复现：

```cpp
#include <ranges>
namespace rv = std::views;   // error: expected namespace name
```

## 根因分析

- OHOS SDK 26.0.0.18 自带 **libc++（libcxx-ohos）未提供 C++20 `<ranges>` views**：
  `#include <ranges>` 可用，但 `std::views` 命名空间缺失。
- 属**工具链缺项**，非库缺陷：icecream.hpp 自身对 ranges 的使用以
  `__cpp_lib_ranges` 守卫，头文件在 C++23（c++2b）下可正常编译（test_c++23 通过）。
- 只有直接依赖 `std::views` 的测试文件（test_c++20.cpp）编译失败。

## 解决方案

1. **台账如实归类**：全量枚举测试入口 → 逐项尝试运行 → 对依赖 std::views 的用例标记
   `blocked_toolchain`，写明首个错误、命令、退出码、恢复条件（工具链升级提供 C++20 ranges 后重跑）。
2. **不把工具链阻塞伪装为库缺陷**：不得通过改测试、删用例或伪造通过率掩盖。
3. **配方侧**：头文件库无编译产物时 `BUILD_TESTING=OFF`，由 test_package 承担消费者验证
   （R34 实质调用被测库 API）；头文件 ranges 用法确认有 `__cpp_lib_ranges` 守卫。

## 验证证据

- `tests/test_c++20.cpp:32` 编译错误日志：`$TMPDIR/icecream-cpp-r01-logs/upstream-test-c++20-c++20.log.compile`
- 最小探针复现（`<ranges>` + `std::views` → expected namespace name）
- 同工具链对照：`-std=c++2b` 下 `test_c++23` 通过（1 test case）；`icecream.hpp` 无 ranges 编译错误
- 通过率口径：全量 9/14=64.3%（未实例化/硬阻塞计入分母）；当前配置可执行集 9/10=90.0%

## 适用边界

- **适用**：OHOS/HarmonyOS（SDK 26.0.0.18 clang15/libc++）上依赖 C++20 ranges 的上游测试与库，
  以及任何"工具链特性缺失 → 测试硬阻塞"的归类处理模式。
- **不适用**：非 OHOS 工具链（如新版 OHOS SDK 或 LLVM≥16 libc++ 已含 ranges）；
  库本体需要 ranges 且未守卫的场景（应另行评估适配方案）。

## 查重结论

- index.tsv：E292（ranges 关键字）为 Arrow 分层 ctest 迁移场景，不同。
- knowledge/doc/、graph、drafts（66 条）：无 OHOS libc++ 缺 std::views 条目。
- 未命中 → 新建本条草稿（路径 B）。