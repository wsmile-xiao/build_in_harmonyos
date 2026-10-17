# bioparser 3.0.15 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: /data/service/hnp/bin/clang++ (clang 15.0.4, target aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 源码: https://github.com/rvaser/bioparser 官方 tag 3.0.15
# SHA-256: 950be627244aa4817d7ad58abcddaaa0b6cddc74b05b7ff3f4c4b51f792bb7b5
cmake .. -DCMAKE_BUILD_TYPE=Release \
  -Dbioparser_install=ON -Dbioparser_build_tests=ON \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build . -j4
```

- bioparser 为 header-only C++11 库（INTERFACE 目标），无平台专属源码，OHOS 下零源码修改。
- CMake 4.1 已移除对 `cmake_minimum_required < 3.5` 的兼容，上游 googletest 1.10.0 的 CMakeLists 声明 3.5，配置时需 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 tag 名无 `v` 前缀，`v3.0.15` 404 | 上游标签命名 | 用 `tags/3.0.15.tar.gz` 下载 |
| 2 | googletest 1.10.0 配置失败 | CMake 4.1 移除 <3.5 兼容 | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 3 | CMake `System is unknown to cmake` 警告（HarmonyOS 平台） | 原生 CMake 无 OHOS 平台文件 | 非致命，pthread 探测成功，照常构建 |

## 依赖版本

- zlib/1.3.1（ohpcd 制品仓已发布，含 OHOS armv8 二进制）
- biosoup/0.10.0（仅测试期 FetchContent 依赖，header-only）
- googletest release-1.10.0（仅测试期 FetchContent 依赖）

## 上游测试完整枚举台账（双口径）

### 源码声明总数（source_declared_total = 35）

按 `TEST`/`TEST_F` 宏逐项枚举（官方 tag 3.0.15 源码）：

| 测试源文件 | 用例数 | 用例名 | 分类理由 |
|---|---|---|---|
| test/parser_test.cpp | 1 | BioparserParserTest.Create | 独立用户用例（TEST） |
| test/fasta_parser_test.cpp | 10 | ParseWhole / ParseWholeWithoutTrimming / ParseInChunks / FormatError / ParseAndReset / CompressedParseWhole / CompressedParseWholeWithoutTrimming / CompressedParseInChunks / CompressedParseAndReset / CompressedFormatError | 独立用户用例（TEST_F） |
| test/fastq_parser_test.cpp | 6 | ParseWhole / ParseInChunks / FormatError / CompressedParseWhole / CompressedParseInChunks / CompressedFormatError | 独立用户用例（TEST_F） |
| test/mhap_parser_test.cpp | 6 | ParseWhole / ParseInChunks / FormatError / CompressedParseWhole / CompressedParseInChunks / CompressedFormatError | 独立用户用例（TEST_F） |
| test/paf_parser_test.cpp | 6 | ParseWhole / ParseInChunks / FormatError / CompressedParseWhole / CompressedParseInChunks / CompressedFormatError | 独立用户用例（TEST_F） |
| test/sam_parser_test.cpp | 6 | ParseWhole / ParseInChunks / FormatError / CompressedParseWhole / CompressedParseInChunks / CompressedFormatError | 独立用户用例（TEST_F） |

### 框架/数据/样例/构建目标（不计为独立用例，但完整列出）

| 入口 | 类型 | 是否独立上游用例 | 说明 |
|---|---|---|---|
| googletest release-1.10.0 | 框架头/源码（FetchContent） | 否 | 测试框架内部宏/实现，非用户用例 |
| biosoup 0.10.0 | 框架头/源码（FetchContent） | 否 | 提供 Sequence 数据结构，bioparser 测试的依赖库 |
| test/data/sample.fasta(.gz) / .fastq(.gz) / .mhap(.gz) / .paf(.gz) / .sam(.gz) | 测试样例数据 | 否 | 共 10 个文件，测试输入数据，被 TEST_DATA 宏引用 |
| test/*.cpp 中 class XxxTest: public ::testing::Test + Setup() | fixture | 否 | TEST_F 的共享 fixture（Setup/Check 辅助），非独立用例 |
| CMake 构建目标 bioparser_test | 构建目标 | 否 | 唯一可执行目标，链接 bioparser + biosoup::biosoup + GTest::Main |

### 双口径统计

- `source_declared_total` = 35（test/*.cpp 中 TEST/TEST_F 宏数）
- `configured_executable_total` = 35（单可执行 `bin/bioparser_test` 注册的 GTest 用例数，`--gtest_list_tests` 核验）
- `executed_passed_total` = 35，失败 = 0，未运行/未实例化 = 0
- 全量通过率 = **35/35 (100.0%)**；当前配置可执行集合通过率 = **35/35 (100.0%)**
- 逐项映射：源码 TEST/TEST_F 宏 → 无互斥编译分支/条件宏/禁用条件 → 全部进入唯一目标 `bioparser_test` → gtest 注册 35 项 → 实际运行全部 PASS

### 运行证据

```bash
$ ./bin/bioparser_test
[==========] 35 tests from 6 test suites ran.
[  PASSED  ] 35 tests.
# exit_code=0；日志 SHA-256: c46a7b8b072019e168a82f36d318cf274d09fc7abd5fc7af1b3531e307b90c2b
```

## 验证结果

```bash
cmake --install . --prefix <stage>
# 安装 6 个头文件 include/bioparser/*.hpp + lib/cmake/bioparser/{bioparserConfig,bioparserConfigVersion,bioparserTargets}.cmake
```

## 注意事项

- 官方 tag 名为 `3.0.15`（无 `v` 前缀）。
- 库为 INTERFACE（header-only）目标，conan 配方需声明 `requires: zlib` 与 header-only 打包方式。
- 测试依赖 biosoup/gtest 均通过 FetchContent 拉取，不在制品仓硬依赖内。

## HarmonyOS 专项测试（harmony_test/）

独立于上游 gtest 用例的 OHOS 专项验证，只使用官方公开头文件与公开 API：

```bash
# 编译（OHOS 工具链 + 本地 zlib 头）
clang++ -std=c++17 -O2 -o bioparser_ohos_test bioparser_ohos_test.cpp \
  -I <bioparser-install>/include -I <zlib>/include -L <zlib>/lib -lz
