# libmwaw 0.3.23 测试报告

- 适配轮次: 2026-09-19/20（finish 内嵌 W3 本地 CI 模拟，私有 CONAN_HOME）
- 上游版本: 0.3.23（SourceForge 官方源）
- 验证环境: OHOS 6.0 arm64, clang 15, conan 2.29.1，profile ci/conan/profiles/ohos-aarch64
- 包形态: 默认静态库变体（--enable-static --disable-shared），--disable-tools

## 上游测试清点（R51 第一步）

| 清点项 | 结果 |
|---|---|
| tests/ 目录 | 不存在 |
| Makefile.am 注册 check_PROGRAMS/TESTS | 无（`find . -name Makefile.am \| xargs grep -l "check_PROGRAMS\|TESTS"` 无输出，0.3.23 解压树实测） |
| make check 入口 | 上游无可运行测试入口 |
| 结论 | 上游无自动化测试套件（与 libmwaw-tools/0.3.22 同上游项目结论一致） |

上游测试计数：N=0（无可运行测试入口），通过率 0/0（不适用）。

## 适配后验证（R51 第二步，实际执行）

| 执行项 | 结果 |
|---|---|
| conan create libmwaw/0.3.23（补丁应用 + staging + configure + make） | PASS |
| test_package 构建（CMakeDeps/CMakeToolchain，mwaw_api_test 链接 libmwaw） | PASS |
| 断言 1: 非 Mac 载荷被拒绝（confidence=NONE） | PASS |
| 断言 2: 空流被优雅拒绝（confidence=NONE） | PASS |
| 断言 3: CDF 头分类结果合法（无崩溃） | PASS（libmwaw API test completed） |

- 断言计数: 4 个 CHECK 断言全部通过（第三处为复合条件，覆盖 2 个比较判定）；消费者用例 1/1 通过
- conan-verify 门禁: G0/G1/G2/G3/G4/L2/L4/L5 全部 passed（verdict=PASS），证据见同目录 conan-verify-report.json / conan-create.log
- W3 完整日志归档: `reports/w3-local-ci.log`（sha256 登记于 `.ci-result.json` 的 log_sha256 字段）

## 计数口径说明

- 上游分母 0：源码树无任何测试注册（证据见上），不与消费者用例混加
- 鸿蒙特有测试 1 个（test_package 消费者用例 mwaw_api_test），不计入上游分母
