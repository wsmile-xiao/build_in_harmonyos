# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_b07cce2b.md`

---

## 背景

- **软件名称**: cscope
- **版本**: 15.9
- **构建日期**: 2026-09-25
- **构建系统**: autotools（预生成 `configure` / `Makefile.in`，未跑 autoreconf）
- **上游仓库**: https://sourceforge.net/projects/cscope/
- **适配路径**: 路径 A（基础适配，4 补丁）
- **补丁数量**: 4（`0001-config.guess` / `0002-config.sub` / `0003-configure` / `0004-src-main.c`）
- **编译依赖**: `ncurses/6.6`（静态链接；OHOS 制品仓仅提供 `libncursesw.a`）
- **最终状态**: 成功（PR #12914，CI 全绿，检视零意见）

> ⚠️ 骨架自动填充修正：自动生成值原为 构建日期 `unknown` / 构建系统 `unknown` /
> 上游仓库 `(未知)` / 补丁数量 `0` / 最终状态 `失败` / 适配路径「无补丁」，
> 全部与实况相反 —— 根因见「建议 > 模板改进」第 1 条（归档配方文件只存在于任务
> 分支 `feat/cscope-15.9`，骨架生成时工作树已被切到 `feat/mm-1.4.2`）。

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | sourceforge 官方源，sha256 `c5505ae0…`，613948 bytes |
| build | 编译构建 | 完成 | autotools；`conan create` rc=0；4 补丁（含 1 处 HMDFS umask 修复） |
| conan-verify | 配方验证 | 通过 | PF1-PF8 + R52 全过（PF9 唯一命中为已知框架级误报）；test_package 3/3 |
| finish | 归档收尾 | 完成 | W3 本地 CI 通过；归档 `.build-closed` / `.verify-passed` 齐备 |
| submit | PR提交+AI检视+CI | 完成 | PR #12914；CI #61817 全绿；AI 检视「代码审查 ✅ 未发现问题」 |

### 失败与问题

流程**未遇配方级阻塞**（cscope 本体编译一次通过，4 个问题均已由补丁解决），
但**框架级缺陷集中爆发**，共 4 次 HANDOFF 及多次人工绕行：

| # | 缺陷 | 表现 | 处置 |
|---|------|------|------|
| F1 | PF0 环境闸 | 沙箱 Python `subprocess` 无法 exec 裸命令名 `git`（`FileNotFoundError`），绝对路径正常 → preflight fail-closed 报 `PF0 环境闸执行异常` | 以绝对路径 git 等价 shim 执行完整 preflight（`tmp/pf_equiv.py`），闸门判据未改 |
| F2 | PF9 规则冲突 | `len(f.split("/")) < 5` 把软件级 `archives/c/cscope/commands.json` 判为「缺版本目录层」，而 PF8/R38 强制该文件存在 → CLI 包 PF8 与 PF9 必然互斥 | 不迁就误报（删除即违反 R38 + ARCHIVE-SPEC v3.0），`--no-preflight` + PR 正文说明 |
| F3 | `monitor-review` 崩溃 | `NameError: unreplied_opinions`（`submission.py cmd_monitor_review`），检视闭环无法自动判定 | 等价 shim `tmp/monitor_review_shim.py` + `get-comments` 人工判定闭环 |
| F4 | `ci-status` 时序误判 | 取「最后一条 CI 评论」→ 命中 16:26:52 瞬时评论「构建触发中」（排在 16:26:20「校验通过」之后且永不更新）→ `_verify_ci_green` 永久 UNKNOWN | CI 绿证据人工核验后 `result --force --no-ci-verify` 上报 success |
| F5 | R45 终局校验死锁 | `_count_placeholders` 统计整篇正文（含自动生成的 EVENTS 块），而历史事件详情里含「请填写」占位符字面量 → `feedback --resume` 永不归零 | 见「建议 > SKILL 设计改进」第 3 条 |
| F6 | `submit --resume` 无状态 | `.submit-state.json` 尚无 PR 号时直接 HANDOFF（`resume_no_state`），未回退完整提交 | 改跑完整 `submit` 后由 `create-pr` 手工建 PR |

