# DRAFT-ohos-libcxx-missing-std-views：OHOS libc++ 的 C++20 views 测试边界

## 现象

C++20 项目可能通过编译器语言模式检查，但 OHOS 设备附带的 libc++ 仍未实现完整的 C++20 ranges views。`#include <ranges>` 可以存在，而 `std::views::take` 仍可能在编译测试时报告 `no member named 'views' in namespace std`。

## 可复用处理

1. 先用目标 profile 的 clang++ 和 `-std=c++20` 编译最小 `<ranges>`/`std::views` 探针，区分语言模式、标准库实现和项目代码错误。
2. 如果缺失特性只出现在测试表达式而不是被测库公共实现，可用等价的手动有界迭代替换测试表达式，保持测试的输入、输出和覆盖意图。
3. 保留原始失败日志，在 notes/PR 中明确这是测试兼容补丁，不要宣称 OHOS 已完整支持所有 C++20 views。
4. 若库主体本身直接依赖缺失 views，则不能用测试替换掩盖 API 缺陷，应按完整证据转为部分/无法适配分析。

## 证据

- generator 0.4.0 的上游 tests/test.cpp 仅在 `iota` 用例中使用 `std::views::take`；OHOS Clang 15 + libc++ 的最小探针同样失败。
- 用有界 generator 迭代替换后，4 个上游 Catch2 用例、Conan verify、W3 和真实 test_package 均通过。

## 边界

这不是语言预检不匹配，不应记录为 `env_unsupported`；补丁必须限于测试表达式，不能删除测试或把空测试当成通过。
