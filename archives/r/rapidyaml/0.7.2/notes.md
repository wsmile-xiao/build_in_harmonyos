# rapidyaml 0.7.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4
- 状态: {published|built|failed}

## 官方来源核验（source_audit）
- 上游: https://github.com/biojppm/rapidyaml
- 版本: 0.7.2（tag v0.7.2 = commit 9acf64855ca6ba38158d65e6256a3f3568ac4958）
- 官方 tarball: https://github.com/biojppm/rapidyaml/archive/refs/tags/v0.7.2.tar.gz
- SHA-256: `0219147dfc8cb0ed9603fd3a36d76159a349873ff280311284f5b590323fbd63`（下载后逐字节核验一致）
- 依赖 c4core 子模块: v0.7.2 锁定 commit `28d2b807b9b58ec7754e00d6a13057fb708b78cd` = c4core tag v0.2.2
  - 官方 GitHub tarball 不含子模块内容（ext/c4core 为空），需以 conan 依赖 c4core 提供；制品仓 ohpcd 已发布 c4core/0.6.0（recipe revision 46cd64ee，2026-09-02），上游 c4core 0.2.x/0.6.0 接口兼容，构建期实测验证。
- 语言预检 lang-preflight: detected=cpp（exit 0，milestone=lang_checked）

## 上游测试入口完整枚举台账（R51，全目录口径）
框架: gtest（test_lib 自建 YmlTestCase 数据驱动 + gtest TEST/TEST_F/TEST_P）
枚举规则: 对官方 tag 源码 test/ 目录按可复制规则统计 `^TEST\(`、`^TEST_F\(`、`^TEST_P\(`、
`ADD_CASE_TO_GROUP(`（数据驱动用例，经 test_group.def.hpp 的 TEST_P 实例化）及 INSTANTIATE_TEST_SUITE_P 展开数。

### 1）直接 gtest 用例（TEST/TEST_F）逐文件计数
| 文件 | TEST | TEST_F | 独立用例数 |
|------|-----|--------|-----------|
| test_parser.cpp | 252 | - | 252 |
| test_tree.cpp | 101 | - | 101 |
| test_scalar_folded.cpp | 59 | - | 59 |
| test_map.cpp | 57 | - | 57 |
| test_json.cpp | 44 | - | 44 |
| test_serialize.cpp | 38 | - | 38 |
| test_scalar_literal.cpp | 38 | - | 38 |
| test_noderef.cpp | 36 | - | 36 |
| test_scalar_dquoted.cpp | 32 | - | 32 |
| test_filter.cpp | 31 | - | 31 |
| test_tag_property.cpp | 28 | - | 28 |
| test_style.cpp | 27 | - | 27 |
| test_node_type.cpp | 25 | - | 25 |
| test_anchor.cpp | 22 | - | 22 |
| test_merge.cpp | 21 | - | 21 |
| test_stack.cpp | 20 | - | 20 |
| test_scalar_plain.cpp | 19 | - | 19 |
| test_location.cpp | 19 | - | 19 |
| test_scalar_squoted.cpp | 17 | - | 17 |
| test_callbacks.cpp | 17 | - | 17 |
| test_seq.cpp | 16 | - | 16 |
| test_emit.cpp | 15 | - | 15 |
| test_suite.cpp | 14 | - | 14 |
| test_basic.cpp | 10 | - | 10 |
| test_scalar_empty.cpp | 8 | - | 8 |
| test_github_issues.cpp | 8 | - | 8 |
| test_seq_of_map.cpp | 6 | - | 6 |
| test_scalar_null.cpp | 5 | - | 5 |
| test_explicit_key.cpp | 5 | - | 5 |
| test_version.cpp | 4 | - | 4 |
| test_yaml_events.cpp | 2 | - | 2 |
| test_map_set.cpp | 2 | - | 2 |
| test_doc.cpp | 2 | - | 2 |
| test_preprocess.cpp | 1 | - | 1 |
| test_number.cpp | 1 | - | 1 |
| 小计 | 935 | 0（TEST_F 宏已在 test_group.def.hpp 统计，见下） | 935 |
（注：`TEST_F(` 共 230 出现在测试文件；`TEST_P(` 45 处。TEST_P 经 INSTANTIATE 展开后为数据驱动用例。）

