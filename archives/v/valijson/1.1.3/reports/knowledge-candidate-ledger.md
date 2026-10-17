# 知识候选台账 — valijson 1.1.3 (pc3-8)

## 任务信息
- task_id: valijson-1.1.3-r01-pc3-8-20260904T192801Z
- task_type: 知识库扩展（路径 B 候选）
- 候选观察期：执行阶段登记，不做提前草稿；查重与交付在同一主任务内完成

## 候选清单（非噪声）

### 候选 1：OHOS libcxx 缺浮点 from_chars → 上游已内置自动回退（无需补丁）
- **真实错误**：valijson 1.1.1 适配时 `std::from_chars(double)` 在 OHOS libcxx
  不可用，需两个补丁把 std_string_adapter/basic_adapter 的 from_chars 替换为 strtod。
- **根因**：OHOS libcxx（clang 15 工具链，`_LIBCPP_VERSION=15004`）不提供浮点
  from_chars 重载；上游按编译器版本而非平台能力判断。
- **本轮修复/观察**：valijson 1.1.3 上游已新增 `internal/double_parser.hpp`，
  用 `_LIBCPP_VERSION>=200000 / _GLIBCXX_RELEASE>=11` 编译期检测
  `VALIJSON_HAS_STD_FROM_CHARS`，未命中时自动回退 `std::istringstream`
  （locale classic + noskipws + peek==eof 严格校验）。OHOS 工具链下
  `VALIJSON_HAS_STD_FROM_CHARS=0`，自动走 istringstream 回退，无需任何补丁。
- **验证**：上游测试 187 全量通过（0 FAIL）；鸿蒙专项测试 parseDouble 覆盖
  9 组合法输入 + 5 组非法输入全部正确（日志 SHA-256 见最终回传）；
  conan create + test_package 消费者编译运行通过。
- **适用范围**：C++17 库在 OHOS aarch64 使用浮点字符串→double 转换且上游
  依赖 std::from_chars；指导适配时**先检查上游是否已内置自动回退**，避免盲目
  复制 1.1.1 式补丁。
- **查重（四范围）**：
  - 正式知识（knowledge/graph/）：E355 命中（meson 平台映射，无关）、
    E455 命中（libcxx profile 误配 -stdlib=libstdc++，不同错误面）、
    E092（CMake 平台识别，候选 2 复用）——无同错误面的正式条目。
  - 图谱引擎：`engine "from_chars double charconv OHOS"` → E455/E217（误匹配）。
  - 草稿（knowledge/drafts/）：**DRAFT-bitserializer-0.85.0-ohos-float-from-chars-fallback**
    （.md/.kv，2026-09-03，pc1-5）同根因（OHOS libcxx 缺浮点 from_chars），
    但方案不同：bitserializer 靠**补丁关闭能力宏 + strtod 回退**；
    本轮新增差异是**上游已内置编译期自动检测 + istringstream 回退**，
    属于"先查上游内置回退，再决定是否补丁"的决策知识。
  - 知识库 doc/：无 valijson/from_chars 自动回退条目。
- **七轴查重（vs DRAFT-bitserializer）**：
  | 轴 | 结论 |
  |----|------|
  | exact_duplicate | 否（不同库、不同方案） |
  | causal_duplicate | 部分（同根因：OHOS libcxx 缺浮点 from_chars） |
  | trigger_overlap | 是（触发面相同：浮点 from_chars 编译/运行） |
  | solution_overlap | 部分（回退思路一致，但本候选是"上游内置自动检测"，非补丁） |
  | combination_novelty | 是（编译期 `_LIBCPP_VERSION/_GLIBCXX_RELEASE` 自动检测 + istringstream 严格回退的组合，既有条目未覆盖） |
  | boundary_novelty | 是（适用边界新增：先查上游版本是否已内置回退；1.1.1→1.1.3 演进实例） |
  | test_migration_novelty | 是（istringstream 回退的正确性验证方法：9 合法 + 5 非法输入用例可迁移） |
  - 既有条目覆盖：bitserializer 覆盖"需要补丁关闭 from_chars"场景。
  - 本轮新增：上游内置回退时**零补丁**；检测宏决策链；回退路径严格性验证。
  - 关系：`similar_to: DRAFT-bitserializer-0.85.0-ohos-float-from-chars-fallback`,
    `prerequisite_of: 适配前先查上游 from_chars 回退`。
  - 适用边界/反例：仅整型 from_chars 的库不适用；标准 libc++（浮点可用）不适用；
    反例：硬传 `std::chars_format` 重载仍失败。
- **决定**：`new_draft`（路径 B）——建立同 stem 草稿对
  `DRAFT-valijson-1.1.3-ohos-float-from-chars-auto-fallback.{md,kv}`。

### 候选 2：CMake 不识别 OHOS 平台（E092 复用）
- **真实错误**：`System is unknown to cmake`，valijson CMakeLists 无 OHOS 平台模块。
- **根因/修复**：generate() 设 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64。
- **查重**：正式知识 E092 完全命中（cmake-toolchain 方案）。
- **决定**：`reuse_existing`（E092），路径 A 复用，不建草稿。

### 候选 3：StdStringAdapter 持 const std::string& 引用（API 契约陷阱）
- **观察**：StdStringAdapter 成员 `const std::string &m_value`，绑定字面量临时对象
  会悬垂（maybeDouble/maybeBool 行为异常）。正确用法是绑定生存期更长的命名对象。
- **查重**：无既有条目；属库 API 文档级契约，非 OHOS 平台通用知识，跨库复用性低。
- **决定**：记录于 notes.md，不建草稿（`path_a_no_knowledge` 类）。

### 候选 4：W3 JC5 基线噪声（他库 .ci-trigger 误报）
- **观察**：main 基线已跟踪 `archives/u/util-linux-login/2.42.2/.ci-trigger`，
  本分支无提交时 junk_check 回退 full 模式误报；提交本库变更后增量模式通过。
- **查重**：属框架/基线行为，非本库知识。
- **决定**：不建草稿，仅记录（隔离/哈希记录/原样恢复，不写入知识库或 PR）。

## 路径判断
- 候选 2/3/4 → 路径 A 复用或记录。
- 候选 1 已验证、可跨库复用、查重为部分覆盖且存在新增差异 → **路径 B（知识库扩展）**，
  建草稿对，PR 前缀【知识库扩展】。
