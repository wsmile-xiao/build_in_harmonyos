# Knowledge Candidate Ledger — tar 1.35

**路径初判**: A（常规基础适配，复用既有知识）— 核心适配点全部命中既有知识库，无新增可跨库复用知识价值
**task**: tar-1.35-r01-pc3-13-20260911T082155Z
**日期**: 2026-09-11
**前置说明**: 任务头 `knowledge_candidate_observation: required`，本台账为候选观察记录；未提前创建草稿，未修改任何知识库文件。

## 候选台账

### C1: config.guess/config.sub 不识别 HarmonyOS/ohos 三元组

- **真实错误**: `./build-aux/config.sub aarch64-unknown-linux-ohos` → `Invalid configuration ...: OS 'ohos' not recognized`；config.guess 无 HarmonyOS 分支（初始 grep ohos=0）。
- **根因**: GNU config.guess/config.sub（2023-07-18 tar 1.35 自带版本）不包含 OHOS 检测分支与 ohos OS 接受项。
- **修复**: 补丁 `0001-build-aux-config.guess.patch`（UNAME_MACHINE:UNAME_SYSTEM=HarmonyOS 分支 → `${MACHINE}-unknown-linux-ohos`）+ `0002-build-aux-config.sub.patch`（`-ohos*` OS 别名 + `ohos*` 基础 OS 接受列表 + `linux-ohos*` 内核-OS 校验）。补丁后 `config.sub aarch64-unknown-linux-ohos` 返回正常三元组。
- **验证**: `./build-aux/config.sub aarch64-unknown-linux-ohos` → `aarch64-unknown-linux-ohos`（exit 0）；configure 全程通过（logs/02-configure.log）；交叉编译产物 `file bin/tar` = `ELF 64-bit LSB arm64 ... /lib/ld-musl-aarch64.so.1`。
- **适用范围**: 所有 autotools 项目在 OHOS 交叉编译的第一道门槛。
- **查重结果（七轴）**:
  - `exact_duplicate`: **是** — E007（patch-autotools-script，config.guess/sub HarmonyOS 识别）错误签名 `Invalid configuration.*ohos|OS ohos not recognized`、根因、方案与本候选完全一致。
  - `causal_duplicate`: 是 — 同一根因（GNU 脚本缺 OHOS 分支）同一修复。
  - `trigger_overlap`: 是 — 触发工具 configure/autotools、错误文本逐字命中 E007 签名。
  - `solution_overlap`: 是 — E007 推荐 patch-autotools-script 即 config.guess 两处 + config.sub 三处修改，与本补丁同构。
  - `combination_novelty`: 否 — 无新增组合（仅 E007 单点）。
  - `boundary_novelty`: 否 — E007 affected_scope 已注明"所有 autotools 项目（鸿蒙编译第一道门槛）"。
  - `test_migration_novelty`: 否 — 无测试迁移差异。
- **结论**: 完整重复，复用既有 E007，不建草稿。

### C2: HMDFS 上 autotools configure/config.status umask 077 临时目录权限失败

- **真实错误**: `./config.status: line 629: ./confFpgkCg/subs1.awk: Permission denied`；`config.status: error: could not setup config files machinery`（configure exit 1）。
- **根因**: configure/config.status 用 `(umask 077 && mktemp -d "./confXXXXXX")` 创建临时目录，HMDFS UID 映射/权限语义下 0700 目录对当前进程不可写，subs1.awk 写入失败。
- **修复**: 补丁 `0003-configure.patch`：configure 与 config.status 中 5 处 `umask 077` → `umask 022`（对应 E011 edit-umask-in-configure）。
- **验证**: 补丁后 configure 成功生成全部 Makefile/config.h（logs/02-configure.log `CONFIGURE_EXIT=0`）；conan create 干净构建通过。
- **适用范围**: 所有 autotools 项目在 HMDFS 上 configure 时。
- **查重结果（七轴）**:
  - `exact_duplicate`: **是** — E011（edit-umask-in-configure）错误签名 `umask 077.*mktemp|cannot create.*subs[0-9]*\.awk.*Permission denied` 与本错误逐字命中。
  - `causal_duplicate`: 是 — HMDFS UID 映射 + umask 077 同根因。
  - `trigger_overlap`: 是 — 触发工具 configure|config.status、阶段 configuration 一致。
  - `solution_overlap`: 是 — E011 方案 edit-umask-in-configure 即本补丁做法（077→022）。
  - `combination_novelty`: 否。
  - `boundary_novelty`: 否 — E011 affected_scope 已含"所有使用 autotools 的项目在 HMDFS 上"。
  - `test_migration_novelty`: 否。
- **结论**: 完整重复，复用既有 E011，不建草稿。

### C3: CLI 工具软件级 commands.json 声明（R38/L0k）

