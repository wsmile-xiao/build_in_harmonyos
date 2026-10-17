# DRAFT-jsoncons-1.9.0-test-count-and-baseline-noise

> Contributor: junshi_liu | Status: Draft | Updated: 2026-09-01
> Source: jsoncons 1.9.0 HarmonyOS PC 适配（PR #7353 审查 + W3 JC 基线噪声豁免）
> 主题：上游测试注册→运行映射（源码宏数 vs Catch2 case 数 vs assertion 数）；共享 W3 JC 基线噪声的官方 prdiff 豁免

## 现象

**问题 A（上游测试计数少报 + 注册→运行口径混淆）**：PR 模板「上游库测试用例统计」声明
jsoncons 上游为「869 test cases（20615 assertions）」。审查按官方 `test/CMakeLists.txt`
的 `add_executable(unit_tests ...)` 实际注册范围独立统计：**151 个 cpp、907 个
`TEST_CASE(...)` 宏**（含 893 常规 `TEST_CASE` + 14 `TEMPLATE_TEST_CASE` 子串；全 `test/`
目录 160 cpp、按 grep 词面约 906–910）。实测注册宏 907 > 声明 869，构成「上游 N 少报」。
但 907 是**源码宏词面**口径，Catch2 实际注册/运行 case 是 **869**（`--list-test-names-only`
去重 869，全量运行 "All tests passed (20615 assertions in 869 test cases)"，EXIT=0）。
必须区分「源码注册宏数 / Catch2 运行 case 数 / assertion 数 / 消费者 CHECK 断言数」，
不得混为同一统计口径；907→869 差额 38 需逐类归因（非测试减少或跳过掩盖）。

**问题 B（W3 JC 基线噪声拦截）**：finish/W3 本地 CI 的 `junk_check.sh` 在无 PR diff /
无增量提交时回退到 `full` 模式（`git ls-files` 整仓扫描），会把其他库 main 基线中已提交的
历史 junk 文件（如 `conandata.yml.orig`、`conandata.yml.ghfast-bak`、`.staging-verified`）
当作杂项拦截，阻塞当前库的 W3/L0-L5 门禁，即使当前库本身完全干净。

## 根因

**A**：jsoncons 上游测试用 Catch2，`test/CMakeLists.txt` 的 `unit_tests` 只注册 151 个
测试源文件（含 `testmain.cpp`），而整个 `test/` 目录有 160 个 cpp。直接数「全目录
TEST_CASE」或只跑了一次 `ctest` 后按运行输出（`unit_tests` 报 869 test cases/20615
assertions）填写模板，会与「注册范围内 TEST_CASE 宏总数 907」不一致（907 = 893 常规
`TEST_CASE` + 14 `TEMPLATE_TEST_CASE` 子串；R05 纯宏口径 893、R06 grep 子串口径 907，
均已独立复核并保留逐文件清单）。**907 是源码宏词面，而 Catch2 实际注册/运行 case 是
869**，907→869 差额 38 的构成：11 个 `#if 0` 永不编译（json_location tests 6 个、
fuzz_regression 2 个等）+ 3 个 OHOS 条件未启用（`_MSC_VER`/`FILESYSTEM && _MSC_VER`/
`!(__GNUC__ && __GNUC__<=5)`，clang 15 aarch64-linux-ohos 下不成立）+ 24 个编译但未
注册/条件编译块内未启用（allocator/stateful/polymorphic 系）。普通 `TEST_CASE` 1:1
注册 1 case，`TEMPLATE_TEST_CASE` 按类型列表实例化（31 个模板实例化 case，如
`bson_cursor reset test - bson_*_traits`），最终运行 869 case 全量通过。且 893 中约
11 个位于 `#if 0` 永不编译块、数十个位于条件编译块（`JSONCONS_HAS_STATEFUL_ALLOCATOR`
31 / `__GNUC__ && JSONCONS_HAS_INT128` 8 / `JSONCONS_HAS_POLYMORPHIC_ALLOCATOR` 6 /
`JSONCONS_HAS_STD_VARIANT` 2 / `JSONCONS_HAS_STD_REGEX` 2 / `_MSC_VER` 1 / `__GNUC__<=5` 1 /
filesystem+_MSC_VER 1），剔除 `#if 0` 后可编译约 882——不逐条说明排除项就会被判少报。

