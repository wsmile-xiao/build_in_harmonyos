# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_3356d6c8.md`

---

## 背景

- **软件名称**: since
- **版本**: 1.1
- **构建日期**: 2026-09-21
- **构建系统**: makefile（上游手写 Makefile，无 configure）
- **上游仓库**: https://salsa.debian.org/debian/since （upstream/1.1 tag，内容与 http://welz.org.za/projects/since 原始 tarball 逐文件一致）
- **适配路径**: 路径 B（贡献创新：1 个可移植性补丁 + 2 条知识草稿）
- **补丁数量**: 1（patches/0001-Makefile.patch，6 增 5 删，无平台宏）
- **编译依赖**:
无
- **最终状态**: 适配完成并已提交 PR #11728；CI 与 AI 检视在平台侧排队中，尚未闭环（result.json = partial）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | makefile + OHOS clang 交叉编译，一次通过 |
| conan-verify | 配方验证 | 通过 | G0/G1/G2/G3 全绿，L2 因 since 用 -V 而非 --version 记 skip |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 部分完成 | PR #11728 已建；AI Review 监控因 monitor-review 崩溃空转 30min 超时；CI 已触发但平台侧长时间排队 |

### 失败与问题

本次共 4 类问题，其中 1 类为框架缺陷：

1. **（框架缺陷，阻塞 submit 闭环）`scripts/gitcode_pr.py` 的 `monitor-review` 子命令崩溃**
   ```
   File "scripts/gitcode_pr.py", line 1066, in cmd_monitor_review
       "unreplied_opinions": unreplied_opinions,
   NameError: name 'unreplied_opinions' is not defined. Did you mean: 'review_opinions'?
   ```
   submit 的 AI Review Phase 1 把该崩溃当作"获取检视状态失败"反复重试，必然空转到 30 分钟
   超时退出（`EXIT_REASON: ai_review_summary_timeout`），而实际 PR 上机器人摘要仍在生成中。
   影响：**任何走 `submit` / `submit --resume` 的任务都无法推进到 CI 监控阶段**。
   协作者只读 `scripts/`，故未修改，此处上报主编。绕行办法：改用
   `gitcode_pr.py ci-status` + `get-comments` 轮询。

2. **（流程摩擦）W3 本地 CI 在分支无 commit 时退化为全仓扫描**
   junk_check 的模式判定是 `git diff origin/main...HEAD` 为空即 fallback 到 full，
   于是首次 finish 被 `archives/c/cloog`、`archives/k/kics` 的**他人存量**状态文件判失败
   （JC1+JC5 共 2 条），与本包无关。先 commit 再跑 finish 即可规避。

3. **（工具交互坑，已沉淀 E543 草稿）init-build 的 .work 与 .orig 是硬链接**
   原地写回的编辑器会把 .orig 一并改掉，`refresh-patch --auto` 因此报"无有效新补丁"，
   patches/ 为空——但本地源码看起来改好了，极具迷惑性。

4. **（平台能力边界，已沉淀 E544 草稿）x86_64 runner 无法执行 OHOS 动态产物**
   qemu-user 加载 musl 解释器时 signal 11（hello world 同样复现），只有 `-static` 副本能跑。

### 知识图谱使用情况

- **引用知识条目**: E484（patch --dry-run 占位文件）/ E356（固定目标编译器）/ E374（can_run≠可执行）/ E002（/tmp 只读）——均为查重与比对用
- **新增知识草稿**: 2 条（E543-draft-7C1A：硬链接致空补丁；E544-draft-7C1A：qemu 跑不了 OHOS 动态产物）；draft-review 均判 create
- **引擎命中情况**: 草稿目录 1406 条
- **测试统计**: 上游 0 条（tarball 无测试资产）；补全 8 条（1 产物校验 + 7 功能断言），qemu 实跑 8/8 通过
- **未覆盖的错误模式**: ①上述框架缺陷（monitor-review NameError）属工具 bug，不宜作 E-entry；
  ②"分支无 commit 导致 junk_check 退化 full 模式、被他人存量文件误伤"值得单独立项一条，
  本次未提（避免一个 PR 塞三条草稿），建议主编评估后由框架侧修正模式判定

### AI 检视结果

