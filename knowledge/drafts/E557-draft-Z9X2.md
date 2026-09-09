# E557 — libc++ 不完整标准库特性的 __has_include 误判：改用 __cpp_* 特性宏

## 问题概述

OHOS clang 15 自带 libc++ 中，`<format>`、`<ranges>` 等标准库头文件**物理存在但实现被抑制**（`_LIBCPP_HAS_NO_INCOMPLETE_FORMAT`、`_LIBCPP_HAS_NO_INCOMPLETE_RANGES`，对应 `__cpp_lib_format`、`__cpp_lib_ranges` 特性宏不导出）。上游 C++20/23 头文件级库惯用 `#if __has_include(<format>)` 作为特性开关并紧随其后特化 `std::formatter`，在该工具链上条件判真而特化写法与 libc++ 声明（`formatter` 为双模板形参且无默认 charT）不匹配——**`#include` 该库头的瞬间编译失败**，一行 API 没写的消费者也挂。

解法：把库头的特性门控从 `__has_include(<头名>)` 换成 `__cpp_lib_*` 特性宏判真。不完整 libc++ 上条件判假，功能优雅缺席但编译可用；完整实现上宏为真，行为与上游逐字一致。若上游测试文件本身已用特性宏守卫，把库头对齐到同款守卫即零语义差异的最小移植补丁（可回提交上游）。

## 典型错误

```
In file included from test.cpp:2:
include/boxed-cpp/boxed.hpp:215:13: error: explicit specialization of non-template struct 'formatter'
  struct std::formatter<boxed::detail::boxed<Type, Tag>> : std::formatter<Type>
include/boxed-cpp/boxed.hpp:215:13: error: out-of-line definition of 'formatter' does not match any declaration in namespace 'std'
include/boxed-cpp/boxed.hpp:215:62: error: too few template arguments for class template 'formatter'
include/boxed-cpp/boxed.hpp:219:21: error: too few template arguments for class template 'formatter'
4 errors generated.
```

触发条件：
- 工具链：OHOS clang 15.0.4 + libcxx-ohos（`-D_LIBCPP_HAS_NO_INCOMPLETE_FORMAT` 生效形态）
- 阶段：任何编译单元（含纯消费者 `#include <boxed-cpp/boxed.hpp>; int main(){}`）
- 与构建系统无关（cmake/autotools/meson/裸 clang++ 均可复现），与任务语言无关（只要头文件含该模式）

## 根因

1. libc++ 对 `<format>`/`<ranges>` 等采用"头先发布、实现分批补齐"策略：头可 include（`__has_include` 为真），但 `version` 头里的 `__cpp_lib_*` 宏被 `_LIBCPP_HAS_NO_INCOMPLETE_FORMAT` 等抑制为未定义。
2. OHOS SDK 的 libcxx-ohos（clang 15 基线）正处于不完整阶段：`std::formatter` 声明为 `template <class _Tp, class _CharT>`（无双默认实参形态），而 C++20 标准与完整实现允许 `formatter<T>` 单参特化。
3. 上游库以头可见性作为能力开关（`__has_include(<format>)`），开关语义与实现真实状态**不一致**：判真但特化不合法。
4. boxed-cpp 上游测试文件 test-boxed-cpp.cpp 自己用的是正确守卫 `#if defined(__cpp_lib_format)`——库头与测试文件守卫不同步，导致同一宏在头处误开、在测试处正确关。

## 适用范围

- 以 `__has_include`/头可见性作为标准库 C++20/23 特性开关，并依赖该特性标准形态 API（`std::formatter` 特化、`std::ranges` 适配等）的**头文件级库**；
- 目标工具链的 libc++ 处于 `_LIBCPP_HAS_NO_INCOMPLETE_*` 阶段（OHOS clang15 当前状态，亦见于旧 Android NDK libc++ 等）；
- 上游存在配套特性宏守卫（或可对齐到标准宏）时，改判据属零语义差异的最小移植补丁。

