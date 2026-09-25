# Knowledge Candidate Ledger — cpp-yyjson 0.8.0

**任务类型**：知识库扩展（task_type: 知识库扩展，analysis 下发）
**查重范围**：正式知识（index.tsv/E*.kv）、graph（E 条目）、drafts（knowledge/drafts/）、doc/

## 候选 1：OHOS SDK libc++（LLVM 15）缺失 C++20 `<format>` 实现（std::format 不可用）

- 真实错误：`no member named 'format' in namespace 'std'`（28 处）；`<format>` 头存在但 `__cpp_lib_format` 未定义（`_LIBCPP_HAS_NO_INCOMPLETE_FORMAT`）
- 根因：OHOS SDK26 libcxx-ohos（clang 15.0.4）将 format 标记为不完整特性
- 修复：`yyjson::detail::format` 本地最小等价实现（`{}` 占位替换，支持 bool/整数/浮点/字符串/`.write()` 类型），`#if !defined(__cpp_lib_format)` 守卫
- 验证：G2 conan create 通过，上游 21/21 测试通过
- 适用范围：任何在 OHOS clang15 上无条件 include/call std::format 的 C++20 头文件库

### 查重

| 轴 | 结果 | 说明 |
|----|------|------|
| exact_duplicate | false | 无完全同库条目 |
| causal_duplicate | false | 根因同类但修复面不同 |
| trigger_overlap | true | 触发特征（std::format 缺失）与既有条目重叠 |
| solution_overlap | true | 本地 helper 替代与 DRAFT-memsafe 方案重叠 |
| combination_novelty | false | 无新组合 |
| boundary_novelty | false | 无新边界 |
| test_migration_novelty | false | 无测试迁移新意 |

**既有条目**：DRAFT-memsafe-0.4.0-format-stub-unconditional-public-header-local-helper.kv（公开头无条件 std::format → 本地单占位符替代，高度覆盖本候选）；DRAFT-ohos-libcxx15-format-ranges-capability-gap.kv（format stub 守卫 + ranges 经典算法）；E557 主题（`__has_include(<format>)` 误判 → `__cpp_lib_format` 特性宏）
**决定**：本候选完整覆盖 → **reuse_existing**

## 候选 2：OHOS SDK libc++（LLVM 15）缺失 `<source_location>` 头

- 真实错误：`field_reflection.hpp:16 fatal error: 'source_location' file not found`
- 根因：`<source_location>` 为 C++20 P0662，libc++ LLVM 16 才落地；SDK 为 LLVM 15
- 修复：`__has_include(<source_location>)` 守卫，缺失时 `get_function_name()` 回退 `__PRETTY_FUNCTION__`（与上游 clang-cl 分支同构）
- 验证：G2 通过，反射相关全套测试（Writer/Reader/Readme）通过
- 适用范围：任何在 OHOS clang15 libc++ 上 include `<source_location>` 的 C++20 代码

**既有条目**：DRAFT-reflect-cpp-0.17.0-ohos-sdk26-libcxx-missing-source-location.kv（source_location 缺失 → __has_include 守卫降级，逐字覆盖本候选）
**七轴**：exact_duplicate=false（库不同）；trigger_overlap=true；solution_overlap=true；其余均为 false/无新增
**决定**：完整覆盖 → **reuse_existing**

## 候选 3：OHOS SDK libc++ 缺失 std::ranges 算法（transform/fill/equal/uninitialized_default_construct）与 std::ranges::views

- 真实错误：`no member named 'transform'/'fill'/'equal'/'uninitialized_default_construct' in namespace 'std::ranges'`
- 根因：libc++15 裁剪版将 ranges 归入不完整特性
- 修复：替换为 `std::transform/fill/equal` + 显式迭代器（`std::ranges::begin/end/size` 可用）；`std::ranges::views::transform` 块被上游 `__clang_major__ >= 16` 守卫自动排除
- 验证：测试全通过
- 适用范围：所有在 OHOS clang15 上使用 ranges 算法的 C++20 项目

**既有条目**：DRAFT-E5xx-ohos-libcpp-missing-ranges-algorithms.kv（ranges 算法 → std 迭代器对版本，kholidays 实证）；DRAFT-ohos-clang15-libcxx-cxx20-capability-gaps.kv（ranges + P1091 综合，cdo 实证）
**七轴**：exact_duplicate=false；trigger_overlap=true；solution_overlap=true；其余无新增
**决定**：完整覆盖 → **reuse_existing**

## 候选 4：clang 15 未实现 P1091（lambda 捕获结构化绑定）

- 真实错误：`reference to local binding 'key'/'value' declared in enclosing function`
- 根因：P1091R3 需 clang 17
- 修复：`for (auto&& [key, value] : obj)` 内先绑定具名引用 `ref_key`/`ref_value` 再捕获
- 验证：测试全通过

**既有条目**：DRAFT-ohos-clang15-libcxx-cxx20-capability-gaps.kv（P1091R3 捕获复制方案，cdo 实证 4 处同一修复）
**七轴**：trigger_overlap=true；solution_overlap=true；其余无新增
**决定**：完整覆盖 → **reuse_existing**

## 候选 5：CMake header-only 库 Conan 配方：CMakeDeps 缺失导致 find_package(依赖) 失败

- 真实错误：`Could not find a package configuration file provided by "yyjson"`（G2 configure 阶段）
- 根因：配方 generate() 只生成 CMakeToolchain，未生成 CMakeDeps，依赖的 CMake 包配置缺失
- 修复：`CMakeDeps(self).generate()`；上游安装的 config 名 `cpp_yyjsonConfig.cmake`（PROJECT_NAME）→ test_package `find_package(cpp_yyjson CONFIG REQUIRED)`
- 验证：G2 通过
- 适用范围：所有用 CMake find_package 消费 Conan 依赖的 recipe

**查重**：E092（CMake OHOS 平台映射相关）、E518/E540 等 build 类条目；grep index.tsv 未命中相同"CMakeDeps 缺失"精确模式（相关：conan 配方类目通用实践）。
**七轴**：trigger_overlap=false（针对性差异：CMakeDeps 生成器组合）；solution_overlap=false；combination_novelty=false；无既有同模式条目；不具显著跨库新增知识价值（属 Conan 2 标准用法，文档已覆盖）
**决定**：不建草稿（path_a_no_knowledge，标准工具用法）——但已在 notes.md 记录

## 路径决定

- `reuse_existing`：候选 1-4（format/source_location/ranges/P1091）均被既有草稿完整覆盖，复用已有知识
- `path_a_no_knowledge`：候选 5（CMakeDeps 标准用法）无新增知识价值
- **结论：path A（无新增知识草稿）**；不创建 .md/.kv 新草稿（避免与既有条目重复）

## 关系字段

- `similar_to`：DRAFT-memsafe-0.4.0-format-stub、DRAFT-reflect-cpp-0.17.0-ohos-sdk26-libcxx-missing-source-location、DRAFT-E5xx-ohos-libcpp-missing-ranges-algorithms、DRAFT-ohos-clang15-libcxx-cxx20-capability-gaps
- `caused_by`：OHOS SDK26 libc++15（clang 15.0.4）的 C++20 标准库能力裁剪
- `prerequisite_of`：无
- `conflicts_with`：无

## 查重结论

全部候选在正式知识/图谱/草稿/文档四范围查重后未命中"未覆盖"项；既有草稿已完整覆盖候选 1-4 的根因与方案，候选 5 为标准用法。**无新增跨库可复用知识 → 走路径 A**。