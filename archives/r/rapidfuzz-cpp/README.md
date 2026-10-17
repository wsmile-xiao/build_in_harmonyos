# rapidfuzz-cpp

Rapid fuzzy string matching in C++（使用 Levenshtein Distance 及其他算法计算字符串相似度）。

- 官网: <https://github.com/rapidfuzz/rapidfuzz-cpp>
- 类型: header-only C++ 库（CMake INTERFACE target）
- License: MIT

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.3.4 | published | HarmonyOS PC (arm64) 适配完成，Conan 配方（ohpcd/stable） |

## HarmonyOS 适配说明

- `package_type=header-library`，无编译；拷贝 `rapidfuzz/**/*.hpp` 与 `*.impl` 头文件。
- 上游 21 个独立 TEST_CASE / 10 测试目标在 HarmonyOS arm64 主机全量通过。
- 消费者 test_package 实际调用 fuzz/distance API 断言通过。
