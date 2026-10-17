# ssdeep 2.8 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am，libtool 2.5.4 重建）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 / clang++（OHOS aarch64 原生）
- 状态: built

## 编译步骤

```bash
# 1. 替换 config.guess/config.sub（tarball 自带 2005 版无法识别 HarmonyOS）
#    使用 2023-08-22 / 2023-09-19 版（与仓库内已适配 autotools 库一致）
# 2. libtoolize --copy --force   # tarball 无 m4/ 宏目录，补齐 libtool 宏
# 3. autoreconf -fi               # 重建构建系统（2.69 旧宏有废弃警告但成功）
# 4. ./configure --prefix=/storage/Users/currentUser/usr/local
# 5. make -j1 && make install
# 6. make check（exit=0，上游无注册测试）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | tarball 内 config.guess 2005-12-13 不认识 HarmonyOS/aarch64 | 替换 2023 版 config.guess/config.sub（禁止 --build/--host 绕行） |
| 2 | make 触发 autotools 重生成链失败（aaclocal-1.12/automake-1.12 缺失、m4/libtool.m4 打不开） | tarball 未打包 m4/ 宏目录，aclocal.m4 引用 m4/libtool.m4 等 | libtoolize --copy --force 补齐 m4/*.m4 + autoreconf -fi 重建 |
| 3 | configure 报"newly created file is older than distributed files" | 时间戳操作导致 | 统一 touch 源文件时间戳后重跑 configure |
| 4 | sample.c 注释里的 `-Lfuzzy` 是笔误 | 上游注释错误 | 实际链接用 `-lfuzzy` |

## 源码修改

1. `config.guess`（替换为 2023-08-22 版，支持 __OHOS__ 检测）
2. `config.sub`（替换为 2023-09-19 版，支持 *-linux-ohos triplet）

## 依赖版本

- 无外部 Conan 依赖（纯系统头文件：libgen/dirent/inttypes/fcntl/sys-types/ioctl/param/wchar/unistd/stat/mount）
- libtool 2.5.4（构建期工具）

## 上游测试完整枚举台账（R51，全目录口径）

枚举对象：官方 tag release-2.8 源码全目录。结论：**上游无独立测试用例**（source_declared_total = 0）。

| 条目 | 类型 | 是否独立上游用例 | 说明 |
|------|------|----------------|------|
| tests/ 目录 | - | 否 | 不存在 |
| Makefile.am TESTS/check_PROGRAMS | 构建目标 | 否 | 无任何 TESTS/check 注册 |
| sample.c | 样例 | 否（样例不计入独立用例） | API 示例程序，已实际编译运行（输出 fuzzy hash + MATCH score=99，exit=0） |
| normal.sh / world.sh / win.sh | 构建辅助脚本 | 否 | 仅为 configure/make 开关（调试/发布/交叉构建），非测试 |
| reconfig | 构建辅助脚本 | 否 | aclocal/autoconf/autoheader/libtoolize/automake 重建，非测试 |
| doc/（api/manpage/usage html） | 文档 | 否 | 无测试价值 |
| 内嵌 ssdeep-2.8.tar.gz / .zip | 发布包残留 | 否 | 非测试源 |
| 源码测试宏（TEST_CASE/CHECK/assert 业务断言） | - | 否 | `grep -rn` 无任何测试框架宏 |

**make check 实际运行**：exit=0（无注册测试，空操作）。已按 R51 附清点证据（上表）。

**双口径统计**：
- source_declared_total = 0（官方 tag 源码按可复制枚举规则发现的测试声明总数）
- configured_executable_total = 0（当前 OHOS 配置实际实例化的独立可执行用例）
- executed_passed_total = 0，失败 0，未运行/未实例化 0
- 全量通过率：0/0（无测试可计；样例 sample.c 仅作公开 API 验证，计入消费者/专项用例口径，见下方验证结果）

## 验证结果

```bash
# CLI 功能验证（公开 API 可观察结果）
$ ssdeep -h
ssdeep version 2.8 by Jesse Kornblum ...

$ echo -n 'Hello HarmonyOS ssdeep 2.8 test' > testfile && ssdeep testfile
ssdeep,1.1--blocksize:hash:hash,filename
3:at8BPt6Wn:atM6Wn,"/storage/Users/currentUser/tmp/ssdeep-testfile.txt"

