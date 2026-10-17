# 知识候选台账 — uvg266 0.8.1（第一轮适配，知识库扩展候选评估）

> 本台账记录本轮适配中每项非噪声候选的真实错误、根因、修复、验证、适用范围，
> 完成正式知识/图谱/草稿四范围查重与七轴查重，最后给出路径决定。
> 适配库：uvg266 0.8.1（ultravideo/uvg266，VVC 视频编码器，C 语言，CMake 构建）。

## 一、候选清单

### C1. 官方 release tarball 不含测试子模块 `greatest`，CMake `add_subdirectory(tests)` 需 greatest/greatest.h
- **真实错误**：`tests/*.c` 均 `#include "greatest/greatest.h"`；tarball 中
  `greatest/` 为空目录（git submodule 是 gitlink，tar 归档只落目录骨架），
  CMakeLists 因 `if(NOT EXISTS greatest/greatest.h)` 静默不注册测试，
  tests 无法编译运行。
- **根因**：GitHub release tarball 只打包 `.gitmodules` 描述的目录结构，
  不含 submodule 内容（E150 同类根因）。
- **修复**：配方 `conandata.yml` 增加 `greatest:` 第二 source（官方子模块
  URL + v0.8.1 钉扎提交 `60e25ce7658ced49f03b52ac14c553cf6ea33de4` + SHA-256
  `3914a24a...`），`source()` 中 `get(..., destination=greatest/)` 拉取；
  不污染源码 diff、不依赖 git 环境、哈希可复现（CI 干净环境一致）。
- **验证**：W3 `conan create` 中 `Test_uvg266`（39 个 greatest TEST）实际编译
  并全部通过（0.03s），`uvg266_tests` 链接运行成功；`test_external_symbols`
  通过。
- **适用范围**：官方 tarball 缺失测试框架子模块（greatest/Catch2/check 等）
  的 C/C++ CMake 项目（跨库可复用；greatest 自身已于 archives/g/greatest
  建包，但作为**测试框架源码**仍需直接落源码树）。
