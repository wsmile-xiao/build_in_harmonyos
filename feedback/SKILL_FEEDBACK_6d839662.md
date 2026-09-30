# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_6d839662.md`

---

## 背景

- **软件名称**: libosmscout
- **版本**: 2024.06.02.1
- **构建日期**: 2026-09-29
- **构建系统**: cmake
- **上游仓库**: https://github.com/Framstag/libosmscout
- **适配路径**: 路径 A+B（基础适配 + 知识库扩展）
- **补丁数量**: 0
- **编译依赖**:
  - libxml2/2.15.3.1
- **最终状态**: 成功（上游 ctest 69/69 通过，消费者端到端用例 39/39 通过）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 官方 release tarball `libosmscout-2024.06.02.1.tar.xz`（12.0 MB），sha256 与上游 `checksums_sha256.txt` 一致 |
| lang-preflight | 语言预检 | 完成 | `detected=cpp`，一次通过 |
| build | 编译构建 | 成功 | 构建系统: cmake；未施任何补丁，仅通过 CMake 变量切分组件（core/map/map-svg/import/gpx/client/test） |
| conan-verify | 配方验证 | 通过 | G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS（报告 `reports/conan-verify-report.md`） |
| finish | 归档收尾 | 已完成（需先 commit 再 resume 一次） | 首次因 `junk_check` 回落 full 模式扫到**其它包**的遗留隐藏文件而 HANDOFF；commit 版本目录后按增量模式通过 |
| submit | PR提交+AI检视+CI | 待执行 | AI Review: — |

### 失败与问题

本次流程遇到并已解决的实质问题（均已沉淀为知识草稿）：

1. **消费者链接静态导入库时报 `__kmpc_*` 未定义**：上游 `libosmscout-import` 只按 `if(TARGET OpenMP::OpenMP_CXX)` 就无条件链接 OpenMP，不看 `OSMSCOUT_BUILD_WITH_OPENMP` 选项；OHOS clang SDK 自带 libomp 使 `find_package(OpenMP QUIET)` 成功，于是即便选项为 OFF，导入库仍被 `-fopenmp` 编译。修复：追加 `CMAKE_DISABLE_FIND_PACKAGE_OpenMP=ON`。（草稿 E429）
2. **消费者运行时报 `Error loading shared library libxml2.so.16`（errno 为空）**：`libxml2/2.15.3.1` 包内以 `libxml2.so -> libxml2.so.16 -> libxml2.so.16.1.3` 符号链接链安装，OHOS 存储侧加载器拒载符号链接；对照实验确证「同一实体文件 `cp -L` 成普通文件即可、软链接版本必败」。修复：test_package `generate()` 把依赖 .so 实体化到 `realdep_libs` 并前置 `LD_LIBRARY_PATH`。（草稿 E479）
3. **test_package 的 `cmake.test()` 报 `No rule to make target 'test'`**：CMakeLists 用了 `add_test` 但缺 `enable_testing()`。修复：补 `enable_testing()`。
4. **包内混入测试/基准可执行文件**：上游测试宏把 69 个测试与基准装进 `share/osmscout/tests` 与 `share/osmscout/demos`。修复：`package()` 中递归删除。（草稿 E546）
5. **finish 首轮 HANDOFF（非包缺陷）**：未先 commit 版本目录 → `junk_check.sh` 回落 full 模式扫全仓，把 `archives/c/cloog`、`archives/k/kics`、`archives/l/libbfio`、`archives/t/thc` 的遗留 `.staging-verified`/`.build-closed`（均已在 origin/main 中，非本次改动）算作本包失败。修复：先 commit 再 resume。
6. **G0 干净构建验证误报（框架侧）**：对 CMake 包执行 `./configure` 报 `./configure: No such file or directory`（exit 127），属框架对非 autotools 包的已知误报，非包缺陷；`conan-verify` 的 G0–G4 全部真实通过。

### 知识图谱使用情况

