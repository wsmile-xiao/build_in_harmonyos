# DRAFT-icecream-cpp-1.0.0-libc-nullptr-format — OHOS/musl 系 libc 的 %p 空指针输出差异与上游测试断言平台适配

## 问题现象

icecream-cpp 1.0.0（C++ 单头文件调试打印库）在 OHOS PC aarch64（clang15 + libc++ + OHOS/musl 系 libc）
上运行官方上游测试，两处断言失败：

```
# test_c++11.cpp:789（float* v0 = nullptr; IC(v0);）
REQUIRE( str == "ic| v0: (nil)\n" )
with expansion:
  "ic| v0: 0\n"  ==  "ic| v0: (nil)\n"          # 实际输出 0，期望 (nil)

# test_c++11.cpp:805（std::unique_ptr<double> v0;）
REQUIRE( str == "ic| v0: (nil)\n" )             # 同上，实际输出 0

# test_clang.cpp:46
REQUIRE_THAT( str, Catch::Matches("ic\\| v0: \\{integers: \\[(0x)*[0-9a-fA-F]+, \\(nil\\)\\]\\}\n") )
# 实际输出 "ic| v0: {integers: [0x..., 0]}"，第二元素空指针输出 0 而非 (nil)
```

## 根因分析

- `printf("%p", nullptr)` 的输出是**平台 libc 行为**：glibc 输出 `(nil)`；OHOS/musl 系 libc 输出 `0`。
- 上游测试在 `#if !defined(__APPLE__) && defined(_LIBCPP_VERSION)` 分支硬编码 glibc 的 `(nil)`。
- OHOS 工具链使用 libc++（`_LIBCPP_VERSION` 已定义），但底层 libc 是 musl 系 → 测试必然失败；
  同一测试在 glibc 平台（libc++ + glibc）不受影响。**库逻辑本身无缺陷。**

## 解决方案

断言层最小平台适配（不改库逻辑、不禁用/排除测试）：

```cpp
// 修改前（libc++ 分支）：
REQUIRE(str == "ic| v0: (nil)\n");
// 修改后：
REQUIRE_THAT(str, Catch::Matches("ic\\| v0: (\\(nil\\)|0x0|0)\n"));
```

- 正则同时兼容 glibc `(nil)`、OHOS `0`、部分平台 `0x0`，glibc 平台行为不变（超集匹配）。
- 补丁标记 `platform_only=true`，PR「上游测试用例修改说明」如实记录。
- test_clang.cpp 同理：`\(nil\)` → `(\(nil\)|0x0|0)`。

## 验证证据

- 适配后复跑（clang++ 15.0.4，Catch2 v2.9.1 单头，Boost 1.90 头仅 test_c++11 需要）：
  - `test_c++11`：`All tests passed (115 assertions in 16 test cases)`，exit 0
  - `test_clang`：`All tests passed (4 assertions in 1 test case)`，exit 0
- 最小探针：`printf("|%p|", nullptr)` 在 OHOS 实测输出 `|0|`（glibc 为 `|(nil)|`）。

## 适用边界

- **适用**：libc++ + musl 系 libc（OHOS/HarmonyOS 等）平台上断言 `%p` 空指针输出格式的上游测试；
  头文件/库逻辑不受影响时均可按此模式做断言适配。
- **不适用**：库自身实现依赖 `%p` 具体输出（应改为平台无关格式化）；glibc 平台无需修改。

## 查重结论

- index.tsv grep `nil/%p/printf` 仅命中 musl 兼容类 E020/E026/E029/E032/E033/E039/E078
  （均为编译/链接/运行时崩溃场景，非 printf 输出格式断言差异）。
- graph engine 命中 E040（man-db NULL 解引用 SIGSEGV），场景不同。
- drafts 中 DRAFT-ghc-filesystem-1.5.14-ohos-filesystem-privilege-semantics 含 "nil" 但为
  filesystem 权限语义，正交。
- 未命中 → 新建本条草稿（路径 B）。