# 运行（3 个场景全部 exit 0）
./bioparser_ohos_test fasta sample.fasta        # OK fasta sequences=14 name_len=65 data_len=109117
./bioparser_ohos_test fasta sample.fasta.gz     # OK fasta sequences=14 name_len=65 data_len=109117
./bioparser_ohos_test fastq sample.fastq.gz     # OK fastq sequences=13 first_name=1 first_len=6709
```

- 自定义 Sequence 类型仅满足公开模板参数约束（构造参数 name/data/quality），不含库内部头文件。
- 可观察断言：FASTA 14 条序列、名称总长 65、碱基总量 109117（与上游固定断言一致）；支持 gz 压缩路径。
- 该测试作为本目录交付源文件入库，可复现；编译产物 ELF 不入仓。
## 知识候选台账与七轴查重（路径判定：reuse_existing / 路径 A）

### 候选 1：GitHub tag 无 v 前缀导致 404（v3.0.15 → 404，3.0.15 → 200）

- 真实错误/根因/修复：官方 tag 名为 `3.0.15`；照抄带 `v` 前缀的 URL 得 404；用 api.github.com/repos/rvaser/bioparser/tags 枚举后取真实 tag。
- 七轴查重：
  - exact_duplicate: 否（既有条目不以 bioparser 为实例）
  - causal_duplicate: 是（根因相同：上游 tag 名 ≠ 版本号默认形态，opencsg 草稿同因）
  - trigger_overlap: 是（触发条件相同：凭版本号臆造 tag URL）
  - solution_overlap: 是（解法相同：用 releases/tags API 确认真实 tag 再拼归档 URL）
  - combination_novelty: 否（无新组合）；boundary_novelty: 否；test_migration_novelty: 否
- 既有条目覆盖部分：`knowledge/drafts/opencsg-1.8.2-upstream-tag-name-vs-version-archive-selection(.kv/.md)` 已完整覆盖"tag 名 ≠ 版本号，须 API 核实"；知识条目 E276 覆盖 tar.gz basename 解压识别。
- 本轮新增部分：无（仅新增 bioparser 实例，查重差异为空）。
- 适用边界/反例：tag 恰好无 `v` 前缀（如 bioparser 3.0.15）与带前缀/连字符形态同属一类；不构成独立知识。
- 关系：similar_to opencsg 草稿；caused_by 上游 tag 命名惯例；无 conflicts_with。
- 决定：复用既有条目，路径 A（不建草稿）。

### 候选 2：CMake 4.1 移除 <3.5 兼容，googletest 1.10.0 cmake_minimum_required 失败

- 真实错误/根因/修复：googletest CMakeLists 声明 `cmake_minimum_required(VERSION 3.5)`，CMake 4.1 报 "Compatibility with CMake < 3.5 has been removed"；修复 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`。
- 七轴查重：
  - exact_duplicate: 是（E187 特征与解法逐字命中）
  - causal_duplicate: 是；trigger_overlap: 是；solution_overlap: 是；组合/边界/迁移客观性: 否
