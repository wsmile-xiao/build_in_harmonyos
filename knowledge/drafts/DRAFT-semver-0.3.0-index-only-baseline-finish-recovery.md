# DRAFT — 整仓 git ls-files junk_check 对无关 tracked 基线的误阻断与可恢复 index-only 隔离

- 主题: index-only baseline isolation + shared finish recovery
- 来源库: semver 0.3.0（R06-R09 真实证据, 与本库同 worktree 验证）
- 日期: 2026-08-31
- 状态: DRAFT（路径 B 知识草稿, 待权威 Issue 模板恢复后经分析端受权转为正式交付）

## 问题背景

在 OpenHarmony PC 三方库本地 finish 流程中, `ci/scripts/junk_check.sh` 的 JC 门禁会因
**与当前库无关的、main 中已跟踪的基线文件** 而被误阻断。其扫描机制为:

- 无 PR diff / 无 `origin/main...HEAD` 提交差异时, JUNK_CHECK_MODE 回退为 `full` 模式,
  扫描范围 = 整仓 `git ls-files`（即 git 索引跟踪的全部文件）。
- 因此即使某基线文件与当前库毫无关系, 只要它在 main 索引中被跟踪, 就会进入 JC3
  （tarball 检测）或 JC5（archives 隐藏文件白名单）命中清单, 使 W3/finish 阻塞。

本库真实遇到的 3 条精确基线路径（main 已跟踪、磁盘存在、与 semver 无关）:

- `archives/g/goaccess/1.10.2/ncurses-headers.tar.gz`
- `archives/s/scudo-malloc/19.1.6/.manifest-complete`
- `archives/s/scudo-malloc/19.1.6/.progress-closed`

## 发现机制

1. R05 观察: 对基线路径做磁盘移动（`mv`）后重跑 finish, JC 门禁**仍然**命中 —
   说明 JC 判定依据不是磁盘存在性, 而是 git 索引（`git ls-files`）。
2. R06 验证: 采用 **index-only 隔离**（`git rm --cached <路径>`, 不触碰磁盘内容）,
   隔离后 `git ls-files` 不再列出 3 条路径, 完整 W3（`zsh ci/conan/build_and_test.sh`）
   外层退出码为 0（Build Summary Success 1/1）。
3. R07/R08 复验: 隔离态完整 finish 的外层退出码受共享流程 W4/Step8/gen_summary 影响;
   R09 按任务授权临时修正共享 finish 范围后, 完整 finish 外层退出码为 0。

## 根因

- junk_check 的 `full` 模式以整仓 git 索引（`git ls-files`）为扫描范围, 无法区分
  "当前库变更" 与 "共享基线历史预存内容"。
- 磁盘隔离（`mv`）不改索引, 故无效; 必须用 **index-only 隔离**（`git rm --cached`）才能
  让 `git ls-files` 不再命中, 且不破坏磁盘内容、可逆恢复。
- 完整 finish 还存在共享流程层问题（与当前库无关）: W4 对共享预存知识条目
  （E219/E253/E305 等）的字段检查、Step8 对 header-only 不适用项（packaging/ 与
  .staging-verified）的机械检查、gen_summary 的 scalar/list 混用缺陷。

## 解决方案（可复用原则）

### 基线处理（临时、可恢复、不入 semver diff）

1. 逐路径记录: `git ls-files --stage`、`git rev-parse main:<path>`（blob）、
   `sha256sum <path>`（磁盘哈希）、`git status --porcelain`。
2. 临时 index-only 隔离: `git rm --cached -- <p1> <p2> <p3>`。
3. 复验: 隔离态运行完整 W3 / finish, 记录真实外层退出码。
4. 恢复: `git reset HEAD -- <p1> <p2> <p3>`, 核验恢复后 stage blob 与磁盘哈希
   与隔离前一致, `staged=0`。
5. 原子性: 三条基线路径、共享框架、SUMMARY.md 均不得进入 staged/diff/未来 PR。

### 共享 finish 范围处理（仅限任务授权, 复验后必须完整恢复）

- W4 仅以当前库知识缺口为阻塞条件; 共享预存条目字段缺失仅记录、归属共享流程。
- Step8 对 header-only 配方豁免 packaging/ 与 .staging-verified 不适用项;
  test-report.md 与 build-closed 必须真实存在。
- gen_summary 对 scalar/list 混用做防御处理（先转列表再 append）。
- 所有临时共享修改记录绝对路径 + 前后 SHA-256, 复验后 `git checkout HEAD --` 恢复,
  证明共享 diff=0。

## R09 真实复验结论

- 隔离态 W3: 外层退出码 0（success 1/1）。
- 完整 finish: 外层退出码 0（W2/W3/W5/Step8 全部通过）。
- `baseline_noise_exempted=true`, 质量结论 quality_pass。
- 恢复后: 三条基线 stage blob/磁盘 SHA-256 与原值一致、staged=0、共享 diff=0、
  当前库 diff 仅 `archives/s/semver/**`。

## 适用边界

- 适用于: 本地/CI finish 因无关 tracked 基线文件被 junk_check 整仓索引扫描误阻断的场景,
  以及 header-only 配方的共享 finish 恢复审计。
- 不适用: 不能作为永久白名单、不能提交/隔离/删除其他库文件、不能伪装共享问题为
  当前库源码缺陷; 远端写操作必须由分析端受权后另行执行。
- 共享维护恢复条件: 由共享框架维护方对 junk_check 增加基线白名单/豁免登记,
  或修正 W4 块标量解析、Step8 header-only 适用性、gen_summary 缺陷。

## 参考证据（真实日志, 仅引用不做修改）

- R09 natural_terminal 日志 SHA-256: 6318f1807de5a1bc25aef2fe057cf2829f0ccd3cc929508063f6a953b8e407e2
- R09 isolated_finish_revalidation 日志 SHA-256: bd6358030ebef6bfff5a746300641200fbfa8fc65a8d85682a2c48ecd4fc8c86
