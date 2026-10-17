# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_f2d2653f.md`

---

## 背景

- **软件名称**: leave
- **版本**: 1.12
- **构建日期**: 2026-09-15
- **构建系统**: makefile（实为 BSD make 片段，绕开 make 直接编译单一 TU）
- **上游仓库**: https://deb.debian.org/debian/pool/main/l/leave/leave_1.12.orig.tar.gz （NetBSD/FreeBSD `usr.bin/leave`，无官方独立 tarball，用户已批准用 Debian 未修改原包）
- **适配路径**: 路径 A（基础适配），PR 前缀 `【积分赛】`
- **补丁数量**: 1
- **编译依赖**:
无（仅 libc）
- **最终状态**: 成功（PR #10369 已创建，CI #48795 PASSED，result 终态 `success`）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | sha256 与 conandata 一致 |
| build | 编译构建 | 成功 | 绕开 BSD make，用 Conan toolchain 的 clang 直接编译 `leave.c`（R33：CC/CFLAGS 取自 `self.conf`） |
| conan-verify | 配方验证 | 成功 | G1/G2/G3/G4 全 PASS；test_package 5/5 + ohos_specific 6/6 |
| finish | 归档收尾 | 完成 | W2 结构 + R36 依赖 + W3 本地 CI 模拟 100%（1/1，`.ci-result.json exit_code=0`） |
| submit | PR提交+AI检视+CI | 成功 | PR #10369（标题后改为 `【积分赛】leave 1.12 适配 HarmonyOS PC (arm64)`）；AI Review：摘要已生成 + 检视结论"✅ 未发现问题"；CI #48795 PASSED（conan test_package / L0 / L1 全绿） |
| result | 终态上报 | 成功 | `status=success`（pr_number=10369、branch、commit_hash 齐全，draft=false） |

### 失败与问题

- **1｜BSD make 片段不可用**: 上游 `Makefile` 只有 `PROG=leave` + `.include <bsd.prog.mk>`，OHOS/CI 无该框架文件 → 无法用 make。解决方案：配方绕开 make，直接用 Conan toolchain 提供的 clang 编译单一 TU。
- **2｜musl 缺 NetBSD 专有宏**: `<sys/cdefs.h>` 不提供 `__COPYRIGHT`/`__RCSID`。解决方案：补丁中以 `#ifndef` 兜底宏提供。
- **3｜无 `getprogname(3)`**: OHOS musl 仅导出 `__progname`。解决方案：非 BSD 平台 fallback 实现（`#if !defined(__FreeBSD__) ...` 守卫）。
- **4｜`u_int` 未声明**: `u_int` 是 BSD `<sys/types.h>` 拼写，musl 下受 `_GNU_SOURCE`/`_BSD_SOURCE` 守卫，本 sysroot 的 `<sys/param.h>` 亦不含 `<sys/types.h>`，实测 `-D_GNU_SOURCE` 无效。解决方案：补丁统一改为 portable 的 `unsigned int`。
- **5｜W3 的 JC 全仓扫描误报（harness 缺陷，已解）**: 归档尚未提交时 `git diff origin/main...HEAD` 为空 → `junk_check.sh` 回退 `full` 模式扫描整仓 66728 文件，把 **origin/main 里他人归档**的运行时标记 `archives/c/cloog/0.21.1/{.build-closed,.staging-verified}`（`906cc59ae` 误提交入库）算作本包失败，首次 `finish` 被 JC1/JC5 阻断。绕过：**先 commit 本次归档再跑 finish**（diff 非空 → incremental 模式只查本包，与 CI 的 prdiff 语义一致）。
- **6｜submit 自检 `packaging_present` 是 v3.0 遗留**: 要求 `packaging/*.tar.gz` 存在（R19/R20 已废弃手动打包），而 `packaging/` 被 `.gitignore`（不入 PR）→ 必须手工 `tar czf` 才能过闸（先例：bluefish）。
- **7｜preflight PF7/PF9 双拦截（需用户拍板+逃生口）**: PF7 把 `deb.debian.org` 判为"Debian 下游重打包源"；PF9 要求变更路径 ≥5 段（`archives/<字母>/<包>/<版本>/...`），而 **PF8/R38 又要求 CLI 包必须有软件级 `archives/l/leave/commands.json`** → 两闸自相矛盾，任何新 CLI 包 PR 必被 PF9 拦。本次经用户批准以 `OHC_PREFLIGHT=0` 提交，理由已写进 PR 正文留痕。
- **8｜submit PR 标题硬编码**: `feat(<包>): <版本> 适配完成`，无 `--title` 入口 → §10.2 要求的 `【积分赛】…` 前缀只能在建 PR 后 `gitcode_pr.py update-pr --title` 改。
- **9｜`monitor-review` NameError（harness 缺陷，已本地热修）**: `scripts/gitcode_pr.py` 的 `unreplied_opinions` 从未定义 → 该子命令每次 NameError → `submit` Phase 1 永久"获取检视状态失败"直到 30 分钟超时（09-03 的 poster 任务反馈里已记录同一缺陷，说明**并非本次新引入**）。
- **10｜`submission.py` 调 `monitor-review` 时 `--json` 顺序错误（harness 缺陷，已本地热修）**: `_call_monitor_review` 传 `--json` 在子命令**之前**，而 `--json` 是子命令级参数 → JSON 永不输出、`--- JSON ---` 标记不出现 → 即使修了 #9 仍判失败。另 `_verify_review_closure` 顺序正确，两处不一致。
- **11｜检视意见闭环无法在平台侧标记（平台 API 限制）**: 本条检视意见内容为"✅ 未发现问题"，`handle-review-opinion --action accept` 的回复成功但 discussion resolve 报 `404 discussion not found`，且回复未出现在 `get-comments` 流中 → `_verify_review_closure` 永远判"1 条未闭环"。最终按 CI 实证绿 + 零实质意见由主管执行终态上报。

