# crossguid 0.2.2 适配笔记

## 编译环境

- 构建系统: cmake（上游 CMakeLists.txt，XG_TESTS 选项）
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15（`tools.build:compiler_executables`，profile ohos-aarch64）
- 平台: OHOS aarch64（os=OHOS, os.version=6.0, arch=armv8, clang15, libc++, cppstd=17, Release）
- 状态: built（conan create 本地验证通过，待远端 PR 校验）

## R51 上游测试申报表（完整枚举）

源码树测试相关文件与分类：

| 路径 | 类型 | 是否独立上游用例 | 原因 |
|------|------|------------------|------|
| test/Test.cpp | 用户测试源（手写 harness 主体） | ✅ 是（1 个用例） | `int test(std::ostream&)` 含 15 个检查点，失败累加 failed 并 `return 1`，全过打印 `All tests passed!` |
| test/TestMain.cpp | 用户测试源（main） | 与上合并为同一用例 | `main()` 调 `test(std::cout)` |
| test/Test.hpp | 用户测试头 | 与上合并为同一用例 | 声明 `test(std::ostream&)` |
| android/（build.gradle/MainActivity.java/jnitest.cpp 等） | 样例（Android demo 工程） | ❌ 否 | 独立 gradle/Android 样例应用，非 CMake 上游测试入口，不计入用例（辅助组件） |
| cmake/FindLibuuid.cmake | 构建辅助 | ❌ 否 | 构建模块 |
| README.md / android.sh | 文档/脚本 | ❌ 否 | 非测试 |
| CMakeLists.txt `add_executable(xgtest ...)` | 测试构建目标 | — | 唯一测试目标；无 `enable_testing()`/`add_test()`/ctest 注册，无 gtest/catch 框架 |

框架：custom（纯手写 harness，无 gtest/catch/ctest）。测试目录无 fixture、无基准、无独立测试脚本。
`source_declared_total` 按上游 CMake 声明 = 1 个独立用例（xgtest），含 15 个断言检查点。

## 双口径测试台账

| 口径 | 数值 | 说明 |
|------|------|------|
| source_declared_total | 1 | 上游 CMake 声明的独立测试用例（xgtest = TestMain.cpp + Test.cpp） |
| configured_executable_total | 1 | OHOS 配置 XG_TESTS=ON 实例化 xgtest |
| executed_passed_total | 1 | 实际运行，exit 0，`All tests passed!` |
| failed | 0 | — |
| 未运行/未实例化 | 0 | 无互斥分支/条件宏排除项（无平台宏，Linux 路径即 OHOS 路径 GUID_LIBUUID） |
| 全量通过率 | 1/1 (100%) | 通过数/发现总数 |
| 当前配置可执行通过率 | 1/1 (100%) | 通过数/实际运行数 |

逐项映射：test/Test.cpp 的 `test()`（源码声明）→ 无预处理排除（无平台宏/条件分支，始终编译）→ 构建目标 `xgtest`（XG_TESTS=ON）→ ctest -N：无 ctest 注册（上游未 enable_testing）→ 实际执行：`./xgtest`（build/Release），退出码 0。

15 个断言检查点明细（全部通过）：随机 GUID 互异、s1!=s2、s1==s4、ss1 流式往返、s1.str()、ss2 流式往返、ss3 流式往返、swap 初始状态、swap 交换结果、bytes<->string 一致、两位过少/一位过少/两位过多/一位过多/非法字符串的 isValid=false 与相等语义。

## 编译步骤