## 不适用范围

- 非 C++ 标准库特性（第三方可选功能探测仍用 `__has_include`，语义正确）；
- 头存在且 `__cpp_*` 宏也为真的完整实现环境（无需改动，改动也无损）；
- 库在判真后使用了该 libc++ 版本的非标准形态 API 且无法用单一宏收口 → 用 fallback 的探针矩阵逐点守卫；
- 任务声明语言与主源码/构建系统不匹配导致 env_unsupported 的场景（与 R47 语言例外无关，不得借此走路径 B）。

## 检测流程

1. **最小探针**（本机与目标 profile 各跑一次，记录 exit code）：

```bash
printf '#include <version>\n#include <ranges>\nint main(){ return\n#if defined(__cpp_lib_ranges)\n 0;\n#else\n 1;\n#endif\n }\n' | clang++ -std=c++20 -x c++ - -o probe; ./probe; echo exit=$?
```

- `exit 0`：头可见且特性宏在 → 完整实现，无需处理；
- `exit 1` 且 include 不报错：**头在但宏被抑制** → 本模式命中；
- `__cpp_lib_format` 同理换头名/宏名复测。

2. **命中判定**：目标工具链 include `<format>` 成功而 `defined(__cpp_lib_format)` 为假 → 任何以 `__has_include(<format>)` 守卫标准 formatter 特化的头都会编译失败。
3. **受影响面**：grep 上游（含其 vendored 第三方）头文件 `__has_include(<format>` 与 `std::formatter<` 组合出现点，逐处改判据。

## 方案

**rec（优先）**：守卫替换一行，保存为 portability 补丁，禁止平台宏：

```diff
-#if __has_include(<format>)
+#if defined(__cpp_lib_format)
 #include <format>
```

（若上游已有 `#elif __has_include(<fmt/format.h>)` 回退分支，保留不动；`fmt` 的探测语义正确。）

**fallback**：标准形态特化之外的多触点（如 `formatter` 模板参数数量不一致的派生用法），用探针矩阵逐点平台守卫降级，禁删功能/空壳 stub。

## 证据与验证

- **失败→修复最小复现**：boxed-cpp 1.4.3（contour-terminal）适配中，未打补丁时 `#include <boxed-cpp/boxed.hpp>` 的最小消费者 4 errors 失败；打 `0001`（`__cpp_lib_format` 守卫）后同最小消费者编译通过，上游 Catch2 v3 测试 14/14 实跑通过（21 assertions）。
- **绑定证据**：补丁文件 `archives/b/boxed-cpp/1.4.3/patches/0001-include-boxed-cpp-boxed.hpp.patch`；配方 `archives/b/boxed-cpp/1.4.3/conanfile.py`（BOXED_TESTING=OFF，package() 经 cmake.install 装头与 CMake config）；PR !8711 head `d309e18da7cefed85d322089f0e45e6e146af1a8`。
- **独立第二数据点**：同工具链探针实测 `__cpp_lib_ranges` 同样未导出（`<ranges>` 可 include 但探针 exit 1）——证明这是 libc++ 不完整阶段的**通用模式**，非 boxed 单例；任何 ranges 头文件用法命中同根因。
- **draft-review 查重**：与 E531/E548/E338 等现存条目关键词/签名不重叠（见 draft-review JSON 输出）。

## 解除条件与风险

- **解除**：OHOS SDK libc++ 升级到导出 `__cpp_lib_format`（实现完整、`std::formatter` 回归标准形态）后，本补丁仍无害；如需可向上游提交一行 PR 长期消除。
- **风险**：①`std::format`/formatter 能力在该工具链仍缺席（补丁只是"不误开"，不创造能力）——已作为"已知限制"写入归档 notes 与 PR 正文；②对 `__cpp_*` 宏语义的误用（手写伪造或 `-D` 注入）列为 forbid_2，防止把能力边界伪造成可用。