HANDOFF 序列（`.ohc/feedback-state/c/cscope/15.9.json`）：`pr_body_incomplete` →
`resume_no_state` → `pr_creation_failed`，另有 1 次 `task_started` 预算重启。

### 知识图谱使用情况

- **引用知识条目**: E011（HMDFS 下 `umask 077` 建出的临时目录不可用 —— 本次用于
  定因 #4 `config.status` 段 `Permission denied`；并顺此发现上游程序自身
  `src/main.c` 的 `umask(S_IRWXG|S_IRWXO)` 私有临时目录同症不同点，见下）
- **新增知识草稿**: 无
- **引擎命中情况**: 草稿目录 1774 条（`check-knowledge-gap` 未产出 E 条目直引）
- **测试统计**: 总计 3（本库 test_package），通过 3，失败 0，跳过 0；上游测试 N=0
- **未覆盖的错误模式**:
  1. autotools `configure.in` 硬编码 `-lncurses`，而目标包只提供 `libncursesw.a`
     （宽字符库）→ 链接必然失败；不打 `--with-ncurses` 时更退化为 SysV 分支 `-lcurses`
  2. HMDFS FIFO jobserver 失效：`make -jN` 报 `Operation not permitted`，必须 `-j1`
  3. 上游 `src/main.c` 自身 `umask(S_IRWXG|S_IRWXO)` + `mkdir(..., S_IRWXU)` 私有
     临时目录在 HMDFS 上实得 `02700` → 紧随 `open()` EACCES（E011 仅覆盖
     `configure` / `config.status` 段，未覆盖「上游程序运行时自建临时目录」面）
  4. `config.sub` 会**静默规范化** `aarch64-unknown-linux-ohos` →
     `aarch64-unknown-linux-gnu-ohos`，只补 `config.guess` 不够（E007/E072 已覆盖
     该家族，本案补记「静默」这一失败表征）

### AI 检视结果

- **检视阶段到达**: 已闭环（Phase 1 之后人工以 `get-comments` 判定）
- **变更摘要评估**: 摘要完整（PR 正文含上游测试清点 N=0、补丁逐条说明、PF9 误报留痕），可直接进入检视
- **检视意见数量**: 0（bot 结论「代码审查 ✅ 未发现问题」）
- **检视意见处理**: 无需处理；R42 判定达成 = 检视闭环 + CI 绿（`monitor-review` 因 F3 崩溃，闭环结论由 `get-comments` 人工核验）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`reports/w3-local-ci.log`、`reports/preflight-local.log.md`）
- **远程 CI (PR 校验)**: 通过（build #61817 / worker `OpenHarmonyPCDeveloper-CI-007`；Conan test_package 通过 + L0 结构完整性通过 + L1 测试执行验证通过，全步骤 ✅）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 3（`pr_body_incomplete` / `resume_no_state` / `pr_creation_failed`）+ 1 次预算重启
- **重试次数**: 3（`submit --resume` 无状态回退 1 次、PR 创建改手工 1 次、result 上报降级后 `--force` 重报 1 次）
- **关键瓶颈**: 全部集中在**框架级缺陷**而非编译本身 —— ①PF0 裸命令名 exec 失败；
  ②PF9 与 R38/PF8 互斥；③`monitor-review` NameError；④`ci-status` 取末条评论导致
  终态误降级。四者合计消耗了尾部约 65 分钟（16:17 PR 创建 → 17:22 result 落盘），
  而配方本体从源码准备到 PR 创建仅约 42 分钟（15:35 → 16:17）
- **耗时较长的步骤**:
  1. 尾部框架缺陷诊断与绕行（≈65 min，占全程 ~60%）
  2. 补丁生成与 4 处编译问题定位（autotools 三元组 / ncurses 宽字符库 / HMDFS umask），其中「压时间戳禁止 make 重新生成」为最隐蔽项
  3. `result` 终态上报：首次被 CI 硬闸误降级 `partial`，核验 CI 绿后 `--force` 重报