# 库 API 示例（sample.c 链接 libfuzzy）
$ clang sample.c -lfuzzy -o sample && ./sample
Hashing buffer / Hashing file / MATCH: score = 99 (exit=0)
```

## 交付物

| 文件 | 说明 |
|------|------|
| usr/local/bin/ssdeep | CLI 工具（静态链接 libfuzzy.a，51KB） |
| usr/local/lib/libfuzzy.so.2.0.0 + .a + .la | fuzzy 哈希库 |
| usr/local/include/fuzzy.h | 公开头文件 |

## 注意事项

- ssdeep 是 CLI 工具 + 库双产物（R38：软件级 commands.json 必需）
- 版本号 2.8 与上游 tag release-2.8 对应，分支 feat/ssdeep-release-2.8
- tarball 无 m4/ 宏目录 + config.guess 过旧是 2012 老 autotools 项目通病，同类库可直接沿用 libtoolize+autoreconf+新版 config.guess 三板斧
---

## 对话记录

### 对话 #1
- 2026-09-16 23:41 init-build：从官方 tag release-2.8 下载（SHA-256 3485a8dc…6134d 核验一致），创建 .orig/.work
- 2026-09-16 23:42 lang-preflight：检测语言 cpp，匹配通过
- 2026-09-16 23:43 configure 失败（config.guess 2005 版无法识别 HarmonyOS）→ 替换 2023/2024 版 config.guess/config.sub
- 2026-09-16 23:44 make 触发 autotools 重生成链失败（tarball 缺 m4/ 宏）→ libtoolize + autoreconf 重建
- 2026-09-16 23:58 configure + make + make install 全部通过，ssdeep CLI 实际运行产出 fuzzy hash
- 2026-09-17 00:01 上游测试枚举：无独立用例（R51 台账已记录）；sample.c 编译运行 OK
- 2026-09-17 00:06 HarmonyOS 专项测试 9/9 通过（确定性/文件哈希/相似度/CLI 管线）
- 2026-09-17 00:12-00:15 conan-verify：G2 首跑失败（source() 未导出 patches）→ export_sources 补 copy patches/* → G0-G4 全过
- 2026-09-17 00:20-00:29 finish：W3 本地 CI .ci-result.json exit_code=0；submit 就绪 4 项补齐（test-report.md/packaging/.staging-verified/build-closed）

## 知识候选台账（path B 判定）

### 候选 1：2012 老 autotools tarball 无 m4/ 宏目录 + 2005 版 config.guess

- 真实错误：configure "cannot guess build type"（config.guess 2005-12-13 不认识 HarmonyOS）
- 真实错误：make 触发 autotools 重生成链失败（aclocal-1.12/automake-1.12 缺失；autom4te 打不开 m4/libtool.m4，aclocal.m4 引用 m4/*.m4 但 tarball 未打包 m4/）
- 根因：2012 老 autotools 工程 tarball 未打包 m4/ 宏目录；config.guess 过旧无 __OHOS__ 分支
- 修复：新版 config.guess/config.sub 整体替换 + `libtoolize --copy --force` 补齐 m4/*.m4 + `autoreconf -fi` 重建；Conan 配方内 source() 复制 vendored autotools、export_sources 导出 patches/*、build() 把 autotools 依赖时间戳设为过去阻止 maintainer 重生成
- 验证：configure/make/make install 通过；conan create G2 通过（见 conan-verify-report）
- 适用范围：scripts/patch-autotools-ohos.pl 缺失或不适用的老 autotools 工程（2010s tarball 不带 m4/ 或源码仓库 git tag 不含生成文件）

### 候选 2：conan source() 需随配方导出 patches/autotools 修复文件

- 真实错误：conan-verify G2 首跑失败——source() 复制 config.guess 失败（verify 用 cache 内 source，未 export_sources 的 patches 不可见）
- 根因：export_sources() 未导出 patches/*，只导出 conandata.yml/conanfile.py
- 修复：export_sources() 中 `copy(self, "patches/*", ...)`（babeltrace 1.5.11 同法）
- 验证：export_sources 补丁后 G2 PASS

### 候选 3：fuzzy_compare 短/重复内容得分语义（测试设计）

- 真实现象：44B 短输入相同摘要 score=19、16KB 重复内容相同摘要 score=0；8KB 内容丰富输入相同=100、单字节扰动=99、无关=0
- 根因：score_strings 基于编辑距离 + SPAMSUM 长度缩放；eliminate_sequences 削短重复序列；has_common_substring(≥7) 对短串失败
- 修复/应对：测试采用内容丰富大输入验证真实语义（专项测试 9/9 已按此设计）
- 适用范围：任何使用 fuzzy_compare 断言相似度的测试设计

### 四范围查重（index.tsv / doc / graph / drafts）

| 候选 | 命中条目 | 覆盖情况 |
|------|---------|---------|
| 1 | E007/E160（config.guess 无法识别 HarmonyOS，patch-autotools-script）；E041（automake 版本不匹配重生成，bypass）；E059（aclocal placeholder）；E514/E521（libtoolize）；DRAFT-6048（babeltrace 六类坑含 timestamps 阻止重生成）；DRAFT-E564（旧式 config.guess 换锚点） | 部分覆盖：E007/E160 覆盖"config.guess 不认识 OHOS"（其方案是 perl 补丁或 sed 加分支）；E041 覆盖"重生成链"但方案是 /bin/true 绕过；DRAFT-6048 覆盖 umask/timestamps；**未覆盖**：tarball 无 m4/ 目录时 libtoolize 补齐 + autoreconf 重建的整体可复制链 |
| 2 | DRAFT-6048（babeltrace）| 部分覆盖：babeltrace 配方同法；export 缺失导致 G2 失败的显式教训未单列 |
| 3 | 无 | 未命中（库 API 语义，非编译模式） |

### 七轴查重（候选 1 为主线）

| 轴 | 结论 |
|----|------|
| exact_duplicate | 否——无条目完整描述"无 m4/ + 旧 config.guess → libtoolize+autoreconf 重建 + timestamp 阻止重生成"链 |
| causal_duplicate | 部分——E007/E160 同因（config.guess 过旧）；E041/DRAFT-6048 同因（重生成链）；但"m4 目录缺失导致 aclocal.m4 引用文件不存在"这一具体根因未被现有条目单列 |
| trigger_overlap | 高——E007/E160（configure 查询 build type）、E041/DRAFT-6048（make 触发重生成）触发器相同 |
| solution_overlap | 中——E007 用 patch-autotools-ohos.pl 补丁；E041 用 ACLOCAL=/bin/true 绕过；DRAFT-6048 用 timestamps 阻止；本候选组合"libtoolize + autoreconf + vendored 替换 + timestamps"四合一 |
| combination_novelty | 有——移植可复制的 4 步链（替换 config.guess/sub → libtoolize 补 m4 → autoreconf 重建 → timestamps 阻止重生成）作为老 autotools Conan 适配标准动作 |
| boundary_novelty | 有——明确边界：仅适用"tarball 自含 configure 但缺 m4/"形态；已含 m4/ 或源码仓库 tag 的工程不需要 autoreconf 重建 |
| test_migration_novelty | 不适用（无测试迁移） |

### 关系字段

- similar_to: E007, E160, E041, E514, DRAFT-6048, DRAFT-E564
- caused_by: -（无已知条目由本候选导致）
- prerequisite_of: -（无下游条目）
- conflicts_with: -（E041 的 /bin/true 绕过与新链不冲突，属替代方案）

### 路径决定

**new_draft（path B）**：候选 1 已验证、可跨库复用、四范围查重为部分覆盖且存在组合/边界新增差异，
按任务要求建立同 stem 的 .md/.kv 草稿。候选 2 合并进同一草稿（配方导出要点）。
候选 3 属库 API 语义，不进知识图谱（测试设计已在 notes.md/test-report.md 沉淀）。
草稿：`knowledge/drafts/DRAFT-ssdeep-oldautotools-m4-config-guess-chain.kv`（+ .md 同 stem）。

**编译结束**: 2026-09-17 00:29
**最终状态**: built

---

## R02 知识候选台账（R40 分支名门禁）

### 候选 4：上游 tag 名（release-2.8）与 Conan 包版本（2.8）不一致 → R40/L0n 分支名门禁失败

- 真实错误（远端 CI build #49031, conan-build-test）：L0n R40 分支名校验失败（branch_name_r40）：
  分支 'feat/ssdeep-release-2.8'（去前缀后 'ssdeep-release-2.8'）不包含包名-版本号 'ssdeep-2.8'；exit code 1。
- 根因：R01 任务版本 slug 使用上游 tag 名 release-2.8 生成分支 feat/ssdeep-release-2.8，
  而 Conan 包版本为 2.8（archives/s/ssdeep/2.8/、manifest version "2.8"、commands.json versions.2.8），
  R40 要求分支必须以 包名-版本号 结尾。
- 修复：`git branch -m feat/ssdeep-2.8`（同一 HEAD，未执行强制推送、变基或合入操作）→ push 新分支 →
  PR #10456 关闭（GitCode 不支持改源分支，注明原因）→ 同标题正文新 PR #10508 → 触发一次 /rebuild。
- 验证：远端 CI 复验 R40（待 CI 结果；本地 git worktree list 唯一性 1、分支名 feat/ssdeep-2.8 已确认）。
- 适用范围：任何"任务版本 slug 从上游 tag 名推导"导致分支名与包版本不一致的库；
  分支 slug 必须以 Conan 包版本号（version 目录）为准，而不是上游 tag 字符串。

### 四范围查重（R40 候选）

| 范围 | 命中条目 | 覆盖情况 |
|------|---------|---------|
| index.tsv/graph | E416（conan slug 大小写/L0m-5）、E470（上游 version 与 tag 不一致，tag 为 provenance 源）、E527（无关，broadway） | 部分覆盖：E470 讲"配方 version 滞后 tag"（取 tag 为准）；本候选相反——版本以包 version 目录为准、分支 tag 名是错的 |
| doc/ | E416.md | 部分：slug 规范化概念，未覆盖"分支名 = 包名-版本号 门禁 + tag 名误用" |
| drafts/ | DRAFT-hfsm2-beta73-uppercase-tag-version-slug（大写 tag→小写 slug 三处同步）、E563-draft-A465（单字符版本/L0n 分支门禁）、E999-draft-35E4（大写版本 slug 小写化+分支三处一致） | 部分覆盖：E563/E999/hfsm2 覆盖"版本 slug 与分支一致性"家族，但均为"版本含大写/单字符→slug 小写化/归一化"；本候选是"分支误用上游 tag 名（release- 前缀）而非版本号"→R40 分支名门禁，触发机制与修复动作（branch -m + PR 重建）未被单列 |

### 七轴查重（候选 4）

| 轴 | 结论 |
|----|------|
| exact_duplicate | 否——无条目描述"分支用 tag 名（release-2.8）导致 R40 门禁失败，需 branch -m 为包名-版本号" |
| causal_duplicate | 部分——E470（tag vs version 不一致）、E563/E999/hfsm2（slug 与分支一致）同因族；但"tag 前缀（release-）被带入分支名"这一具体成因未覆盖 |
| trigger_overlap | 中——L0n/R40 分支名门禁在 E563（单字符版本场景）提及；本候选是"分支名与版本号不匹配"另一形态 |
| solution_overlap | 中——E563/E999 均含"分支 feat/<pkg>-<ver-slug>"动作；本候选新增"已推分支改名 + PR 源分支不支持改 → 关闭重建同标题正文 PR + /rebuild"完整闭环 |
| combination_novelty | 有——分支名必须取自 Conan 包版本（version 目录）而非上游 tag 字符串；改名→重建 PR→rebuild 的 R40 修复链可跨库复用 |
| boundary_novelty | 有——明确边界：仅当上游 tag 名 ≠ Conan 版本 slug（如 release-前缀/tag 带额外标识）且分支已创建推送时才触发；新库首次建分支直接以版本号命名可完全避免 |
| test_migration_novelty | 不适用（无测试迁移） |

### 关系字段

- similar_to: E470, E416, E563-draft-A465, E999-draft-35E4, DRAFT-hfsm2-beta73-uppercase-tag-version-slug
- caused_by: -（无已知条目由本候选导致）
- prerequisite_of: -（无下游条目）
- conflicts_with: -（与 slug 家族无冲突，互为分支命名规范补充）

### 路径决定（R40 候选）

**new_draft（path B）**：候选 4 已验证（远端 CI R40 实测失败 + 本地修复链路真实执行）、可跨库复用、
查重为部分覆盖且存在组合/边界新增差异，建立同 stem 草稿
`knowledge/drafts/DRAFT-ssdeep-branch-slug-from-package-version.kv`（+ .md）。
DRAFT-ssdeep-oldautotools-m4-config-guess-chain 草稿保持不动。

**R02 最终状态**: in-progress（等待本地门禁复核与终态回传）

---

## R03 知识候选台账（configure config.status 临时目录 Permission denied）

### 候选 5：config.status `umask 077 && mktemp -d "./confXXXXXX"` 0700 私有临时目录在 CI 构建目录写入 EACCES

- 真实错误（远端 CI PR #10508, conan-build-test）：`./config.status: line 871: ./confGJNPjp/subs1.awk: Permission denied` / `config.status: error: could not setup config files machinery`（L0 全过，L1 conan create failed，exit 1）
- 根因：autoconf config.status 用 `umask 077 && mktemp -d "./confXXXXXX"`（或 `tmp=./conf$$-$RANDOM`）在当前构建目录建 0700 私有临时目录，随后 `echo 'BEGIN {' >"$ac_tmp/subs1.awk"` 写入；CI worker 构建目录（conan cache p/b/... 类路径）对新建 0700 私有临时目录内写入拒绝（HMDFS 语义）；同源问题还影响 configure 编译 conftest 时 clang 写 $TMPDIR 临时文件
- 修复（本配方内，参照 libgsf/abiword E114）：build() 预建可写目录（tempfile.gettempdir()/ssdeep-ac-tmp）、设 TMPDIR/TMP/TEMP、把 configure 内嵌 config.status 模板 `ac_tmp=$tmp` 改指该目录、trap 删除动作改为仅透传退出码
- 验证：CI 等价路径（conan cache p/b）实测补丁后 configure exit=0；conan-verify G0-G4 全 PASS；W3 exit_code=0（.ci-result.json log_sha256 f4c2e36f…）
- 适用范围：所有 autotools 工程在 OHOS CI conan 缓存构建目录（HMDFS 语义）上跑 configure 的场景

### 四范围查重（候选 5）

| 范围 | 命中条目 | 覆盖情况 |
|------|---------|---------|
| index.tsv/graph | **E110/E112/E114/E118**（error_signature 逐字匹配 `can't create ./confXXXXXX/subs1.awk: Permission denied`/`could not setup config files machinery`，rec_approach=bypass-mktemp/use_alternate_build_dir/patch-script）；E011（umask 077）；E052（modify_tmpdir）；E060（use-tmpfs）；E125（relocate-build-dir）；E129（sed-replace）；E136（TMPDIR/patch-script） | **完整覆盖**：首错、根因（HMDFS 0700 setgid 临时目录）、方案（预建目录+改 tmp/ac_tmp+TMPDIR）全部已有专条 |
| doc/ | E110.md/E112.md/E114.md/E118.md 等 | 完整覆盖，方案文档在位 |
| drafts/ | DRAFT-6048-babeltrace、DRAFT-hogweed-3.9.1、DRAFT-buildtorrent-0.9.1（autoconf-umask-tmpdir）等 | 已覆盖同类修复链 |
| recipes（实现先例） | archives/a/abiword-plugin-*/3.0.8/conanfile.py（E114 同款 ac_tmp+TMPDIR 补丁）、libgsf 配方 | 本修复直接复用同款实现 |

