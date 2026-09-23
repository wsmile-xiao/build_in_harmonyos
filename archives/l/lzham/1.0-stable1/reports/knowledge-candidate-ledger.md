# lzham 1.0-stable1 知识候选台账与七轴查重

**任务**: lzham-1.0-stable1-r01-pc4-3-20260907T141525Z（知识库扩展候选评估）
**查重范围**: knowledge/graph/index.tsv(542 条)、knowledge/doc/、knowledge/graph/*.kv、knowledge/drafts/*.kv 四范围
**查重日期**: 2026-09-08

## 候选清单（非噪声）

| # | 候选（真实错误→根因→修复→验证） | 适用范围 | 是否噪声 |
|---|----------------------------------|----------|---------|
| C1 | OHOS musl 极小 malloc/realloc 仅 8 字节对齐 → lzham 自定义分配器要求 16 对齐不变量被破坏 → 初始分配改 `memalign(16,size)` 且 realloc 返回未对齐时拷贝修复 → 修复后 8/8+全矩阵通过 | 任何自带对齐契约分配器的 C/C++ 库（2015 年前后代码常见） | 否 |
| C2 | musl stdint.h 将 INT32_MIN/INT32_MAX 等定义为宏 → 2015 年代 C++ 代码自声明 `const int32 INT32_MIN = ...` 编译报 expected unqualified-id → 平台守卫 `#undef`（lzham 上游仅覆盖 Apple/BSD，OHOS 需追加 `__OHOS__`）→ 构建通过 | 定义 INTxx_MIN/MAX 等常量的旧 C/C++ 代码库 | 否 |
| C3 | CMake 4.x 移除 `cmake_minimum_required < 3.5` 兼容 → 配置报错 → `CMAKE_POLICY_VERSION_MINIMUM=3.5` → 构建通过 | 所有老版本 CMake 项目 | 否，但完全重复 |
| C4 | conan `get()` 无法从无扩展名 codeload URL 推断 tar.gz 类型 → BadZipFile → conandata.yml sources 加 `filename:` → 构建通过 | 所有用 codeload tar.gz 的配方 | 否，但完全重复 |

## 逐项七轴查重

### C1: musl 小分配 8 字节对齐 vs 16 对齐不变量

| 轴 | 结论 | 依据 |
|----|------|------|
| exact_duplicate | false | 无同库同错误条目标题命中 |
| causal_duplicate | **true（部分）** | E476（foonathan/memory）根因同为"OHOS musl 对小尺寸 malloc 返回 8 字节对齐，破坏 16 字节 max_alignment 契约"，因果完全一致 |
| trigger_overlap | **true** | E476 error_signature `alignment.*16`、match_keywords `max_align_t/posix_memalign/OHOS` 与 C1 触发面重叠 |
| solution_overlap | **true** | E476 rec_approach 同为 source-code-patch：`posix_memalign(max_alignment, size)` + `std::free`；C1 用 `memalign(16,size)` + `free`，方案同族 |
| combination_novelty | false | 无新组合 |
| boundary_novelty | **true** | E476 仅覆盖 foonathan/memory 的 malloc_allocator/new_allocator 路径；C1 新增两点：(a) 2015 年代**自定义分配器封装**（`lzham_default_realloc` 整层）同样受影响；(b) **musl realloc 移动分配时也可能落到 8 对齐小块**，因此 realloc 返回指针也必须复检对齐并修复——E476 未覆盖 realloc 路径 |
| test_migration_novelty | false | 无测试迁移价值差异 |

**判断**: 部分覆盖 + 存在新增差异（自定义分配器层 + realloc 返回对齐复检）且已实测可跨库复用 → **走路径 B，建草稿**

### C2: INTxx_MIN/INTxx_MAX 宏冲突

| 轴 | 结论 | 依据 |
|----|------|------|
| exact_duplicate | false | 全库检索 `INT32_MIN|INT8_MIN|undef.*_MIN|expected unqualified-id` 无命中 |
| causal_duplicate | false | E082（gnulib conftest）/E133（musl 头遮蔽）/E432（native API 契约）均非同一因果 |
| trigger_overlap | false | E133 触发是 -isystem 头遮蔽，非宏冲突；E082 是 sed 读取 conftest 失败，无关 |
| solution_overlap | false | 无既有条目提供 `#undef` 守卫方案 |
| combination_novelty | false | 无新组合 |
| boundary_novelty | **true** | lzham 上游已为 Apple/FreeBSD/NetBSD 提供 undef 守卫，OHOS 属新增平台边界（musl 定义这些宏），守卫需追加 `__OHOS__` |
| test_migration_novelty | false | 无 |

**判断**: 未命中 + 已实测（__OHOS__ 守卫编译通过、全测试过）+ 可跨库复用（旧 C++ 代码定义同名常量很常见）→ **走路径 B，建草稿**

### C3: CMake 4.x 策略版本

| 轴 | 结论 |
|----|------|
| exact_duplicate | **true**（E103、E187、DRAFT-E321-cmake4-policy-version-minimum 完全覆盖） |
| 其余轴 | 触发/方案/边界均重叠，无新增差异 |

**判断**: 完整重复 → **复用已有知识，路径 A（不建草稿）**

### C4: conan get() BadZipFile

| 轴 | 结论 |
|----|------|
| exact_duplicate | **true**（E276、E392 完全覆盖：codeload + filename + BadZipFile） |
| 其余轴 | 无新增差异 |

**判断**: 完整重复 → **复用已有知识，路径 A（不建草稿）**

## 路径决定

- C1 → **new_draft**（DRAFT-lzham-1.0-stable1-musl-alloc-alignment，.kv/.md 配对）
- C2 → **new_draft**（DRAFT-lzham-1.0-stable1-stdint-int-min-macro，.kv/.md 配对）
- C3 → **reuse_existing**（E103/E187）
- C4 → **reuse_existing**（E276/E392）
- 结论: 路径 B（知识库扩展）成立，2 个新草稿随本 PR 交付

## 关系字段

- C1: similar_to=[E476]; caused_by=[]; prerequisite_of=[]; conflicts_with=[]
- C2: similar_to=[E133]; caused_by=[]; prerequisite_of=[]; conflicts_with=[]
- C3: similar_to=[E187]; caused_by=[]; prerequisite_of=[]; conflicts_with=[]
- C4: similar_to=[E276, E392]; caused_by=[]; prerequisite_of=[]; conflicts_with=[]

## 适用边界/反例

- C1 反例: glibc/新版 musl 若对全部尺寸保证 16 对齐则不触发；已在目标运行时实测 malloc(2/3) 返回 8 对齐为触发前提
- C2 反例: 使用标准 `<cstdint>` 且不自声明同名常量的新代码不触发；仅影响定义 `INTxx_MIN/MAX` 等常量的旧代码
- 两草稿均记录"验证命令 + 退出码 + 触发前提 + 恢复条件"（见草稿 verification_cmd / fallback）