**B**：`junk_check.sh` 模式选择优先级为 prdiff > incremental > full。incremental 依赖
`git diff origin/main...HEAD`（本地开发分支有提交时生效）；当分支相对 origin/main 无
差异（新库 bootstrap 未 commit 前）或无 origin/main 时回退 full，整仓 `git ls-files`
把其他库历史基线 junk 一并扫出。JC1/JC5 只按文件路径模式匹配（`.orig`/`.ghfast-bak`/
`.staging-*` 等），不区分归属库。

## 方案

**A**：PR 模板统计一律采用「注册→运行双口径」，严禁把源码宏数当运行 case 数：
1. **源码注册宏口径**：解析官方 `test/CMakeLists.txt` `add_executable(unit_tests ...)`
   注册块，逐文件统计 `TEST_CASE(` 宏总数（907 = 893 常规 + 14 TEMPLATE 子串）作为「上游
   源码宏数」；
2. **实际运行 case 口径**：编译并运行 `unit_tests`，用 `--list-test-names-only` 列出
   去重后实际注册 case（869），全量运行确认 "All tests passed (N assertions in 869 test
   cases)" 且 EXIT=0，作为通过率分母；
3. 单独统计并说明 `#if 0`（11）与条件未启用（3：`_MSC_VER`/`FILESYSTEM && _MSC_VER`/
   `!(__GNUC__ && __GNUC__<=5)`）与编译但未注册（24），907→869 差额 38 逐类归因、严格
   合计 907，无未归属；普通 `TEST_CASE` 1:1、`TEMPLATE_TEST_CASE` 按类型列表实例化；
4. 保留完整统计命令、源码 tag/commit、日志、逐文件清单与判定台账及差异说明，不得继续
   沿用旧的 869，也不得把 CHECK 断言当 test case（消费者按 1 入口 / N 断言计）。

**B**：使用官方 prdiff 豁免：构造仅含当前 PR 白名单文件的 `pr.diff`（`git diff --no-index
/dev/null <白名单文件>` 拼接出 `+++ b/` 行），以 `JUNK_PR_DIFF=<diff>` 注入
`finish`/W3，使 `junk_check.sh` 进入 `prdiff` 模式只检查 PR 文件清单；三个基线文件
不在清单即豁免。若 W3 允许也可先 commit 使 incremental 生效（`git diff
origin/main...HEAD` 非空），但更稳妥的是 prdiff。恢复后复核基线文件内容/SHA-256 与
HEAD blob 一致、`git status` 无新增删除。

## 验证

**A**：`python3 <scripts>/count_tests.py`（解析注册块 + 逐文件统计 TEST_CASE，排除
TEST_CASE_METHOD）在官方 jsoncons v1.9.0 源码上输出：registered=151、TEST_CASE=907
（893 常规 + 14 TEMPLATE）、#if 0=11、条件分布如上；`unit_tests --list-test-names-only`
去重 869，全量运行 EXIT=0 "All tests passed (20615 assertions in 869 test cases)"；
907→869 差额 38 台账（11 + 3 + 24）严格合计 907；PR 模板按双口径（907 源码宏 + 869
实际运行 case）填写后审查规则 4（通过率/N 少报）转 PASS。

**B**：`JUNK_PR_DIFF=<pr.diff> bash ci/scripts/junk_check.sh .` 干跑输出
「检查模式: prdiff (N 个文件) / Junk Files: 0 / JC_RESULT=pass」；注入同 diff 重跑
`finish`，W3 本地 CI 通过（Build Summary 100%）；三基线文件 `git status` 干净、
磁盘 SHA-256 与 `HEAD:<path>` blob 一致。

## 适用边界

- A：所有用 Catch2/单元测试宏计数且 CMakeLists 只注册部分测试源文件的上游库；PR
  模板需区分「注册范围 TEST_CASE 数」「全目录宏数」「实际可编译数」，逐条列排除。
- B：新库 bootstrap / 无增量提交 / 无 origin/main 时 W3 JC 回退 full 被历史基线 junk
  阻塞的场景；仅对「无关历史基线文件」使用豁免，绝不豁免当前库自身真实 junk，也
  不修改、删除、提交或带入被豁免文件。

## 查重差异

- 与本仓库已有 E212（CI pre-download 正则截断 PyPI URL）不同：E212 是 CI 改写
  conandata.yml 导致 conan create 失败；本条目是「审查计数口径」+「JC full 模式基线
  噪声豁免」两个独立可复用点，且 B 已在实际 PR（jsoncons #7353）用官方 prdiff 验证。
- 不申请正式 E 编号，仅作草稿随 jsoncons PR 提交。
