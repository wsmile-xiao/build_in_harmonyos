# hash-library 8 知识候选台账（knowledge_candidate_ledger）

任务类型: 知识库扩展（task_type=知识库扩展）；路径初判依据 ./SKILL.md §6 流程 + knowledge-reuse-governance 四范围查重。
时间: 2026-09-22

## 候选枚举（适配过程真实触发的非噪声问题）

| # | 候选（真实错误/根因/修复/验证） | 适用范围 | 四范围查重结果 |
|---|------|------|------|
| C1 | 单字符版本号 "8" 被 Conan 拒绝（Invalid package version '8'）；根因 Conan 2.29.1 validate_ref 正则要求 ≥2 字符；修复 set_version() 归一化为上游 tag "v8"，归档目录/分支保持 "8"；验证 conan-verify G0-G4+L2/L4/L5 全 PASS | 任务头固定单字符版本、分支/白名单锁死、上游 tag 形如 v<N> 的库 | **exact_duplicate**：DRAFT-strong_type-9-conan-single-char-version-set-version 草稿已完整覆盖同错误签名/同方案/同验证（strong_type/9→v9 与 hash-library/8→v8 完全同构），另 cronic/3、ndpi/5、dbskkd-cdb/3、cutmp3/4、rapidhash/3、tweeny/3 均为既有实践 |
| C2 | tools.build:compiler_executables 是 dict 类型，conf.get 直接取 str 报 "does not exist in configuration list"；根因 Conan profile 中该 conf 为字典 {'c','cpp'}；修复 check_type=dict 整体获取再 .get("c")；验证 conan create 编译通过 | 所有 OHOS profile 下 Conan 配方的编译器获取 | **exact_duplicate**：E392（raw-makefile-conan-recipe-pattern）已正式收录（compiler_executables, dict, check_type），E307 亦引用同 conf 读取模式 |
| C3 | self.run() 默认 cwd 为 build_folder，源码在 source_folder 报 "no such file or directory: crc32.cpp"；根因 basic_layout 下 build 与 source 分离；修复 self.run(..., cwd=self.source_folder)；验证 conan create 全流程通过 | 无构建系统/raw makefile 配方 | **exact_duplicate**：E392 已收录（cwd, source_folder, build_folder, raw makefile） |
| C4 | copy() 相对 dst 解析到 build 目录导致 "No files in this package!"；根因 copy() dst 相对路径基于 cwd（build）而非 package_folder；修复 dst=os.path.join(self.package_folder, ...)；验证 conan create package 产出 lib/include/bin/licenses | 所有手动打包配方 | **exact_duplicate**：DRAFT-cmrc-2.0.1-cmake-module-distribution（"copy() 相对 dst 会解析到 build 目录而非 package_folder，导致包目录为空"）与 DRAFT-boost-te-1.0.0-headeronly-copy-abs-path 已覆盖 |
| C5 | 多 TU 无构建系统 C++ 库（6 个 .cpp 实现 + .h + digest CLI 示例）的 Conan 配方组合模式：逐文件 clang++ -c → llvm-ar rcs → ranlib → CLI 编译 → 头文件/静态库/CLI 打包 → R38 commands.json 声明 CLI | 无构建系统、多翻译单元（>1 个 .cpp 实现文件）、附带 CLI 示例工具的 C++ 库 | **partial_overlap + combination_novelty**：DRAFT-hashmap-0.8.1-no-build-system-single-tu-lib 仅覆盖单 TU C 源库（1 个 .c）；E392 覆盖 raw makefile；E257 覆盖纯 header-only no-op；本库是多 TU C++ 实现（循环编译 6 个 TU）+ 静态库 + CLI 工具 + commands.json（R38）组合，hashmap 草稿 affected_scope 明确排除多 TU（"仅适用…单 TU 库"） |

## 七轴查重（C5，唯一需要新草稿的候选）

| 轴 | 结果 | 说明 |
|----|------|------|
| exact_duplicate | false | 无条目与"多 TU 无构建系统 C++ 库 + CLI"完全同构 |
| causal_duplicate | false | hashmap 草稿根因是"单 TU .c 被误判 autotools"，本库根因是"多 TU .cpp 无构建系统需逐 TU 编译"，机制不同（循环编译 + 多 TU 归档） |
| trigger_overlap | true | 均触发于"conan-init 按 autotools 模板生成不适用配方"（hashmap 草稿 error_signature 同） |
| solution_overlap | true | 均用 custom 配方 + conf 取编译器 + cwd=source_folder + 绝对路径 copy（部分共享 E392/DRAFT-cmrc 要素） |
| combination_novelty | true | 新增差异：多 TU 循环编译模式、C++（非 C）实现、库+CLI 双产物、R38 commands.json 原子性声明（CLI 交付）——hashmap 草稿明确排除多 TU 且无 CLI |
| boundary_novelty | true | 边界差异：hashmap 草稿限制"仅适用实现体在 .c、无任何构建系统的单 TU 库"；本候选扩展至多 TU C++ 库 + CLI 双产物 + commands.json 交付边界 |
| test_migration_novelty | false | 上游测试 3 独立可执行（tests.cpp/issue2/issue6）为常规直编运行，无迁移创新 |

## 关系字段

- similar_to: DRAFT-hashmap-0.8.1-no-build-system-single-tu-lib（同族 custom 直编配方，TU 数与语言不同）
- similar_to: E392 raw-makefile-conan-recipe-pattern（编译器 dict / cwd / copy 共享要素）
- caused_by: 无（不因某既有条目导致）
- prerequisite_of: 无
- conflicts_with: 无

## 路径决定

- C1-C4: reuse_existing（复用 DRAFT-strong_type-9 / E392 / DRAFT-cmrc / DRAFT-boost-te 既有知识）
- C5: **new_draft** — 已验证（conan-verify 全 PASS + 上游 3/3 + OHOS 专项 14 项全过）、可跨库复用（同形态 C++ 库）、查重部分覆盖且存在组合/边界新增差异 → 建立 DRAFT-hash-library-8-*.kv/.md 草稿
- 综合决定: **Path B（知识库扩展）**，PR 前缀 【知识库扩展】，草稿与三方库归档同 PR 交付