### 知识图谱使用情况

- **引用知识条目**: E113（BSD 类型 `u_int` 等在 OHOS musl 下不可见）、E203（musl 无 `getprogname()`，仅 `__progname`）
- **新增知识草稿**: 3 条（含 `bsd.prog.mk` 类无 make 路径——实测现有库未覆盖，见下）
- **引擎命中情况**: 草稿目录 668 条
- **测试统计**: 上游 0（确无测试套件，附文件级清点证据）；本适配 2 个测试入口，test_package 5/5、ohos_specific 6/6（合计 11/11）
- **未覆盖的错误模式**: ①BSD `usr.bin/*` 的 Makefile 为 BSD make 片段（`.include <bsd.prog.mk>`），OHOS/CI 无法用 make（实测知识库 E113/E203 已覆盖 ②③，但此条未覆盖）；②musl 缺 `__COPYRIGHT`/`__RCSID` 专有宏；③`u_int` 受 feature 宏守卫

### AI 检视结果

- **检视阶段到达**: Phase 3（摘要已生成 + 1 条检视意见）
- **变更摘要评估**: 摘要准确——正确概括"绕开 BSD make 直接编译单 TU""POSIX 兼容补丁（无 `__OHOS__`）""上游无测试→补 5 通用 + 6 鸿蒙""commands.json 声明"，无失实描述，**无需修改**
- **检视意见数量**: 1（内容为"#### 代码审查 / ✅ 未发现问题"）
- **检视意见处理**: 已按 accept 回复（说明无需修改 + CI 绿），但平台 discussion resolve 接口 404，闭环标记无法落地（见问题 #11）；实质为**零缺陷意见**

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`.ci-result.json exit_code=0`，L0/L1/L4/L5 全 pass，JC incremental pass，`Pass rate 100% (1/1)`）
- **远程 CI (PR 校验)**: 通过（build #48795，worker CI-021；Conan test_package 通过、L0 通过、L1 通过）
- **CI 失败原因**: 无（一次通过）

