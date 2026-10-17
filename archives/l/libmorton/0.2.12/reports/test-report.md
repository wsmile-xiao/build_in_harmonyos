# libmorton 0.2.12 测试报告

- 任务: libmorton-0.2.12-r06-step10-closure-and-path-b-knowledge-drafts-pc1-21-20260901T031036Z
- 日期: 2026-09-01
- worktree: /storage/Users/currentUser/runnerljs002/build_in_harmonyos-libmorton-0.2.12
- 分支: feat/libmorton-0.2.12, HEAD 369a6e53d39022be53f2e93a0a05fd5ca03d3c1b

## 1. 上游测试（OHOS aarch64 真实执行）

- 命令: `/data/service/hnp/bin/clang++ -O2 -I <patched-include> test/libmorton_test.cpp -o ohos-libmorton-test && ./ohos-libmorton-test 64`
- cwd: /storage/Users/currentUser/tmp/libmorton-src/libmorton-0.2.12
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 退出码: 0
- 日志: /storage/Users/currentUser/tmp/libmorton-src/ohos-test-r03.log
  SHA256: 7db35fd5bf87863ba47a689dbe9aebe0f5ebc21a19b3f60f6f46093b91e65938
- 结果: 12/12 正确性检查全部 Passed
  - 3D encode/decode match (64/32-bit), 3D encode/decode correctness (64/32-bit)
  - 2D encode/decode match (64/32-bit), 2D encode/decode correctness (64/32-bit)

### 上游测试逐目标台账

| 目标 | 标志 | add_test | 可运行性 | 证据 |
|---|---|---|---|---|
| libmorton-test | 默认 | 是 | 可运行 PASS 12/12 | ohos-test-r03.log |
| libmorton-test-bmi2 | -march=haswell | 是 | x86-only 不可运行 exit 1 | upstream-targets-r03.log |
| libmorton-test-avx512 | -march=icelake-client | 否(上游注释) | x86-only 不可运行 exit 1 | upstream-targets-r03.log |
| libmorton-test-zen2 | -march=znver2 | 否(上游注释) | x86-only 不可运行 exit 1 | upstream-targets-r03.log |

x86-only 目标证据日志: /storage/Users/currentUser/tmp/libmorton-src/upstream-targets-r03.log
SHA256: 198ff13a506c89bb879d4a9dda458f5c7f0cd00f5dc0b8197fa424d186e7be0f

## 2. Conan 包验证（conan-verify 全门禁）

- conan-verify-report.md: **Verdict PASS** (G1/G2/G3/G4/L2/L4/L5 全部通过)
- conan create 干净构建成功（含上游 libmorton-test 与 test_package）

## 3. 消费者测试（test_package）

- 命令: conan create 内 `./test_libmorton`
- 断言: 23 项（morton2D_64 / morton3D_64 encode↔decode 往返）
- 结果: `test_libmorton: all assertions passed` (exit 0)
- 日志: reports/conan-create.log

## 4. 上游缺陷修复验证

- 缺陷: m2D_d_for 32-bit 解码循环 `i <= checkbits` 末次迭代移位 32 位（UB）
- 复现: x=48584,y=42285 → morton=3446888674 → 修复前解出 y=1（错误）
- 修复（patches/0001-fix-m2d-d-for-loop-bound.patch）: `i < checkbits`
- 修复后: 相同样本解出 x=48584,y=42285；128 随机样本 0 失败