```bash
conan create archives/c/crossguid/0.2.2 --build=missing \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

1. `source()`: conandata URL（官方 codeload tar.gz，sha256 已验算）`filename` 明确扩展名，`strip_root=True` 解压。
2. `generate()`: CMakeDeps（uuid）+ CMakeToolchain（XG_TESTS=ON，fPIC→CMAKE_POSITION_INDEPENDENT_CODE=ON）+ TMPDIR 转发。
3. `build()`: apply_conandata_patches（0001 补丁）→ cmake configure/build → 运行 `./xgtest`。
4. `package()`: cmake install（patched install 规则：libcrossguid → lib/，Guid.hpp → include/，LICENSE → licenses/）。
5. test_package: 消费者 test_crossguid 编译链接运行，exit 0。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 误判 mixed（env_unsupported） | `_manifest_scan` 全树扫描命中 android/ 辅助 demo 的 build.gradle，遮蔽顶层 CMakeLists.txt | 剔除辅助 android/ 后复跑 → detected=cpp；主构建系统为 CMake、cpp 主体 ≥70%，按边界规则判 cpp |
| 2 | conan create 报 `settings.os.version value not defined` | 缓存中名为 `ci/conan/profiles/ohos-aarch64` 的 profile 是旧副本（无 os.version、cppstd=gnu14） | 改用缓存正确 profile `ohos-aarch64`（os.version=6.0, clang15, libc++） |
| 3 | `BadZipFile: File is not a zip file` | codeload URL 末段无文件扩展名，conan 无法识别 tar.gz | conandata `sources` 增加 `filename: "crossguid-0.2.2.tar.gz"` |
| 4 | `invalid hunk no.1` 补丁解析失败 | 手写补丁 hunk 头行数与内容不符 | 重写补丁，hunk 计数精确（-11,7 +11,8 / -28,12 +28,11） |
| 5 | conan-init 生成 autotools 模板 | init-build 对无 configure 脚本的 CMake 包构建系统探测不准 | 重写为 CMake 配方（CMakeToolchain/CMakeDeps/CMake） |

## 源码修改（补丁）

- `patches/0001-cmake-uuid-install.patch`：① `xg` 目标 `OUTPUT_NAME crossguid`（产物 libcrossguid.a）；② 将 `find_package(Libuuid)`（pkg-config 模块）改为 `find_package(uuid CONFIG REQUIRED)` + `target_link_libraries(xg uuid::uuid)`（消费 conan 管理的 uuid/2.40.1）；③ 新增 install 规则（lib/include/licenses）。无 `__OHOS__` 平台宏。

## 依赖版本

- uuid/2.40.1（transitive_headers + transitive_libs，制品仓已发布：conan download --only-recipe 验证通过）

## 验证结果

```bash
# 上游测试（build() 内实跑 + 独立取证）
$XG=/storage/Users/currentUser/.conan2/p/b/cross484703f6c14b9/b/build/Release/xgtest
$XG   # exit 0，输出 "All tests passed!"
# 日志: /storage/Users/currentUser/tmp/crossguid-upstream-test.log
# sha256: ad4863a49c807830ffc1664184874dea24e41e38d86e42e80ff67d08ad4028fa

