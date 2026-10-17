# hat-trie

hat-trie 是 Tessil 提供的 C++11 header-only HAT-trie、字符串映射和集合库。
HarmonyPC 适配导出上游的 `tsl::hat_trie` CMake target，并保留 `include/tsl` 下的公开头文件。

## 版本

- 0.7.1：CMake header-only 包，Conan 引用为 `hat-trie/0.7.1`。
- 上游项目：[Tessil/hat-trie](https://github.com/Tessil/hat-trie)。

## HarmonyOS 适配

上游测试 CMake 使用 Boost.Test 的编译库入口。HarmonyPC 的 OHOS 构建将测试入口切换为
header-only `boost/test/included/unit_test.hpp`，并移除不可用的
`Boost::unit_test_framework` 链接路径；配方直接编译上游三个测试源，这些修改只作用于测试构建，不改变库头文件或测试断言。
Boost 1.90.0 只作为带 SHA-256 校验的官方测试源提供头文件，不成为消费者依赖或 Conan 依赖图节点。