- **引用知识条目**: E092（`System is unknown to cmake`，实测原生构建下仅为告警，处方不适用，已沉淀为草稿 E545）、E214（`ld.lld: undefined symbol` 签名相似但根因不同，用于排除 lld `--gc-sections` 假设）
- **新增知识草稿**: E429（OpenMP 仅按 target 存在就链接）、E479（依赖共享库 SONAME 符号链接链被 OHOS 加载器拒载）、E545（原生 OHOS 构建的 `System is unknown to cmake` 无需覆盖系统名）、E546（上游测试/基准可执行文件装进 `share/`，纯库包须在 `package()` 裁剪）
- **引擎命中情况**: 两处报错分别命中 E214 与 E274，均为**签名相似但根因不同**的误命中（E214 是 lld `--gc-sections` 裁剪 `__start_`/`__stop_`；E274 是「缺 SONAME 符号链接」而本次是「符号链接存在但加载器拒载」），故未覆盖本次根因，已按 R30/R31 补草稿
- **测试统计**: 总计 69, 通过 69, 失败 0, 跳过 0（另有消费者端到端用例 39/39 断言通过）
- **未覆盖的错误模式**: `__kmpc_*` 未定义（OpenMP 静态归档缺运行时）、OHOS 加载器拒载符号链接共享库 —— 两者此前均未入库，已补 E429/E479

### AI 检视结果

- **检视阶段到达**: 未到达（本流程到 PR 创建即停，AI Review 交 follow-up 续环）
- **变更摘要评估**: 待 AI 检视
- **检视意见数量**: 0（尚未进入检视）
- **检视意见处理**: 预案——提交前已按踩坑清单逐项自查：`conandata.yml` 仅保留官方 https 单值 URL 且已删除 `conandata.yml.ghfast-bak`；`reports/` 只 force-add 文本报告（`test-report.md`/`conan-verify-report.md`/`pr-body.md`/`audit-result.json`），`conan-create.log` 与 `w3-local-ci.log` 一律不入库；PR 正文按赛事模板 11 字段手写，实测数填入

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（commit 版本目录后按增量模式运行；`junk_check`/`knowledge_check` 等门禁通过）
- **远程 CI (PR 校验)**: 待触发（GitCode CI 为评论触发型，PR 创建后需 `trigger-ci`）
- **CI 失败原因**: 无（首轮 W3 失败系 full 模式误扫他包遗留文件，非包缺陷）

### 效率分析

- **HANDOFF 次数**: 2（① finish 的 W3 `junk_check` full 模式误报；② test_package 首次 `cmake.test()` 缺 `enable_testing()`，均由本流程自行定位修复）
- **重试次数**: `conan create` 共 6 轮（r1 建包；r2/r3 修 test_package 的 generators 声明与 `StyleError` API；r4 暴露 OpenMP 链接缺陷；r5 修 `enable_testing()`；r6 全绿），其中 2 轮为真实缺陷定位
- **关键瓶颈**: 每轮 `conan create` 都要完整重建 428 个 C++ 源文件（约 4–5 分钟），且 conan 不会因仅改 `test_package/` 而复用主包构建缓存；改进手段是另建探针构建目录（复用 conan 生成的 generators 目录 + `cmake --build`）把消费者侧的编译迭代压到秒级
- **耗时较长的步骤**: 主包构建（428 个 cpp，8 核约 4.5 分钟）；上游 69 个 ctest 用例约 32 秒；消费者端到端用例约 2 秒

---

## 建议

### SKILL 设计改进

1. **`finish` 前强制 commit 版本目录**：`junk_check.sh` 的增量模式依赖 `git diff origin/main...HEAD`，未 commit 时静默回落 full 模式并把他包的遗留隐藏文件算作本包失败。建议 `finish` 在检测到本包目录存在未 commit 改动时直接提示“先 commit 再 finish”，而不是给出 HANDOFF 让人从 106890 个文件的扫描结果里反推。
2. **G0 干净构建验证应按构建系统分派**：当前对 CMake/Meson 包仍尝试 `./configure`，必然 exit 127 并产生 HANDOFF 噪音（与 `conan-verify` 的 G0–G4 结论矛盾）。建议按 `manifest.yaml: build.system` 选择验证命令（cmake 用 `cmake -S . -B build`，meson 用 `meson setup`）。
3. **`conan-verify` 的镜像注入应默认清理备份文件**：E017 预防会把 `conandata.yml` 改写为 `ghfast.top` 镜像并留下 `conandata.yml.ghfast-bak`；URL 虽正确还原，但 `.ghfast-bak` 残留会被 `junk_check`/AI 检视误判。建议还原时一并删除备份，或写入 `.gitignore`。

