# sqlitecpp 3.3.3 — 知识候选台账与查重结果

任务: sqlitecpp-3.3.3-r01-pc1-31-20260903T014443Z
worktree: （worktree: worktrees/pc1-31-sqlitecpp-3.3.3）
分支: feat/sqlitecpp-3.3.3

## 一、候选记录

### 候选 1：内部自带静态库必须随 package_info 声明完整静态链

- 真实错误：conan create 的 test_package 阶段链接失败，`ld.lld: error: undefined symbol: sqlite3_column_name / sqlite3_open_v2 / sqlite3_exec ...`（too many errors emitted），消费者仅链接 `sqlitecpp::sqlitecpp` 却缺全部 sqlite3_* 符号。
- 根因：SQLiteCpp 上游 CMake 以 `SQLITECPP_INTERNAL_SQLITE=ON`（默认）内嵌编译 sqlite3 静态库（sqlite3/CMakeLists.txt → libsqlite3.a），但初始 conanfile.py 的 `package_info()` 只声明 `cpp_info.libs = ["SQLiteCpp"]`。静态库不会传递依赖：libSQLiteCpp.a 中对 sqlite3_* 的引用必须由消费者显式链接 libsqlite3.a 满足。
- 修复：`package_info()` 改为 `self.cpp_info.libs = ["SQLiteCpp", "sqlite3"]`（链接顺序：消费者在前，依赖在后）。
- 验证：修复后 conan create（test_package 消费者）→ `1/1 Test #1: test_sqlitecpp ... Passed`；上游 googletest 49/49 通过（构建产物独立验证）。
- 适用范围：任何「库 A 内嵌/捆绑另一个静态库 B（add_subdirectory + target_link_libraries(A PUBLIC B)）」的 Conan 静态配方；不限于 sqlitecpp/sqlite3，适用于 zlib→libpng、libxml2 内嵌 ICU 等同类模式。仅影响静态链接（shared 时由动态链接器解析）。
- 知识类型：Conan 配方 / package_info 静态链建模。

## 二、四范围查重

| 范围 | 命中条目 | 覆盖情况 |
|------|----------|----------|
| 正式知识 knowledge/graph/ | E221（library 契约：libs/system_libs 按实际顺序填写）、E539（静态归档链接 DSO 探针） | 部分覆盖：E221 强调"按实际顺序填写 libs"，但场景是 CLI+库双模型，未覆盖"内嵌静态依赖库必须在 libs 列出才能被消费者链接"；E539 证明静态库可用性（PIC），非内嵌依赖链声明 |
| 图谱 knowledge/graph/index.tsv | E236（libtool .la 元数据）、E524（依赖注入私有 prefix）、E092（CMake OHOS 平台） | 未命中：均为 autotools/libtool 或注入前缀场景，与 cmake 内嵌静态库声明无关 |
| 知识草稿 knowledge/drafts/ | DRAFT-concurrencpp（头文件 includedirs）、DRAFT-cpplocate（test_package 可靠性） | 未命中：前者头文件安装路径，后者 NDEBUG/断言可靠性，均非静态链声明 |
| 图谱文档 knowledge/doc/ | E236.md / E280.md / E524.md | 未命中（同 index.tsv 结论） |
| 引擎匹配（ohc-run.py engine） | 首匹配 E123（meson 静态/动态库混链） | 部分覆盖：同为"静态库依赖链在链接期缺符号"，但构建系统为 meson 且场景为 .so/.a 混用，非 Conan cpp_info.libs 建模 |

## 三、查重结论与路径初判

- 候选 1 在正式知识中未被完整覆盖（E221 是 CLI+库双模型契约，非内嵌静态依赖链；E123 是 meson 混链）；存在新增差异：**Conan 2 配方中内嵌静态库必须按链接顺序写入 cpp_info.libs**。
- 但该候选为 Conan 标准行为（静态库不传递依赖）在 sqlitecpp 具体配方中的一次落地，通用性高、与已有 E221 理念同源，属"已存在知识的具体应用"而非全新错误模式。按 knowledge-reuse-governance：复用已有 E221 知识（按实际顺序声明完整 libs），不新建草稿 → 走**路径 A（【积分赛】常规适配）**。
- 补充：本任务任务头标注 `task_type: 依赖项`、`initial_pr_prefix: 【依赖项】`，路径判定与任务头一致（依赖项标注不替代路径前缀，本任务无高难证据，不构成路径 B/C）。

## 四、测试台账

见 3.3.3/reports/sqlitecpp-r01-tests-ledger.md（完整枚举台账）。
