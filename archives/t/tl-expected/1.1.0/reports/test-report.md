# tl-expected 1.1.0 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device (HongMeng Kernel, aarch64)
- Clang 15.0.4
- Conan 2.29.1
- Worktree: /storage/Users/currentUser/.oh-runner/worktrees/tl-expected-1.1.0
- Branch: feat/tl-expected-1.1.0

## Verification

- `conan-verify tl-expected 1.1.0`: G1-G4 + L2/L4/L5 全部通过
- W3 本地 CI（incremental 扫描，8 文件）: `.ci-result.json` exit_code=0, JC_RESULT=pass
- L0: passed（junk_check incremental 通过，无框架/基线噪声）
- 上游测试: ctest 1/1 passed（451 assertions in 36 test cases）

## HarmonyOS 专项测试 (test_package/test_tl_expected_ohos.cpp)

覆盖: 值/错误分支、value_or、and_then/map 链式调用、constexpr 路径、
版本宏（TL_EXPECTED_VERSION 1.1.0）、OHOS/aarch64 平台检测、嵌套 expected。
运行: `./tl-expected-ohos-test` → checks=17 ok=18 result=PASS, exit 0

- Test cases: 5（函数组）
- Passed: 5
- Failed: 0
- Skipped: 0

## 消费者验证

独立消费者工程 `find_package(tl-expected REQUIRED)` + `tl::expected` 链接:
`./consumer` → `consumer: value=15 ok=true`, exit 0

## Result

PASS — tl-expected 1.1.0 header-only 适配验证完成（无补丁、无依赖）。