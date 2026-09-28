# Knowledge Candidate Ledger — fmi-ls-bus 1.0.0

**日期**: 2026-09-22
**任务**: fmi-ls-bus-1.0.0-r01-pc7-14-20260922T133943Z（知识库扩展候选评估）
**执行端**: pc7-14 @ build_in_harmonyos worktree `feat/fmi-ls-bus-1.0.0`

## 一、知识候选台账（逐项非噪声候选）

### 候选 1: header-only C API 库的公开头 include 未入 registry 的必备标准头 → 配方以第二官方源固定提交打包

- **真实错误**: `fmi3LsBus.h:54: #include "fmi3PlatformTypes.h"` —— 该头来自官方 `modelica/fmi-standard` 仓库，ohpcd registry 无任何 fmi* 配方包（`conan list "fmi*" -r=ohpcd` → 0 匹配）；若不处理，消费者编译公开头必报 `fmi3PlatformTypes.h file not found`（上游 tests/CMakeLists.txt 亦显式 `-I ../fmi-standard/headers`，上游 CI 用 actions/checkout 单独拉 fmi-standard）
- **根因**: 上游将 FMI 3.0 标准头（fmi3PlatformTypes.h 等）与 fmi-ls-bus 模块头拆分在两个仓库；标准头没有 conan 包；公开头直接 include 标准头，纯头文件库的配方若只装自身头文件，消费者 include 链断裂
- **修复**: conanfile.py `source()` 双 `get()`：主源码（官方 v1.0.0 tarball，strip_root）+ `fmi_standard` 第二源（官方 fmi-standard 固定提交 5365a496… 的 archive tarball，strip_root + destination="fmi-standard"）；`package()` 把 `headers/*.h` 与 `fmi-standard/headers/fmi3PlatformTypes.h` 一并拷入 `include/`；conandata.yml 双源各带官方 URL 与核验 SHA-256
- **验证**: conan-verify G2 conan create 通过（rc=0）；test_package 消费者仅经已安装公开头 include `<fmi3LsBus.h>` + 调用 CAN API 编译链接运行成功，8/8 断言通过；鸿蒙专项测试 7/7 通过
- **适用范围**: 任何 header-only C/C++ 库其公开头 include 来自独立官方仓库的配套标准头/平台头（如 FMI 族、标准组织头），且该配套头无 conan 包时；cross-library 可复用
- **四范围查重**: 正式知识 **E321**（martinmoene lite 系 header-only Conan1→2 迁移，命中"package_type=header-library/cpp_info.set_property"但未涉及第二官方源打包）、**E322**（Taskflow header-only CMake INTERFACE 配方，命中 header-only 配方骨架，未涉及打包必备标准头）、**E257**（header-only G1 需显式 no-op build()，本轮同样命中该坑并沿用，非新增）、**E282**（多源码配方补丁 base_path，主题相关但面向 patches 路由，非本候选）；图谱 index 命中上述；草稿 **DRAFT-EA-headeronly-dependency-chain**（EA 族公开头相互 include 的依赖链传播——但该方案是"依赖已有 conan 包 eabase + cpp_info.requires/includedirs 传播"，**前提是依赖包已入 registry**，与"registry 完全没有该头包、需以第二官方源打包"是不同解决路径）；无草稿覆盖"第二官方源固定提交打包缺失标准头"

### 候选 2: GitHub 官方两端点（archive URL 与 api tarball）对同一 ref 返回不同 gzip 字节 → conandata sha256 必须以声明 URL 实际字节为准