- **检视阶段到达**: Phase 1（等待变更摘要），因工具崩溃未能推进
- **变更摘要评估**: 未产出——atomgit-bot 自 01:59 起显示"正在生成合并请求摘要"，至 02:45 仍无结论
- **检视意见数量**: 0（截至收尾时机器人未给出任何检视意见）
- **检视意见处理**: 无需处理；若后续出现，用 `gitcode_pr.py handle-review-opinion` 逐条闭环

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（L0/L1/L4/L5 pass，L2 skip；含 L1e 破坏性反向验证）
- **远程 CI (PR 校验)**: 已于 02:03 收到 /rebuild 并显示"构建触发中"，至 02:45 仍无结果评论（平台队列）
- **CI 失败原因**: 无失败；是未出结果（排队）

### 效率分析

- **HANDOFF 次数**: 5（W3 junk_check 1 次、W4 审计未执行 1 次、submit 自检 1 次、git push 无权限 1 次、AI Review 超时 1 次）
- **重试次数**: finish 4 次（每次配方/测试改动后复验 W3）、W4 审计 3 轮、submit 3 次
- **关键瓶颈**: ①平台侧 AI 检视与 CI 排队（不可控，占用近 1 小时且未出结果）；②monitor-review 崩溃导致的 30 分钟空转；③W4 三轮审计（但这部分是有价值的，见下）
- **耗时较长的步骤**: submit 的 AI Review 轮询 30min（全部空转）> 平台 CI 排队 40min+ > 4 次 finish（W3 conan create 各约 1-2min）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 8 个事件（含 4 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-21T00:46:40 | skeleton_created | result_partial |
| 2026-09-21T00:46:40 | lang_checked | detected=c 与任务 cpp 匹配 |
| 2026-09-21T01:03:03 | handoff:w4_audit_not_done | W4 Pre-PR 审计未执行，请先完成审计 \| python3 scripts/pre_pr_audit.py generate --repo-dir /data/harmony-compact/build_in_harmonyos --package since --version 1.1 \| 审计子任务完成后将结果保存为 reports/audit-result.json |
| 2026-09-21T01:57:23 | handoff:self_check_failed | 自检未通过: ['packaging_present', 'test_report_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit since 1.1 |
| 2026-09-21T01:58:33 | handoff:git_push_failed | git push 失败: fatal: could not read Username for 'https://gitcode.com': No such device or address \| 检查远端仓库配置和权限 \| 手动推送后重新 submit: python3 scripts/ohc-run.py submit since 1.1 |
| 2026-09-21T02:00:15 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-21T02:00:15 | skeleton_exists | resume_pr_exists |
| 2026-09-21T02:30:19 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #11728 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 11728 \| 摘要出现后: python3 scripts/ohc-run.py submit since 1.1 --resume |
<!-- EVENTS:END -->

---

## 建议

### SKILL 设计改进

1. **`monitor-review` 崩溃应 fail-fast，而不是被吞成"获取失败"重试 30 分钟**（P0 级体验问题）。
   建议：submit 的 Phase 1 对子进程**非零退出且 stderr 含 Traceback** 的情况直接 HANDOFF，
   并在提示里给出绕行命令（ci-status / get-comments），而不是与"网络抖动"同等对待。
   顺带修掉 `cmd_monitor_review` 里 `unreplied_opinions` 未定义的 NameError。

2. **junk_check 的模式判定不应在"分支无 commit"时退化为全仓 full 扫描**。
   新包首次 finish 时工作区通常还没 commit，结果被他人存量垃圾文件判失败，
   排查成本高且结论误导（报错里全是别人的目录）。建议：diff 为空时改用
   `git status --porcelain` 的未跟踪清单，或直接提示"请先 commit 再跑 W3"。

3. **PF9 与 R38/ARCHIVE-SPEC 存在硬冲突**：CLI 包必须在软件级目录放 `commands.json`
   （L0k 校验），软件级还必须有 `README.md` / `manifest.yaml`，但 PF9 判"路径段数 < 5"
   即拦截，导致**每个首次适配的 CLI 新包都必须 `OHC_PREFLIGHT=0` 才能建 PR**——
   逃生口被迫常态化使用，PF1-PF8 也一起被跳过，反而削弱了门禁。
   建议：PF9 白名单 `archives/<字母>/<包>/{README.md,manifest.yaml,commands.json}`。

4. **`submit` 的 git push 默认只推 origin**，无上游权限时直接 HANDOFF 失败。
   建议：检测到 origin 推送权限不足且存在 fork remote 时，自动改推 fork 并把 PR head
   拼成 `<fork-owner>:<branch>`（当前需要人工完成这一段）。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **`conan-init` 对纯 Makefile 项目只给 autotools 模板**（生成的 `conanfile.py` 带
   `AutotoolsToolchain.configure()` + `CMakeLists.txt` + `test.c`），本次全部推倒重写。
   仓库普查里 Make 类占 21%，建议补一个 `conanfile-make.py.tmpl`：
   `self.run(f'make CC="{cc}" -j1', cwd=self.source_folder)` + `copy()` 打包 + 无 configure。

2. **`test_package` 模板默认是 CMake + test.c**，而 CLI 工具包（`package_type=application`）
   需要的是"跑二进制"的脚本型测试。建议按 `package_type` 分流模板，
   并内置"产物校验 + 可执行性探测 + 如实 skip"的骨架——本次这套逻辑是手写的，
   且第一版就踩了"把非零退出码当作不可执行"的坑（被 W4 审计判 P1）。

3. **版本级 `manifest.yaml` 模板留了 `{software}` / `{BUILD_SYSTEM}` 占位符且不校验**，
   `patch_classification` 每次 refresh-patch 都被重写回 `type: auto / platform_only: True /
   guard: 'pending'`，人工填好的分类会被覆盖。建议：refresh-patch 保留已填写的分类字段。

4. **软件级 `manifest.yaml` 的模板与 ARCHIVE-SPEC §4.1 不一致**（仓库存量普遍缺 `display`、
   `versions` 写成 list），新人照抄存量就会偏离规范。建议提供 `templates/manifest-software.yaml`。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **W4 审计的"改完再审"回路应工具化**：本次审计 3 轮，每轮都要人工重跑
   `pre_pr_audit.py generate` → 派子任务 → 转格式落盘。建议 `submit` 内置
   `--audit-round N`，并在检测到"审计后文件有改动"时自动提示需要复审。

2. **`pre_pr_audit.py report` 只打印不落盘**，而 submit 的 Gate 3 读的是
   `reports/audit-result.json`；且工具读的字段是 `issues`，模板 prompt 里写的是同名，
   但 SKILL.md 示例用 `findings`。建议 report 直接写入权威路径并统一字段名。

3. **`packaging/*.tar.gz` 与 `reports/test-report.md` 属于 submit 自检硬性项，
   却要人工手动打包/撰写**。建议 finish 成功后自动从 conan 包目录生成 tar.gz，
   并用 W3 日志 + test_package 输出自动生成 test-report 初稿。

4. **`conan cache path <ref>` 给的是 export 目录而非 package 目录**，
   本次打包时先打错了一次。建议在文档或脚本里封装一个"取包产物目录"的辅助命令。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

本次新增 2 条草稿（已随 PR #11728 提交，字段填实并通过 `graph validate`）：

1. **E543-draft-7C1A** — `refresh-patch --auto` 报"无有效新补丁"的隐蔽根因：
   `.work` 与 `.orig` 是硬链接，原地写回的编辑把基线一起改了，difflib 恒为空。
   与 E484（patch --dry-run 占位文件）根因不同，`draft-review` 判 `create`。

2. **E544-draft-7C1A** — x86_64 runner 上 qemu-user 无法加载 OHOS musl 动态解释器
   （signal 11，hello world 复现），静态副本可跑；给出"静态副本跑完整断言 + 发布产物
   不改链接方式 + aarch64 宿主禁止 skip"的验证范式。与 E356（异架构代码生成）、
   E374（真机缺签名工具链）互补，已互相引用。

建议主编另行评估两个尚未成条目的模式：
- "分支无 commit → junk_check 退化 full → 被他人存量文件误伤"（工具行为，或许更适合修工具）
- "PF9 与 R38 软件级文件位置冲突"（规则冲突，建议改规则而非记知识）

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: lilliv3
- **邮箱**: lilliv3@users.noreply.gitcode.com
- **Agent ID**: 4732
- **生成时间**: 2026-09-21 00:46:40
- **PR 编号**: —
- **Git Commit**: ae4c307fc4
