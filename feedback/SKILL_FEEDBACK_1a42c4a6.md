# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_1a42c4a6.md`
>
> ⚠️ 注：背景节的多个字段自动采集失效（`{BUILD_SYSTEM}` 模板变量未替换、
> 补丁数量/知识草稿/测试统计均取到 0），已按实人工修正，详见「自动化补全」节。

---

## 背景

- **软件名称**: socket
- **版本**: 1.1
- **构建日期**: 2026-09-21
- **构建系统**: makefile（1992 年 shapeTools 风格，无 configure）
- **上游仓库**: https://ftp.debian.org/debian/pool/main/s/socket/socket_1.1.orig.tar.gz
  （上游站 ftp.cs.tu-berlin.de 已消失、salsa 无 VCS，取 Debian 归档中未重打包的原始 tarball）
- **适配路径**: 路径 B（贡献创新：适配 + 知识草稿同 PR）
- **补丁数量**: 3（均为 portability，无平台宏）
- **编译依赖**:
无（仅 libc）
- **最终状态**: PR #11735 已创建，AI 检视与 CI 待闭环（result.json 当前为 partial）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 复现 E543：`.work` 与 `.orig` 硬链接，原地编辑污染 `.orig` |
| build | 编译构建 | 成功 | 构建系统: makefile；`make targets` 绕开 shapeTools `+all` 递归 |
| conan-verify | 配方验证 | 通过 | G1-G4 通过；L2/L4/L5 报 PASS 但实为「跳过（无 cache 路径）」 |
| finish | 归档收尾 | 完成（第 2 次起） | 第 1 次被 JC 闸误拦，根因见「失败与问题」 |
| submit | PR提交+AI检视+CI | 部分完成 | submit 不支持 fork 贡献者，push/建 PR/状态文件均手动完成；AI Review: Phase 1 进行中 |

### 失败与问题

1. **W3 被 JC 闸误拦（最耗时的一次阻塞）**
   `finish` 首次运行报 `JC_ERRORS=2 / L0_RESULT=fail`，但列出的 3 个文件
   （`archives/c/cloog/0.21.1/.build-closed`、`.staging-verified`、
   `archives/k/kics/2.1.20/.staging-verified`）**全部是他人包、且早已提交在 `origin/main`**。
   根因：`ci/scripts/junk_check.sh` 在 `git diff origin/main...HEAD` 为空时静默回退
   `full` 模式（改扫全仓 84833 个已跟踪文件）。当时任务分支尚无 commit，故必然回退。
   解法：先 `git commit` 再跑 `finish`，即进入 `incremental` 模式只扫本 PR 文件。
   危险性：错误信息指向他人归档，极易诱导协作者去「清理别人的包」，直接撞红线。

2. **PF9 与 PF8/R38 对新增 CLI 包互斥**
   PF8/R38 要求 CLI 包必须有软件级 `archives/<字母>/<包>/commands.json`（4 段路径），
   PF9 又硬性要求 `archives/` 下每个变更文件都带版本目录层（≥5 段）。
   新增 CLI 包必然同时触发，无法两全。本次已在本地实跑完整 `run_preflight`
   确认「唯一命中项是 PF9」，再以 `--no-preflight` 建 PR，并把理由与已合并同形态先例
   （ntopng 6.6 / xe 1.0 / rgxg 0.1.2 / pgreplay 1.5.0 / openkermit 11.0.508）写入 PR 正文。

3. **submit 不支持 fork 贡献者**
   `submission.py` 硬编码 `git push origin <branch>`；本机既无 git 凭据、也无上游 push 权限，
   该步必失败。且 `create-pr --source <owner>:<branch>` 会让 PF0 直接挂
   （本地 `git diff main...<fork-owner>` 无法解析带冒号的 ref）。

4. **`gitcode_pr.py monitor-review` 抛 NameError**
   `NameError: name 'unreplied_opinions' is not defined`（line 1066），子命令完全不可用。

### 知识图谱使用情况

- **引用知识条目**: E543（`.work`/`.orig` 硬链接污染，本次复现并按其处方修复）、
  E544（动态产物无法在 x86 runner 执行，本次复现）、E102（查重参照，非命中）
- **新增知识草稿**: 1 条 —— `DRAFT-socket-1.1-bsd-sigvec-probe-sig-setmask`
  （`draft-review` verdict=create，最高相似度 0.2）
- **引擎命中情况**: `engine` 对本次核心错误签名未命中根因，最近邻是 E102（mmsg/`__linux__` 家族，
  根因与修法均不适用）；草稿目录 1436 条
