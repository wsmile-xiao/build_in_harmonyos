# sqlitecpp 3.3.3 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64（OHOS clang 15 工具链 /data/service/hnp/bin）
- Conan 2.29.1（ohos-aarch64 profile）

## Verification

- `conan-verify sqlitecpp 3.3.3`: exit 0（G0-G4 + L2/L4/L5 全通过）
- `CI_PACKAGES="archives/s/sqlitecpp/3.3.3" bash ci/conan/build_and_test.sh`（W3 本地 CI 模拟）：exit 0
- L0（junk/原子性）: passed（含配方 13 文件，无框架文件）
- L1（L0 依赖）: passed
- L4（静态安全扫描）: passed
- L5（产物基线）: passed

## 上游测试（googletest，OHOS 工具链编译产物）

- 测试程序: `build-ohos/bin/SQLiteCpp_tests`
- 用例数: 49（Column 5 / SQLiteCpp 1 / Database 15 / Statement 16 / Backup 4 / Exception 4 / ExecuteMany 1 / Savepoint 1 / Transaction 1 / VariadicBind 1）
- Passed: 49 / Failed: 0 / Skipped: 0（[  PASSED  ] 49 tests.）
- 完整台账: reports/sqlitecpp-r01-tests-ledger.md

## test_package

`test_sqlitecpp.cpp` 创建内存库 → 建表 → 绑定插入 → 查询校验返回值（真实调用 SQLiteCpp API，非空壳）。

- ctest: `1/1 Test #1: test_sqlitecpp ... Passed`（conan create test 阶段）

## Result

配方在 OHOS aarch64 工具链下验证通过，可标记 published 状态。