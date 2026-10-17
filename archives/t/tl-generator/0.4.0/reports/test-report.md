# Test Report — tl-generator 0.4.0

## 编译信息
- 软件: tl-generator
- 版本: 0.4.0
- 构建系统: cmake (header-only INTERFACE library)
- 编译器: clang/clang++ 15.0.4 (OHOS SDK, libc++ 15.0.4)
- 平台: OpenHarmony/HarmonyOS PC aarch64

## 编译步骤
1. `ohc-run.py init-build tl-generator 0.4.0 --url=<official tarball>` — 下载解压官方 v0.4.0 源码
2. `lang-preflight` — C/C++ 语言预检通过 (cpp, exit 0)
3. `conan-verify tl-generator 0.4.0` — G1-G4 + L2/L4/L5 全部通过 (G2 conan create PASS)
4. `zsh ci/conan/build_and_test.sh archives/t/tl-generator/0.4.0` — L0 pass / L1 pass / L1e R34 negative test pass / L4 pass / L5 warn (header-only 无 bin/lib)

## 测试结果
- 上游测试 (tests/test.cpp, Catch2 v2.13.9):
  - 4 test cases, 45 assertions, 全部通过
  - `All tests passed (45 assertions in 4 test cases)`
  - 适配说明: OHOS libc++ 15 无 `std::views` (无 `__cpp_lib_ranges`)，上游 `iota` 用例以等价手工 take 循环执行 (语义不变，见 patches/0001-adapt-iota-test-for-ohos-libcxx.patch)
- test_package 消费者测试 (OHOS aarch64):
  - `tl::generator<int>` firstn: 20 values in order ✅
  - `tl::generator<std::vector<std::string>>` split_lines: 2 non-empty lines ✅
  - 输出: `test_tl-generator: ALL PASSED`
- 破坏性反向验证 (R34/L1e): include/ 移走 → 测试失败 (真实依赖被测包) ✅

## 结论
编译状态: ✅ SUCCESS (header-only, built)