- **测试统计**: test_package 8 条断言（7 运行时 + 1 artifact）；qemu-aarch64 下同源静态副本
  实跑 7/7 通过；`conan create` 中运行时层因宿主非 aarch64 而 skip（如实标注，未计为通过）
- **未覆盖的错误模式**: `#ifdef SIG_SETMASK` 被老 BSD 代码当作「BSD 信号 API 存在性」探针——
  该宏是 POSIX 强制定义，musl/OHOS 必有，而 `sigvec()`/`struct sigvec` 必无，探测恒真且必选错分支。
  OHOS sysroot 实证：`signal.h:32` 有宏，`grep -rlw sigvec` 命中 0 文件。已产草稿。

### AI 检视结果

- **检视阶段到达**: 检视完成（变更摘要与代码审查均已产出）
- **变更摘要评估**: 准确。摘要正确归纳了三类可移植性问题与补丁的对应关系，
  并如实转述了「非 aarch64 主机上运行时检查标记为 `[skip]` 而非通过」这一关键限定，
  未出现把 skip 误读为通过的情况
- **检视意见数量**: 0（代码审查结论为「✅ 未发现问题」）
- **检视意见处理**: 无意见需处理

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`conan create` + junk_check incremental）
- **远程 CI (PR 校验)**: 已评论 `/rebuild` 触发，结果待回
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 2（`w3_local_ci_failed`、`result_invalid`）
- **重试次数**: `finish` 4 次、`create-pr` 2 次、`conan-verify` 1 次通过
- **关键瓶颈**: 全部集中在**流程摩擦**而非技术适配——编译与 3 个补丁一次打通、根因一次定位；
  耗时主要花在 (a) JC full 模式误报的排查，(b) fork 旁路的摸索（凭据/PF0/状态文件三处卡点），
  (c) PF9 与 PF8 互斥的取证与定性
- **耗时较长的步骤**: W3 本地 CI 模拟（`conan create` 全量走一遍）；其次是 AI 检视等待
  （机器人摘要 5min+ 未出，实测可能长达数小时，不宜阻塞轮询）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 4 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-21T02:09:35 | skeleton_created | result_partial |
| 2026-09-21T02:09:35 | lang_checked | detected=c 与任务 cpp 匹配 |
| 2026-09-21T02:57:24 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-21T02:57:24 | skeleton_exists | resume_pr_exists |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`junk_check.sh` 的 full 回退应显式告警而非静默降级**。建议：回退 full 模式时打印
   「⚠️ 当前分支无 commit，已回退全仓扫描，命中项可能属于历史存量而非本 PR」，
   并把命中项按「本 PR 变更 / 历史存量」分组展示。更优解：`finish` 在跑 W3 前先检查
   `git diff origin/main...HEAD` 是否为空，为空则直接提示「请先 commit 再跑 finish」。
2. **PF9 需要为软件级元文件开白名单**。`commands.json` / 软件级 `manifest.yaml` / `README.md`
   是 ARCHIVE-SPEC 规定的 4 段路径文件，且 PF8/R38 强制要求前者存在。
   建议 PF9 的 `len(f.split("/")) < 5` 判据排除这三个已知文件名，
   或改判据为「变更集中至少存在一个版本目录层文件」即放行。
3. **`submit` 应支持 fork 贡献流**。建议：push 目标从硬编码 `origin` 改为可配置
   （读 git remote `fork` 或 `OHC_PUSH_REMOTE` 环境变量），凭据沿用现有 token 读取逻辑；
   `create-pr` 的 `--source` 增加 `--head-namespace` 参数，让 PF0 的本地 diff 用裸分支名、
   API 载荷用 `owner:branch`。
4. **`finalize-archive` 仍在校验已废弃的 `packaging/*.tar.gz`**。ARCHIVE-SPEC v2.0 第 7 行明写
   「packaging/ 目录废弃（Conan 体系替代手动 tar.gz 打包）」，但 `finalize_archive.py:116`
   仍查 `*-ohos-aarch64.tar.gz` / `*-debug.tar.gz` 并报「缺失项」。建议删除该检查，
   否则每次收尾都产生一条无法消除的假告警，干扰对真实缺失项的判断。

### 模板改进

