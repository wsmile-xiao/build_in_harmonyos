# Knowledge Candidate Ledger — buddy_alloc 1.3.2 (R01)

任务：buddy_alloc-1.3.2-r01-pc1-39-20260924T215533Z | executor: pc1-39
查重范围：knowledge/graph/index.tsv（766 条）+ knowledge/doc/ + knowledge/drafts/（2920 条）
决定：**path_a_no_knowledge（reuse_existing）** —— 全部候选命中既有条目/草稿，无验证过的新增差异，不新建草稿。

## 候选台账（每项：真实错误 → 根因 → 修复 → 验证 → 适用范围）

### 候选 C1：header-only 配方 package() copy() 相对 dst 导致空包（G2 "No files in this package"）
- 真实错误：`conan create` package() 后 `package(): WARN: No files in this package!`，test_package 配置期 `Imported target "buddy_alloc::buddy_alloc" includes non-existent path ".../p/include"`（CMake Error）。
- 根因：Conan 2 `copy()` 相对 dst 按当前 build 目录解析，非 package 目录；头文件未进包 → CMakeDeps 的 INTERFACE_INCLUDE_DIRECTORIES 指向不存在的 package_folder/include。
- 修复：`copy(self, "*.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"), keep_path=False)`（绝对路径）。
- 验证：修复后 conan-verify G2 PASS（日志 archives/b/buddy_alloc/1.3.2/reports/conan-create.log；本次实测）。
- 适用范围：所有 header-only / 无编译族 Conan 2 配方（占配方 26%）。
- **查重**：**exact_duplicate** → `DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental`（相同错误特征 `Imported target ... includes non-existent path`、相同根因、相同绝对路径修复，boost-te 1.0.0 已记录）。七轴：exact_duplicate=true；causal_duplicate=true（同因）；trigger_overlap=true（同为 G2/test_package 配置期）；solution_overlap=true（同为绝对 dst）；combination_novelty=false；boundary_novelty=false（本库无新增差异，仅 C 单头文件与 C++ 单头文件的格式差异）；test_migration_novelty=false。similar_to=DRAFT-boost-te；caused_by=none；prerequisite_of=none；conflicts_with=none。

### 候选 C2：W3/finish JC 全仓 full 模式命中其他库基线空标记文件（cloog/kics .build-closed/.staging-verified）
- 真实错误：`finish` W3 本地 CI 模拟 `JC_RESULT=fail / JC_ERRORS=2`，JC1+JC5 命中 `archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`（main 基线已提交的空 blob，SHA-256 = e3b0c442…）。
- 根因：junk_check.sh 回退 full 模式用 `git ls-files`（索引）整仓扫描；工作区 mv 无效，必须从索引层面隔离。
- 修复（基线隔离复验四步）：记录 pre-SHA-256 → `git rm --cached`（临时取消跟踪）→ 复跑 finish（W3 PASS）→ `git reset` 恢复索引 + 恢复工作区文件 → 核对 post-SHA-256 == e3b0c442…（本次实测全部通过；diff 不含这些路径）。
- 验证：本次 finish W3 PASS；恢复后 `git ls-files` 3 条回归、路径 status 干净、`git diff HEAD` 无 cloog/kics。
- 适用范围：任何在含基线垃圾标记文件的仓库上跑 W3 full 模式的新库适配。
- **查重**：**exact_duplicate** → `DRAFT-fastnoiselite-1.1.1-jc-full-mode-baseline-junk-isolation`（同一批文件、同一根因"JC 读索引非工作区"、同一 git rm --cached 四步流程，fastnoiselite 1.1.1 已记录）。七轴：exact_duplicate=true；causal_duplicate=true；trigger_overlap=true（同为 W3 JC1/JC5 full 模式）；solution_overlap=true（同为索引级隔离+恢复）；combination_novelty=false；boundary_novelty=false；test_migration_novelty=false。similar_to=DRAFT-fastnoiselite（同批文件）、DRAFT-dr_mp3-0.7.2-baseline-noise-isolation、DRAFT-jsoncons-1.9.0-test-count-and-baseline-noise、DRAFT-boost-te（commit-first 替代路径）；caused_by=none；prerequisite_of=none；conflicts_with=none。

