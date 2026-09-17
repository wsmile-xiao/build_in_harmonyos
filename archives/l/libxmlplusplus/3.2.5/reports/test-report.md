# Test Report — libxmlplusplus 3.2.5

**Date**: 2026-09-16
**Build System**: Meson (MesonToolchain + PkgConfigDeps)
**Platform**: HarmonyOS PC aarch64 (clang 15.0.4, musl libc)

## 上游测试双口径台账

### 统计口径
- **source_declared_total**: 4 —— tests/meson.build 注册的独立上游用户测试用例
  （tests/ 下 4 个独立 main.cc 用户测试源，Makefile.am check_PROGRAMS 同源）
- **configured_executable_total**: 4 —— 当前 OHOS 配置（build-tests=true）实际
  实例化/注册的独立可执行用例数
- **executed_passed_total**: 4 —— 实际执行并全部通过
- **failed**: 0
- **uninstantiated**: 0

### 逐项映射（源码声明 → 构建条件 → 构建目标 → meson 注册 → 执行日志）
| # | 源码文件 (tests/) | 声明形式 | 构建目标 | meson test 注册 | 结果 | 证据 |
|---|-------------------|----------|----------|-----------------|------|------|
| 1 | tests/istream_ioparser/main.cc | meson.build test_programs + Makefile.am check_PROGRAMS | tests/istream_ioparser_test | 是 | ✅ PASS | meson test 1/4 |
| 2 | tests/saxparser_chunk_parsing_inconsistent_state/main.cc | 同上 | tests/saxparser_chunk_parsing_inconsistent_state_test | 是 | ✅ PASS | meson test 2/4 |
| 3 | tests/saxparser_parse_double_free/main.cc | 同上 | tests/saxparser_parse_double_free_test | 是 | ✅ PASS | meson test 3/4 |
| 4 | tests/saxparser_parse_stream_inconsistent_state/main.cc | 同上 | tests/saxparser_parse_stream_inconsistent_state_test | 是 | ✅ PASS | meson test 4/4 |

**通过率**: 4/4 源码声明（100%）；当前配置可执行集合 4/4（100%）。

### 非独立用例分类（不计入 source_declared_total）
| 类别 | 项数 | 说明 | 结果 |
|------|------|------|------|
| examples/ 示例程序 | 16 | meson.build 在 build-examples=true 时也注册为 test() 运行，但属样例非独立测试用例（任务口径：样例/基准不得误算） | 探索构建 16/16 全部运行 PASS |
| 框架/基座 | - | meson.build 顶层 testchar/testdict 仅当 libxml2 为 subproject 时注册；本配方 libxml2 来自 conan 依赖，不适用（xml2_is_subproject=false） | 不适用 |
| 文档/工具 | - | tools/（build_scripts、conf_tests）为构建辅助脚本，docs/ 为文档 | 非测试入口 |

### 上游测试执行证据
- conan-verify G2（conan create build() 内 meson test）4/4 OK：
  `reports/conan-create.log`（`Ok: 4 / Fail: 0`）
- 探索构建（build-ohos, build-examples=true + build-tests=true）20/20 OK：
  tests 4/4 + examples 16/16，日志 `$HOME/tmp/builds/libxmlplusplus-3.2.5.work/build-ohos/meson-logs/testlog.txt`

## HarmonyOS 专项测试
- 源码：`tests/ohos-libxmlplusplus-encoding/main.cpp`（UTF-8 中文解析/
  属性/序列化往返，3 组断言，非空壳；调用公开 API：DomParser/Element/
  TextNode/Node::get_children/write_to_string）
- 编译：cmake + pkg-config libxml++-3.0（仅公开 pc/头文件）
- 运行：PASS（exit 0），日志 `reports/ohos-encoding-test-run.log`
  （SHA-256 af2bfc7cbe36383733f991dd73a9052847ceb8258ef7e764ee1a41c0ee3480d9）

## test_package 消费者用例（R34 实质 API 测试）
- 源码：`test_package/test_libxmlplusplus.cpp`
- 断言：DomParser::parse_memory + parse_file + get_document +
  get_root_node + Element::get_attribute_value + Node::get_children（8 断言）
- 运行：`libxml++ 3.0 consumer OK: parse_memory + parse_file both pass`
  （conan-verify G2 test_package 阶段真实执行）

## 结论
上游测试 source_declared 4/4 全量通过；当前配置无未实例化或未运行项；
HarmonyOS 专项测试与消费者用例均 PASS。