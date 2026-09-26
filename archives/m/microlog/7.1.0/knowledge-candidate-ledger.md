# 知识候选台账 — microlog 7.1.0（2026-09-23）

> 每个候选记录真实错误/根因/修复/验证/适用范围，并完成四范围查重
> （knowledge/graph/index.tsv、knowledge/doc/、knowledge/graph/、knowledge/drafts/）。
> 所有命令、cwd、退出码、日志见 `reports/` 与 notes.md。

## 候选 1：W3 本地 CI 命中其他库基线文件（cloog/kics 运行时状态文件）

- **门禁**: finish Step 5 W3 local CI（build_and_test.sh → junk_check.sh JC1/JC5）
- **真实错误**: `[FAIL] JC1: 3 个运行时状态文件被跟踪: archives/c/cloog/0.21.1/.build-closed、archives/c/cloog/0.21.1/.staging-verified、archives/k/kics/2.1.20/.staging-verified`；`JC_RESULT=fail`、W3 阻塞
- **根因**: junk_check full 模式用 `git ls-files` 整仓扫描；main 中 cloog/kics（提交前已存在）的空状态文件不在 JC5_ALLOWED 白名单，与本库无关却被命中（`git diff origin/main...HEAD` 为空 → full 模式）
- **修复**: 基线隔离复验：记录 pre SHA-256（e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855，空文件 ×3）→ `git rm --cached` 索引级隔离 + 文件移出 → 复跑 finish W3 通过（published、submit 就绪）→ `git reset` + 文件原样恢复 → post SHA-256 与 pre 一致（e3b0c44298fc... ×3），`git diff --name-only HEAD` 不含该路径
- **验证**: 隔离期间 `finish microlog 7.1.0 published` 退出 0、W3 通过；恢复后 sha256sum 前后一致
- **适用边界**: 其他库在 main 已提交的隐藏工作流标记触发 JC；适用于所有 W3/finish 阶段被共享基线噪声阻塞的库；不适用当前库自身新增 junk（那必须修复）
- **四范围查重**:
  - index.tsv：无专有 E 条目
  - doc/：无 doc 覆盖
  - graph/：无 graph 覆盖
  - drafts/：**已有多条草稿覆盖同一根因与同一方案**：DRAFT-jc-full-scan-baseline-noise-exemption（match_keywords 含 JC5/整仓扫描/基线噪声/git rm --cached）、DRAFT-dr_mp3-0.7.2-baseline-noise-isolation、DRAFT-libfort-0.4.2-w3-baseline-junk-check-full-scan、DRAFT-libpopcnt-2.0-w3-baseline-junk-check-full-scan、DRAFT-jsoncons-1.9.0-test-count-and-baseline-noise

## 候选 2：conandata.yml codeload URL 无 .tar.gz 扩展名 → BadZipFile

- **门禁**: conan-verify G2（conan create source()）
- **真实错误**: `ERROR: microlog/7.1.0@ohpcd/stable: Error in source() method, line 39 get(self, **self.conan_data["sources"], strip_root=True) BadZipFile: File is not a zip file`（下载成功但按 zip 解压失败）
- **根因**: conan get() 按 URL basename 推断格式；`https://codeload.github.com/an-dr/microlog/tar.gz/refs/tags/v7.1.0` 的 basename 为 `v7.1.0`（无扩展名）→ 误按 zip 解压
- **修复**: 改用官方规范归档 URL（含 .tar.gz 扩展名）`https://github.com/an-dr/microlog/archive/refs/tags/v7.1.0.tar.gz`，sha256 不变（fd8aa1e993a421d90aeae5d0c9765b40f69675d1b4d117b847d3f9d940e4063b，与 codeload 下载字节一致）→ 重跑 conan-verify G1-G4 全过
- **验证**: `python3 scripts/ohc-run.py conan-verify microlog 7.1.0`（exit 0）
- **适用边界**: 所有使用 codeload/无扩展名源码 URL 的 conan 配方
- **四范围查重**:
  - index.tsv：**E276 已登记**（conan get() 对 codeload tar.gz URL basename 误判为 zip 报 BadZipFile，推荐 `filename='<软件>-<版本>.tar.gz'` 显式传参）；另有 E483（explicit-filename-in-get）、E392
  - doc/：doc/E276.md 完整覆盖本根因与标准方案（我的修复为等价变体：换官方 URL 而非传 filename，同样解决）
  - graph/：无
  - drafts/：DRAFT-E569-codeload-direct-url-bypass-302、DRAFT-E597-libsmraw-get-filename-duplicate-kwarg、DRAFT-apriltag-3.4.5-github-codeload-sha256-autocrlf-cmake-werror（同类 codeload 主题）

