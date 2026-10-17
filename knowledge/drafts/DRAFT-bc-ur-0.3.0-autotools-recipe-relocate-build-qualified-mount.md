# DRAFT-bc-ur-0.3.0-autotools-recipe-relocate-build-qualified-mount — autotools 配方级自动修复：构建目录文件系统不保留 POSIX 0700/exec 语义时探测合格挂载点并迁移构建

> **Contributor**: pc2-34 | **Status**: DRAFT | **Updated**: 2026-09-25
> **Severity**: medium | **Category**: build-system / autotools / conan / hmdfs / permissions / recipe-pattern
> **Audience**: 任何在 OHOS HMDFS（或其它不保留 POSIX 权限位的文件系统）上以 Conan + autotools 构建三方库、且构建工作区由 CI 框架固定在 HMDFS 的适配工程师
> **Stem**: DRAFT-bc-ur-0.3.0-autotools-recipe-relocate-build-qualified-mount（与同名 .kv 配对，字段逐一对齐）

## 问题（Symptom）

bc-ur 0.3.0 的远端 CI L1 三次以同一首错失败（R01/R02/R03）：

```text
./config.status: line 604: ./conffHojbF/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
bc-ur/0.3.0: Error in build() method — autotools.configure() — ConanException: Error 1
```

CI 构建工作区固定位于 `/storage/Users/currentUser/.cache/conan2/p/b/...`（OHOS HMDFS 用户存储）。R02 的"修复"（本机把 CONAN_HOME/TMPDIR 迁移到 tmpfs）只改变执行端本机环境，CI 环境未受影响 → 同一 EACCES 复现。

## 根因（Root Cause）

autoconf 生成的 config.status 以 `(umask 077 && mktemp -d ./confXXXXXX)` 创建 **0700 临时目录**（`ac_tmp=./conffHojbF`），随后在其中写/读临时 awk 脚本 `subs1.awk`（config.status L604-694）。OHOS HMDFS **不保留/不允许 POSIX 权限位**：

- 本机取证：`umask 077 && mktemp -d ./confXXXXXX` 在 HMDFS 上创建出的目录被归一化为 `2771`（非 0700），脚本 700 → `760`（chmod 被忽略）；
- 严格 HMDFS 设备（CI）：对 0700 语义目录内的写入直接 `EACCES`（Permission denied）；
- 对照：tmpfs（`/data/storage/el2`）严格保留 `0700/700` 语义，`stat` 实测 `drwx------ 700`，写入与执行均正常。

既有知识全部覆盖"手动/补丁"手段：E060（use-tmpfs-workaround：runner 在 tmpfs 构建）、E125（relocate-build-dir：runner 把源码移到 HMDFS 外）、E011（edit-umask-in-configure：改 configure 脚本 umask）、E112/E114（bypass-mktemp）、E118（patch-script）、E052（modify_tmpdir）、DRAFT-6507-cln-mktemp-0700-hmdfs（configure 层 mkdir -m 0777）。**均未提供随库自包含、不依赖 runner 配合的配方级自动方案**——CI 的 CONAN_HOME/工作区由框架固定，runner 手段在真实 CI 上无法由执行端落地。

## 方案（Solution）

在 conanfile.py 中实现**配方级自动探测 + 迁移**（随库交付，CI 环境无需任何 runner 配合）：

1. `_build_folder_needs_relocation()`：在 `self.build_folder` 内 `os.mkdir(probe, 0o700)` + `stat` 实测模式（`!= 0o700` 即 HMDFS 归一化特征）+ 写入并 `./x.sh` 执行探测；任一异常 → 判定需要迁移（R49 警示的 `os.access(X_OK)` 探测在 HMDFS 上恒 False，因此用 mkdir+stat+exec 实证而非 access）。
2. `_relocated_work_dir()`：候选合格挂载点（`/data/storage/el2/base`、`/data/local/tmp`、`/storage/External`、`/storage/userExternal`）逐一以 `mkdir 0700 + stat drwx------ 700 + ./x.sh` exec 探测；合格后建立**专用构建根** `<base>/.bc-ur-build-<pid>`（0700）并把源码复制到 `<根>/src`（in-source，兼容手写 Makefile install 裸名头文件约束），返回 src 路径。
3. `build()`：需要迁移且找到合格目录时，用 `env="conanbuild"` 在迁移目录执行与 Autotools helper **完全一致**的命令（configure_args 从 `conanbuild.conf` 读取）：`./configure <args>` → `make -j1`；否则回退 `Autotools(self)` 原位构建（并输出警告，无合格挂载点时不阻塞交付流程）。
4. `package()`：迁移构建时 `make install DESTDIR=<package_folder>`，随后仅清理**专用构建根**（守卫 `basename.startswith(".bc-ur-build-")`，绝不触碰挂载根本身——R03 曾误删挂载根子目录，教训记录于此）。
5. 探测与迁移均需"无合格挂载点回退原位 + 文档记录恢复条件"。