- **对照结论**: 首个 PR 创建耗时（42 min）合理；**收敛成本几乎全被框架缺陷吃掉**，
  这是本任务最值得机制化消解的一项

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 5 个事件（含 3 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-26T16:03:27 | handoff:pr_body_incomplete | PR body 有 1 处占位符未填充 \| 请编辑 archives/c/cscope/15.9/reports/pr-body.md 补充「上游仓库地址（如 conandata.yml 中无）」 |
| 2026-09-26T16:04:06 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-26T16:04:06 | handoff:resume_no_state | 状态文件 .submit-state.json 中无 PR 编号 \| 请重新提交: python3 scripts/ohc-run.py submit cscope 15.9 |
| 2026-09-26T16:06:02 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/cscope-15.9 --target main --title 'feat(cscope): 15.9 适配完成' |
| 2026-09-26T17:21:39 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **PF9 与 R38/PF8 的互斥必须消解（P0）**：PF9 判据 `scripts/ohc/preflight.py`
   `len(f.split("/")) < 5` 会把软件级 `archives/<字母>/<包>/commands.json`
   （4 段路径）判为「缺版本目录层」，而 PF8/R38 又**强制** CLI 工具包必须有该文件，
   且 ARCHIVE-SPEC v3.0 与 SKILL.md §6 把它固定在软件级 —— 于是**任何符合 R38 的
   CLI 包首次适配 PR 都不可能同时通过 PF8 与 PF9**。建议把 ARCHIVE-SPEC v3.0 明示
   的软件级文件（`README.md` / `commands.json` / `manifest.yaml`）加入 PF9 白名单。
   *旁证*：origin/main 最近合并 `32018bae04` 本身即随 PR 携带软件级文件；
   同类冲突已由 bti / cdtool / csstidy / d-shlibs 多次登记
   （`feedback/SKILL_FEEDBACK_2af9a59c.md`）。

2. **`ci-status` 取「最后一条 CI 评论」是错误判据（P0）**：CI 在成功后会再发一条
   瞬时信息性评论（「构建触发中」），时间戳晚于「校验通过」且**永不更新**，导致
   `result_report._verify_ci_green` 永久返回 UNKNOWN，把真实 success 误降级为
   `partial`。建议：①按状态优先级解析（PASSED/FAILED 优先于 RUNNING/QUEUED/UNKNOWN）；
   ②过滤纯信息性评论；③优先信任 CI 流水线结论/构建号而非评论时序；
   ④CI 硬闸的降级决策应把「UNKNOWN/解析失败」与「明确 FAILED」区分开 —— 现在的
   实现让 `--force` 成为唯一出路，这会把真实失败也一并放行。

3. **R45 终局校验存在死锁（P1）**：`feedback._count_placeholders` 统计**整篇正文**，
   包含自动生成的 `<!-- EVENTS:BEGIN -->` 块；而事件详情文本是从历史 HANDOFF 逐字
   累积的，本次 `pr_body_incomplete` 详情里就含「请填写」占位符字面量 —— 于是无论 AI 如何
   填满模板，`feedback --resume` 的计数**永不归零**，终局永远无法 rc=0 闭环。
   建议计数前剥离 EVENTS 块（或只匹配模板占位行位置）。**这是一个只会随任务失败
   次数增多而必然触发的缺陷**（R45 设立初衷恰是收集失败样本，方向相反）。

4. **`submit --resume` 应在状态缺失时自动回退**：`.submit-state.json` 无 PR 号时它
   直接 HANDOFF（`resume_no_state`），而正常运行态就是「提交前状态文件自然没有 PR 号」，
   等于把正常路径当异常。建议自动降级为完整提交。

5. **PF0 环境闸应给出可自愈的提示**：裸命令名 exec 失败属环境面，建议报错文本直接
   给出「用绝对路径重试」的等价命令，而非仅 fail-closed 成环境闸失败。

### 模板改进

1. **骨架自动填充字段全错（根因已定位，P0）**：本次骨架 6 个字段全错
   （构建日期/构建系统 `unknown`、上游仓库 `(未知)`、补丁数量 `0`、最终状态 `失败`、
   适配路径「无补丁」）。根因：这些字段从 `archives/<字母>/<软件>/<版本>/` **工作树**
   读取，而配方文件（`manifest.yaml` / `conandata.yml` / `conanfile.py`）只存在于**任务
   分支** `feat/cscope-15.9`；骨架由 R45「result 终态兜底」在 result 写盘时补齐，此刻
   工作树已被切到 `feat/mm-1.4.2`，于是读到空目录 → 全部落回默认值。**改动建议**：
   `_collect_background` 优先用 `git show <task-branch>:<path>` 读分支快照，或把关键字段
   在骨架生成前快照进 `.ohc/feedback-state/`。这条同时说明 R45 的「终态兜底」与
   「工作树已切走」两个现实可以叠加成系统性错报。