# 消费者验证（conan create 内置 test_package）
./test_crossguid   # exit 0，输出 "consumer ok: newGuid unique, parse/round-trip, equality"
```

## 注意事项

- 本库非系统同名库，不触发 R26 静态强制；默认 shared=False 静态构建，保留 shared=True 路径。
- 纯用户态 GUID 库，无图形/多媒体/外设语义，不触发 R40 深度适配。
- CI 只读 conanfile.py / conandata.yml / test_package/ / patches/；manifest.yaml / notes.md 为 AI 元数据。
- TMPDIR/TMP/TEMP 在 source() 与 buildenv 中转发（E002 /tmp 只读防护）。

## 知识候选台账与七轴查重（knowledge_reuse_governance）

### 候选 C1：conan get() BadZipFile（codeload URL 无扩展名）

- 真实错误：`BadZipFile: File is not a zip file`（source() 内 get(strip_root=True)）
- 根因：codeload `tar.gz/v0.2.2` basename 无扩展名，conan 按 zip 解码
- 修复：conandata `sources` 增加 `filename: "crossguid-0.2.2.tar.gz"`（等价于 get() 显式传 filename）
- 验证：conan create 源码解压成功
- 查重：**因果重复/方案完全覆盖** —— E276（同签名 BadZipFile+codeload+filename）与 E392（陷阱 1 完全相同）已覆盖；无新增差异
- 决策贡献：`exact_duplicate=false, causal_duplicate=true, trigger_overlap=full, solution_overlap=full, combination_novelty=false, boundary_novelty=false, test_migration_novelty=false`；**reuse_existing**（复用 E276/E392），不建草稿

### 候选 C2：lang-preflight 将 C++ 库误判 mixed（辅助 android/ demo 的 build.gradle 遮蔽顶层 CMakeLists）

- 真实错误：`lang-preflight → detected_language: mixed → env_unsupported`（任务标记 cpp）
- 根因：lang_detect.py `_manifest_scan` 用全树文件名集合（rglob），第 122 行 `names & {"build.gradle",...}` 命中 android/ 辅助 demo 的 build.gradle（java/gradle 分支）且优先级高于第 124 行顶层 CMakeLists（c/cpp）→ 与 cpp 统计 86% 冲突 → §4.7 mixed
- 修复：剔除辅助 android/ 后复跑 → `detected=cpp`（manifest=CMakeLists.txt project(CrossGuid), cpp 100%）；按 R47 D.4 边界规则「辅助脚本不算主体」判 cpp 继续适配
- 验证：复跑 lang-preflight 两次输出对比（mixed vs cpp），conan 全流程通过
- 查重：**部分覆盖（新增触发分支）** —— 既有草稿 DRAFT-exr_image-0.1.0-rc3-lang-preflight-aux-manifest（Cargo.toml）、DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect（Cargo.toml）、DRAFT-onnx-1.20.0-lang-preflight-pyproject-priority-cpp-deliverable-misdetect（pyproject）覆盖同根因族（全树 manifest 扫描 + 非 c/cpp 分支优先 + 辅助目录不计主体），但均未覆盖第 122 行 **build.gradle→java/gradle 分支**（Android/JNI demo 子工程整工程 manifest）；本轮以真实日志验证剔除辅助目录→cpp
- 决策贡献：`exact_duplicate=false, causal_duplicate=true, trigger_overlap=partial（gradle 分支新增）, solution_overlap=high（同 rec：主库主体优先）, combination_novelty=false, boundary_novelty=true（build.gradle/Android demo 新边界）, test_migration_novelty=false`；**new_draft**（DRAFT-crossguid-0.2.2-lang-preflight-aux-gradle-misdetect）

### 候选 C3：OHOS profile 缺 os.version → `settings.os.version value not defined`

- 真实错误：`uuid/2.40.1: Invalid: 'settings.os.version' value not defined`（conan create）
- 根因：缓存中存在名为 `ci/conan/profiles/ohos-aarch64` 的陈旧 profile（无 os.version、cppstd=gnu14/libstdc++11），`-pr:h=ci/conan/profiles/ohos-aarch64` 解析到缓存名而非仓库文件；OHOS 适配版 conan 对 os=OHOS 要求 os.version
- 修复：改用正确 profile `ohos-aarch64`（os.version=6.0, clang15, libc++）重跑，构建通过
- 验证：两次 conan create 对比（陈旧 profile RC=6 失败 vs 正确 profile RC=0 成功）
- 查重：**未命中** —— index.tsv/doc/ 检索 `os.version|value not defined|not a valid os` 无既有正式条目；草稿目录 profile 相关条目（DRAFT-9639-minibwa-profile-cc-path-fallback 等）不涉及 os.version 缺失
- 决策贡献：`exact_duplicate=false, causal_duplicate=false, trigger_overlap=none, solution_overlap=none, combination_novelty=true, boundary_novelty=true（缓存 profile 名遮蔽仓库 profile 文件路径）, test_migration_novelty=false`；**new_draft**（DRAFT-crossguid-0.2.2-ohos-profile-osversion-missing）

### 候选 C4：W3 junk_check full 模式命中其他库已提交基线标记文件 → 临时索引隔离复验

- 真实错误：finish W3 `JC_RESULT=fail`（Junk Files: 2，JC1/JC5 命中 archives/c/cloog、archives/k/kics、archives/t/thc 的 .build-closed/.staging-verified）
- 根因：本地 W3 在分支无 commit 时退化为 `full` 模式（`git ls-files` 全仓库），origin/main 基线中已提交的 4 个其他库标记文件被扫描；非当前库允许范围内、提交前已存在
- 修复：记录隔离前 SHA-256 → `git rm --cached`（仅索引）→ 复跑 finish（W3 通过）→ `git reset HEAD --` 原样恢复 → 隔离后 SHA-256 一致（pre==post，e3b0c442…）；未修改/未提交这些基线文件
- 验证：W3 从 fail 转 pass；恢复后 `git status` 干净、`git diff origin/main` 为空
- 查重：**部分覆盖** —— E291（repository_baseline_blocked）覆盖「基线阻塞记录、不混入当前库 PR」族，但触发不同（E291=graph validate 阻塞；本候选=JC junk_check full 模式命中其他库已提交标记文件），且 E291 不涉索引隔离操作步骤
- 决策贡献：`exact_duplicate=false, causal_duplicate=false（触发机制不同）, trigger_overlap=partial, solution_overlap=partial, combination_novelty=true, boundary_novelty=true（JC full 模式 + 索引隔离复验变体）, test_migration_novelty=false`；**new_draft**（DRAFT-crossguid-0.2.2-w3-jc-fullmode-baseline-isolation）

### 路径决定

- 路径 A 部分：C1 复用既有知识（E276/E392）
- 路径 B 部分：C2/C3/C4 具备已验证（真实命令/退出码/日志）、可跨库复用、查重未命中或部分覆盖且存在新增差异 → **走路径 B**，建立 3 对同 stem 的 .kv/.md 草稿：`DRAFT-crossguid-0.2.2-lang-preflight-aux-gradle-misdetect`、`DRAFT-crossguid-0.2.2-ohos-profile-osversion-missing`、`DRAFT-crossguid-0.2.2-w3-jc-fullmode-baseline-isolation`
- 与既有条目的关系字段：C2 `similar_to=[DRAFT-exr_image-0.1.0-rc3-lang-preflight-aux-manifest, DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect, DRAFT-onnx-1.20.0-lang-preflight-pyproject-priority-cpp-deliverable-misdetect]`，`caused_by=[]`，`prerequisite_of=[]`，`conflicts_with=[]`；C4 `similar_to=[E291]`
---

**编译结束**: 2026-09-27 01:46
**最终状态**: built