### 效率分析

- **HANDOFF 次数**: 4（finish Step5 的 JC full 误报 ×1、submit 自检 `packaging_present` ×1、`ai_review_summary_timeout`（由 #9/#10 缺陷导致）×1、`ai_review_opinions` ×1）
- **重试次数**: `submit --resume` 3 次（其中 2 次是被 monitor-review 缺陷逼出的白等重跑）
- **关键瓶颈**: ①harness 缺陷 #9+#10 使 AI Review Phase 1 无法感知"摘要已生成"，白等到 30 分钟超时；②JC full 模式误报把他人归档垃圾算成本包失败，阻断首次 finish；③PF7/PF9 双闸拦截需人工拍板 + 逃生口
- **耗时较长的步骤**: AI Review 监控（缺陷导致的白等）；两次 `conan create`（W3 与 conan-verify）；PF7/PF9 的判定与上报澄清

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 16 个事件（含 5 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-15T18:00:03 | lang_checked | detected=c 与任务 cpp 匹配 |
| 2026-09-15T23:29:18 | skeleton_created | result_partial |
| 2026-09-16T13:03:57 | lang_checked | detected=c 与任务 cpp 匹配 |
| 2026-09-16T17:52:28 | handoff:self_check_failed | 自检未通过: ['packaging_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit leave 1.12 |
| 2026-09-16T18:07:28 | skeleton_exists | pr_created |
| 2026-09-16T18:07:28 | pr_created | PR #10369 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/10369 |
| 2026-09-16T18:37:36 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #10369 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 10369 \| 摘要出现后: python3 scripts/ohc-run.py submit leave 1.12 --resume |
| 2026-09-16T19:18:12 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-16T19:18:13 | skeleton_exists | resume_pr_exists |
| 2026-09-16T19:48:21 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #10369 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 10369 \| 摘要出现后: python3 scripts/ohc-run.py submit leave 1.12 --resume |
| 2026-09-16T20:02:04 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-16T20:02:04 | skeleton_exists | resume_pr_exists |
| 2026-09-16T20:02:09 | handoff:ai_review_opinions | atomgit-bot 已发布 1 条检视意见，请逐条评估并处理： \|  \| ⚠️ 注意：检视意见不一定正确，需严格判断是否合理后再修改！ |
| 2026-09-16T20:34:46 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-16T20:34:47 | skeleton_exists | resume_pr_exists |
| 2026-09-16T20:34:49 | handoff:review_closure_incomplete | PR #10369 有 1 条检视意见未回复（闭环未完成）： \|  \|   - comment_id: 190042293: #### 代码审查  ✅ 未发现问题    |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **修 `monitor-review` 的两处 harness 缺陷（优先级最高）**：①`scripts/gitcode_pr.py` 中 `unreplied_opinions` 未定义（NameError，L1066 使用/无定义）；②`scripts/ohc/submission.py::_call_monitor_review` 把 `--json` 传在子命令**之前**（子命令级参数 → 永远取不到 JSON）。两者叠加使 submit 的 AI Review 阶段**结构性失效**，所有任务都白等 30 分钟或被迫手动绕过；09-03 poster 任务与本任务各踩一次。
2. **W3 的 `junk_check.sh` full 模式应限定范围**：归档未提交（`git diff origin/main...HEAD` 为空）时不应回退为"扫整仓 `git ls-files`"，而应只针对本次 `CI_PACKAGES` 路径；否则 main 里任何历史误提交的运行时文件都会持续阻断**所有**包的 finish。建议同时清理 `archives/c/cloog/0.21.1/{.build-closed,.staging-verified}`（`906cc59ae` 误提交）。
3. **PF8 与 PF9 自相矛盾需消除**：PF9 要求变更路径 ≥5 段，PF8/R38 又要求 CLI 包的 `commands.json` 位于软件级（仓库已有 2110 个先例）→ 新 CLI 包 PR 必被 PF9 拦。建议 PF9 对同包的软件级 `commands.json`/`README.md` 放行（或纳入白名单）。
4. **submit 自检去掉 `packaging_present`**（v3.0 遗留）：R19/R20 已废弃手动 tar.gz 打包，该检查只剩"逼 AI 手工造包"的副作用；若要保留请自动从 conan cache 生成，或仅在 `status=published` 时要求。
5. **submit 支持自定义 PR 标题**：新增 `--title`/`OHC_PR_TITLE`，使 §10.2 规定的前缀格式（如 `【积分赛】…`）能在创建时就写对，避免"先建后改"。
6. **`handle-review-opinion` 的 discussion API 404 需容错**：resolve 失败时应降级为普通评论回复并降级闭环判定（当前回复实际未落到讨论串，导致闭环永远不通过）。

### 模板改进

1. `templates/conanfile-makefile.py.tmpl` 未覆盖"上游 Makefile 是 BSD make 片段（`.include <bsd.prog.mk>`），必须绕开 make、由 conanfile 直接调用编译器编译单一 TU"的情形，建议补充该范式（本次按此自写）。
2. `templates/test_package-executable/test.sh.tmpl` 仅探测 `--version`/`--help`。对**没有 `--version`/`--help`**、且**正常路径会阻塞或后台常驻**的命令行工具（如 `leave` 会 fork 后等待到点），该范式不适用（还会导致 CI 的 L2 被 skip）。建议补充"退出码/错误用法断言 + 后台子进程显式回收"的确定性测试范式。
3. `templates/积分赛事PR模板.md` 的"使用知识库"一栏建议注明"先做知识库覆盖查证（`engine`/`index.tsv` grep）"，避免把已入库条目（本次 E113/E203）当作新增知识去冲 B-1 路径。

### 自动化补全

1. **CI 环境性失败自动重试**：CI 失败评论（ohpcd-robot）已含 build URL，可自动抓取日志识别"链接器自身崩溃/库加载失败"类环境特征（如 09-03 poster 遇到的 `libxml2.so.16 not found`）并自动 `trigger-ci` 重试一次，减少人工定位。
2. **AI Review 等待的手动验证降级**：`monitor-review` 连续失败 N 次时应自动降级为 `get-comments` 解析（摘要评论与"未发现问题"结论可直接从评论流判读），而非硬等 30 分钟。
3. **远程执行层统一走 stdin 脚本**（`bash -s`/scp 脚本）而非内联引号命令，规避 Windows OpenSSH 吞双引号导致的误解析（本次踩坑后改用该方式）。
4. `refresh-patch --auto` 每次重写 `manifest.yaml` 的 `patch_classification`（`type: auto`/`guard: pending`），建议保留 AI 已填分类或提供 `--keep-classification`。

### 知识图谱覆盖

建议新增一条 E-entry：**"BSD 基础系统工具（usr.bin/*）在 OHOS/musl 的通用移植配方"**——
(a) 上游 Makefile 依赖 `bsd.prog.mk` 不可用，绕开 make 由 conanfile 直接编译单一 TU；
(b) musl `<sys/cdefs.h>` 缺 `__COPYRIGHT`/`__RCSID`（`#ifndef` 兜底）且无 `getprogname(3)`（非 BSD 平台 fallback）；
(c) `u_int` 需改 portable 的 `unsigned int`。
已实测：现有知识库仅有 E113（(c)）与 E203（(b)）两条**片段**，缺少 (a) 这一"没有 make 目标怎么做"的整链范式；此类问题在 BSD 工具适配中会反复出现。

---

## 作者

- **姓名**: 2301_77929998
- **邮箱**: gmh5787317@163.com
- **Agent ID**: 8283
- **生成时间**: 2026-09-16 21:30
- **PR 编号**: 10369
- **Git Commit**: 42c850fb9