- **真实错误**: 经 `api.github.com/repos/.../tarball/v1.0.0` 下载得 `73126acc…`（3,190,027 B）；经官方 `github.com/.../archive/refs/tags/v1.0.0.tar.gz`（codeload 重定向）下载得 `c72ea6bc…`（3,190,126 B）；两 tarball 解压后源码完全一致（diff 仅顶层目录名），但 gzip 字节不同——若把 api 端点哈希写进 conandata，CI 用官方 URL 下载会 SHA-256 mismatch
- **根因**: GitHub archive URL 与 REST tarball 端点为同一 ref 生成字节序/元数据不同的 gzip（源码内容一致）；"官方"≠"同一字节"
- **修复**: conandata.yml sha256 取**声明 URL**（官方 archive URL）实际下载字节的 SHA-256 `c72ea6bc…`，并做解压内容 diff 确认源码等价后再采信
- **验证**: 官方 archive URL 下载 `HTTP:200`，sha256 `c72ea6bc…`；与 api 端点 tarball 解压内容 diff 仅顶层目录名；conan-verify G2 以该 sha256 通过
- **适用范围**: 任何 conandata/manifest 声明 GitHub archive URL 的配方；采集期不可只信单一官方端点哈希；cross-library 可复用
- **四范围查重**: 正式知识 **E406**（scout/recipe 创建期 SHA-256 多网络路径交叉验证，命中"哈希必须对官方字节校验"，但 E406 语境是代理/直连路径内容被改；本轮新增边界=**两个都是官方端点也会字节不同**，须以"声明 URL 实际字节"为准）；草稿 **E332-draft-nymphrpc-sha256-multipath**（同 E406 场景实例）；无草稿覆盖"官方端点间字节差异"这一具体边界

### 候选 3: 上游 v1.0.0 发布版 tests 引用发布包内不存在的模块头 → 双口径台账按"明确上游排除条件"处理

- **真实错误**: `MODULE_LIST=all` 构建失败 `fatal error: 'fmi3LsBusFlexRay.h' file not found`（v1.0.0 发布版 headers/ 仅 4 个文件，无 flexray/ethernet/lin 模块头；main 与 v1.1.0-beta.2 才有）
- **根因**: 上游 tests 目录同时提交 can/flexray 测试源，但 v1.0.0 发布版头文件只含 can 模块；上游 CI 工作流 run-header-tests.yml 输入说明亦声明 "Available is 'can'"
- **修复**: 以 `MODULE_LIST=can` 构建并实际运行 130/130 通过；flexray 104 个 TEST 计入 source_declared_total=234 分母但不计通过；台账逐项说明排除原因、复现命令/退出码/首错与恢复条件（上游发布含 flexray 头的版本）
- **验证**: ctest 130/130 passed；双口径 130/234=55.6%（全量）/130/130=100%（可执行集合）
- **适用范围**: 任何发布版 tests 含未随发布头文件/源码的模块测试入口时的双口径统计；cross-library 可复用（台账纪律性知识）
- **四范围查重**: 正式知识 **E370**（上游测试完整性——Meson 夹具逐 key 终态映射，主题相关但面向 Meson/夹具计数，非 CMake/GTest 头测试排除场景）；无直接覆盖"发布版测试源引用不存在模块头→按上游排除条件双口径"的既有条目/草稿

### 候选 4: CMakeDeps 下 gtest_discover_tests 需显式 include(GoogleTest)

- **真实错误**: 以 CMakeDeps 生成的 conan_toolchain.cmake 构建上游 tests 报 `Unknown CMake command "gtest_discover_tests"`；补 `include(GoogleTest)` 后 configure/build/ctest 全过
- **根因**: 上游 tests/CMakeLists.txt 直接用 gtest_discover_tests 但未 include(GoogleTest)；CMakeDeps 配置包（GTestConfig.cmake）不隐式加载该模块（FindGTest 传统路径才隐式）；仅影响本地/消费者测试入口构建，配方本体无此问题（本库无编译）
- **修复**: 本地验证构建加最小补丁 `include(GoogleTest)`（仅用于验证，不进配方 patches）
- **验证**: 补丁后 CMake configure exit 0、build exit 0、ctest 130/130 passed
- **适用范围**: CMakeDeps 消费者/本地验证用 GTest 的项目；低严重度局部修复
- **四范围查重**: 正式知识 **E332**（gtest_discover_tests——面向"上游自带 GTest 兼容原生 runner 但默认关闭"场景，非 CMakeDeps 模块缺失场景，部分相关）；无既有条目精确覆盖"CMakeDeps 下需显式 include(GoogleTest)"

### 噪声项（不入账）
- fmi3LsBusCanId 为 32 位（测试数据 64 位值被截断告警）：库特有 API 语义，非跨库可复用知识 → 噪声，仅在测试源码注释与 notes.md 记录
- HMDFS `libXext/libxext` 大小写折叠污染：平台既有问题，其他 worktree 同样存在，非本库引入 → 噪声，按 W3 基线隔离协议处理（见候选外记录与 notes.md）

