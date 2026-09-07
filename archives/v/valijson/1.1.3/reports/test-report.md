# valijson 1.1.3 上游测试报告

## 测试统计（双口径台账）

| 口径 | 数量 | 说明 |
|------|------|------|
| source_declared_total | 194 | 官方 tag 源码 `tests/test_*.cpp` 中 GTest `TEST/TEST_F/TEST_P` 宏声明总数（含条件编译的 Boost/Poco/Qt 适配器用例） |
| configured_executable_total | 187 | 当前 OHOS 配置（无 Boost/Poco/Qt）下 test_suite 实际注册并执行的用例数 |
| executed_passed_total | 185 | 实际通过 |
| failed | 0 | 实际失败 |
| skipped | 2 | 上游源码显式 `GTEST_SKIP`（默认 Validator 下正则鲁棒性用例会段错误/挂起，上游自行禁用） |
| not_built_declared | 9 | 因编译条件（Boost/Poco/Qt 未安装）未实例化的声明用例 |

## 逐项映射（声明 -> 构建条件 -> 目标 -> 注册 -> 执行）

- 25 个 `tests/test_*.cpp` 用户测试源全部计入 source_declared_total（194 个宏）。
- CMake `valijson_BUILD_TESTS=ON` 且无 Boost/Poco/Qt 时，`TEST_SOURCES` 实际编译 19 个文件：
  `test_adapter_comparison`(64)、`test_validator`(85)、`test_date_time_format`(1)、
  `test_double_parser`(2)、`test_fetch_*`(3×1)、`test_json_pointer`(2)、`test_json11_adapter`(2)、
  `test_jsoncpp_adapter`(2)、`test_nlohmann_json_adapter`(4)、`test_rapidjson_adapter`(2)、
  `test_picojson_adapter`(2)、`test_poly_constraint`(2)、`test_uri`(1，TEST_P 参数化展开为
  Rfc3986/ValijsonUriResolution 等 4 组参数化实例)、`test_validation_errors`(3)、
  `test_validator_with_custom_regular_expression_engine`(2，均 GTEST_SKIP)、
  `test_yaml_cpp_adapter`(3)、`test_utf8_utils`(3)。
- 未实例化 9 个声明：`test_boost_json_adapter`(3)、`test_property_tree_adapter`(2)（依赖 Boost）、
  `test_poco_json_adapter`(2)（依赖 Poco）、`test_qtjson_adapter`(1)+`test_qvariant_adapter`(1)（依赖 Qt，
  Qt6 下 qvariant 才加入），当前 OHOS 工具链无这些依赖，属真实互斥编译分支。
- 独立可执行 `test_rapidjson_crt_allocator`（0 个 GTest 宏，独立 main）另行编译运行，退出码 0。
- 构建目标：`test_suite` + `test_rapidjson_crt_allocator`（CMake `-Dvalijson_BUILD_TESTS=ON`）。

## 全量通过率

- 全量口径（发现总数=194）：`185/194 ≈ 95.4%`（2 skipped + 9 未实例化 + 0 failed，未计为通过）
- 实际执行口径（187 注册用例）：`185/187 ≈ 98.9%`（2 skipped 未计为通过，0 failed）
- 执行集合通过率（去掉上游自禁 skip）：`185/185 = 100%`

## 运行命令与证据

- 配置：`cmake -S . -B build-ohos -Dvalijson_BUILD_TESTS=ON -Dvalijson_EXCLUDE_BOOST=ON
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64`
- 构建：`cmake --build build-ohos -j2`
- 运行：`./test_suite` → 输出摘要 `[==========] 187 tests from 22 test suites ran.
  [  PASSED  ] 185 tests. [  SKIPPED ] 2 tests.` 退出码 0
- 详细日志：随最终回报 evidence（`log_path` + `log_sha256`）提交；`test_suite_run.log` SHA-256：`d07e451c6bf293b2aa0e63b4d198510c13ab05a46eea11a0721a175882973ddf`
- thirdparty 子模块按上游 v1.1.3 钉定 commit 版本还原（JSON-Schema-Test-Suite 等），测试数据与上游一致。
