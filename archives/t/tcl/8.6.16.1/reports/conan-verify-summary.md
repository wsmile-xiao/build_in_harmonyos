# Conan Verify 真机验证摘要 — tcl 8.6.16.1

- **Verdict**: PASS
- **Reference**: `tcl/8.6.16.1@ohpcd/stable`
- **Profile**: ohos-aarch64
- **Date**: 2026-09-26T17:05:25（UTC+8）
- **环境**: HarmonyOS PC 真机 aarch64 / OHOS NDK clang 26.0.0.18 / Conan 2.29.1

## 门禁结果

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 预构建风险评估 | ✅ PASS | 知识图谱预查询 |
| G1 配方完整性检查 | ✅ PASS | 结构/MANIFEST 齐全 |
| G2 conan create 干净构建 | ✅ PASS | 构建 + 上游测试 + test_package |
| G3 系统同名库隔离 (R26) | ✅ PASS | libtcl8.6.so 动态形态 |
| G4 产物完整性检查 | ✅ PASS | bin/tclsh8.6、libtcl8.6.so、tclConfig.sh、lib/tcl8.6、lib/tcl8 齐备 |
| L2 平台功能矩阵 smoke test | ✅ PASS | tclsh8.6 实跑 |
| L4 静态安全扫描 checksec | ✅ PASS | |
| L5 产物基线对比 | ✅ PASS | DT_SONAME=libtcl8.6.so |

## 上游测试统计（G2 内 make test-tcl）

```
tcl/8.6.16.1@ohpcd/stable: L1_UPSTREAM_RESULT: files=1 total=47105 passed=43606 failed=55 file_errors=0 pass_rate=92.57%
tcl/8.6.16.1@ohpcd/stable: WARN: 规则 5 豁免: 55 项失败均为 OHOS HMDFS 沙箱环境差异(env/safe/filename/io/chan/link/zlib/filesystem/cmdAH/exec/iocmd,与 #3521 评审接受记录一致), passed=43606/47105 pass_rate=92.57%
```

- tests/ 全量 152 个 .test 文件（官方 tarball 实测），合计 47,105 用例；
- failed=55 全部命中环境失败白名单（HMDFS errno/ACL/symlink 语义），白名单外 0 失败；
- 本修订新增豁免 6 项：exec-9.1/9.2/9.5、exec-13.3、exec-14.4、iocmd-11.4（HMDFS 执行不存在命令返回 EACCES 而非 POSIX ENOENT，upstream_test.log 逐一核对同根因）。

## 消费者测试（test_package）

```
======== Testing the package: Executing test ========
tcl/8.6.16.1@ohpcd/stable (test package): RUN: tclsh8.6 ".../test_package/test_tclsh.tcl"
PASS tclsh8.6 consumer
```

- test.c（C API 7 断言）+ test_tclsh.tcl（tclsh 7 断言）= 14/14 通过。
