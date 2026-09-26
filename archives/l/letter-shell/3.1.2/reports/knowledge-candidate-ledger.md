# 知识候选台账 — letter-shell 3.1.2（R01，pc4-17）

> 任务路径判定：`task_type: 知识库扩展`（B）。每项候选记录真实错误、根因、修复、
> 验证、适用范围与四范围查重（正式知识 knowledge/graph/E*.kv、doc/、草稿
> knowledge/drafts/、图谱 index.tsv）。

## 候选清单

### C1: W3/JC5 full 模式命中其他库基线文件（cloog/kics 空标记）

- **真实错误**：`finish` step [5/10] W3 本地 CI 被 JC1/JC5 拦截：
  `archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、
  `archives/k/kics/2.1.20/.staging-verified`（JC_ERRORS=2，blocked_by_JC）。
- **根因**：junk_check.sh 在 full 模式（零提交新库分支，`git diff origin/main...HEAD`
  为空 → 回退 `git ls-files` 整仓扫描）按 **git index** 扫描 archives 隐藏文件；
  上述文件已被其他库（cloog 906cc59ae7、kics d9489aee83）提交进 main 且为空 blob
  （sha256 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855），
  gitignore 不豁免已跟踪文件。
- **修复**：记录路径+SHA-256 → `git rm --cached` 临时取消跟踪 → 复跑完整
  `finish`（W3 通过）→ `git add -f` 恢复（gitignore 拒绝普通 add）→ 核对恢复后
  SHA-256 一致、git status 无该路径、diff/staged/PR 不含该路径。
- **验证**：隔离后 finish 走到知识整理阶段；恢复后三文件 SHA-256 均
  e3b0c442… 一致，`git status` 干净。
- **适用范围**：共享 build_in_harmonyos 仓库零提交新库分支执行 W3/finish 且 main
  存在其他库遗留空隐藏标记的所有执行端。
- **四范围查重**：DRAFT-fastnoiselite-1.1.1-jc-full-mode-baseline-junk-isolation.kv
  完整覆盖同场景（同 cloog/kics 三文件、同 git rm --cached 隔离、同恢复审计）；
  DRAFT-dr_mp3-0.7.2-baseline-noise-isolation.kv 亦覆盖 JC3/JC5 全仓基线噪声隔离。
  **完整重复且无独立差异 → 复用既有草稿，不新建。**

### C2: GitHub 直连超时 → 使用官方 codeload 端点下载同一官方 tarball

- **真实错误**：`curl https://github.com/NevermindZZT/letter-shell/...` 与
  `ohc-run.py init-build --url=github.com` 连接超时（urllib errno 110）。
- **根因**：网络环境对 github.com 主域直连不稳定（E017 已知模式）。
- **修复**：改用官方 codeload.github.com 下载端点获取同一 tag tarball，SHA-256
  （d98d6274…20daf）与 conan 源 URL（github.com 官方 URL，R39 保持）核验一致；
  init-build 复用本地 tarball（EXPECTED_SHA256 校验）。
- **验证**：tarball sha256 与 conan create 实际下载产物一致；conan-verify G2 通过。
- **适用范围**：GitHub 主域直连超时的源码获取场景。
- **四范围查重**：E017（GitHub 超时→镜像）、E406（sha256 多路径交叉验证，
  含 codeload）、DRAFT-fastnoiselite-1.1.1-e017-codeload-ghfast-403.kv
  （codeload/ghfast）。**既有条目已覆盖，无新增差异 → 复用，不建草稿。**

### C3: 段注册型嵌入式库的消费者链接需最小链接片段（INSERT AFTER .data）

- **真实错误**：消费者链接 libletter-shell.a 时
  `ld.lld: undefined symbol: _shell_command_start/_shell_command_end`（首个
  消费者原型链接失败；随后 shellRun 执行 add 命令时因 CMD_FUNC int 参数约定
  与 main 型 argc/argv 签名不匹配产生段错误，改用 SHELL_TYPE_CMD_MAIN 后通过）。
- **根因**：letter-shell 的 SHELL_EXPORT_CMD 把命令表放入自定义 `shellCommand`
  链接段，shellInit 在 __GNUC__ 下取 `&_shell_command_start/_shell_command_end`
  边界符号；该符号只由链接脚本（上游 demo 的 shell.lds KEEP(*shellCommand)）
  提供。Conan 包消费者无该脚本时链接失败；且命令执行按 attr.type 分派：
  SHELL_TYPE_CMD_FUNC 以解析后 int 参数调用（SHELL_PARAM_FLOAT 转换），
  SHELL_TYPE_CMD_MAIN 以 (argc, argv) 调用——消费者导出命令必须按 main 型。
- **修复**：配方随包提供最小链接片段 `shellcmds.lds`
  （`SECTIONS { .shellCommand : { _shell_command_start = .; KEEP(*(shellCommand))
  _shell_command_end = .; } } INSERT AFTER .data;`），test_package 以
  `-Wl,-T,<lds>` 链接；消费者命令用 SHELL_TYPE_CMD_MAIN 导出。
- **验证**：原型链接/运行通过（add 3 4 → 7、add 10 32 → 42、mul 6 7 → 42）；
  conan create test_package 2/2 通过（test_letter-shell、test_letter-shell_ohos）。
- **适用范围**：所有使用「自定义链接段 + 段边界符号」注册机制的嵌入式 C 库
  （letter-shell 及同类段注册库）在 Conan/静态库打包下的消费者链接场景。
- **四范围查重**：index.tsv 无 `INSERT AFTER|linker fragment|shellCommand|
  _shell_command_start|KEEP(*` 顶点；doc/ 无链接片段相关内容；graph 无；
  drafts 无。**未命中 → 新建草稿（path B）。**

## 七轴查重（仅对候选 C3，走 path B 判定）

| 轴 | 结论 |
|----|------|
| exact_duplicate | 否 — 知识库无段注册链接片段条目 |
| causal_duplicate | 否 — E307 是 test_package 缺 CMake 用 profile 直编（compile-only），不涉及链接段符号；E236/E385 是 llvm-ar 归档与静态库，非消费者链接片段 |
| trigger_overlap | 低 — E307 同为 test_package 直编场景，但触发错误不同（cmake not found vs undefined section symbols） |
| solution_overlap | 低 — E307 解决编译对象，本候选解决链接段符号定义；无命令重叠 |
| combination_novelty | 有 — INSERT AFTER .data 最小片段 + 配方随包分发 + 消费者 -Wl,-T 链接 + main 型命令导出，四者组合为新增 |
| boundary_novelty | 有 — 边界明确：仅段注册型库需要；SHELL_TYPE_CMD_MAIN 与 CMD_FUNC 的调用约定差异是 letter-shell 特有 |
| test_migration_novelty | 有 — test_package 双用例（消费者 + OHOS 专项）以链接片段驱动，模式可迁移 |

## 路径决定

- **C1**：完整重复 → reuse_existing（DRAFT-fastnoiselite-1.1.1-jc-full-mode-baseline-junk-isolation.kv）。
- **C2**：既有覆盖 → reuse_existing（E017/E406）。
- **C3**：未命中且有已验证、可跨库复用（段注册库通用）的新增差异 → **new_draft
  （path B）**，建立同 stem 的 .md/.kv 草稿。
- 最终：**path_b_new_draft**（C3），与 letter-shell 归档同 PR 交付。

## 知识库条目说明

- 本包 `knowledge_gained`（manifest.yaml）三条为 letter-shell 特有（库级 notes），
  不单独建正式条目；通用部分归入 C3 草稿。
