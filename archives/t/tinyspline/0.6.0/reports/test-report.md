# tinyspline 0.6.0 测试报告

## 上游测试（Step 2 实测，CTest）

| 测试 | 结果 | 耗时 |
|------|------|------|
| tinyspline_tests（C API 全量） | ✅ PASS | 6.76s |
| tinysplinecxx_tests（C++ API 全量） | ✅ PASS | 0.46s |

**结论**: 2/2 通过，0 失败。

命令（cwd: `/storage/Users/currentUser/tmp/builds/tinyspline-0.6.0.work/build`）:
```
ctest --output-on-failure
100% tests passed, 0 tests failed out of 2
```

## test_package 消费者测试（conan create 内）

| 测试 | 结果 |
|------|------|
| test_tinyspline（创建/求值 B-spline 并转 Bezier，断言非 NULL） | ✅ PASS 0.03s |

命令（conan create 自动执行）:
```
1/1 Test #1: test_tinyspline ... Passed 0.03 sec
100% tests passed, 0 tests failed out of 1
```

## W3 本地 CI 模拟（finish step 5/10）

- setup.sh: ✅ 通过
- build_and_test.sh tinyspline/0.6.0: ✅ 通过（JC 以 PR-diff 语义隔离基线其他库遗留后）
- `.ci-result.json` exit_code=0，log_sha256=74f76790b9edc101ade9cedb3bfa6424ca35ba24df8c446648241d561dad88f9

## Conan 配方验证（conan-verify 8 门禁）

G0 预构建风险: ✅ PASS
G1 配方完整性: ✅ PASS
G2 conan create 干净构建: ✅ PASS（E017 ghfast 镜像注入后恢复官方 URL）
G3 系统同名库隔离: ✅ PASS
G4 产物完整性: ✅ PASS
L2/L4/L5 smoke/安全/基线: 通过（详见 reports/conan-verify-report.md）

## 结论

所有适用测试与门禁通过；上游 2 项测试与 test_package 消费者测试均无失败，测试统计以实际执行为准（2/2、1/1）。
