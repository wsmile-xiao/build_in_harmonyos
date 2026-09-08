# tinyfsm 0.3.3 适配笔记

## 编译环境
- 库类型: header-only C++11 FSM 库（单头文件 include/tinyfsm.hpp）
- 构建系统: custom（无构建步骤，仅打包头文件）
- 编译日期: 2026-09-05
- 编译器: clang/clang++（本机无 g++；上游 examples Makefile 硬编码 g++，改用 CXX=clang++ 显式编译示例验证）
- 状态: built

## 编译步骤

1. `git worktree add -b feat/tinyfsm-0.3.3 ... main`（分支自 main HEAD 2f60a10778 创建）
2. init-build 从 GitHub 下载失败（urllib 超时），改用 `curl -fsSL -o ~/tmp/builds/tinyfsm-0.3.3.tar.gz 'https://github.com/digint/tinyfsm/archive/refs/tags/v0.3.3.tar.gz'` 手动预取官方标签 tarball（sha256 99aaad53...）后重跑 `ohc-run.py init-build tinyfsm 0.3.3 --url=...` 成功
3. init-build 的嵌套源码提升误判根目录为 examples/api，已用完整 tarball 重新解压 .orig/.work 修正
4. `ohc-run.py lang-preflight` 通过（detected=cpp, 源文件 13 个 cpp 100%）
5. 上游测试: `clang++ -I ../../include -std=c++11 -fno-exceptions -fno-rtti ...` 编译 examples/api 的 6 个示例（simple_switch/resetting_switch/multiple_switch/debugging_switch/mealy_machine/moore_machine）全部成功并运行验证状态机输出正确
6. `ohc-run.py conan-verify tinyfsm 0.3.3` — G1/G2/G3/G4 全部 PASS（G2 conan create 含 test_package 3 断言 + L1e 破坏性反向验证通过）
7. `ohc-run.py finish tinyfsm 0.3.3 built` — W3 本地 CI 模拟通过，.ci-result.json exit_code=0（integrity_hash 3f016c5b198b5d33, log_sha256 95ee1561...）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build GitHub 下载超时（Errno 110） | urllib 请求超时（git ls-remote/curl 均正常） | curl 手动预取官方标签 tarball 到 ohc 约定路径 ~/tmp/builds/ 后重跑 |
| 2 | 嵌套源码提升误判 examples/api 为源码根 | 自动检测把含 Makefile 的 examples/api 当根 | 用完整 tarball 重新解压，root=include/tinyfsm.hpp |
| 3 | conan-verify G1 缺补丁应用调用 | 模板配方无 patch 调用 | conanfile.py 补 export/apply_conandata_patches（E241/E257 类） |
| 4 | conan create: test.cpp 中 Off 未声明 | transit<Off>() 前向引用，缺 `class Off;` 声明 | test_package/test.cpp 顶部补前向声明 |
| 5 | W3 本地 CI L0p: settings 缺 compiler/build_type | header-only 模板 settings="os","arch" 被 L0p 门禁拦截 | settings 补全四项（命中 E391） |
| 6 | W3 JC 整仓扫描命中其他库基线状态文件 | 分支尚无 commit 时 junk_check 回退 full 模式，扫到 main 历史基线中 embree/flatcv/libmorton 等遗留运行时文件 | 按 oh-executor 基线隔离规则：审计 tracked/blob 哈希 → 以 JUNK_PR_DIFF 提供 PR 文件清单使 JC 走 prdiff 模式（与 CI 同口径）→ 通过后无条件恢复（临时 pr.diff 在工作区外，不触碰基线文件） |

## 源码修改

无（header-only 纯打包，patches/ 为空）

## 依赖版本

无第三方依赖（header-only，不依赖 RTTI/异常/外部库）

## 验证结果

- conan create（ohos-aarch64 profile）: exit 0
- test_package: 3/3 断言通过（Off 初始状态 + 两次 Toggle 状态切换），L1e 破坏性反向验证确认真实依赖被测 API
- 上游 6 个示例: 编译成功并运行验证
- W3 本地 CI 模拟: L0 pass / L1 pass / L4 pass / L5 warn（无 bin/lib 产物属预期）

## 注意事项

- 生成物为 header-only，无普通 .so/.a 产物；L5 warn 属预期，不阻塞
- W3 JC 基线隔离为临时 checker-input 隔离，未改动、未提交任何基线文件；临时 pr.diff 位于 /storage/Users/currentUser/tmp/tinyfsm-pr.diff（工作区外）

## 知识判定（executor_local_required 本地快照查重）

- 快照: /storage/Users/currentUser/.ohpc-executor/knowledge-snap-tinyfsm-0.3.3-r01/repo
  - remote: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git
  - ref: main（HEAD 0b458be188c0740435e57607d31384570d947f57）
  - sparse: knowledge（E*.kv 540 / doc E*.md 540）
- 扫描范围: graph/E*.kv + doc/E*.md 全文、drafts/*.{md,kv}
- knowledge_decision: **reuse_existing（路径 A）** — 不创建草稿
- 逐字段等价命中：
  - **E391**: CI L0p 门禁要求 conanfile settings 声明全部四项（缺 compiler/build_type 即报 missing_setting_compiler/missing_setting_build_type）— 与本任务 W3 首错完全一致
  - **E257**: header-only 无 CMake 库配方 conan-verify G1 结构完整性要求显式方法（no-op build）— 覆盖本任务 G1 补丁应用调用修复
  - **E322 / DRAFT-ctre-3.10.0**: header-only 库 Conan 配方模式（package_type=header-library、copy 头文件、test_package 真实 API + CTest）— 覆盖本任务配方组装
  - E241/E321/E484/E515 等: 补丁应用/配方完整性类条目佐证
- 未命中新知识: 无等价命中的可跨库复用新候选；基线文件隔离（规则禁止路径 B）、下载超时（网络/基础设施，规则禁止路径 B）、L0p settings（E391 已覆盖）
- 结论: 路径 A（常规基础适配），PR 标题前缀 【积分赛】

---

**编译结束**: 2026-09-05 21:42
**最终状态**: built