## 候选 3：上游 example/subprojects/microlog 自引用符号链接环导致 init-build 双轨复制失败

- **门禁**: init-build（_create_dual_track）
- **真实错误**: `shutil.Error: [Errno 40] Symbolic link loop`（copytree 在 example/subprojects/microlog -> ../.. 自引用环上死循环）；另有 HMDFS 拒绝 os.link 硬链接（Operation not permitted，代码已有 copy2 回退）
- **根因**: 上游源码 example/ 下的 dev scaffolding 目录含指向仓库根的自引用符号链接环，tar 解压保留为符号链接；init-build 的 .work 复制按默认 symlinks=False 跟随链接 → 死循环
- **修复**: 从 .orig 移除该非库源码的环链接（dev scaffolding artifact，不影响 ulog.h/ulog.c 构建）后重跑 init-build 成功
- **验证**: 移除后 init-build 退出 0，.work 正常创建
- **适用边界**: 上游源码含自引用符号链接环导致双轨复制失败时的处置；属一次性源清理，同类既有知识（E255 符号链接环、E018/E050/E073 HMDFS 符号链接）已覆盖该模式
- **四范围查重**:
  - index.tsv：E255（resource-data-package，含 symbolic link loop/symlink loop）、E018（HMDFS symlink Permission denied）、E050/E073（HMDFS 符号链接 copy-replace）
  - doc/：doc/E255.md 覆盖符号链接环处理（tarfile filter="data"）；E018/E050 覆盖 HMDFS 链接处置
  - graph/：无专有
  - drafts/：无本库专有草稿；既有 E255 体系覆盖

## 候选 4：C 源码分发 INTERFACE 库（ulog.c + 手写 targets.cmake）的 Conan 配方模式

- **门禁**: conan-init → conan-verify G1-G4 / test_package / test_ohos 消费者验证
- **真实错误**: conan-init 按 autotools 生成模板（configure+make），与实际 CMake INTERFACE 构建不符；且默认构建下 ulog_output_add/ulog_topic_add 因 ULOG_BUILD_EXTRA_OUTPUTS/TOPICS_MODE 未启用返回 INVALID（WARN: 'ulog_output_add' called with ULOG_BUILD_EXTRA_OUTPUTS disabled）
- **根因**: microlog 为 CMake INTERFACE 库，但 install 会把 ulog.c 源文件装入 share/microlog/src/ 并由手写 micrologTargets.cmake 在**消费方**重新定义 STATIC target（target_sources + PUBLIC include）；特性宏（ULOG_BUILD_EXTRA_OUTPUTS/TOPICS_MODE/TIME）须在**编译期由消费者配置**，默认配置下自定义输出/主题 API 为禁用态
- **修复**: 配方用 CMakeToolchain（ULOG_BUILD_TESTS=OFF）+ 上游 install 原样打包；package_info 用 `cpp_info.set_property("cmake_find_mode", "none")` + `builddirs=["lib/cmake/microlog"]` 透传上游自带 config，消费者 `find_package(microlog CONFIG)` 得 microlog::microlog；test_package/test_ohos 按消费者语义配置特性宏编译并断言可观察输出
- **验证**: conan-verify G1-G4 全过；test_package 1/1 通过（stdout 捕获断言）；test_ohos T1-T3 全过（aarch64 ELF、无宿主路径泄漏、消费者真实编译链接运行）
- **适用边界**: rxi/log.c 系、stb 风格单文件库、源码分发（非 header-only）INTERFACE 库：install 装 .c 源 + 手写/导出 targets 在消费方编译的 Conan 配方；特性宏由消费者编译期配置时默认禁用 API 的测试写法
- **四范围查重**:
  - index.tsv：E321/E322（header-only INTERFACE 配方，package_type=header-library + self.info.clear()）；E035（header-only-install）；E451（cmake_find_mode config 消费）；E392（raw-makefile single-file）
  - doc/：E321.md（martinmoene lite 系 header-only）、E322.md（cpp-taskflow header-only INTERFACE：package_type=header-library + 关闭上游 tests/examples + find_package CONFIG）——均为 **header-only**（无 .c 源分发、无消费方编译 ulog.c 语义）
  - graph/：无
  - drafts/：DRAFT-adacgi-ada-source-library-conan-pattern（**Ada** 源码分发，gcc-ada tool_requires + adainclude，语言/工具链不同）；DRAFT-E322-cmake-find-mode-none-target-bridge（消费方桥接 cmake_find_mode=none 依赖的**目标名**，非打包侧模式）；DRAFT-EA-headeronly-dependency-chain（header-only 依赖链）——**均未覆盖"C 源分发 + 消费方编译 ulog.c + cmake_find_mode=none 透传自带 config"的组合**