- **真实错误**: W3 本地 CI `L0_RESULT=fail: gate failed: commands_json_r38`（构建产物含 bin/tar 可执行文件但软件级目录无 commands.json）。
- **根因**: tar 是 CLI 工具（package_type=application，bin/tar 产物），R38 要求软件级 `archives/t/tar/commands.json` 声明。
- **修复**: 创建 `archives/t/tar/commands.json`（type=tool、versions.1.35.ref=tar/1.35、binary=true）。
- **验证**: 复跑 build_and_test.sh 后 L0k/R38 门禁通过（见 W3 复验日志）。
- **查重结果（七轴）**: `exact_duplicate` **是** — E424（add-software-level-commands-json，R38/L0k CLI 声明）方案一致；E255 亦含 commands.json 关键词。其余六轴均为是/否、无新增差异。
- **结论**: 完整重复，复用既有 E424，不建草稿。

### C4: OHOS 用户 uid（20001006）超出 ustar/v7 21-bit octal 字段容量导致上游 v7/ustar 测试失败

- **真实错误**: `tar: value 20001006 out of uid_t range 0..2097151`（create.c `UID_TO_CHARS` 失败）；testsuite 82/93 失败用例为该错误（测试强制 `-H v7`/`TEST_TAR_FORMAT=v7|ustar`）。
- **根因**: 执行环境用户 uid=20001006（HMDFS UID 映射）> ustar/v7 头字段 21-bit octal 上限 2097151；GNU tar 默认/gnu/posix 格式用 base-256/xheader 可正常存储（实测 exit 0），仅 v7/ustar 格式受格式容量限制。属上游格式定义 + 环境 uid 空间特性，非 tar 适配缺陷。
- **处理**: 如实列入测试台账失败分类（UIDRANGE 82 项，含首错/命令/退出码/恢复条件）；鸿蒙专项测试验证默认格式大 uid 往返通过。未修改上游行为（v7/ustar 字段容量为格式规范，改写将破坏格式兼容）。
- **适用范围**: OHOS 大 uid 环境下运行 GNU tar 上游 testsuite 中强制 v7/ustar 的用例。
- **查重结果（七轴）**: 四范围检索（graph/E*.kv、doc/E*.md、drafts/、index.tsv）关键词 `2097151|out of.*range.*uid|uid_t range|base-256|octal.*uid` **全部 0 命中**；`exact_duplicate`/`causal_duplicate`/`trigger_overlap`/`solution_overlap`/`combination_novelty`/`boundary_novelty`/`test_migration_novelty` 七轴均无既有条目可对照 → **未命中**。
- **判断**: 该候选是环境/格式限制观察，非可跨库复用的修复方案（无代码修复动作，仅记录测试分类口径）。未证明新增知识价值（无可复用的修复方案与验证动作），按任务规则**路径 B 不成立**；仅作为候选观察记录在台账。

### C5: HMDFS 上 tar --xattrs 对目录 fgetxattr 返回 EINVAL

- **真实错误**: `tar: dir: Warning: Cannot fgetxattr: Invalid argument`；`getfattr: getxattr failed: Invalid argument`（xattr 类测试 9 项失败）。
- **根因**: HMFS 文件系统目录 xattr 语义（listxattr 返回 security.hmmac/security.selinux 等条目但 getxattr 对部分条目返回 EINVAL），平台文件系统特性；文件级 user.* xattr 实际可用（python os.setxattr 探测通过）。
- **处理**: 如实列入测试台账失败分类（XATTR 9 项，含首错/命令/退出码/恢复条件）。
- **查重结果（七轴）**: 四范围检索 `fgetxattr|setxattr.*EINVAL|xattr.*Invalid|xattr.*HMDFS|--xattrs` **0 命中** → 未命中。
- **判断**: 平台文件系统限制观察，无跨库可复用修复方案（不改上游、不伪造环境），**路径 B 不成立**；仅作候选观察记录。

## 路径决定

- C1/C2/C3 完整重复 → `reuse_existing`（复用 E007/E011/E424），符合路径 A 特征。
- C4/C5 未证明新增知识价值（平台/环境限制观察，无跨库复用修复动作）→ `path_a_no_knowledge`，路径 B 不成立（证据见上）。
- **最终决定**: **path_a_no_knowledge**（路径 A）— 无 new_draft 草稿创建。PR 前缀保持任务头指定的【高难度挑战】。
- 知识草稿 `.md/.kv`：**未创建**（本任务无满足路径 B 条件的候选）。
- 关系字段: C4 `similar_to`（无）、`caused_by`（OHOS 用户 uid 空间 + ustar 格式规范）、`prerequisite_of`（无）、`conflicts_with`（无）；C1/C2 `similar_to` E007/E011。