- 既有条目覆盖部分：E103（bump-cmake-minimum-version）与 E187（add-cmake-flag: `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`）完整覆盖根因与修复。
- 本轮新增部分：无。
- 决定：完整重复 → reuse_existing（路径 A）。

### 候选 3：conandata.yml 注释中裸 URL 被 CI predl 预下载提取污染（file:// + gh-proxy 包装坏 URL）

- 真实错误/根因/修复：ci/conan/build_and_test.sh predl 提取任意 https URL（含注释行），把注释中裸仓库 URL 下载成 29KB 垃圾文件并做全文子串 `file://` 替换，再被镜像 fallback 包成 `gh-proxy.com/file://...` 坏 URL → W3 conan create NotADirectoryError。修复：注释不得含裸 https URL，官方 URL 保持单值；已恢复官方单 URL 并核验 SHA-256 一致。
- 七轴查重：
  - exact_duplicate: 否
  - causal_duplicate: 是（predl 正则任意提取含注释 + 子串改写，jwt-cpp 实证同因）
  - trigger_overlap: 是（注释/自定义 key 中的 URL 被 predl 提取）
  - solution_overlap: 是（不在注释写裸 URL；CI 后核验/恢复 conandata）
  - combination_novelty: 否；boundary_novelty: 否；test_migration_novelty: 否
- 既有条目覆盖部分：`knowledge/drafts/DRAFT-VENDP-PUREPY-DEP-CLOSURE(.kv/.md)` 以 jwt-cpp 0.7.1 实证"注释中的裸仓库 URL 被 predl 提取并改写"；E333 覆盖 predl 正则提取缺陷；E415 覆盖 mirror-fallback 原地改写 conandata 须 CI 后恢复。
- 本轮新增部分：无（bioparser 实证与 jwt-cpp 机理完全一致）。
- 决定：部分覆盖且新增差异为空 → reuse_existing（路径 A），不建草稿。

### 候选 4：W3 junk_check full 模式命中其他库已提交基线文件（cloog 0.21.1）

- 真实错误/根因/修复：分支零提交时 junk_check 回退 full 模式（git ls-files 整仓），命中 main 中其他库 cloog/0.21.1 已跟踪的 `.build-closed`/`.staging-verified`（JC1+JC5 fail）。按基线隔离流程 `git rm --cached` 临时隔离 → 重跑 finish → `git restore --staged` 原样恢复，pre/post SHA-256 均为 e3b0c442...（空文件，与 HEAD blob 一致）。
- 七轴查重：
  - exact_duplicate: 是（DRAFT-libfort-0.4.2 与 DRAFT-dr_mp3-0.7.2 记录同模式：full 扫描命中其他库历史遗留文件，JC fail）
  - causal_duplicate: 是（当前库未提交 → diff 为空 → full 模式兜底）
  - trigger_overlap: 是；solution_overlap: 是（精确隔离 + SHA-256 前后比 + 恢复）
  - combination_novelty: 否；boundary_novelty: 否；test_migration_novelty: 否
