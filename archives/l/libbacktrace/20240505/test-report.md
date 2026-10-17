# Test Report — libbacktrace 20240505

**Date**: 2026-09-02
**Build System**: Autotools（conan create 干净构建，ohos-aarch64 profile）
**Upstream Suite**: `make check`（conanfile build() 内执行）

## Test Results

**Total Tests**: 33
**Passed**: 33 (100%)
**Failed**: 0
**Skipped**: 0

```text
Testsuite summary for libbacktrace 20240505
# TOTAL: 33
# PASS:  33
# FAIL:  0
# SKIP:  0
# XFAIL: 0
# ERROR: 0
```

### 上游测试全量清单（33 项，全部 PASS）

1. allocfail.sh（OOM 回退）
2. test_elf_32 / 3. test_elf_64 / 4. test_macho / 5. test_xcoff_32 / 6. test_xcoff_64 / 7. test_pecoff / 8. test_unknown（8 项格式 fileline/syminfo）
9. unittest / 10. unittest_alloc
11. btest（26 处断言）/ 12. btest_lto / 13. btest_alloc
14. stest / 15. stest_alloc
16. ztest / 17. ztest_alloc
18. zstdtest / 19. zstdtest_alloc
20. edtest / 21. edtest_alloc
22. ttest / 23. ttest_alloc
24. dwarf5 / 25. dwarf5_alloc
26. mtest
27. xztest / 28. xztest_alloc
29. b2test_buildid / 30. b2test_buildidfull / 31. btest_gnudebuglink / 32. btest_gnudebuglinkfull / 33. mtest_minidebug

### 适配修改轮次（13 FAIL → 7 FAIL → 0 FAIL）

- 首轮（无适配参数）：20 PASS / 13 FAIL
  - 8 项栈帧断言失败（clang 忽略 `noclone`，sibling-call/omit-frame-pointer 优化合并帧）
  - 5 项 objcopy 派生二进制 exit 126（`.codesign` 失效，Operation not permitted）
- 第 2 轮（测试编译追加 `-fno-optimize-sibling-calls -fno-omit-frame-pointer`）：28 PASS / 5 FAIL（仅剩 objcopy 派生类：b2test_buildid、b2test_buildidfull、btest_gnudebuglink、btest_gnudebuglinkfull、mtest_minidebug）
- 第 3 轮（Makefile.in 派生规则内联重签名：remove-section .codesign → binary-sign-tool selfSign → chmod）：33 PASS / 0 FAIL

### 消费者测试（test_package/）

- test_libbacktrace：backtrace_create_state / backtrace_full / backtrace_syminfo 实质调用，校验帧数、main 解析与符号范围 — PASS（conan create test_package 阶段）

## Evidence

- 最终轮日志：reports/upstream-tests.log（Testsuite summary 33/33）
- 中间轮日志：reports/upstream-tests-flags.log
- conan create 全量日志：reports/conan-create.log
- 上游测试套件与消费者测试均在 G2 干净构建中复现通过