1. **`conan-init` 生成的 `notes.md` 骨架含占位符，但无任何环节校验其是否被填写**。
   本次 `notes.md` 直到 `conan-verify` 通过之后仍是
   `- 构建系统: {cmake|autotools|makefile|meson|custom}` 的原始模板，
   若非人工发现，会带着模板提交进 PR。建议 `finish` 的 W2 结构检查增加一条：
   归档内 `.md`/`.yaml` 若匹配 `\{[a-z]+\|[a-z|]+\}` 或未填充标记（与本报告同款占位符）
   则阻塞并列出行号。
2. **缺 `reports/test-report.md` 模板**。该文件是 `finish` 的 submit 就绪预检必需项，
   但仓库未提供模板，各包格式不一。建议提供最小模板，且模板中**显式区分**
   「上游用例 N/N′」与「test_package 补全用例」，并强制要求标注执行环境
   （原生 aarch64 / qemu / skip），从模板层面堵住「把 skip 写成通过」。
3. **本报告背景节的自动填充存在错误**，见下节。

### 自动化补全

1. **SKILL_FEEDBACK 背景节自动采集失效**（本次实测）：
   `构建系统` 渲染出未替换的模板变量 `{BUILD_SYSTEM}`；`补丁数量` 取到 0（实际 3，
   `patches/` 下三个 `.patch` 文件俱在）；`新增知识草稿` 取到「无」（实际已写入
   `knowledge/drafts/`）；`测试统计` 全 0；`上游仓库` 取到「(未知)」（`conandata.yml`
   与 `manifest.yaml` 均有 url）；`适配路径` 误判为「路径 A（基础适配，无补丁）」。
   这些字段在归档目录里都是现成的，建议直接从 `manifest.yaml` / `conandata.yml` /
   `patches/` 目录读取，避免协作者手工回填时引入不一致。
2. **`gitcode_pr.py monitor-review` 修复 NameError**（line 1066，`unreplied_opinions` 未定义）。
3. **`create-pr` 未回写 `.submit-state.json`**：代码中有回写逻辑，但本次 PR 创建后该文件不存在，
   导致 `submit --resume` 报「无 PR 编号，无法恢复」，只能手工补写状态文件。
   建议确认回写路径，并在 `--resume` 找不到状态文件时，回退为按分支名调 `list-prs` 自动定位 PR。
4. **AI 检视等待机制应支持非阻塞**。本次 PR 创建后约 10 分钟内轮询，两条机器人评论
   仍是「正在生成…」占位，稍后再查已产出完整摘要与审查结论；经验上该过程可长达数小时。
   `submit` 的阻塞式轮询会长时间占用构建会话。
   建议提供 `--poll-once` 模式：查一次状态即返回并落盘 phase，由调度器周期性续跑。
5. **建议在 PR 创建成功后显式警示「不要再追加 commit」**。实测机制是：PR 提交瞬间同时触发
   变更摘要（快）与代码审查（慢），CI 则需手动评论 `/rebuild` 另行触发（慢）；
   审查一旦开始无法中途停止，而在审查/CI 进行期间新增 commit 会使其失效、白白浪费一轮。
   本次即因在 CI 调度期间追加了一个文档 commit 而打断了 CI。
   建议 `create-pr` 成功后打印醒目提示，并在 `submit` 文档中明确「首次提交 PR 时即应为完整内容」。

### 知识图谱覆盖

建议将本次草稿 `DRAFT-socket-1.1-bsd-sigvec-probe-sig-setmask` promote 为正式 E-entry：

- **新增点**：`SIG_SETMASK` 作为「BSD 信号 API 存在性」的特性探针在 musl/OHOS 上**恒真且必错**。
  这是一类**探针失效**问题（探的是 POSIX 宏，用的是 BSD API 本体），与现有条目中
  「musl 缺某函数」「平台宏 `__linux__` 误判」两类根因都不同。
- **查重证据**：`engine` 最近邻 E102（mmsg 家族，根因是 `__linux__` 误判，修法
  `!defined(__OHOS__)` 不适用）；全库 `grep -rli sigvec` 命中 0 条；
  `draft-review` verdict=create，最高相似度 0.2。
- **可推广的预扫规则**：交叉编译前 `grep -rn "sigvec\|sigblock\|sigsetmask\|sigpause" src/`，
  命中即预判此坑。建议将该规则并入 `prescan` 的检测项。
- 另建议将「BSD 特性探针失效」抽象为一个**条目族**：同期代码还常用
  `#ifdef SIGVEC`、`#ifdef BSD`、`#if defined(sun)` 等做同类探测，
  在 musl 上都有选错分支的风险。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: D2A5
- **生成时间**: 2026-09-21 04:10:00
- **PR 编号**: 11735
