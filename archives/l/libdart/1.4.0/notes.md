# libdart 1.4.0 适配笔记

## 编译环境
- 构建系统: cmake (CMakeLists.txt, project(libdart VERSION 1.4.0), cmake_minimum_required 3.1.0)
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, /data/service/hnp/bin/clang++)
- 状态: built

## 编译步骤

1. 官方源下载（task 头指定官方 URL github.com/target/libdart，tag v1.4.0）：
   - `curl -sSL -o libdart-1.4.0-v1.4.0.tar.gz https://codeload.github.com/target/libdart/tar.gz/refs/tags/v1.4.0`
   - SHA-256 = `cedfd970047a128e5c53613c738ae3c8cfffd5880d446498c22524f49eb182da`
2. 本地探索构建（注入 ms-gsl/rapidjson/libyaml 头文件路径）：
   ```bash
   cmake .. -Dtest=ON -Dbuild_abi=ON -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
     -DCMAKE_INCLUDE_PATH="<ms-gsl>/include;<rapidjson>/include;<libyaml>/include" \
     -DCMAKE_LIBRARY_PATH="<libyaml>/lib"
   make -j4 && ctest --output-on-failure
   ```
3. conan 配方：`conanfile.py` (header-library, requires ms-gsl/4.2.1, test_requires rapidjson/1.1.0 + libyaml/0.2.5)；generate() 注入 CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH + CMAKE_CXX_FLAGS；build() 全量运行上游 ctest；test_package 消费者 + 鸿蒙专项测试。
4. `conan create`（ohos-aarch64 profile，双 host/build）通过；`conan-verify` G0-G4 + L2/L4/L5 全部 PASS；`finish published` 通过（W3 本地 CI 模拟通过，`.ci-result.json` exit_code=0）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2: "Compatibility with CMake < 3.5 has been removed" | 上游 cmake_minimum_required(3.1.0)，CMake>=4.0 移除 <3.5 兼容 | generate() 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（tc.variables 实测有效，见知识台账 C2） |
| 2 | conan get() "BadZipFile: File is not a zip file" | codeload URL 末段无文件扩展名，get() 无法识别 tar.gz | conandata.yml sources 显式 `filename: libdart-1.4.0.tar.gz`（E276/E392/E483 已有） |
| 3 | G2: `AttributeError: 'CMakeToolchain' object has no attribute 'cxxflags'` | Conan 2 CMakeToolchain 无 cxxflags/cflags 属性（E293 用 extra_cxxflags 是 AutotoolsToolchain 场景） | 改 `tc.variables["CMAKE_CXX_FLAGS"]`（见知识台账 C3） |
| 4 | yaml_test 未注册、dart_abi 编译 "yaml.h not found" | 上游 find_path/find_library 不读取 -I/-L 编译标志；yaml.h 被 common.h #include 需真实 -I | 双路注入：`CMAKE_INCLUDE_PATH`/`CMAKE_LIBRARY_PATH` 供 find_* 探测 + `CMAKE_CXX_FLAGS -I` 供 #include 编译（见知识台账 C3） |
| 5 | W3 JC1/JC5 拦 4 个其他库空标记文件（cloog/kics/thc 的 .staging-verified/.build-closed） | main 已提交的其他库基线 junk，本地 full 模式扫描全仓；CI PR 模式不命中 | 基线隔离复验：记录 pre-SHA-256（均 e3b0c44...），`git rm --cached` 临时隔离，复跑 finish 通过，`git reset` 原样恢复，post-SHA-256 一致且无残留（详见最终回报 baseline_isolation_audit） |

## 源码修改

无补丁（patches/ 为空）。配方层修改均在 conanfile.py / conandata.yml / test_package/ 内。

## 依赖版本

- ms-gsl/4.2.1（Microsoft GSL header-only，公开头文件依赖 gsl::span）
- rapidjson/1.1.0（test-time，DART_HAS_RAPIDJSON 解析/序列化）
- libyaml/0.2.5（test-time，yaml_test）

## 验证结果

```bash
# 本地探索构建
ctest --output-on-failure   # 4/4 PASS: dart_unit_tests/json/yaml/abi
# 上游用例统计: unit_tests 170 + json_test 2 + yaml_test 1 + abi_tests 70 = 243 TEST_CASE/SCENARIO，全量通过
# 消费者测试 (test_package/test.cpp)
./test_libdart             # PASS: parse/取值/to_json 往返
# 鸿蒙专项测试 (test_package/test_ohos.cpp)
./test_ohos                # PASS: char 符号探针/int64+double 精度/1MB 大对象/嵌套往返
# conan-verify: G0-G4 + L2/L4/L5 PASS
# finish published: W3 本地 CI 模拟通过 (.ci-result.json exit_code=0)
```

## 知识候选台账（本轮，四范围查重）

