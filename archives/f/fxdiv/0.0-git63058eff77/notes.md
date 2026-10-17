# fxdiv 0.0-git63058eff77 适配笔记

## 编译环境
- 构建系统: cmake（FXDiv 为 header-only CMake INTERFACE 库）
- 编译日期: 2026-09-28
- 编译器: clang/clang++ (15.0.4)
- 状态: built（conan-verify 8 门禁全过，本地 finish/W3 通过，PR 交付后由 CI release 流水线 upload）

## 编译步骤

1. init-build：官方 archive（commit 63058eff77）下载并核验 SHA-256
   （GitHub 直连超时 → codeload 官方路径下载，SHA-256 与官方 archive URL 一致：ec74d882...）
2. lang-preflight：detected=cpp 匹配（cmake + C/C++ 源码统计），通过
3. 探索编译：cmake -DFXDIV_BUILD_TESTS=ON -DFXDIV_BUILD_BENCHMARKS=OFF 配置；
   上游测试依赖 GoogleTest（CMake 默认 ExternalProject 从 GitHub 下载，本机直连超时 →
   用 codeload 下载官方 googletest release-1.10.0 源码并传 GOOGLETEST_SOURCE_DIR 复用）；
   构建 multiply-high-test + quotient-test，ctest 2/2 通过（20 个独立 TEST_CASE 全过）
4. conan-init → 配方重写为 CMake header-only 模式（package_type=header-library，
   FXDIV_BUILD_TESTS=OFF/FXDIV_BUILD_BENCHMARKS=OFF，cpp_info.libs=[]）
5. conan-verify：G0-G4/L2/L4/L5 全过（G2 conan create 干净构建通过）
6. finish built：W2 结构 + R36 依赖（无外部依赖）+ W3 本地 CI（L0/L1 pass，JC 门禁
   经基线隔离复验通过）+ W5 知识完整性通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | CI/本机到 github.com 443 超时 | 用 codeload.github.com 官方 archive 路径下载，SHA-256 核验一致；conan get 由工具自动注入 ghfast 镜像（E017） |
| 2 | CMake 4.x 与 googletest 1.10 不兼容 | CMake 4.x 移除 cmake_minimum_required<3.5 兼容 | -DCMAKE_POLICY_VERSION_MINIMUM=3.5（E187/E103 已覆盖） |
| 3 | benchmark 1.5.0 配置失败 | write_basic_package_version_file 在 CMake 4.x 需显式 VERSION，benchmark 1.5 上游缺省 | FXDIV_BUILD_BENCHMARKS=OFF（基准非测试用例，不阻塞）；头部 GTest 源码自带同根因处理 |
| 4 | 本地 W3 JC 门禁 full 模式误拦其他库基线隐藏文件 | 本地无 pr.diff 时 junk_check 回退整仓 git ls-files，命中 HEAD 已跟踪的 cloog/kics .build-closed/.staging-verified | 按基线隔离规则：记录 SHA-256 → 临时隔离 → 用 pr.diff（prdiff 模式，与真实 CI 同口径）复跑受影响门禁 → 原样恢复核对 SHA-256（pre==post，e3b0c442... 空文件） |

## 源码修改

无（header-only 库，无需补丁；配方在 conanfile.py/test_package 中表达）

## 依赖版本

- 无运行时依赖（header-only）；测试依赖 GoogleTest（上游声明 release-1.10.0，探索编译阶段本地实测）

## 验证结果

```bash
# 上游测试（探索编译阶段，gtest 源码实测）
ctest --test-dir build        # 2/2 passed（20 个独立 TEST_CASE）
# 配方干净构建
conan create ... （G2 PASS，含 test_package 消费者 + OHOS 专项两个测试自运行）
# W3 本地 CI
setup.sh + build_and_test.sh  # L0 all checks passed，L1 test_package executed，Pass rate 100%
```

## 知识候选台账（knowledge_candidate_ledger）

| 候选 | 真实错误/根因 | 修复/验证 | 四范围查重（graph/doc/drafts/archives） | 结论 |
|------|--------------|-----------|----------------------------------------|------|
| C1 CMake 4.x 与旧版 gtest/benchmark 兼容 | cmake_minimum_required<3.5 被移除；benchmark write_basic_package_version_file 缺 VERSION | CMAKE_POLICY_VERSION_MINIMUM=3.5；bench 关闭（非测试） | E103/E187 正式条目 + DRAFT-E321-cmake4-policy-version-minimum 草稿；fast_float 等归档配方同法 | exact_duplicate，复用已有知识 |
| C2 上游测试 ExternalProject 网络下载 | CMake 配置期从 GitHub 下载 gtest/benchmark，离线/受限网络失败 | FXDIV_BUILD_TESTS=OFF + test_package 消费者+OHOS 专项覆盖（本机用官方 gtest 源码实测 20 用例全过） | E342 正式条目（disable-networked-upstream-tests-and-run-consumer-test） | causal_duplicate/solution_overlap，复用已有知识 |
| C3 GitHub 直连超时 | github.com 443 超时 | codeload 官方路径 + ghfast 镜像注入（工具自动） | E017 正式条目 | trigger_overlap，复用已有知识 |
| C4 W3 JC full 模式误拦其他库基线隐藏文件 | junk_check 无 pr.diff 时整仓扫描，命中 HEAD 已跟踪其他库文件 | 基线隔离复验（SHA-256 记录→隔离→prdiff 复跑→恢复） | DRAFT-fastnoiselite-1.1.1-jc-full-mode-baseline-junk-isolation / DRAFT-dr_mp3-0.7.2-baseline-noise-isolation / DRAFT-cute_tiled-1.0.0-cross-library-tracked-baseline-provenance-transport 草稿已覆盖 | trigger_overlap/solution_overlap，复用已有草稿知识 |

## 七轴查重结论

- exact_duplicate: true（C1→E187/E103；C4→既有草稿）
- causal_duplicate: true（C2→E342）
- trigger_overlap: true（C3→E017；C4）
- solution_overlap: true（C2/C4）
- combination_novelty: false（无新增组合）
- boundary_novelty: false（无新增边界/反例适用差异）
- test_migration_novelty: false（无新增测试迁移差异）

## 路径决定

**path_a_no_knowledge**：所有候选均被正式条目或既有草稿完整覆盖，无验证过的新增可跨库复用差异；
不建新草稿。related: similar_to=E187/E103/E342/E017, caused_by=无, prerequisite_of=无, conflicts_with=无

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake header-only 配方（package_type=header-library） |
| conandata.yml | 官方 archive URL + SHA-256 |
| test_package/ | 消费者测试（test.c）+ HarmonyOS 专项测试（ohos_special_test.c） |
| MANIFEST.yml | 上游测试声明 |
## 结束标记

编译结束(status: built, conan-verify 8 门禁全过、W3 本地 CI 通过;PR 交付后由 CI release 流水线 upload to CNB)
