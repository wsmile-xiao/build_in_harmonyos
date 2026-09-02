# semver 0.3.0 测试报告

## 本地验证结果（R07 就绪审计, 非远端交付）

- **上游测试**: `test/test.cpp` 5 个 TEST_CASE 逐入口实际运行全通过, 全量 **57396 assertions in 5 test cases**
  - constructors: 5 assertions ✅
  - operators: 57202 assertions ✅
  - from/to string: 137 assertions ✅
  - ranges: 14 assertions ✅
  - ranges with prerelase tags: 38 assertions ✅
  - 运行命令: `/data/service/hnp/bin/clang++ -std=c++17 -I<...>/include -I<...>/test/3rdparty/Catch2 <...>/test/test.cpp -o test_semver_upstream` + `./test_semver_upstream <entry>`（OHOS clang 15, aarch64）→ RC=0
  - 证据日志: `reports/gate-upstream_tests.log` sha256=`ab9eb276be3c31b66ea85a198485db2c8f4709f82696b0194e3efce01c336b7c`
- **Conan / test_package**: `conan-verify` G0-G4 全 PASS（G2 `conan create` 成功, 含 test_package 消费者测试; G3 无系统同名库冲突; G4 产物完整; L2/L4/L5 因无 cache 路径跳过）→ RC=0, 可标记 published
  - 证据日志: `reports/gate-conan.log` sha256=`2250edeed1214512eee5ddb58e673d466906a38f1a79d1a11e7926d4270e3c6f`
- **鸿蒙特有测试**: `hmos_test.cpp` 实际调用 semver API 验证 OHOS 平台行为
  - `__OHOS__/__OHOS_FAMILY__`=1（OHOS clang 工具链定义）
  - C++17 库特性 string_view/optional=1
  - semver 运行时解析/比较/范围匹配值正确
  - `/proc/self/maps` 确认 `libc++_shared.so` 动态加载=1
  - → PASS, 运行 RC=0; 证据日志: `reports/gate-hmos_test.log` sha256=`1464592b97a26d78ae7d06b67fc28c96bac89ad6fc67447f6daa64fdecffc5e6`

## 统计汇总

| 测试层 | 入口/项 | 结果 |
|--------|---------|------|
| 上游测试 | 5 TEST_CASE / 57396 assertions | 全过 |
| Conan L1 消费者 | test_package 编译+运行 | 通过 |
| 鸿蒙特有测试 | 平台+运行时行为断言 | PASS |

## 说明
- 本报告仅基于实际运行的测试命令、统计与日志生成, 未伪造、未复制无关库报告。
- header-only 配方（package_type=header-library）无编译产物/可执行文件, `packaging/` 与 `.staging-verified` 判定不适用, 不产生伪制品。
