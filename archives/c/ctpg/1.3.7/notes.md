# ctpg 1.3.7 适配笔记

## 编译环境
- 构建系统: cmake（CTPG 单头文件编译期解析器生成库，INTERFACE target）
- 编译日期: 2026-09-05
- 编译器: clang/clang++（ohos-aarch64 profile: os=OHOS, arch=armv8, clang 15, libc++ 17）
- 状态: published

## 编译步骤

1. init-build ctpg 1.3.7 --url=https://github.com/peter-winter/ctpg（官方源）
2. lang-preflight: detected=cpp（32 个 cpp 源，主体 100%）
3. conan-init 生成配方后按 header-only 重写 conanfile.py（参考 CLI11/span-lite 同型）
4. conan-verify：G1/G0/G2/G3/G4/L2/L4/L5 全 PASS
5. finish published：W3 本地 CI 模拟（zsh build_and_test.sh）Success 1/1，Pass rate 100%

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 将构建系统误判为 autotools | URL 猜测逻辑不含 cmake 关键字 | 按 header-only CMake 模板重写 conanfile.py（package_type=header-library） |
| 2 | G2: find_package(Catch2 2 REQUIRED) 找不到 Catch2Config | 主配方缺 CMakeDeps generator | conanfile 声明 generators = "CMakeDeps" |
| 3 | G2: include(Catch) 找不到文件 / catch_discover_tests 未知命令 | ohpcd catch2/2.13.10-r0 只打包头文件，不含 Catch2 2.x 的 CTest 集成模块 Catch.cmake | generate() 注入最小 Catch.cmake（catch_discover_tests → add_test(testbin)）到 CMAKE_MODULE_PATH（知识草稿 C1） |
| 4 | W3 L0d: test() 无 self.run() — stub_test_method | test_package 用 cmake.test() 未直接 self.run 二进制 | test() 改经 self.run 直接运行 test_ctpg |
| 5 | W3 JC5: 命中 main 基线 util-linux-login/2.42.2/.ci-trigger | junk_check full 模式整仓扫描命中其他库历史残留 | 按先例（googletest/replxx pr.diff）建本任务 pr.diff 走 prdiff 模式；不动其他库内容（知识草稿 C2 复用既有条目） |

## 依赖版本

- catch2/2.13.10-r0（仅测试期，can_run 守卫）

## 验证结果

```bash
# 上游测试（testbin 内含 52 个 TEST_CASE）
testbin: All tests passed (319 assertions in 52 test cases)  # exit 0

# 鸿蒙专项测试（test_package）
test_ctpg: ctpg 1.3.7 consumer test OK: 1+2+3=6, 4+5=9  # exit 0

# W3 本地 CI 模拟
zsh ci/conan/build_and_test.sh archives/c/ctpg/1.3.7  # Success 1/1, Pass rate 100%
```

## 注意事项

- CTPG 为 header-only 库，package_id 清空（无二进制依赖）；测试依赖 catch2 仅在 can_run 时引入，不污染下游
- 上游 CMakeLists 的 CTPG_WARNING_FLAGS 需置 OFF（is_top_level 时默认 ON 会 -Werror）
- 上游 project VERSION 为 1.3.6（CMakeLists 未随 tag 更新），以 tag v1.3.7 为准

**编译结束**: 2026-09-05 04:12
**最终状态**: published