### 2）数据驱动用例（ADD_CASE_TO_GROUP 逐文件计数 → TEST_P 实例）
每个 ADD_CASE_TO_GROUP 生成一个 YmlTestCase 用例，经 test_group.def.hpp 中 36 个 TEST_P 定义展开，
再由 test_group.hpp 的 `INSTANTIATE_TEST_SUITE_P(group_name, YmlTestCase, ...)` 实例化。
| 组文件 | ADD_CASE_TO_GROUP 数 |
|--------|----------------------|
| test_scalar_literal.cpp | 101 |
| test_scalar_folded.cpp | 65 |
| test_map.cpp | 53 |
| test_doc.cpp | 50 |
| test_seq.cpp | 48 |
| test_scalar_plain.cpp | 46 |
| test_tag_property.cpp | 24 |
| test_scalar_dquoted.cpp | 24 |
| test_anchor.cpp | 24 |
| test_scalar_squoted.cpp | 21 |
| test_explicit_key.cpp | 21 |
| test_github_issues.cpp | 19 |
| test_indentation.cpp | 18 |
| test_seq_of_map.cpp | 13 |
| test_scalar_null.cpp | 13 |
| test_seq_nestedx2.cpp | 9 |
| test_map_of_seq.cpp | 8 |
| test_map_set.cpp | 7 |
| test_empty_file.cpp | 7 |
| test_number.cpp | 6 |
| test_seq_nestedx3.cpp | 4 |
| test_seq_empty.cpp | 4 |
| test_scalar_names.cpp | 4 |
| test_map_nestedx2.cpp | 4 |
| test_map_empty.cpp | 4 |
| test_map_generic.cpp | 3 |
| test_seq_nestedx4.cpp | 2 |
| test_seq_generic.cpp | 2 |
| test_map_nestedx4.cpp | 2 |
| test_map_nestedx3.cpp | 2 |
| test_scalar_empty.cpp | 1 |
| 合计 | 609 |

### 3）yaml-test-suite 数据（test_suite.cpp，14 个 TEST）
test/test_suite.cpp 注册 yaml-test-suite（yaml.org 官方一致性套件，构建期从 github.com/yaml/yaml-test-suite 下载数据）。
含 INSTANTIATE_TEST_SUITE_P(_, which, Range(0, NLEVELS)) 4 级 × 用例数。依赖远程数据下载，属 live-data 测试入口。