### 模板改进

1. **`templates/test_package/MANIFEST.yml.tmpl` 补充大测试集写法**：当上游注册几十~几百个 CTest 用例时，逐条列 `- file:` 不现实，建议模板给出「按测试宏分组 + `source:` 指向上游 CMakeLists + 实测结果段」的示例（本包参照仓内 `osmium-tool/1.19.1` 的成熟写法）。
2. **`templates/conanfile-cmake.py.tmpl` 增加依赖共享库实体化的可选片段**：OHOS 上「依赖共享库以符号链接安装 → 加载器拒载」是高频问题，模板里给出一段注释掉的 `generate()` 片段（遍历 `cpp_info.libdirs` + `shutil.copy2` + `Environment().prepend_path`）可显著降低每个包重复踩坑的概率。
3. **`templates/skill-feedback.md` 的 `{BUILD_SYSTEM}` 占位符会在自动生成时漏填**（本次生成的骨架里同时残留 `{BUILD_SYSTEM}` 与 `(请填写)`，前者不在校验清单里容易被忽略），建议一并纳入占位符校验。

### 自动化补全

1. **占位符统一校验**：建议把 `feedback/`、`reports/`、`test_package/MANIFEST.yml` 里的 `{大写占位符}`、`(请填写)`、`请填写` 一并作为 `finish`/`submit` 的硬校验项，避免只校验 `(请填写)` 而漏掉 `{BUILD_SYSTEM}` 这类。
2. **依赖共享库实体化可自动化**：既然「符号链接 .so 在 OHOS 上不可加载」是确定性环境行为，可由框架在 test_package 生成阶段自动注入实体化逻辑，而非每个适配者手写。
3. **消费者测试编译的快速回路**：建议框架提供 `ohc-run.py test-build <pkg> <ver>`，复用 conan 生成的 generators 目录直接 `cmake --build` 一个独立探针目录，把「仅改消费者代码」的迭代从 5 分钟压到秒级（本次已手工验证该做法可行）。

### 知识图谱覆盖

1. **新增 E429**：`__kmpc_*` 未定义 —— 需要覆盖「上游只在 target 存在时就链接可选运行库（OpenMP/TBB 等），使构建选项失效」这一类模式，检索词应包含 `__kmpc`、`OpenMP::OpenMP_CXX`、`CMAKE_DISABLE_FIND_PACKAGE`。
2. **新增 E479**：依赖共享库以 SONAME 符号链接链安装时被 OHOS 加载器拒载 —— 现有 E274/E019/E207 覆盖的是「缺符号链接导致 SONAME 找不到」的**创建侧**问题，本条是其反面（链接存在但加载器拒载，errno 为空），检索词应包含 `Error loading shared library`、`errno empty`、`realdep_libs`。
3. **新增 E545**：修正 E092 的适用边界 —— E092 的 `-DCMAKE_SYSTEM_NAME=Linux` 处方只适用于交叉场景；原生（build==host==OHOS）构建下同一签名只是告警。建议在 E092 的 `conflicts_with`/`similar_to` 里互指，避免后续适配者被处方误导。
4. **新增 E546**：上游测试宏把测试/基准可执行文件装进 `share/`，纯库包必须在 `package()` 裁剪 —— 覆盖「包内混入未签名可执行文件 + 被判定为混装应用」这一类打包问题。
5. **建议提高引擎匹配精度**：本次两处报错都命中了签名相似但根因完全不同的条目（E214/E274），若引擎对「命中项根因与日志不匹配」有二次判定，可直接提示“可能未覆盖，请补草稿”。

---

## 作者

- **姓名**: kongling
- **邮箱**: 308360610@qq.com
- **Agent ID**: CCB0
- **生成时间**: 2026-09-29
- **PR 编号**: —
- **Git Commit**: —