## 二、七轴查重

| 轴 | 候选 1（双源打包标准头） | 候选 2（官方端点字节差异） | 候选 3（发布版测试排除） | 候选 4（CMakeDeps+GoogleTest） |
|---|---|---|---|---|
| exact_duplicate | false（E321/E322 无第二源打包；DRAFT-EA 依赖已入 registry 的包，前提不同） | false（E406 为代理/直连路径差异语境，非官方端点间差异） | false（E370 面向 Meson 夹具） | false（E332 面向原生 runner 开关） |
| causal_duplicate | false（根因=registry 无配套标准头包，E321/E322 根因为 Conan 版本迁移/上游测试默认开） | false（根因=官方两端点 gzip 字节不同；E406 根因=路径内容被改） | false（根因=发布版未随模块头；E370 根因=夹具计数失真） | false（根因=CMakeDeps 不隐式加载 GoogleTest 模块） |
| trigger_overlap | partial（同为 header-only 打包，但触发签名不同：file-not-found-in-consumer vs Conan1 API 移除） | true（同为 sha256 mismatch 族） | partial（同为测试统计，但签名不同：头缺失 vs Meson 夹具 key） | partial（同为 gtest_discover_tests 关键词，触发条件不同） |
| solution_overlap | partial（DRAFT-EA 用 cpp_info.requires 传播；本候选用第二官方源打包进 include/，路径不同） | partial（E406 建议多路径交叉验证；本候选细化=以声明 URL 实际字节为准） | false（无双口径既有方案） | partial（E332 建议开原生 runner；本候选=include(GoogleTest) 一行） |
| combination_novelty | **true**（"header-only 配方 + registry 无配套头包 + 第二官方源固定提交打包"为新组合） | **true**（"官方 archive URL vs api tarball 端点字节不同"为新事实） | true（发布版测试源引用不存在头→双口径排除，为新组合） | false（低危局部修复，组合常见） |
| boundary_novelty | **true**（新边界：registry 无头包时不得谎报依赖，须以官方第二源打包；DRAFT-EA 未覆盖该边界） | **true**（新边界：两个官方端点也会字节不同，哈希必须绑定声明 URL） | true（新边界：上游 CI 声明 Available-is-can 即可证排除条件） | false（无新边界） |
| test_migration_novelty | false | false | true（测试台账口径迁移/排除） | false |

**关系字段**：
- 候选 1: `similar_to` E321/E322/E257/E282、DRAFT-EA-headeronly-dependency-chain；`caused_by` fmi-standard 头未入 registry；`prerequisite_of` 无；`conflicts_with` 无
- 候选 2: `similar_to` E406、E332-draft-nymphrpc-sha256-multipath；`caused_by` GitHub 端点字节差异；`prerequisite_of` 无；`conflicts_with` 无
- 候选 3: `similar_to` E370；`caused_by` 上游发布版未随模块头；`prerequisite_of` 双口径台账；`conflicts_with` 无
- 候选 4: `similar_to` E332；`caused_by` CMakeDeps 模块加载语义；`prerequisite_of` 无；`conflicts_with` 无

## 三、路径决定

**`new_draft`** — 候选 1 已验证（conan-verify G2 + 消费者 8/8 + 鸿蒙专项 7/7）、可跨库复用（任何公开头 include 未入 registry 配套标准头的 header-only 库）、查重为部分覆盖（E321/E322 只覆盖 header-only 配方骨架，DRAFT-EA 以"依赖已入 registry"为前提，未覆盖"第二官方源固定提交打包缺失标准头"），存在新增差异（combination/boundary novelty 均为 true）→ **路径 B（知识库扩展）成立**，建立同 stem 的 `.md/.kv` 草稿（DRAFT-fmi-ls-bus-1.0.0-headeronly-dual-source-standard-header）。

候选 2 作为候选 1 的证据支撑一并写入同一草稿（双源声明的 SHA-256 必须以官方 archive URL 实际字节为准），不单独立项；候选 3 在草稿中记录双口径排除纪律；候选 4 低危不建草稿。

**决定依据**（knowledge-reuse-governance）: 至少一个候选已验证、可跨库复用且存在新增差异 → 路径 B，草稿与三方库归档进入同一 PR。
