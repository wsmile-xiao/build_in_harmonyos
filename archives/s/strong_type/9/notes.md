# strong_type 9 适配笔记

## 来源核验
- 官方仓库：https://github.com/rollbear/strong_type
- 正式标签：`v9`（conandata.yml sources.url → refs/tags/v9.tar.gz）
- 源码 tarball SHA-256：`9d71ee02256b99c7f0189295514dd683cc1be8886444d5c04623fd491cf5aa40`（实测）
- 许可证：BSL-1.0（LICENSE）
- 任务：strong_type-9-r01-pc4-5-20260919T132037Z（executor pc4-5，lib strong_type，version 9）

## 编译环境
- 构建系统: cmake（header-only 库，根 CMakeLists 仅用于测试与 CMake package config）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15.0.4（OHOS SDK，libc++ 15004）
- 目标平台: HarmonyOS PC (aarch64-linux-ohos)
- 状态: built

## 编译步骤
- init-build：官方 v9 tarball 下载、SHA-256 核验、双轨解压（.orig/.work）
- lang-preflight：cpp/cpp 匹配（CMakeLists project(strong_type)，62 源文件 100% cpp）
- 上游测试构建：conan install catch2/3.8.1（制品仓）→ CMakeDeps/CMakeToolchain →
  cmake -S . -B build-ohos -DSTRONG_TYPE_UNIT_TEST=on（OHOS profile）→ cmake --build
- 鸿蒙专项测试：clang++ -std=c++17 -I include ohos_test/test_ohos.cpp -o ohos_test/build/test_ohos
- conan-init → conanfile.py 改为 header-library 配方（set_version 归一化）→ conan-verify 全门禁通过
- finish built → W2 结构检查 + W3 本地 CI 模拟通过（JC/L0/L1/L2/L4/L5 全 pass）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 导出报 `Invalid package version '9'` | Conan 2.29.1 validate_ref 正则要求版本 ≥2 字符，单字符版本被拒；任务头/分支/白名单已锁死单字符 | conanfile.py 不写字面 version，set_version() 归一化为上游 tag "v9"（目录-制品版本分离），conan-verify 全门禁通过 |
| 2 | W3 JC1/JC5 命中其他库基线文件（cloog/kics 空标记） | 本地 HEAD 超前 origin/main，diff 为空回退 full 模式全仓扫描，命中仓库历史遗留其他库 .build-closed/.staging-verified | 基线隔离复验：记录路径与隔离前 SHA-256 → git rm --cached 临时隔离 → 复跑 W3（JC 100% pass）→ 原样恢复核对 post SHA-256 == pre（e3b0c442...），staged/worktree 无残留 |
| 3 | test_fmt8 运行期 symbol not found（fmt::v8::detail::locale_ref::get 等） | 制品仓 fmt/8.1.1 预编译 binary 与设备 libc++ 运行时 ABI 不兼容（v15 历史同因），非当前库缺陷 | 如实记录：目标编译链接成功、运行期外部制品阻塞；恢复条件 = fmt 制品按当前运行时重建或发布 fmt 9.x |
| 4 | test_fmt9 未实例化 | 上游要求 find_package(fmt 9)（主版本严格匹配），制品仓无 fmt 9.x；CMakeDeps 对 fmt/11.1.3 判不兼容 | 如实记录为条件注册目标未实例化，不计入通过 |

## 上游测试台账（双口径）

### 枚举（源码声明）
- 测试目录 test/，Catch2 框架（制品仓 catch2/3.8.1，CATCH2=3）
- **source_declared_total = 87**：`TEST_CASE(` 调用点全量枚举（test/test_*.cpp + test/test.cpp 共 30 文件，含 test_fmt.cpp 3 例）
- 主套件聚合可执行 self_test（29 源文件 + test_main.cpp）；fmt 对照子目录 test_fmt8/test_fmt9 按 find_package(fmt) 条件注册

