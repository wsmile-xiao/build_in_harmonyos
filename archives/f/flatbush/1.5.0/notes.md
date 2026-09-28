# flatbush 1.5.0 适配笔记

## 基线隔离审计（baseline_isolation_audit）

W3 本地 CI 模拟（junk_check full 模式）命中 3 个**其他库已提交基线空文件**（
非本库改动，origin/main 中由其他 PR 提交）：

| path | pre_sha256 | post_sha256 |
|------|-----------|-------------|
| archives/c/cloog/0.21.1/.build-closed | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 同 pre（空文件） |
| archives/c/cloog/0.21.1/.staging-verified | 同上 | 同 pre |
| archives/k/kics/2.1.20/.staging-verified | 同上 | 同 pre |

- isolation_command: `git rm --cached <path> && mv <path> ~/tmp/baseline-isolation-flatbush/`
- rerun_command: `ohc-run.py finish flatbush 1.5.0 built`（W3 本地 CI 模拟 build_and_test.sh）
- rerun_exit_code: 0（隔离期 W3 全绿：conan create 通过、L0/L1 pass、
  `.ci-result.json` exit_code=0 已写入）
- restore_command: `mv ~/tmp/baseline-isolation-flatbush/<file> <path> && git reset HEAD -- <path>`
- 核对: post_sha256 == pre_sha256（e3b0c44…），git status 无该路径改动，
  本库 diff/staged/PR 不含该路径；未修改/提交/写入知识库或 PR 该基线文件
- 结论: 隔离复验通过，继续本库审计与交付

## 编译环境
- 构建系统: cmake（header-only INTERFACE target）
- 编译日期: 2026-09-22
- 编译器: /data/service/hnp/bin/clang++ (Clang 15.0.4, aarch64 OHOS)
- 状态: built

## 适配步骤

1. 官方源码: https://github.com/chusitoo/flatbush tag v1.5.0
2. SHA-256: 69f80255bc279a66c1aade27cb0d7702f509c23ffd5bd7119de736a17d40e5fe
3. conanfile.py: header-library（只打包 flatbush.h + LICENSE），
   上游默认 WITH_SPAN=ON → FLATBUSH_SPAN 宏（C++11 兼容 span）。
   OHOS profile cppstd=17，所以 `self.cpp_info.defines = ["FLATBUSH_SPAN"]`
   必须传播，否则消费方按 C++17 编译头文件时报 `no template named 'span'`。
4. conan create（-pr=ohos-aarch64）通过；test_package L1 消费者用例通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C++17 消费方编译 `no template named 'span'` | 上游 WITH_SPAN=OFF 时要求 cxx_std_20 | recipe 传播 FLATBUSH_SPAN（自带 C++17 span），与上游默认一致 |
| 2 | 本机 github.com 直连不稳定（TLS 超时） | 网络环境 | conan sources download cache 预置官方 tarball（sha256 一致），conan create 可复现 |

## 依赖版本

无运行时/编译依赖（header-only）。测试框架 googletest v1.15.2 仅上游测试构建用。

## 验证结果

- 上游单元测试: 70 TEST + 5 TYPED_TEST × 8 类型 = 110 gtest 用例，110/110 PASS（OHOS clang 原生运行）
- fuzz_test: 24 个 FUZZ_TEST 入口（fuzztest 框架，依赖 abseil/re2/antlr 经 git 拉取，
  本机 github.com 不可达 + git 子模块受限，未能在本机构建；上游另有 fuzz.yml CI 作业）
- bench: 7 个 benchmark（非测试用例）
- tests/package 消费者用例: PASS
- test_package L1 用例（conan create）: PASS
- 鸿蒙专项测试 reports/ohos-test.cpp（C++17 + FLATBUSH_SPAN + JS 兼容字节往返）: PASS

## 注意事项

- flatbush.h 的 SIMD 路径仅在 x86 定义 __AVX* 时启用；aarch64 OHOS 自动走标量路径（已验证 1M 项用例通过）。
- 上游 JS 兼容字节布局（Uint8ClampedArray/跨语言互操作）为库的核心卖点，适配无需改动头文件。
---

**编译结束**: 2026-09-23 01:30
**最终状态**: built
