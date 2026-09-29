# qwinff 0.2.1-git20201215 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 (clang 15.0.4, profile ohos-aarch64)
- Conan 2.29.1, qt5-qtbase/5.15.2.2
- Source: QWinFF git snapshot 17e987e7c72affb7acdc67e95aae07e4bbfe93f2 (pre-2020-12-15 master)

## Verification

- `conan-verify qwinff 0.2.1-git20201215`: exit 0
  - G0 PASS / G1 PASS / G2 PASS (clean conan create) / G3 PASS / G4 PASS
  - L2 (platform smoke) PASS, L4 (checksec) PASS, L5 (baseline) PASS
- `ci/conan/build_and_test.sh` (W3 local CI simulation): PASS, 100% (1/1)
  - L0 PASS (recipe/structure checks)
  - L1 PASS (upstream tests + test_package executed)
  - L2 skip: GUI 应用无 -v/--version 类 CLI 输出，version/help 冒烟不适用
  - L4 warn: 补丁中含 `set(CMAKE_AUTOUIC ON)` 等关键字误报（非危险函数调用）
  - L5 PASS (bin/ has content)

## Upstream tests (R51 三步法)

- 清点: `src/tests/` 包含 2 个 QtTest 单元测试
  - testversioncompare: initTestCase / testVersionEquality / testVersionInequality /
    testVersionSingleRange / cleanupTestCase（13 处 QCOMPARE/QVERIFY 断言）
  - testupdateinfoparser: initTestCase / testParseXml / cleanupTestCase（4 处断言）
  - 上游 `run-tests.sh` 逐目录构建并运行；conanfile 中 `upstream_check_command` 已声明
- 运行: test_package 在 OHOS aarch64 上重建两测试（Qt5::Test），`QT_QPA_PLATFORM=offscreen` 执行
- 结果:
  - `TestVersionCompare` Totals: **5 passed, 0 failed, 0 skipped**
  - `TestUpdateInfoParser` Totals: **3 passed, 0 failed, 0 skipped**
  - 通过率 **8/8 = 100%**

## Package smoke (R34)

- 打包产物 `bin/qwinff`（ELF aarch64，rpath 指向 qtbase lib）存在且可加载
- 数据文件 `share/qwinff/{presets,constants}.xml` 已随包安装（DATA_PATH 注入）

## Result

qwinff 0.2.1-git20201215 recipe verified on OpenHarmony aarch64; eligible for
published status.