> 范围: knowledge/graph/index.tsv + graph/*.kv + doc/*.md + drafts/*。路径判定见台账与最终回报。

### C1 — codeload URL 无扩展名 → BadZipFile（显式 filename）
- 真实错误: `conan create: BadZipFile: File is not a zip file`（source() 中 get()）
- 根因: codeload.github.com/.../tar.gz/refs/tags/v1.4.0 末段无 `.tar.gz`，get() 按 zip 解压失败
- 修复: conandata.yml sources 加 `filename: libdart-1.4.0.tar.gz`；URL 保持官方源（R39 不变）
- 验证: conan-verify G2 PASS
- 四范围查重: **exact_duplicate** — E276/E392/E483（含 E483 完整方案 explicit-filename-in-get）
- 关系: caused_by(conan get 扩展名推断), similar_to(E392 raw-makefile 分支)
- 判定: **reuse_existing（E483）**，不新建草稿

### C2 — CMake 4.x 拒绝 cmake_minimum_required < 3.5
- 真实错误: `CMake Error at CMakeLists.txt:7 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed`
- 根因: 上游声明 3.1.0，CMake 4.0+ 移除 <3.5 兼容策略
- 修复: generate() `tc.variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"`（实测 tc.variables 写入 conan_toolchain.cmake 在项目 CMakeLists 解析前生效，G2 通过）
- 验证: conan-verify G2 PASS
- 四范围查重: **trigger_overlap + solution_overlap** — DRAFT-E321-cmake4-policy-version-minimum.kv 已存在（etcd-cpp-apiv3，方案为 cache_variables 且注明"切勿用 tc.variables"）；本轮实测 tc.variables 同样有效，属 boundary_novelty（与既有草稿"tc.variables 不生效"的断言相反，实测在本场景生效）
- 关系: similar_to(DRAFT-E321), conflicts_with(既有草稿中"tc.variables 无效"断言)
- 判定: **reuse_existing（DRAFT-E321 方向）**；新增边界证据（tc.variables 有效）写入本轮台账供主编参考，不另建同 trigger 草稿（防硬凑）

### C3 — CMakeToolchain 依赖/include 注入双路（cxxflags AttributeError + find_* 探测）
- 真实错误: `AttributeError: 'CMakeToolchain' object has no attribute 'cxxflags'`；以及 `fatal error: 'yaml.h' file not found`、yaml_test 未注册
- 根因: (a) Conan 2 CMakeToolchain 无 cxxflags/cflags 属性（E293 的 extra_cxxflags 是不同工具链场景）；(b) 上游 find_path/find_library 只认 CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH，不认 -I/-L；(c) 头文件被 #include（DART_HAS_YAML 下 common.h include yaml.h）仍需命令行 -I
- 修复: generate() 中 (1) 用 `tc.variables["CMAKE_CXX_FLAGS"]/["CMAKE_C_FLAGS"]` 注入 -I；(2) `tc.variables["CMAKE_INCLUDE_PATH"]/["CMAKE_LIBRARY_PATH"]` 供 find_path/find_library 探测；双路并用以同时满足探测与编译
- 验证: conan-verify G2 PASS（4 个上游 ctest 目标全部注册并运行）；本地复现确认
- 四范围查重: **未命中** — graph/doc/drafts 无条目覆盖"CMakeToolchain 无 cxxflags 属性→CMAKE_CXX_FLAGS 变量"或"find_* 探测注入用 CMAKE_INCLUDE_PATH/LIBRARY_PATH"；最接近的 E293 用 tc.extra_cxxflags（AutotoolsToolchain 场景、用途不同）、E376 是 find_library libm NOTFOUND（机制不同）、E447/E473 是 vendored Find 模块/CMakeDeps target 名失配（不同问题域）
- 七轴: exact_duplicate=false, causal_duplicate=false, trigger_overlap=false, solution_overlap=false（与 E293/E376/E447 仅关键词面相关）, combination_novelty=true（双路注入组合）, boundary_novelty=true（可跨库复用：任何上游 CMake find_* 探测 + 编译 #include 的 header 依赖注入）, test_migration_novelty=false
- 关系: similar_to(E293 标志注入, E376 find_library), prerequisite_of(无)
- 判定: **new_draft** — 建 DRAFT-libdart-cmake-toolchain-find-deps-injection.kv/.md（见 knowledge/drafts/）

### C4 — W3 JC 其他库基线 junk 隔离
- 非知识候选（既有基线噪声，无新知识），按 ./SKILL.md 基线隔离复验处理，台账记为噪声不参与路径判定。

## 路径判定

- 候选 C1 完整重复 → **reuse_existing（E483）**
- 候选 C2 与既有 DRAFT-E321 部分覆盖（含新增边界证据 tc.variables 有效）→ **reuse_existing（DRAFT-E321 方向），边界证据随台账上报**
- 候选 C3 未命中且已验证、可跨库复用 → **new_draft**（DRAFT-libdart-cmake-toolchain-find-deps-injection）
- 结论: **路径 B（知识库扩展）成立**，new_draft 与 libdart 归档进入同一 PR，PR 前缀 【知识库扩展】

## 交付物

| 文件 | 说明 |
|------|------|
| archives/l/libdart/1.4.0/conanfile.py | Conan 2 header-library 配方（CMakeToolchain 双路注入） |
| archives/l/libdart/1.4.0/conandata.yml | 官方源 + SHA-256 + 显式 filename |
| archives/l/libdart/1.4.0/test_package/ | 消费者测试 test.cpp + 鸿蒙专项测试 test_ohos.cpp + MANIFEST.yml |
| archives/l/libdart/1.4.0/reports/ | conan-verify / w3-local-ci 报告 |
| knowledge/drafts/DRAFT-libdart-cmake-toolchain-find-deps-injection.kv/.md | 路径 B 新草稿对 |

## 注意事项

- libdart 为 header-only C++14 JSON 库（公开 API 依赖 gsl::span）；C89 ABI 层（build_abi=ON 时）供上游 abi_tests 使用，未发布为独立制品。
- 上游仓库已于 2024-07 归档（read-only），官方 tag v1.4.0 是最终稳定版，按 R39 使用官方源。
- HMDFS 大小写折叠导致 worktree 恒有 libXext/libxext 伪差异，属既有基线，不纳入本 PR。
---

**编译结束**: 2026-09-27 06:25
**最终状态**: built