bc-ur 0.3.0 实测：CONAN_HOME 指向 **CI 等价 HMDFS 路径**（`.cache/conan2`）时，build() 探测到非 0700 语义 → 迁移到 `/data/storage/el2/base` tmpfs → `config.status` 成功生成全部 Makefile（无 Permission denied）→ conan-verify G1-G4/L2/L4/L5 全过 → test_package 消费者 + 鸿蒙专项 ALL PASSED → W3 本地 CI 模拟通过。

## 适用边界与反例（Boundary & Counter-examples）

- **适用**：构建工作区固定在 HMDFS（或任意不保留 POSIX 权限位文件系统）上、且设备存在可写 tmpfs/ext4 合格挂载点的 autotools（或任何使用 config.status/mktemp 0700 临时目录）库；配方可整体复制。
- **反例（不适用）**：
  - 保留 POSIX 权限语义的常规 Linux/容器环境（探测返回 False → 原位构建，配方行为不变）。
  - 设备无任何合格挂载点时（探测全失败 → 回退原位，按既有平台约束记录恢复条件）。
  - 构建系统为 CMake/Meson 且无 config.status 类临时目录机制的库（无需此迁移）。
  - 纯 runner/CI 侧可改工作区位置的场景：优先按 E060/E125 由框架调整（本方案是 runner 手段之外的库内兜底）。

## 查重结论（四范围）

| 范围 | 命中 | 说明 |
|---|---|---|
| index.tsv ↔ graph/*.kv | E011（umask 补丁）、E052（modify_tmpdir）、E060（use-tmpfs-workaround）、E110（use_alternate_build_dir）、E112/E114（bypass-mktemp）、E118（patch-script）、E125（relocate-build-dir）、E273（conan cache 可重定位，PETSc 域） | 均为 runner/配置补丁手动手段；无"配方内自动探测 + 迁移"条目 |
| knowledge/doc/ | E011/E052/E060/E110/E112/E114/E118/E125 文档 | 同上，均为手动手段 |
| knowledge/graph/ | 同 index | 无配方级方案 |
| knowledge/drafts/ | DRAFT-6507-cln-mktemp-0700-hmdfs（configure 层 mkdir -m 0777）、DRAFT-audacious-buildsys-in-source-static-chain（in-source，不同触发） | 无配方级自动探测迁移 |

**七轴查重**：
- exact_duplicate: false（无"配方 build() 自动探测迁移"签名条目）
- causal_duplicate: partial（E060/E125 同根因家族：HMDFS 权限位）
- trigger_overlap: high（config.status subs1.awk EACCES 同签名）
- solution_overlap: partial（E060/E125 为 runner/手动 relocate；本方案为配方内自动探测+迁移，机制新增）
- combination_novelty: true（"配方自包含探测 0700 语义 + 迁移合格挂载点 + 回退兜底"组合无既有条目）
- boundary_novelty: true（边界=探测 mkdtemp 0700 语义；反例=保留权限位的常规环境自动原位）
- test_migration_novelty: true（bc-ur 在 CI 等价 HMDFS CONAN_HOME 下复验全绿 + 消费者/鸿蒙专项 2/2）

**关系字段**：`similar_to`: E060, E125, E011, E052, E110, E112, E114, E118, DRAFT-6507-cln-mktemp-0700-hmdfs；`caused_by`: HMDFS 不保留 POSIX 权限位（0700→2771/760 归一化或 EACCES）；`prerequisite_of`: 无；`conflicts_with`: 无。

**路径判定**：**B（知识库扩展）** — 候选已验证（CI 等价路径复验全绿）、可跨库复用（配方级模式可整体复制）、四范围查重未命中且存在新增差异（配方自动探测迁移机制），建立同 stem .md/.kv 草稿对，随 bc-ur 归档同一 PR 交付。

## 验证（Verification）

1. 取证：HMDFS 上 `umask 077 && mktemp -d ./confXXXXXX` → 目录归一化 2771、脚本 760；tmpfs → 严格 0700/700（`stat` 实测 + exec 探测通过）。
2. `conan create`（CONAN_HOME=`.cache/conan2`，HMDFS 构建工作区，CI 等价）→ build() 探测非 0700 → 迁移 tmpfs → `config.status: creating Makefile / src/Makefile / test/Makefile / config.h`（无 Permission denied）→ G1-G4/L2/L4/L5 全过。
3. test_package：`bc-ur consumer test: ALL PASSED`、`bc-ur ohos test: ALL PASSED`。
4. W3 本地 CI 模拟（finish）：通过，`.ci-result.json` exit_code=0（本机 W3 harness 需 `TMPPREFIX=/可写目录`，zsh heredoc 临时文件默认 `/tmp/zsh` 落在只读 /tmp——本机运行环境观察，非库交付知识，随本库台账申报）。
