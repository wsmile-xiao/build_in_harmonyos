# lzav 5.17 知识候选台账与四范围/七轴查重

**任务**: lzav-5.17-r01-pc4-1-20260918T174002Z（知识库扩展）
**查重范围**: knowledge/graph/index.tsv(540+ 条)、knowledge/doc/、knowledge/graph/*.kv、knowledge/drafts/*.kv 四范围
**查重日期**: 2026-09-19

## 候选清单（非噪声）

| # | 候选（真实错误→根因→修复→验证） | 适用范围 | 是否噪声 |
|---|----------------------------------|----------|---------|
| C1 | conan `get()` 从 codeload URL（末段为 tag 名 `5.17`，无扩展名）推断为 zip → BadZipFile → conandata.yml sources 加 `filename: lzav-5.17.tar.gz` → G2 通过 | 所有使用 codeload tar.gz 直链的配方 | 否（完全重复） |
| C2 | conan-verify G1 要求 conanfile.py 必须有 `build()` 方法 → header-only 库初始无 build() → 补空 build()（仅 apply_conandata_patches）→ G1 通过 | 所有 header-only 配方 | 否（完全重复） |
| C3 | header-only 模板 package() 相对路径 `dst="include"` 未落到 package 目录 → "No files in this package!" → G2 test_package Imported target 路径不存在 → 改 `dst=self.package_folder` + `includedirs=["."]` + `package_type="header-library"` → G2 通过 | 所有 header-only 配方（Conan 2 copy 相对路径陷阱） | 否（完全重复） |
| C4 | `package_type="library"` 无 `shared` option → conan create 报错 → header-only 库改用 `header-library` 类型 → 构建通过 | 所有 header-only 库 | 否（完全重复） |
| C5 | lang-preflight 对 header-only C 库误判：tarball 仅 LICENSE/README.md/lzav.h，无 .c/.cpp 实源 → `_source_stats` 输出"无源文件可统计" → detected_language=other(none) → 自动写 env_unsupported 终态 | 所有 header-only / 单头文件 C/C++ 库 | **否（新增，未命中/部分覆盖）** |
| C6 | W3 本地 CI 的 junk_check（full 模式 `git ls-files`）命中其他库提交前已存在的基线空文件（cloog/kics 的 .build-closed/.staging-verified）→ JC 拦截 → 基线隔离复验（记录 pre-SHA256 → mv+git rm --cached → 复跑 → 原样恢复 → post-SHA256 一致）→ W3 通过 | 整仓 full 模式扫描场景（工具行为，非配方知识） | 否（流程执行，SKILL 已定义，不建条目） |

## 逐项七轴查重

### C1: codeload BadZipFile → filename

| 轴 | 结论 | 依据 |
|----|------|------|
| exact_duplicate | **true** | E276（error_signature `BadZipFile.*codeload.github.com/.../tar.gz/refs/tags/vX.Y.Z`）、E392（BadZipFile + get() + filename + strip_root + codeload.github.com）、E483（error_signature `BadZipFile.*File is not a zip file` + root_cause 完全一致：URL 末段是 tag 名 → conan 存为 "5.17" 默认按 zip 解压） |
| causal_duplicate | true | 根因同一：conan 按 URL basename 推断格式 |
| trigger_overlap | true | 触发面相同（codeload tag 直链） |
| solution_overlap | true | E276/E483 rec_approach 同为显式 filename（get 调用或 conandata filename） |
| combination_novelty | false | 无新组合 |
| boundary_novelty | false | 无新边界 |
| test_migration_novelty | false | 无 |

**判断**: 完全重复 → 复用已有知识（E276/E392/E483），路径 A 组件。

### C2: header-only G1 缺 build()

| 轴 | 结论 | 依据 |
|----|------|------|
| exact_duplicate | **true** | E257 error_signature `G1: FAIL|conanfile.py 缺少: build() 方法`，rec_approach no-op-build-for-header-only |
| causal_duplicate | true | 同一：G1 静态检查要求 build() 存在 |
| trigger_overlap | true | 同一（conan-verify G1） |
| solution_overlap | true | 同一（no-op build） |
| combination_novelty | false | |
| boundary_novelty | false | |
| test_migration_novelty | false | |

**判断**: 完全重复 → 复用 E257，路径 A 组件。

### C3: header-only package() 空包（copy 相对路径）

| 轴 | 结论 | 依据 |
|----|------|------|
| exact_duplicate | **true** | DRAFT-picojson-1.3.0-conan-copy-absolute-dst（error_signature `package\(\)\..*WARN: No files in this package!|Imported target .* includes non-existent path .*/include`，root_cause 一致：package() 时 CWD 非 package_folder，相对 dst 落错目录）；DRAFT-gulrak-filesystem-1.5.8-headeronly-copy-nested-include（error_signature `Imported target .* includes non-existent path.*\.conan2/p/.*/p/include`） |
| causal_duplicate | true | 同一（copy 相对路径/CWD 陷阱） |
| trigger_overlap | true | 同一（conan create test_package 阶段） |
| solution_overlap | true | 同一（dst=self.package_folder 绝对路径 / subdir-aware copy） |
| combination_novelty | false | |
| boundary_novelty | false | |
| test_migration_novelty | false | |

**判断**: 完全重复 → 复用 DRAFT-picojson / DRAFT-gulrak（同族草案），路径 A 组件。

### C4: library 类型缺 shared option

| 轴 | 结论 | 依据 |
|----|------|------|
| exact_duplicate | **true** | E321（header-only-lite-conan2-migration：package_type=header-library）、E322（header-only-cmake-interface-recipe：`package_type.*header-library` error_signature + self.info.clear）均含该修复 |
| causal_duplicate | true | 同一（Conan 2 package_type 校验） |
| trigger_overlap | true | 同一 |
| solution_overlap | true | 同一（header-library） |
| combination_novelty | false | |
| boundary_novelty | false | |
| test_migration_novelty | false | |

**判断**: 完全重复 → 复用 E321/E322，路径 A 组件。

### C5: lang-preflight header-only 误判 other → env_unsupported

| 轴 | 结论 | 依据 |
|----|------|------|
| exact_duplicate | **false** | 全库无"header-only 无 .c/.cpp 实源 → other"条目 |
| causal_duplicate | **部分** | DRAFT-cl-unicode-lisp-lang-hold-verification 同为 `detected_language: other/无可统计源文件`，但其根因是**纯 Lisp**（真实非 C/C++，lang-hold 正确）；DRAFT-debugbreak-1.0-langpreflight-gnumakefile-misdetect 同为 lang-preflight 误判但根因是 GNUmakefile 未识别 + 辅助 .py 计入主体 → mixed。两者都不覆盖"header-only C/C++ 库因无 .c/.cpp 实源被判 other"这一边界 |
| trigger_overlap | **true（部分）** | cl-unicode 的 `语言不匹配: task=cpp, detected=other|无可统计源文件` 触发面文本重叠；debugbreak 的 lang-preflight 触发工具重叠 |
| solution_overlap | **true（部分）** | cl-unicode rec_approach=lang-hold-with-evidence（针对真实非 C/C++）；debugbreak=manual-boundary-rule-override（针对 mixed 误判）；C5 需要的是"header-only C/C++ 兼容族手动复核覆盖为 cpp 并继续适配"，与 debugbreak 的 manual override 同族但针对无实源场景 |
| combination_novelty | false | 无新组合 |
| boundary_novelty | **true** | 新增边界：**header-only 库（官方 tag 仅 .h 无 .c/.cpp 实源）在 lang_detect 扩展名统计下零计数 → other(none) 误判 → 必须按 R47 c↔cpp 兼容族 + manifest/README 证据人工复核为 cpp 继续适配**；既有条目只覆盖"真实非 C/C++（Lisp）"和"辅助脚本混入 mixed"，均未覆盖"无实源的纯头文件 C/C++ 库" |
| test_migration_novelty | false | |

**判断**: 部分覆盖 + 存在新增差异（无实源 header-only 库的边界判定），且本轮已实测（lzav 适配完整完成，全部门禁通过）可跨库复用（任何单头文件 C/C++ 库）→ **走路径 B，建立草稿对**。

### C6: W3 full 模式命中其他库基线文件（基线隔离）

| 轴 | 结论 | 依据 |
|----|------|------|
| 全部七轴 | 不适用 | 属于 SKILL.md 已定义的流程执行规则（基线隔离复验），非错误模式知识；无需建条目 |

**判断**: 流程执行，按 SKILL 规则完成隔离复验（pre==post SHA-256 e3b0c442...，路径已恢复，本库 diff 不含），不建草稿。

## 路径决定

| 候选 | 决定 | 依据 |
|------|------|------|
| C1 | reuse_existing（E276/E392/E483） | 完全重复 |
| C2 | reuse_existing（E257） | 完全重复 |
| C3 | reuse_existing（DRAFT-picojson/DRAFT-gulrak） | 完全重复 |
| C4 | reuse_existing（E321/E322） | 完全重复 |
| C5 | **new_draft**（DRAFT-lzav-5.17-langpreflight-headeronly-other.kv/.md） | 部分覆盖 + boundary_novelty + 已实测可跨库复用 |
| C6 | path_a_no_knowledge（流程执行） | SKILL 定义，非错误模式 |

**总结**: 存在已验证、可跨库复用且查重为部分覆盖并含新增差异的候选（C5）→ **路径 B**，建立同 stem 的 .md/.kv 草稿对，PR 前缀【知识库扩展】。

## 关系字段

- C5 similar_to: DRAFT-cl-unicode-lisp-lang-hold-verification（同为 lang-preflight other/无可统计源文件）、DRAFT-debugbreak-1.0-langpreflight-gnumakefile-misdetect（同为 manual-boundary-rule-override 家族）
- C5 caused_by: lang_detect.py `_source_stats` 对 .h 中立不计数 + header-only 库无实源
- C5 conflicts_with: 无
- C5 prerequisite_of: 无