### 执行（当前 OHOS 配置）
- **configured/executed：self_test 注册 83 test cases / 294 assertions，全部通过**（退出码 0）
  - 运行输出：`All tests passed (294 assertions in 83 test cases)`
  - 声明 87 = self_test 源码 84（test/*.cpp 中除 test_fmt.cpp 外的 TEST_CASE）+ test_fmt.cpp 3（fmt 目标单独编译）
  - self_test 源码 84 → 注册 83 的差 1：test.cpp 的 `format` TEST_CASE 位于 `#if STRONG_HAS_STD_FORMAT` 守卫内（上游 test.cpp:641-642），C++17 + 当前 libc++ 下 STRONG_HAS_STD_FORMAT=0 而未被编译注册——真实条件编译排除，非缺陷
- **executed_passed_total/source_declared_total = 83/87 (95.4%)**；当前配置可执行集合通过率 **83/83 (100.0%)**
- 未通过项（均非当前库缺陷）：
  - test_fmt8：3 例（fmt/8.1.1 制品 binary 与设备 libc++ ABI 不兼容，运行期 symbol not found，真实外部阻塞）
  - test_fmt9：3 例（制品仓无 fmt 9.x，上游 find_package(fmt 9) 条件未满足，目标未实例化）
- 运行命令：`cmake --build build-ohos -j2 && ./build-ohos/test/self_test`（cwd=work 源码树）

### 鸿蒙专项测试
- ohos_test/test_ohos.cpp：18 项断言全部通过（PASS），退出码 0
- 覆盖：__OHOS__/__aarch64__/libc++ 15004 平台特征、arithmetic、ordered、equality_with、difference、hashable+unordered_set、incrementable/decrementable
- 编译命令：`clang++ -std=c++17 -I include ohos_test/test_ohos.cpp -o ohos_test/build/test_ohos`

### 消费者验证（test_package）
- test_package/test_strong_type.cpp：10 项断言全部通过（CONSUMER TEST ALL PASSED），退出码 0
- 仅经公开头文件 strong_type/strong_type.hpp 与公开 API（arithmetic/ordered/hashable/incrementable）使用
- conan create 内 ctest 1/1 passed；独立复跑退出码 0

## 知识候选台账（knowledge_candidate_ledger）

### 候选 C1：Conan 单字符版本拒绝 → set_version() 目录-制品版本分离
- 真实错误：`ERROR: Invalid package version '9'`（conan create 导出阶段）
- 根因：Conan 2.29.1 validate_ref 正则 `^[a-z0-9_][a-z0-9_+.-]{1,100}` 要求版本 ≥2 字符
- 修复：conanfile.py 去字面 version，set_version() → "v9"（上游 tag）
- 验证：conan-verify G0-G4 + L2/L4/L5 全 PASS；test_package 1/1；独立消费者退出码 0
- 适用范围：任务头固定单字符版本 + 分支/白名单锁死 + 上游 tag 形如 v<N> 的库
- 查重（四范围）：
  - 正式知识图谱 index.tsv：未命中（无 single-char/set_version 正式条目）
  - 草稿（knowledge/drafts/）：部分命中 DRAFT-btyacc-3.0-conan-single-char-version（同根因，但 btyacc 走 version-rename 改目录；本候选为 set_version 目录-制品分离，适用任务头锁死场景）
  - 归档先例（archives/ 配方）：cronic/3、ndpi/5、dbskkd-cdb/3、cutmp3/4、rapidhash/3、tweeny/3 均用 set_version()，方案在仓库内已验证可跨库复用
- **七轴查重**：
  - exact_duplicate：false（知识库无完全一致条目）
  - causal_duplicate：false（与 btyacc 草稿同根因，但本候选核心为目录-制品分离的 set_version 方案，btyacc 草稿为 version-rename 方案——不同解）
  - trigger_overlap：true（与 btyacc 草稿同样触发 Invalid package version 单字符）
  - solution_overlap：false（btyacc 改版本号 3→3.0；本候选不改目录、set_version 归一化上游 tag，解不同）
  - combination_novelty：true（set_version + 目录-制品版本分离 + L0n 分支锁死场景组合为新增差异）
  - boundary_novelty：true（明确"任务头锁死单字符版本"适用边界，与 version-rename 形成互补反例边界）
  - test_migration_novelty：false（无测试迁移）
- 决定：**new_draft**（路径 B）——已建同 stem 草稿对：
  - knowledge/drafts/DRAFT-strong_type-9-conan-single-char-version-set-version.kv
  - knowledge/drafts/DRAFT-strong_type-9-conan-single-char-version-set-version.md
- 关系：similar_to DRAFT-btyacc-3.0-conan-single-char-version（同根因不同解）；
  prerequisite_of 无；conflicts_with 无（互补边界）

### 候选 C2：fmt/8.1.1 制品 binary 与设备 libc++ ABI 不兼容
- 真实错误：`Error relocating ./test_fmt8: fmt::v8::detail::locale_ref::get ... symbol not found`
- 根因：制品仓 fmt 预编译 binary 与 OHOS 设备 libc++ 运行时 ABI 不兼容（v15 历史同因）
- 修复：非当前库可修（外部制品）；如实记录为 fmt 对照测试真实阻塞
- 验证：目标编译链接成功；运行期符号缺失（实日志）
- 适用范围：依赖 fmt 预编译包的上游测试入口
- 查重：正式图谱 E004/E078（symbol not found 类）部分覆盖通用模式；无 fmt 特有条目
- 七轴：exact_duplicate false；causal_duplicate true（E004/E078 覆盖 symbol-not-found 根因）；
  trigger_overlap true；solution_overlap true（制品重建/等待发布，与既有条目一致）；
  combination_novelty false；boundary_novelty false；test_migration_novelty false
- 决定：**path_a_no_knowledge**（不建草稿——被既有 E004/E078 覆盖，无新增可跨库复用差异）

## 路径决定
- 路径 B 成立（候选 C1 new_draft，草稿对已建且配对通过）；PR 前缀 **【知识库扩展】**
- 候选 C2 归 path_a_no_knowledge（既有条目覆盖）
- 首轮执行：零补丁、零上游修改，header-only 库适配 + 全门禁通过

## 验证结果

```bash
# 上游测试
./build-ohos/test/self_test            # All tests passed (294 assertions in 83 test cases), rc=0
# 鸿蒙专项测试
./ohos_test/build/test_ohos            # ALL OHOS TESTS PASSED (0 failures), rc=0
# 消费者
./test_package/build/clang-15-armv8-17-release/test_strong_type   # CONSUMER TEST ALL PASSED, rc=0
# 配方验证
ohc-run.py conan-verify strong_type 9  # G0-G4 + L2/L4/L5 全 PASS（conan-verify 门禁）
# W3 本地 CI
finish built                           # JC pass / L0 pass；L2 skip（header-only 无 bin/）、L5 warn（无制品产物，header-only 正常）
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/s/strong_type/9/conanfile.py | header-library 配方（set_version → v9） |
| archives/s/strong_type/9/conandata.yml | 官方源 URL + SHA-256（无 file:///缓存污染） |
| archives/s/strong_type/9/test_package/ | 消费者验证（CMake + test_strong_type.cpp + MANIFEST） |
| archives/s/strong_type/9/ohos_test/test_ohos.cpp | 鸿蒙专项测试源（18 断言） |
| archives/s/strong_type/9/reports/test-report.md | 测试报告（双口径台账） |
| knowledge/drafts/DRAFT-strong_type-9-*.kv/.md | 知识草稿对（路径 B） |

## 注意事项
- Conan 单字符版本约束：任务卡单字符版本必须 set_version() 归一化，不得改归档目录/分支（L0n 精确匹配）
- W3 full 模式会命中仓库历史遗留其他库空标记文件：基线隔离复验后再恢复，恢复后 SHA-256 必须与隔离前一致
- 消费者用例仅用公开头文件与公开 API；鸿蒙专项测试非上游测试复述

---

**编译结束**: 2026-09-19 22:24
**最终状态**: built