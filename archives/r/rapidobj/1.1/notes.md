# rapidobj 1.1 适配笔记

## 编译环境
- 构建系统: cmake（header-only 库，INTERFACE target，无编译产物）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

1. 环境核验：python3 3.12.9 / conan 2.29.1 / cmake 4.1.2 / clang 15.0.4（OHOS aarch64 profile `ci/conan/profiles/ohos-aarch64`），ohpcd 制品仓可用。
2. W0 依赖发布检查：rapidobj 为 header-only 库，conanfile.py 零 `requires`，无第三方依赖需发布检查。
3. 源码核验：官方 tag v1.1（tar.gz SHA-256 `87640b4d70905081552d31a36e6b68a947e167ba379a7032a056986c16f716d3`，与本地下载校验一致）；头文件 `include/rapidobj/rapidobj.hpp` 声明 `RAPIDOBJ_VERSION 1.1.0`。
4. 上游测试：CMake 配置 `-DRAPIDOBJ_BuildTests=ON -DRAPIDOBJ_BuildTools=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5`（FetchContent 依赖 cxxopts 2.2.1 等声明旧 cmake_minimum_required），构建 unit-tests/func-tests 并运行 ctest。详见 reports/test-ledger.md。
5. Conan 配方：由 ohc-run.py conan-init 生成模板后重写为 header-only 模式（package_type=header-library，无 build 产物，package() 仅安装头文件，package_info 声明 cmake_file_name=RapidObj / cmake_target_name=rapidobj::rapidobj）。
6. test_package：C++17 消费者测试（ParseStream 解析 cube.obj，校验 24 个位置分量/36 索引，Triangulate 后仍 36 索引）。
7. conan-verify 8 道门禁（G1-G4/L2/L4/L5）全部 PASS；finish 中 W2 结构检查 PASS、W3 本地 CI（incremental 8 文件）JC_RESULT=pass、L0_RESULT=pass、Pass rate 100%（1/1）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | FetchContent 依赖（cxxopts 2.2.1 等）configure 报 "Compatibility with CMake < 3.5 has been removed" | CMake 4.x 移除对 <3.5 cmake_minimum_required 的兼容策略 | 配置时加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（知识 E187 / DRAFT-E321 复用） |
| 2 | 上游 func-tests 的 sponza-triangulated 用例确定性失败（17/18 通过） | 参考文件 `sponza.obj.tri.ref` 中索引排列与并行解析结果存在偏移 1 差异（属性数据全量一致，positions 182544==182544），3 次重跑稳定复现，属上游参考数据与平台解析顺序的基线差异 | 按基线噪声隔离记录，不写入 PR/知识库；不阻塞 header-only 库交付 |
| 3 | W3 本地 CI 首轮 JC 拦截 3 个 junk 文件 | 分支尚无 commit 时 junk_check 回退 full 全仓扫描，命中 origin/main 基线历史遗留（embree/.submit-state.json 等） | 先本地提交 rapidobj 配方（8 文件），W3 走 incremental 模式只查本库，JC_RESULT=pass |

## 源码修改

无（header-only 库零修改，无补丁）。

## 依赖版本

零第三方依赖（fast_float/earcut 内嵌于 rapidobj.hpp；上游测试的 doctest/cereal/cxxopts 等仅 FetchContent 构建期使用，不入配方）。

## 验证结果

- conan-verify：G1/G2/G3/G4/L2/L4/L5 全 PASS（reports/conan-verify-report.md）
- W3 本地 CI：JC_RESULT=pass，L0_RESULT=pass，Pass rate 100%（1/1），`.ci-result.json` exit_code=0（log_sha256 6a2c5e892e93f3da69394e2c12193850edd9f746a90a312909af55e6b14ce02e）
- 上游测试：18 个独立 TEST_CASE，17/18 通过 = 94.4%（全量口径，sponza-triangulated 为参考数据基线差异）
- HarmonyOS 专项测试：test_package/test.cpp（ParseStream cube.obj + Triangulate），编译 exit 0，运行 exit 0（"rapidobj 1.1 consumer test OK: 8 vertices, 36 indices parsed and triangulated"）

## 知识候选台账与查重（四范围）

