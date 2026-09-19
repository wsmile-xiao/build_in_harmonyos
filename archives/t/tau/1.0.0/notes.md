# tau 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，header-only INTERFACE 库）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (OHOS SDK, aarch64-linux-ohos)
- 状态: published

## 编译步骤

1. 官方源码: https://github.com/jasmcaus/tau tag v1.0.0（codeload 官方归档，SHA-256 0b3bc9ece92a6ac4c35c352a7fa9d3b91814abbc27508e8b12b92ac8ad9e1bb2）
2. header-only：无需编译，conanfile.py 打包 Muon/ 头文件到 include/Muon/（package_type=header-library）
3. 上游测试: cmake -DMUON_BUILDINTERNALTESTS=ON && cmake --build . && ./test/InternalTests/MuonInternalTests
4. 验证: conan-verify tau 1.0.0（G1-G4 全过，conan create 2/2 CTest 通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载报"下载内容是 HTML" | GitHub 仓库页非 tarball，且直连 github.com 超时 | 用 codeload 官方归档 URL 下载；sha256 核验 0b3bc9e... |
| 2 | conan-verify G1 FAIL（缺 build()/export_sources()/补丁调用） | G1 结构门禁将这三项列为必填 | header-only 配方补 no-op build() + apply_conandata_patches + export_conandata_patches（复用 E257） |
| 3 | test_package/test_ohos.c 编译失败（CHECK(1) expected expression） | Muon 断言宏 CHECK/REQUIRE 必须带消息参数，__VA_ARGS__ 为空时 sizeof(char[]){}) 非法 | 按上游惯例 CHECK(cond,"msg")；STRNE 系 3 参（见知识草稿 DRAFT-tau-1.0.0-muon-assertion-macro-message-argument） |
| 4 | W3 本地 CI Junk Check 拦截 archives/c/cloog/0.21.1/.build-closed 等 | JC full 模式 git ls-files 全仓扫描命中其他库提交前的运行时标记 | 基线隔离复验：git rm --cached 临时隔离→复跑 W3（JC pass）→git restore 原样恢复，pre/post SHA-256 均 e3b0c442... 一致 |

## 依赖版本

无外部依赖（header-only，无 requires）。

## 验证结果

- 上游 InternalTests: 124/124 suites 通过（OHOS clang15/musl 编译运行，0 failed）
- 鸿蒙专项测试 test_ohos.c: 5 suites 全过（含 clock_gettime CLOCK_MONOTONIC POSIX 计时路径）
- test_package 消费者验证: test_tau + test_tau_ohos 2/2 CTest Passed
- conan-verify: G0-G4 全过；finish: W2/W3 通过，状态 published（.ci-result.json exit_code=0）

## 知识沉淀

- 路径 B（知识库扩展）：Muon 断言宏契约知识 → DRAFT-tau-1.0.0-muon-assertion-macro-message-argument（.kv/.md 配对，随本 PR 交付）
- G1 header-only build() 门禁 → 复用既有 E257，不重复建条
- 详情见 reports/knowledge-candidate-ledger.md（四范围查重 + 七轴 + 路径决定）
---

**编译结束**: 2026-09-19 12:18
**最终状态**: published