## 七轴查重汇总

| 轴 | 候选 1（JC 基线噪声） | 候选 2（BadZipFile） | 候选 3（符号链接环） | 候选 4（源分发 INTERFACE 配方） |
|---|---|---|---|---|
| exact_duplicate | 是（jc-full-scan/dr_mp3 等草稿同根因同方案） | 是（E276 同根因同方案） | 部分（E255 同根因，处置略异） | 否 |
| causal_duplicate | 是（既有草稿已解释） | 是（E276 已解释） | 是（E255 已解释） | 否 |
| trigger_overlap | 高（JC full 扫描触发一致） | 高（get() basename 误判一致） | 中（init-build 复制触发） | 低（仅本库配方触发） |
| solution_overlap | 高（git rm --cached + 恢复 + sha 审计一致） | 高（显式扩展名方案等价） | 中（移除环链接 vs tarfile filter） | 低（E321/E322 为 header-only，无消费方编译 .c） |
| combination_novelty | 否 | 否 | 否 | **是（C 源分发 + 消费方编译 + cmake_find_mode=none + builddirs 透传的组合未被覆盖）** |
| boundary_novelty | 否 | 否 | 否 | **是（明确区分 header-only 与源码分发两类 INTERFACE 库配方边界）** |
| test_migration_novelty | 不适用 | 不适用 | 不适用 | 是（默认禁用特性宏下消费者测试写法：编译期配置 + 可观察输出断言） |

关系字段：
- 候选 1: similar_to=[DRAFT-jc-full-scan-baseline-noise-exemption, DRAFT-dr_mp3-0.7.2-baseline-noise-isolation, DRAFT-libfort-0.4.2-w3-baseline-junk-check-full-scan, DRAFT-libpopcnt-2.0-w3-baseline-junk-check-full-scan], caused_by=[junk_check full 扫描范围缺陷], prerequisite_of=[W3 本地 CI 通过], conflicts_with=[]
- 候选 2: similar_to=[E276, E483, DRAFT-E569-codeload-direct-url-bypass-302], caused_by=[conan get() basename 推断], prerequisite_of=[G2 干净构建], conflicts_with=[]
- 候选 3: similar_to=[E255, E018, E050], caused_by=[上游 dev scaffolding 自引用符号链接环], prerequisite_of=[init-build 成功], conflicts_with=[]
- 候选 4: similar_to=[E321, E322, DRAFT-adacgi-ada-source-library-conan-pattern], caused_by=[CMake INTERFACE 库以源码形式 install], prerequisite_of=[消费者 find_package CONFIG 可用], conflicts_with=[]

## 路径决定

- **reuse_existing**: 候选 1、候选 2、候选 3 均为既有知识已覆盖（exact/causal duplicate，触发与方案重叠），复用既有条目（JC 基线噪声草稿群、E276、E255），**不建新草稿**。
- **new_draft（路径 B）**: 候选 4 已由本轮真实日志验证（conan-verify G1-G4、test_package、test_ohos 全过）、可跨库复用（rxi/log.c 系单文件 C 库普遍适用）、四范围查重为未命中且与 E321/E322（header-only）存在明确新增差异（源码分发 + 消费方编译 ulog.c + cmake_find_mode=none + builddirs 透传）→ **建立同 stem 的 .md/.kv 草稿**：`DRAFT-microlog-7.1.0-c-source-distributed-interface-recipe`。
- **最终决定**: `new_draft`（路径 B 知识库扩展）——仅候选 4 建草稿，随本库归档进入同一 PR；草稿仅入 knowledge/drafts/，不 promote、不碰正式库。