| 候选 | 真实错误/现象 | 根因 | 修复 | 验证 | 适用范围 | 正式知识(graph/index.tsv+doc/) | 图谱(kv) | 草稿(drafts/) | 结论 |
|------|--------------|------|------|------|----------|-------------------------------|----------|---------------|------|
| C1 | CMake 4.x 报 "Compatibility with CMake < 3.5 has been removed"（FetchContent 依赖旧 cmake_minimum_required） | CMake 4.x 移除 <3.5 兼容策略 | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` | configure 通过，构建测试全量运行 | 所有依赖 FetchContent 旧 CMake 项目的构建 | E187（命中，add-cmake-flag） | E187.kv | DRAFT-E321-cmake4-policy-version-minimum.kv（同模式已有草稿） | 完整重复，复用已有知识 |
| C2 | header-only CMake INTERFACE 库的 Conan 2 配方模式（package_type=header-library + cmake_file_name/target_name + test_package 消费者测试） | 模板默认 autotools 库配方不适配 INTERFACE 目标 | 重写为 header-only 配方 | conan-verify G1-G4 全 PASS，test_package 实际运行 | 所有单头文件/INTERFACE C++ 库 | E321（命中，header-only-lite-conan2-migration） | E321.kv | DRAFT-cpp-taskflow/ctre/indicators 等 header-only 草稿 | 完整重复，复用已有知识 |
| C3 | func-tests sponza-triangulated 参考序列化索引排列偏移 1 | 并行解析合并顺序/哈希容器顺序与预生成参考文件差异，属性数据一致 | 无（上游参考数据基线差异） | 3 次重跑稳定复现，属性 182544 全等 | 仅本库该用例 | 无匹配（Phase B: 0） | — | — | 基线噪声，隔离记录不入库 |

## 路径决定

- 路径：**A（【依赖项】常规基础适配）**
- 依据：rapidobj 1.1 为 header-only 零依赖库，配方模式完整复用知识图谱既有条目（E187/E321/E322 及同模式草稿），无新增差异需要新建知识草稿；C3 为上游参考数据基线噪声，按规则隔离不写入知识库或 PR。任务初始 PR 前缀【依赖项】。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only Conan 2 配方 |
| conandata.yml | 官方源码 URL + SHA-256 |
| test_package/ | C++17 消费者测试（test.cpp/CMakeLists/conanfile/MANIFEST.yml） |
| manifest.yaml | 版本级元数据（status: built） |
| reports/test-ledger.md | 上游测试完整枚举台账（18 用例） |

## 注意事项

- W3 junk_check 依赖分支增量 diff：先本地 commit 本库文件，再跑 finish，避免 full 全仓扫描命中基线遗留文件。
- 上游测试数据参考文件（.tri.ref）为 x86 预生成，arm64 并行解析存在索引排列差异，不影响库功能。

---

## R02 返工知识候选台账与查重（2026-09-03，task rapidobj-1.1-r02-pc1-28-20260903T062643Z）

### C3-R02 复现结论（替换 R01 摘要：从"摘要基线噪声"升级为"根因已追溯到编译器浮点语义"）

| 字段 | 内容 |
|------|------|
| 真实错误/现象 | 上游 func-tests sponza-triangulated 确定性失败（默认构建 exit=1，断言 34 passed/2 failed） |
| 根因 | aarch64 clang 15 默认 FMA 收缩（-ffp-contract=on）使 `TriangulateSingleTask` 中 quad 对角线选择 `d02_is_less = d02 < d13` 在 46 个近等对角线（\|d02−d13\|/max ≤ 9e-8，float32 舍入内相等）上翻转，与上游 x86 预生成参考文件（sponza.obj.tri.ref，上游 CI ubuntu/windows/macos x86 生成）选择相反合法对角线 |
| 修复/方案 | 无需修复库（两条对角线几何等价，属性数据全量一致）；以 `-ffp-contract=off` 编译上游测试对齐基线浮点语义即可 18/18 全通过（已验证，diff_shapes=0） |
| 验证 | 默认 FMA 构建 3 次重跑稳定失败（exit=1）；`-ffp-contract=off` 构建 3 次重跑稳定通过（exit=0）+ 完整 ctest 2/2；诊断日志 reports/sponza-diag-r02.log（含逐 shape 差异、46 个 quad 的 d02/d13 浮点值与 FMA 对照） |
| 适用边界 | 仅在"库/工具链用浮点比较决定几何拓扑（如对角线选择）且参考数据由异架构预生成"时出现；本库 head-only 交付不受影响 |
| 查重（四范围） | 正式知识 index.tsv（766 条）无 fma/ffp-contract/floating/triangulation/sponza 命中（E253 为 ocaml toolchain 无关；E187 为 cmake policy，E321/E322 为 header-only 配方，均不覆盖本主题）；knowledge/drafts/ 无相关草稿（DRAFT-fast_float 为 C++23 stdfloat 主题，不相关）；无 rapidobj/sponza 条目 |
| 结论 | 属上游参考基线 × 平台浮点语义差异（非解析顺序契约、非适配回归、非并行竞争，可确定性复现）；按基线差异隔离记录，不写入知识库正式条目，不阻塞 head-only 库交付；不满足路径 B（无新增可复用知识价值——修法是编译期浮点语义对齐，属通用工具链知识，已有工程常识） |

### 路径决定（R02）

- 路径：**A（【依赖项】常规基础适配）**，维持 R01 结论不变
- 依据：R02 已完成全部任务要求验证（根因追溯至编译器 FMA 收缩、sponza 三次重跑+逐项比较证据、source_audit 矛盾解释、OHOS 专项测试、原子性审计），未发现需新建知识条目的可复用差异；C3 差异已升级为可追溯、可复现、可恢复的完整证据链，按隔离记录处理。

---

**编译结束**: 2026-09-03 15:55
**最终状态**: built