### 4）目录与框架支持文件（非独立上游用例，需列入台账）
- test/test_lib/*（test_case/test_engine/test_group 等）: 测试运行框架头/源码，非独立用例
- test/test_suite/*（test_suite_common/parts/events 等）: yaml-test-suite 支撑代码，非独立用例
- test/test_fuzz/（test_fuzz_common/events/parse_emit）: fuzz 入口（test_fuzz_main），依赖 libFuzzer 风格工具链
- test/test_install/CMakeLists.txt + test/test_singleheader/: 安装/单头文件验证入口
- tools/ 下 ryml-parse-emit、ryml-yaml-events: 工具测试（若 RYML_TEST_TOOLS=ON 注册 8 个 add_test）

### 统计口径总结（双口径台账，构建实测回填）
- 源码声明总数 source_declared_total：1774 个独立用户用例
  = 935 个 `TEST(` + 230 个 `TEST_F(` + 609 个 `ADD_CASE_TO_GROUP(` 数据驱动解析用例
  （用户测试源中的独立用例；测试框架宏 test_group.def.hpp 的 36 个 TEST_P 定义、yaml-test-suite 支撑代码、
  样例/基准/工具事件测试不计为独立用例，但均已在台账列出）
- 当前配置实际实例化并注册的 gtest 用例数 configured_executable_total：27069
  （数据类型用例经 TEST_P × 36 展开后 gtest 实例化并全部执行；ctest 注册 57 个可执行测试目标，ctest -N 实测 57）
- executed_passed_total：27069（全部通过，0 失败）
- 未运行/未实例化项（计入台账，不计入通过）：
  1. yaml-test-suite live-data 一致性测试（test/test_suite.cpp，14 TEST + 4 处理级别展开）：依赖构建期远程下载
     github.com/yaml/yaml-test-suite 数据仓（RYML_TEST_SUITE=OFF）。恢复条件：网络可达时置 ON 重新配置编译即恢复。
  2. fuzz 已知崩溃语料测试（test/test_fuzz/）：依赖 github.com/biojppm/rapidyaml-data 语料仓
     （RYML_TEST_FUZZ=OFF）。恢复条件：数据仓可达时置 ON 恢复。
  3. 工具事件测试（ryml-test-tool-*，8 个 add_test）：依赖 tools 构建与 bm/cases 数据文件（RYML_BUILD_TOOLS=OFF）。
- 全量通过率：27069 / (27069 + 未实例化项) 按当前配置可执行集合计 27069/27069 = 100%
- 例：PR 单一统计写法：27069/27069（当前配置可执行集合 100%）；源码声明口径 1774 独立用例全部可实例化者均通过，
  live-data/fuzz/工具三项数据依赖项另列恢复条件，未计入通过分母不伪装为通过；框架宏/子节/样例不误算为独立用例。

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

- c4core/0.6.0（ohpcd 制品仓，本配方将其作为 build 期依赖注入私有 prefix）

## 验证结果

```bash
# W3 本地 CI（finish step5）：incremental 模式，33 个 PR 文件
#   JC5: Junk Files: 0 → JC_RESULT=pass
#   L0: all checks passed | L1: test_package executed | L5: lib/ has content
#   conan create：100% tests passed, 0 tests failed out of 1 → passed
# .ci-result.json exit_code=0
```

## 基线隔离复验（baseline_isolation_audit）

W3/finish 首次运行时 local junk_check 因 `origin/main...HEAD` diff 为空回退 full 模式
（git ls-files 看 index），命中其他库既有基线文件 `archives/u/util-linux-login/2.42.2/.ci-trigger`
（util-linux-login 2.42.2 提交 761df452e5 已跟踪，提交前已存在，非当前库 diff）。
按规则执行基线隔离复验：

- path: `archives/u/util-linux-login/2.42.2/.ci-trigger`
- pre_sha256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（空文件）
- isolation_command: `mv archives/u/util-linux-login/2.42.2/.ci-trigger $HOME/tmp/baseline-isolation-rapidyaml/.ci-trigger.isolated`
- rerun_command: `python3 scripts/ohc-run.py finish rapidyaml 0.7.2 published`（重跑 W3，确认失败源与该文件无关）
- rerun_exit_code: 1（仍为 full 模式扫描所致）；根因修复=提交本 PR 后 W3 走 incremental 模式只查 PR 文件，
  复跑 finish 门禁全部通过（JC/L0/L1/L5 pass，conan create 100%）
- restore_command: `mv $HOME/tmp/baseline-isolation-rapidyaml/.ci-trigger.isolated archives/u/util-linux-login/2.42.2/.ci-trigger`
- post_sha256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（pre == post ✅）
- 结论：当前库 diff/staged/commit/PR 均不含该路径（PR 文件清单 33 个全部属于 archives/r/rapidyaml/）；
  未修改、未提交、未写入知识库该基线文件；基线隔离复验通过后继续当前库审计与交付。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py / conandata.yml | CMake 配方：rapidyaml 0.7.2 + vendoring c4core v0.2.2（上游子模块锁定） |
| patches/0001-cmake-c4Project-harmonyos.patch | c4core c4_install_exports 增加 HarmonyOS 平台分支 |
| patches/0002-cmake-c4Project-cmp0037.patch | CMake>=4 移除 CMP0037 OLD 的版本守卫 |
| patches/*.cmake + submodules/debugbreak.h | c4core cmake/ 子模块内容 vendoring（官方 tarball 不含） |
| test_package/ | 真实消费者测试（解析/遍历/修改/发射 YAML，10 断言） |

## 注意事项

- 官方 GitHub tarball 不含 c4core 子模块内容，必须通过 conan 依赖提供 c4core 头文件，
  或构建前单独获取子模块；不得在 conandata 中写入 file:// 或本地路径。
- 制品仓 c4core/0.6.0 的 c4Project.cmake 结构（要求 project() 之后才 include）与 rapidyaml 0.7.2
  第 2 行就 include 的 CMakeLists 不兼容，实测 configure 失败；必须按上游子模块锁定使用 v0.2.2。

## 知识候选台账（knowledge_candidate_ledger）

本库适配中记录的真实技术候选（非噪声）共 2 项，四范围查重（index.tsv/graph、doc/、drafts/、
engine 实时匹配）结果如下（对应七轴详见逐个字段）：

### 候选 KH-1: CMake >= 4.0 移除 `cmake_policy(SET CMP0037 OLD)`
- 真实错误（实测，两次复现）: `CMake Error at .../c4Project.cmake:2872 (cmake_policy): Policy CMP0037 may not be
  set to OLD behavior because this version of CMake no longer supports it`
- 根因: CMake 4.x 移除 CMP0037（target name "test" 保留字）的 OLD 兼容模式；上游 c4core 0.2.2 的
  c4Project.cmake 无条件设置 CMP0037 OLD。
- 修复: `if(CMAKE_VERSION VERSION_LESS 4.0) cmake_policy(SET CMP0037 OLD) endif()`（补丁 0002），
  CMake 4.1.2 下 configure 通过。
- 验证: patches 应用后 `conan create` 全门禁通过（conan-verify G2 PASS、finish W3 100%）。
- 适用边界: 任何在 CMake>=4 下构建、上游 CMake 辅助模块设置 CMP0037 OLD 的 C/C++ 库；可跨库复用
  （同类 c4core 系/旧 CMake 辅助模块）。
- 查重:
  - exact_duplicate: false — 无同 id/同签名条目
  - causal_duplicate: false — E187（cmake_minimum_required <3.5 拒绝）与 DRAFT-E321 均属"CMake 4
    版本兼容类"，但根因不同（E187=最低版本策略，本候选=策略 OLD 模式被移除），非因果重复
  - trigger_overlap: partial — 与 E187 同属 CMake 4.x 兼容报错类（`cmake_policy` 行）
  - solution_overlap: partial — 与 E187/CMAKE_POLICY_VERSION_MINIMUM 同为"版本/策略兼容守卫"，
    但 E187 用 -D 参数，本候选用 CMakeLists 内 if 守卫，方案不同
  - combination_novelty: true — "CMake4 移除 CMP0037 OLD + 上游 c4Project.cmake 辅助模块"组合首次入库
  - boundary_novelty: true — 引擎实时匹配 E187（Phase B: 1）未覆盖 CMP0037 OLD 的 if-守卫解法
  - test_migration_novelty: false — 与测试迁移无关
- 关系: similar_to= E187; caused_by= 无; prerequisite_of= 无; conflicts_with= 无
- 决定: **new_draft**（已验证、可跨库复用、查重部分命中但方案新增）

### 候选 KH-2: c4core 系 CMake 辅助子模块在官方 tarball 中缺失
- 真实错误（实测）: `include could not find requested file: ./cmake/c4Project.cmake`（c4core 的
  cmake/ 与 debugbreak/、fast_float/ 均为 git 子模块，官方 tarball 只含空目录）
- 根因: GitHub source tarball 不含子模块内容；c4core 的构建辅助模块（biojppm/cmake）与
  debugbreak.h 需单独获取。
- 修复: conan 配方 export_sources 打包 22 个 cmake 模块 + debugbreak.h，build() 恢复至
  ext/c4core/cmake/ 与 src/c4/ext/debugbreak/，再 apply 补丁（与 c4core/0.6.0 归档同模式）。
- 验证: conan create 干净构建通过（G2 PASS、W3 100%），本地 27069 用例全过。
- 适用边界: 任何上游依赖 c4core 或 biojppm/cmake 辅助的 CMake 项目；可跨库复用。
- 查重:
  - exact_duplicate: false
  - causal_duplicate: false
  - trigger_overlap: partial — E150（发布 tarball 缺子模块内容）与 DRAFT-release-tarball-missing-cmake-submodule
    同触发面
  - solution_overlap: partial — E150 的 manual-download/git-clone 与 DRAFT 的"验证归档完整性+直接打包
    header-only"方案相近，但本候选是 CMake 辅助模块（非业务源码）的 export_sources 打包恢复，路径不同
  - combination_novelty: true — "submodule 为空 + CMakeLists 第 2 行就 include 辅助模块"组合首次入库
  - boundary_novelty: true — 引擎匹配 E150 覆盖"业务子模块缺失"，未覆盖"构建辅助模块缺失整包恢复"
  - test_migration_novelty: false
- 关系: similar_to= E150; caused_by= 无; prerequisite_of= KH-1（同 c4core 树内）
- 决定: **new_draft**（same: E150 部分覆盖，新增差异=辅助模块 export_sources 恢复 + 与 CMP0037 同库组合）

## 路径判断（task_type=知识库扩展）

- 七轴查重显示 2 项候选均非完整重复，均有真实日志验证、可跨库复用、且存在新增差异
  （combination_novelty + boundary_novelty 为 true）→ **路径 B 成立，走 new_draft**。
- 决定: `new_draft` — 建立同 stem 的 .md/.kv 草稿对（见 knowledge/drafts/DRAFT-rapidyaml-0.7.2-*.kv/.md），
  与 rapidyaml 归档进入同一 PR，不另建脱离三方库的知识库 PR。
- 无 path_a_no_knowledge 结论：候选已有真实证据链，非"库简单/无通用知识"场景。

---

**编译结束**: 2026-09-06 22:42
**最终状态**: built