- **四范围查重**：
  - graph/index.tsv：命中 E150（release tarball 不含 submodule，manual-download）；
    E294（共享包+静态测试第二构建树，test submodules 关键词）。E293 附近无
    greatest 专项。
  - knowledge/doc/：E150.md「manual-download：clone 子模块仓库复制进源码树」；
    E425.md（pico-sdk 空 submodule 占位，不下载）；E294.md（第二构建树）。
  - graph/*.kv：E150.kv 与 E425.kv 已读；DRAFT-kangaru-catch2-submodule
    （**测试框架** submodule——用 test_requires+CMakeDeps 让 find_package 直接
    吃 conan 包，代替手动下载进树）；DRAFT-rapidyaml-c4core（构建辅助
    submodule——export_sources 打包恢复）。
  - knowledge/drafts/：DRAFT-kangaru-4.3.2-catch2-submodule-test-requires.kv
    （测试框架 submodule，方案：conan test_requires 替代）；DRAFT-rapidyaml
    -c4core-cmake-submodule-vendoring.kv（export_sources vendor）；无 greatest
    专项草稿。
- **七轴查重**：
  | 轴 | 判定 | 说明 |
  |----|------|------|
  | exact_duplicate | false | 四范围无 greatest/测试框架子模块下载入树条目 |
  | causal_duplicate | false | E150 因果面相同（tarball 缺 submodule）但方案不同 |
  | trigger_overlap | 是 | 与 E150/kangaru/rapidyaml 同触发（tarball 缺 submodule） |
  | solution_overlap | 部分 | E150 是 git clone 手工复制；kangaru 是 test_requires 替代（仅 find_package 场景）；rapidyaml 是 export_sources vendor；本候选为**配方多 source 直接 get 到子目录 + 钉扎提交 + SHA-256 固定**（find_package 不可用、无 conan 包装时） |
  | combination_novelty | true | 「测试框架子模块 + conan 多 source 下载入子目录」组合无既有条目 |
  | boundary_novelty | true | 边界：find_package(QUIET) 可替代 → 走 kangaru test_requires；无 find_package、直接 include、无 conan 包 → 走本方案（greatest 即此例）；仅需空占位 → E425 |
  | test_migration_novelty | true | 可迁移至任一以测试子模块作框架的 C/C++ 库（check/utest/unity 等） |
- **结论**：**部分覆盖 + 新增差异可跨库复用 → 建草稿（路径 B 候选）**。

### C2. 上游 shell 测试依赖外部工具 ffmpeg + VTM DecoderAppStatic（仅 x86-64 静态制品），OHOS aarch64 无法完整运行
- **真实错误**：8/10 个 ctest shell 入口（test_mtt/intra/monochrome/lmcs/
  tools/slices/cabac_state/invalid_input）依赖 ffmpeg 生成 YUV 输入 +
  `DecoderAppStatic`（VTM VVC 参考解码器）校验输出；缺任一即脚本立即失败。
- **根因**：上游 CI（.travis-install.bash）从 ultravideo.fi 下载预编译工具；
  ffmpeg 有 ohpcd 制品（6.1.6）已恢复；DecoderAppStatic 仅有 **x86-64 静态
  ELF**（实测 readelf），ohpcd 无 vvdec/vtm 包，aarch64/OHOS 无对应制品。
- **修复**：ffmpeg 从制品仓 `conan install` 恢复并验证 test_invalid_input 通过；
  DecoderAppStatic 复查制品仓仍无 → 遵守**上游原生 XFAIL_TESTS 环境变量机制**
  （CMakeLists configure 时读取，上游 CI 对 asan 亦用）排除 8 个外部工具依赖
  入口，保留 Test_uvg266 与 test_external_symbols 注册执行；双口径台账
  （source_declared_total=40，configured_executable_total=39，
  executed_passed_total=39，39/40=97.5%，当前配置 39/39=100%）+ 恢复条件。
- **适用范围**：上游 ctest/shell 测试依赖外部二进制工具（生成器/解码器/
  校验器）且 OHOS aarch64 无对应制品的库；需按上游原生 skip 机制登记而非
  伪造。
- **四范围查重**：
  - graph/index.tsv：E356（chibicc x86-64 输出 vs armv8 worker，two-plane
    fixed-target + exact XFAIL）；E272（DejaGNU/binutils 交叉测试工具缺失）；
    E374（can_run 能力门控）。
  - knowledge/doc/：E356.md 已读（编译器包生成 x86-64 代码，注入头文件混合
    ABI 禁止）；E272.md（测试脚手架工具缺失）。
  - graph/*.kv：E356.kv（compiler/abi/path-c）；E374.kv（can_run 门控）。
  - knowledge/drafts/：DRAFT-E318-draft-chibicc-path-c-assembly-validation；
    无「上游 shell 测试依赖 x86-64 专用解码器」条目。
- **七轴查重**：
  | 轴 | 判定 | 说明 |
  |----|------|------|
  | exact_duplicate | false | 四范围无同类（视频解码器工具 x86-64 缺失） |
  | causal_duplicate | false | E356 根因是编译器输出 ABI 不匹配，本候选是测试工具制品架构缺失 |
  | trigger_overlap | 部分 | 同在「armv8 worker 运行 x86-64 相关测试」域 |
  | solution_overlap | 部分 | E356 用 two-plane + exact XFAIL；本候选用上游原生 XFAIL_TESTS + 双口径 | 
  | combination_novelty | false | 规则层已有「外部工具缺失 → 记录 blocked+恢复条件」 |
  | boundary_novelty | false | 无新增边界（E356/E272/E374 已覆盖 x86-64 工具与测试能力门控） |
  | test_migration_novelty | false | 通用规则已在 SKILL 双口径/依赖复查条款覆盖 |
- **结论**：与既有知识（E356/E272/E374 + SKILL 双口径条款）**同质，复用既有知识，不新建草稿**。测试台账如实记录阻塞与恢复条件即可。

### C3. conan-init 模板误判 CMake 项目为 autotools（构建系统探测）
- **真实错误**：init-build/conan-init 按探测输出 `autotools` 模板，生成
  AutotoolsToolchain 配方；uvg266 实为 CMake 项目 → 需人工改 CMakeToolchain。
- **根因**：构建系统探测启发式对纯 CMake 且无 configure 脚本的项目覆盖不全。
- **修复**：人工改写 conanfile.py 为 CMakeToolchain（本仓库既有做法，非本轮特有）。
- **验证**：改写后 W3 全绿。
- **查重**：此类「模板误判→人工改 CMake」为本仓库既有操作知识（recipe-search/
  migration-guide），非 uvg266 特有模式。
- **七轴**：exact=false；causal=false；trigger_overlap=部分（构建系统探测）；
  solution_overlap=是（人工改写配方）；组合/边界/迁移新颖性均 false。
- **结论**：噪声级候选，**复用既有知识，不建草稿**。

## 二、路径决定

- C1（测试框架子模块 multi-source 下载入树）：**new_draft** —— 已验证、
  可跨库复用、四范围查重为部分覆盖且存在真实新增差异（配方多 source 钉扎
  下载入子目录，find_package 不可用场景）。
- C2（外部工具 x86-64 缺失）：**reuse_existing** —— E356/E272/E374 +
  SKILL 双口径条款已覆盖，台账如实登记。
- C3（构建系统误判）：**reuse_existing** —— 既有通用操作知识。
- **最终路径：path_b_new_draft（C1 建草稿，同 stem 的 .md/.kv 配对，
  与 uvg266 归档文件同一 PR 交付）**；C2/C3 复用既有知识，不另建草稿。

## 三、关系字段（C1 草稿）

- similar_to: E150, DRAFT-kangaru-4.3.2-catch2-submodule-test-requires, DRAFT-rapidyaml-0.7.2-c4core-cmake-submodule-vendoring
- caused_by: []（上游 .gitmodules 子模块 + GitHub release tarball 归档行为）
- prerequisite_of: [] 
- conflicts_with: []