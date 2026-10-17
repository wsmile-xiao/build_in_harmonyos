# Knowledge Candidate Ledger — fruit 3.7.1

**日期**: 2026-09-28
**任务**: fruit-3.7.1-r01-pc7-32-20260928T011515Z（知识库扩展）
**执行端**: pc7-32 @ build_in_harmonyos worktree `feat/fruit-3.7.1`

## 一、知识候选台账（逐项非噪声候选）

### 候选 1: 上游 CMakeLists 带 Conan 1 集成块（`FRUIT_IS_BEING_BUILT_BY_CONAN` → `include(conanbuildinfo.cmake)` + `conan_basic_setup()`）在 Conan 2 下不可用

- **真实错误**: conan create 配置阶段 `include could not find .../conanbuildinfo.cmake` + `Unknown CMake command "conan_basic_setup"`（`reports/conan-create.log`，G2 失败）；上游 CMakeLists `if(FRUIT_IS_BEING_BUILT_BY_CONAN) include(conanbuildinfo.cmake); conan_basic_setup()` 是 Conan 1 时代产物，Conan 2 无此生成器
- **根因**: 上游把「是否由 Conan 构建」作为 CMake 开关，开启后走 Conan 1 的 `conan_basic_setup()` 集成；本项目 OHOS 适配版 Conan 2.29.1 移除了该机制（无 conanbuildinfo.cmake 生成、无 conan_basic_setup 命令）。若在 `generate()` 中设置该变量为 YES，configure 必然失败
- **修复**: 不设置 `FRUIT_IS_BEING_BUILT_BY_CONAN`（保持默认逻辑），使上游跳过 Conan 1 分支、正常走原生 CMake 构建；Release 下 examples/tests 子目录被加入但 `ALL` 默认只构建 libfruit（tests 的 pytest 套件仅注册不构建，另行在适配门禁单独构建并运行）
- **验证**: 修复后 conan create exit 0；上游 pytest 1201/1201 通过；test_package 消费者+鸿蒙专项编译链接运行通过
- **适用范围**: 任何上游 CMakeLists 内含 `*_IS_BEING_BUILT_BY_CONAN` / `conan_basic_setup()` Conan 1 集成分支，在 Conan 2（OHOS 基线 2.29.1）下适配的 CMake 库；cross-library 可复用
- **四范围查重**: 正式知识 **未命中**；图谱 index **未命中**；草稿 **未命中**（`grep -ril "conanbuildinfo|conan_basic_setup|BUILT_BY_CONAN" knowledge/` 无任何既有条目）；recipes catalog **未命中**（无 fruit recipe）。相关近邻：E321（上游 Conan 1.x 配方本身迁移 Conan 2，非 CMakeLists 内建集成块）、E470（Bazel BUILD 目录冲突，不同触发）

### 候选 2: CMake ≥4.x 移除 <3.5 兼容，旧 `cmake_minimum_required` 在 Conan 中须经 `cache_variables` 注入修复变量

- **真实错误**: `cmake_minimum_required` 报 `Compatibility with CMake < 3.5 has been removed`（`reports/conan-create.log`）；上游是 `cmake_minimum_required(VERSION 3.2)`
- **根因**: CMake 4.1 移除 <3.5 兼容模式；修复变量 `CMAKE_POLICY_VERSION_MINIMUM` 须在项目 `cmake_minimum_required()` 前生效，`tc.variables`（写 toolchain 文件，项目 CMakeLists 之后才 include）无效
- **修复**: conanfile.py `generate()` 同时写 `tc.variables[...]` 与 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"`（-D 命令行参数，先于一切 CMakeLists 解析生效）
- **验证**: conan create exit 0（G2）
- **适用范围**: 所有 `cmake_minimum_required(<3.5)` 老项目 + CMake ≥4 工具链（OHOS SDK 4.1.2 必然触发）；cross-library 可复用
- **四范围查重**: 正式知识 **E103/E187 命中**（fallback 即 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`）；草稿 **DRAFT-E321-cmake4-policy-version-minimum.kv 命中**（"切勿用 tc.variables、须 cache_variables" 同一结论）

### 候选 3: Bazel `BUILD` 源文件与 Conan/CMake `build` 构建目录在大小写不敏感 FS 上冲突

- **真实错误**: `NotADirectoryError: [Errno 20] Not a directory: '.../build/Release'`（`reports/conan-create.log`）
- **根因**: 上游源码根含 Bazel `BUILD` 文件；本项目文件系统（HMDFS）大小写不敏感，`build` 目录与 `BUILD` 文件同 inode 冲突
- **修复**: `layout()` 将构建/生成器目录改为 `conan-build/`（`self.folders.build`、`self.folders.generators`）
- **验证**: conan create exit 0
- **适用范围**: 源码根含 `BUILD` 文件的 CMake 库在大小写不敏感 FS 上的 Conan 构建；cross-library 可复用
- **四范围查重**: 正式知识 **E470 命中（cppitertools 同根因同方案 non-default-cmake-build-folder）**；图谱命中；草稿命中（E470 即为同主题 draft）

### 噪声项（不入账）
- fruit 语法语义（`INJECT` 宏标注可注入构造函数、抽象接口须 `get<Greeter*>()` 指针取用、`bindInstance` 临时对象退化 const 绑定）：库特有 API 用法，非跨库可复用知识 → 噪声，仅在 test_package 注释与 test-report/notes 中记录

## 二、七轴查重

| 轴 | 候选 1（Conan1 集成块） | 候选 2（CMake 4 策略） | 候选 3（BUILD 目录冲突） |
|---|---|---|---|
| exact_duplicate | false（无既有条目） | false（E103/E187/DRAFT-E321 为通用条目，无 fruit 具体实例） | false（E470 为 cppitertools 实例，包裹三问题组合） |
| causal_duplicate | false（无既有条目覆盖此根因） | true（同一根因：CMake≥4 移除 <3.5） | true（同一根因：大小写不敏感 FS + BUILD/build 同名） |
| trigger_overlap | false | true（同一错误签名正则族） | true（同一 NotADirectoryError 签名） |
| solution_overlap | false | true（同一方案：-D/cache_variables 注入） | true（同一方案：non-default build dir） |
| combination_novelty | true（Conan2 下上游 CMakeLists 内建 Conan1 集成块的适配处置，无组合先例） | false | false |
| boundary_novelty | true（新增边界：不设 `*_IS_BEING_BUILT_BY_CONAN` 即绕开 Conan1 分支的判别法，含 tests 子目录 Release 行为说明） | false（边界已有草稿表述） | false |
| test_migration_novelty | false | false | false |

## 三、路径判断

- 候选 2、候选 3 為**复用既有知识**（E103/E187/DRAFT-E321 / E470），证据已直接应用于本次配方。
- 候选 1 四范围查重全未命中、七轴 `combination_novelty=true` + `boundary_novelty=true`（已验证、可跨库复用、非完整重复）→ **走路径 B，新建草稿**（同 stem 的 .md/.kv 对，与 fruit 归档同 PR）。
- 决定：`reuse_existing`（E103/E187/E321/E470） + `new_draft`（候选 1，Conan 1 集成块适配）。`path_a_no_knowledge` 不适用。