### 七轴查重（候选 5）

| 轴 | 结论 |
|----|------|
| exact_duplicate | **是**——E110/E112/E114/E118 与本候选错误签名逐字一致，方案同（bypass-mktemp / ac_tmp 改指） |
| causal_duplicate | 是——HMDFS 对 mktemp 0700 setgid 临时目录写入限制，同因 |
| trigger_overlap | 高——config.status mktemp/subs1.awk 触发器完全一致 |
| solution_overlap | 高——预建目录+TMPDIR+tmp/ac_tmp 改指，与 E114/abiword/libgsf 同款 |
| combination_novelty | 无——本候选是已有条目组合的又一遍落地，无新增组合 |
| boundary_novelty | 无——边界（OHOS CI conan 构建目录 HMDFS）已被 E110/E112/E114/E118/E125 覆盖 |
| test_migration_novelty | 不适用 |

### 关系字段

- similar_to: E110, E112, E114, E118, E011, E052, E060, E125, E129, E136
- caused_by: -；prerequisite_of: -；conflicts_with: -

### 路径决定（候选 5）

**path_a_no_knowledge（复用已有条目）**：候选 5 被 E110/E112/E114/E118 等完整覆盖（exact_duplicate=是），
修复直接复用 abiword/libgsf 的 E114 同款实现；按任务规则"已有条目完整覆盖则复用并走路径 A，不得为凑路径 B 拼接条目"，
**不新建草稿**。R01/R02 已建草稿（DRAFT-ssdeep-oldautotools-m4-config-guess-chain、DRAFT-ssdeep-branch-slug-from-package-version）保持不动。

**R03 最终状态**: in-progress（等待原子性审计与终态回传）
---

**编译结束**: 2026-09-17 16:42
**最终状态**: built
