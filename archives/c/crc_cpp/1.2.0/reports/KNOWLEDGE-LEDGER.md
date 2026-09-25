# 知识候选台账 — crc_cpp 1.2.0（task crc_cpp-1.2.0-r01-pc2-29）

## 候选条目

### C1: 上游 CMakeLists 硬编码 RUN_CONAN 导致 configure 失败的 header-only 绕过配方

- **真实错误**：`cmake -S . -B build` → `CMake Error at cmake/Conan.cmake:10 (CONAN_CMAKE_RUN): Unknown CMake command "CONAN_CMAKE_RUN"`；
  原因链：上游 CMakeLists 无条件 `INCLUDE(cmake/Conan.cmake)` + `RUN_CONAN()`，该宏先 `file(DOWNLOAD conan.cmake)`（本环境下载为 0 字节/失败），
  再 `CONAN_CMAKE_RUN(REQUIRES ... catch2/3.2.1)`——本环境 registry 无 catch2/3.2.1（实测 `conan list 'catch2/3.2.1*'` 0 匹配）。
- **根因**：上游用 cmake-conan 集成硬编码测试依赖（catch2 固定 3.2.1），在受限网络/私有 registry 环境 configure 阶段即失败；库本身是 header-only，无编译产物。
- **修复**：不走上游 CMake 构建（build_system: custom），conanfile.py 按 header-library 配方（package_type="header-library"，package() 仅拷贝 include/crc_cpp.h + LICENSE）；
  上游 Catch2 测试改用 registry 可用版本（catch2/3.8.1，仅测试期直接编译使用，不进配方依赖）编译运行，2/2 通过。
- **验证**：`conan create archives/c/crc_cpp/1.2.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...` exit 0（test_package 两个消费者二进制 ALL PASS）；
  上游 test/test.cpp 以 catch2/3.8.1 头文件 + libCatch2Main 直接编译运行，"All tests passed (47 assertions in 2 test cases)"。
- **适用范围**：上游 CMake 硬编码 cmake-conan RUN_CONAN 且测试依赖固定版本在 registry 不可得的 header-only（或可绕过 CMake 的）库；
  E322（上游自带 install/export 的 INTERFACE 库）与 E321（conan1→2 迁移）不覆盖"configure 前 RUN_CONAN 下载失败"这一触发面。

## 四范围查重结果

| 范围 | 命中条目 | 覆盖情况 |
|---|---|---|
| 正式知识 doc/+graph (index.tsv) | E257/E307/E321/E322 等 header-only 条目（E543 之前的全部） | 均无 crc_cpp；均未覆盖 RUN_CONAN/conan.cmake 下载失败+固定 catch2 版本场景 |
| 图谱引擎查询 | ohc engine "RUN_CONAN conan.cmake download failed header-only..." → 返回 E321(conan2 迁移) 等 | 部分覆盖 header-only 配方模式，未覆盖 RUN_CONAN 触发面 |
| 图谱草稿 drafts/ | DRAFT-cpp-taskflow-3.8.0-header-only-cmake-recipe（E322 草稿）等 | 无 RUN_CONAN/cmake-conan/catch2 固定版本草稿 |

## 七轴查重（C1）

| 轴 | 判定 | 说明 |
|---|---|---|
| exact_duplicate | false | 无同名/同错误特征条目 |
| causal_duplicate | false | 既有条目根因是 G1 配方完整性（E257）、conan1→2 迁移（E321）、默认测试选项（E322）；本候选根因是 RUN_CONAN 硬编码+固定测试依赖 |
| trigger_overlap | partial | "header-only" 触发词与 E257/E321/E322 重叠；"RUN_CONAN/conan.cmake 下载失败 + catch2/3.2.1 固定版本不可得" 触发器无重叠 |
| solution_overlap | partial | header-library 打包模式与 E257/E322 重叠；"绕过上游 CMake + registry 可用 catch2 替换固定版本直接编译测试" 是新增 |
| combination_novelty | true | RUN_CONAN 硬编码 + 受限下载 + header-only 绕过 + 测试依赖版本替换的组合为新差异 |
| boundary_novelty | true | 边界明确：header-only 且上游 CMake 集成不可用时绕过；对比 E322（有 install/export 仍走上游 cmake） |
| test_migration_novelty | true | 上游 Catch2 测试以替换版本（3.8.1 vs 固定 3.2.1）直接编译运行并通过，可跨库复用的测试迁移模式 |

## 路径决定

**new_draft**（路径 B：知识库扩展）——C1 已验证、可跨库复用（任何硬编码 RUN_CONAN+固定 catch2 的 header-only 库）、查重为部分覆盖且存在新增差异。
草稿：`knowledge/drafts/E543-draft-8D9D.kv` + `.md`（同 stem 配对，本仓执行端 AgentID=8D9D），与本库归档文件同一 PR。
reuse_existing: false；new_draft: true；path_a_no_knowledge: false。