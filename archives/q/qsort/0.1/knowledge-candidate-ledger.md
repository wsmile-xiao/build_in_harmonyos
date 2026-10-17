# qsort 0.1 知识候选台账（Knowledge Candidate Ledger）

任务: qsort-0.1-r01-pc3-3-20260917T164449Z（知识库扩展）
工作区: worktrees/pc3-3-qsort-0.1 @ feat/qsort-0.1 HEAD 0f232b54ea

## 候选清单

### 候选 A: header-only 无 CMake 库配方的 conan-verify G1 要求显式 build()（no-op）
- 真实错误: `conan-verify` G1 FAIL，报 `conanfile.py 缺少: build() 方法`，阻止后续门禁。
- 根因: G1 是结构检查，把 build() 列为必填；header-only 库无编译步骤，按直觉省略 build() 导致 FAIL。
- 修复: 提供 no-op `def build(self): pass` + `apply_conandata_patches(self)` 调用（本库 source() 中已有），复验 conan-verify 全过。
- 验证: conan create 通过、conan-verify G1-G4/L2/L4/L5 全过、W3 本地 CI 通过。
- 适用范围: 所有 header-only / 无构建系统的 C/C++ 库配方。
- 查重: 正式条目 E257（bshoshany-thread-pool 触发，已 promote，有 doc/E257.md）完全覆盖：error_signature `G1: FAIL|conanfile.py 缺少: build() 方法`、方案 `no-op-build-for-header-only`。
- 七轴查重:
  - exact_duplicate: true（E257 逐字段覆盖）
  - causal_duplicate: true
  - trigger_overlap: true
  - solution_overlap: true
  - combination_novelty: false
  - boundary_novelty: false
  - test_migration_novelty: false
- 关系: similar_to=E257, caused_by=none, prerequisite_of=none, conflicts_with=none
- 决定: **reuse_existing（复用 E257，不建草稿）**

### 候选 B: header-only 配方 package() 中 `package_folder / "include"` 报 `TypeError: unsupported operand type(s) for /: 'str' and 'str'`
- 真实错误: `conan create` 在 package() 阶段报
  `TypeError: unsupported operand type(s) for /: 'str' and 'str'`
  于 `copy(self, "qsort.h", self.source_folder, self.package_folder / "include")`。
- 根因: 本环境（OHOS 适配版 Conan 2.29.1 + basic_layout）下 `self.package_folder` 返回 `str` 而非 `pathlib.Path`，`/` 运算符对 str 不适用。模板生成的 `self.package_folder / "include"` 写法在部分布局/环境下会触发。
- 修复: 改用 `os.path.join(self.package_folder, "include")`（并 `import os`），conan create 复验通过。
- 验证: 修改前后两次 conan create 对比（失败→成功），test_package 1/1 Passed；conan-verify G2 PASS。
- 适用范围: 所有 basic_layout / header-library 配方中手工 `copy(..., package_folder / ...)` 路径拼接场景，跨库可复用。
- 查重: 未命中。检索 E340（cargo glob 定位产物）、E473（WebP imported target）、E396（inventory/package_folder schema）、E226（os.popen bytes TypeError）、E080 等均不覆盖本 error_signature；全库 `error_signature:` 级别无 `unsupported operand type(s) for /` 条目；knowledge/doc、knowledge/graph、knowledge/drafts、knowledge/index.tsv 四范围均未命中。
- 七轴查重:
  - exact_duplicate: false
  - causal_duplicate: false（既有条目均非同类根因）
  - trigger_overlap: false（E340/E396 同为 package()/package_folder 关键词但错误面不同）
  - solution_overlap: false（无既有 os.path.join 方案条目）
  - combination_novelty: true（basic_layout + header-library + 手工 include 拷贝 + str package_folder 的新组合）
  - boundary_novelty: true（此 Conan 版本/布局下 package_folder 为 str 的边界事实）
  - test_migration_novelty: false
- 关系: similar_to=E340（同为 package() 路径处理，但定位方法不同）、caused_by=none、prerequisite_of=none、conflicts_with=none
- 决定: **new_draft（建立 DRAFT-qsort-0.1-package-folder-str-path-join.kv/.md 草稿对，同 stem）**