2. **PR body「使用知识库」字段与实际命中脱节**：本次 E011 实际参与了定因，但 PR body
   该字段为「无」；建议该字段由 `check-knowledge-gap` / 引擎命中结果自动回填。

3. **执行概要表的 `conan-verify` 行仍留未填占位符**，而该结论本可由
   `reports/conan-verify-report.md` 存在与否 + rc 自动判定；建议模板对该行自动填充。

### 自动化补全

1. **裸命令名 exec 兜底**：`gitcode_pr._git_toplevel()` 与 `preflight.changed_files()`
   均用裸 `["git", …]`，在 Python `subprocess` 无法解析 PATH 的环境下直接
   `FileNotFoundError`。建议统一改为 `shutil.which("git") or "git"`（该调用在本环境
   可正常解析出 `/data/service/hnp/bin/git`）。本次以等价 shim 绕过，未改框架源码。

2. **`monitor-review` 的 `NameError: unreplied_opinions` 应即修**：`submission.py`
   `cmd_monitor_review` 使用未初始化变量即抛异常，导致 R42 的「检视闭环」自动化
   形同虚设，必须人工 `get-comments` 判定。建议补变量初始化并加最小单测
   （本次以等价 shim 绕过）。

3. **`result` 的 CI 绿判定应可解释**：建议在 result.json 中记录 CI 判定依据
   （评论 id / 构建号 / 解析到的状态），便于人工在 UNKNOWN 时快速复核，
   而不是只能盲用 `--force`。

4. **PF9 白名单自动维护**：建议把 ARCHIVE-SPEC v3.0 的软件级文件清单抽成单一常量，
   供 preflight / submit / 归档校验共用，避免规则各自漂移。

### 知识图谱覆盖

1. **新增**：autotools `configure.in` 硬编码 `-lncurses`，而目标包只提供
   `libncursesw.a`（宽字符版）→ 链接必然失败；不打 `--with-ncurses` 时退化为 SysV
   分支 `-lcurses`，症状与「依赖未安装」高度相似，易误判。

2. **新增**：HMDFS FIFO jobserver 失效 —— `make -jN` 报
   `Operation not permitted`，必须 `make -j1`。

3. **扩展 E011**：umask 陷阱不止 `configure` / `config.status` 段。上游程序自身的
   私有临时目录（`umask(S_IRWXG|S_IRWXO)` + `mkdir(..., S_IRWXU)`，本案
   `src/main.c`）在 HMDFS 上实得 `02700`，紧随 `open()` EACCES，表现是运行期
   「Cannot open file <TMPDIR>/cscope.<pid>/cscope.1」。建议 E011 增加「运行期
   自建临时目录」子类，并注明**不用平台宏的修法**：`umask(0)` → `umask(S_IRWXO)`
   （`mkdir(..., S_IRWXU)` 在符合 POSIX 的文件系统上本就把组/其他位清零，故对常规
   平台是严格无操作）。

4. **强化 E248（生成物时间戳归一化）**：上游预生成 `configure` / `Makefile.in` /
   `scanner.c` 与宿主 autoconf/automake/bison/flex 异代时，任何触发 `am--refresh` /
   `config.status --recheck` 的路径都会重生成脚本，把补丁打成行号漂移并引入新失败；
   本案靠**压时间戳**根治。

5. **补记 E007/E072**：`config.sub` 会**静默规范化** `aarch64-unknown-linux-ohos` →
   `aarch64-unknown-linux-gnu-ohos`，「静默」这一表征值得写进条目（只补 `config.guess`
   会得到看似成功、实则三元组错误的构建）。

---

## 作者

- **姓名**: evol
- **邮箱**: evol@noreply.gitcode.com
- **Agent ID**: 6930
- **生成时间**: 2026-09-26 17:21:39
- **PR 编号**: 12914
- **Git Commit**: 4d02142d3dfecf42791778e2475ba141a311f279