### 候选 C3：header-only 配方 conan-verify G1 要求显式 build()（no-op 即可）
- 真实错误：`G1: conanfile.py 缺少: build() 方法`（结构门禁，非编译门禁）。
- 修复：`def build(self): apply_conandata_patches(self)`（header-only 无编译，仅补丁应用）。
- 验证：修复后 G1 PASS → G2-G4 全过。
- **查重**：**exact_duplicate** → 正式条目 **E257**（no-op-build-for-header-only，来源 PR !7243）。七轴：exact_duplicate=true；其余五轴无新增。similar_to=E257；caused_by=none。

### 候选 C4：worker 无法直连 github.com → 下载/取源走镜像
- 真实错误：init-build 下载 `<urlopen error Errno 110 Operation timed out>`；curl github.com 直连超时。
- 修复：init-build 离线路径（手动经 gh-proxy 下载官方 tarball → 放 $HOME/tmp/builds/ → EXPECTED_SHA256=官方 sha256 → init-build 跳过下载核验）；conan-verify G2 自动注入 ghfast.top（E017 预防逻辑）。
- 验证：tarball SHA-256 5c1b045c… 与官方一致；conan create 经 ghfast.top 取源成功。
- **查重**：**exact_duplicate** → 正式条目 **E017**（use-ghfast：GitHub timeout/mirror/ghfast 全族）。七轴：exact_duplicate=true；solution_overlap=true；combination_novelty=false；boundary_novelty=false（init-build 离线置 tarball 属 E017 适用边界的工程变体，无独立新增差异）；test_migration_novelty=false。similar_to=E017；caused_by=none。

### 候选 C5：上游 test-fuzz.c 引用未声明 buddy_tree()（上游缺陷）
- 真实错误：`clang -std=c99 test-fuzz.c` → `call to undeclared function 'buddy_tree'`（头文件仅前向声明 `struct buddy_tree;`，无 `buddy_tree()` 函数）；该入口不在 CMake/Makefile 主目标内。
- 处理：台账列为不可运行上游 fuzz 驱动（不计入通过率分母为独立用例），未改上游、未伪造。
- **查重**：库内缺陷观察，非跨库可复用知识 → 不构成路径 B 候选（适用边界=buddy_alloc 1.3.2 本体）。七轴：exact_duplicate=false（无既有条目）；causal_duplicate=false；trigger_overlap=false；solution_overlap=false；combination_novelty=false（不可跨库复用）；boundary_novelty=false；test_migration_novelty=false。similar_to=none；caused_by=upstream；conflicts_with=none。

## 覆盖/新增差异
- 既有条目覆盖：E017（镜像取源）、E257（header-only no-op build）、DRAFT-boost-te（copy 绝对路径 + commit-first 规避）、DRAFT-fastnoiselite（JC 基线隔离四步）、DRAFT-dr_mp3 / DRAFT-jsoncons（基线噪声）。
- 本轮新增差异：无（四项核心候选均为 exact_duplicate，C5 为库内缺陷不可跨库）。未用改标题/换关键词硬凑新增。

## 路径决定
- **reuse_existing / path_a_no_knowledge**：完整重复，复用既有条目与草稿，不新建 .md/.kv 草稿、不 promote、不写入 knowledge/graph/ 或 knowledge/doc/。
- 依据：任务规则"完整重复且无独立差异时复用原条目"；SKILL R31/R30 仅要求知识图谱未命中时生成草稿（本次 G2 失败经引擎命中 E540 指向环境类问题、G1 修复命中 E257 族，均非未命中）。

## 关系字段
- similar_to：DRAFT-boost-te、DRAFT-fastnoiselite、DRAFT-dr_mp3、DRAFT-jsoncons、E017、E257
- caused_by：none（均为仓库基线/既有流程特征，非本库引起）
- prerequisite_of：none
- conflicts_with：none