### 候选 C: conan-verify E017 镜像注入后 conandata.yml 残留 gh-proxy 镜像 URL，须恢复官方 URL
- 真实错误: conan-verify G2 为加速下载临时注入 `gh-proxy.com` 镜像到 conandata.yml（`sources.url` 变为列表，镜像在前）；完成后恢复不完全，W3/finish 后 conandata.yml 残留镜像 URL，违反 PF7/R39（镜像域黑名单）。
- 根因: E017 镜像注入机制写回 conandata.yml，工具恢复逻辑未覆盖全部形态。
- 修复: 手工恢复 `sources.url` 为官方 HTTPS 单值 `https://github.com/svpv/qsort/archive/refs/tags/v0.1.tar.gz`，sha256 `0431b733…` 与官方 tarball 复核一致；提交前扫描确认无 `file://`/gh-proxy/ghfast/缓存路径残留。
- 验证: 恢复后 conandata.yml 无镜像域，复扫污染 grep 无命中。
- 适用范围: 所有 E017 镜像注入流程涉及的 GitHub 源配方，提交前必须核对 conandata.yml。
- 查重: 正式条目 E415（verify-and-restore-conandata-after-ci）已覆盖（match_keywords: mirror fallback, gh-proxy, conandata.yml 原地改写, 恢复）；E017 为注入机制本身。
- 七轴查重:
  - exact_duplicate: true（E415 覆盖）
  - causal_duplicate: true
  - trigger_overlap: true
  - solution_overlap: true
  - combination_novelty: false
  - boundary_novelty: false
  - test_migration_novelty: false
- 决定: **reuse_existing（复用 E415，不建草稿）**

### 候选 D: W3 本地 CI 的 JC1/JC5 命中其他库既有基线状态文件（archives/c/cloog/0.21.1/.build-closed、.staging-verified）
- 真实错误: `finish` W3 的 junk_check（JC1+JC5）报 2 个运行时状态文件被跟踪，阻塞构建。
- 根因: 其他库（cloog）提交到 main 的既有基线文件含 `.build-closed`/`.staging-verified`，JC 按 `git ls-files` 全仓扫描命中；非当前库所致。
- 修复: 基线隔离复验（SKILL 内嵌流程）——记录隔离前 SHA-256（两者均为 `e3b0c44…` 空文件）→ `rm -f` + `git rm --cached` 临时隔离 → JC 复检通过（Junk Files: 0）→ finish W3 重跑通过（.ci-result.json exit_code=0）→ `git restore --source=HEAD --staged --worktree` 原样恢复 → 恢复后 SHA-256 与隔离前一致，qsort diff/staged 不含该路径。
- 验证: 隔离后 JC_RESULT=pass；恢复后 sha256sum 与 pre_sha256.txt 逐字节一致。
- 适用范围: W3 全仓扫描命中其他库基线文件的场景。
- 查重: 该行为是 SKILL 内嵌流程（基线隔离复验规则），非新错误模式；四范围检索（基线隔离/JC1/junk_check/.build-closed）无正式条目，属流程而非知识，不建条目。
- 决定: **流程内嵌处理，非知识候选（path 不依赖此候选）**

## 路径判断（汇总）

- reuse_existing: 候选 A（E257）、候选 C（E415）
- new_draft: 候选 B（DRAFT-qsort-0.1-package-folder-str-path-join）
- path_a_no_knowledge: 否——存在已验证、可跨库复用、查重未命中的新增差异（候选 B）
- **路径决定: 路径 B（知识库扩展）——new_draft，草稿与 qsort 归档同 PR 交付**
- 适用边界/反例: 候选 B 仅适用于手工 `package_folder / ...` 拼接的配方；使用 CMake install/export 自动安装头文件的配方（如 E321/E322 的 INTERFACE 库）不触发；`package_folder` 为 Path 的环境不触发。反例: 不应把 E257（build() 门禁）或 E415（镜像恢复）误记为新增。
