# rapidfuzz

Rapid fuzzy string matching for Python（使用 Levenshtein Distance 及其他算法计算字符串相似度）。

- 官网: <https://github.com/rapidfuzz/RapidFuzz>
- 类型: Python C 扩展（CMake 构建，Cython 预生成 .cxx）
- License: MIT

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.12.2 | built | HarmonyOS PC (arm64) 适配完成，Conan 配方（ohpcd/stable） |

## HarmonyOS 适配说明

- `package_type=library`，构建 5 个 CPython 扩展模块（fuzz_cpp / utils_cpp / process_cpp_impl / metrics_cpp / _initialize_cpp）。
- 依赖 `python/3.12.9`（Conan 管理的 OHOS aarch64 Python 运行时）。
- 上游 vendored `extern/rapidfuzz-cpp@3.2.0`（header-only C++ 核心）与 `extern/taskflow`。
- 消费者 test_package 通过 conan Python 3.12.9 真实导入 rapidfuzz 并断言 fuzz/distance/process/utils API（15 项断言）。
- 上游官方测试：sdist 的 `tests/` 逐字 vendor 进 `test_package/tests/`，由 `test()` 用同一解释器真实执行
  `python3.12 -m pytest tests/ -q`（18 个测试文件 / 129 个测试函数 / 386 个 pytest 用例项），
  并输出 `HMBS_UPSTREAM_TEST_RESULT` 标记（详见 `test_package/MANIFEST.yml` 与 `reports/test-report.md`）。