- 既有条目覆盖部分：`DRAFT-libfort-0.4.2-w3-baseline-junk-check-full-scan(.kv/.md)`、`DRAFT-dr_mp3-0.7.2-baseline-noise-isolation(.kv/.md)` 完整覆盖该 W3 基线噪声模式及隔离/恢复流程。
- 本轮新增部分：无新增机理（bioparser 实例与 goaccess/scudo-malloc 基线条目同类）。
- 决定：完整重复 → reuse_existing（路径 A），不建草稿。

### 路径决定

- `reuse_existing`：四项候选全部命中既有正式条目/草稿，无独立、可跨库复用的新增差异。
- `new_draft`：否（七轴查重四个方向均无组合/边界/迁移新颖性，新增差异为空）。
- `path_a_no_knowledge`：否（知识库已有相关条目，非"无知识可用"）。
- 结论：走路径 A（复用既有知识），不新建 .md/.kv 草稿；PR 前缀遵任务头 initial_pr_prefix: 【知识库扩展】。

---

**编译结束**: 2026-09-16 10:43
**最终状态**: built

## R02 知识台账复核（返工修复轮）

本轮仅修复 CI 审查 2 个 P2 测试健壮性问题，无新的库适配知识产生：

### 候选 5：测试工具 argv 解引用前缺少 argc 守卫（argc<3 越界）

- 真实错误/根因/修复：harmony_test 仅校验 `argc < 2` 即解引用 `argv[2]`，`argc==2` 时越界/空指针；修复为 `argc < 3` 先校验再解引用，错误路径 exit 2 + usage。
- 七轴查重：
  - exact_duplicate: 否；causal_duplicate: 否（通用 C/C++ 防御性编程惯例，非平台/构建机理）
  - trigger_overlap: 否（与 E357 argv 白名单等既有条目触发条件不同域）；solution_overlap: 否
  - combination_novelty: 否；boundary_novelty: 否；test_migration_novelty: 否
- 既有条目覆盖部分：无直接命中（E357 为 CLI 信息选项白名单，非测试工具 argc 守卫）。
- 本轮新增部分：无（属通用编码规范，`usage: <prog> ...` + 非零退出为标准做法，无跨库可复用差异）。
- 决定：不构成新候选，沿用路径 A。

### 候选 6：test_package CTest add_test 无参注册与二进制参数契约矛盾

- 真实错误/根因/修复：`add_test(NAME test_bioparser COMMAND test_bioparser)` 无参调用，与 test.cpp 需要 FASTA 路径的契约矛盾，CTest 用例必然失败且 sample.fasta 未被引用；修复为 `add_test(... COMMAND test_bioparser ${CMAKE_CURRENT_SOURCE_DIR}/sample.fasta)`，ctest 1/1 真实 Passed。
- 七轴查重：
  - exact_duplicate: 否；causal_duplicate: 否（通用 CMake 测试声明一致性惯例）
  - trigger_overlap: 否（E535 enable-upstream-ctest 为上游 ctest 开启，非 test_package 参数契约）；solution_overlap: 否
  - combination_novelty: 否；boundary_novelty: 否；test_migration_novelty: 否
- 既有条目覆盖部分：E321（header-only Conan 2 迁移）提到 test_package/CTest，但未覆盖 add_test 参数契约问题。
- 本轮新增部分：无（add_test 携带与二进制一致的参数属 CMake 标准用法，无跨库可复用差异）。
- 决定：不构成新候选，沿用路径 A。

### R02 路径决定

- `reuse_existing`：R02 两个 P2 修复均为通用测试健壮性惯例（argc 守卫、CTest 参数契约），七轴查重无命中、无新增可跨库复用差异，R01 路径 A 结论沿用，无草稿。
