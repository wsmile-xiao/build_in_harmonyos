# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_2af9a59c.md`

---

## 背景

- **软件名称**: nowplaying-cli
- **版本**: 2.1.0
- **构建日期**: 2026-09-14
- **构建系统**: makefile（上游声明）；实际由 `conanfile.py::build()` 以单条 `clang++` 调用构建（上游 Makefile 为 macOS 专用，OHOS 不适用）
- **上游仓库**: https://github.com/kirtan-shah/nowplaying-cli
- **适配路径**: 平台可移植分支（`#if defined(__APPLE__)` 双路径 + 映射到原生 AVSessionKit provider）
- **补丁数量**: 1
- **编译依赖**:
无（仅链接 OHOS SDK 系统库 `libohavsession.so`）
- **最终状态**: 成功（PR #9947，CI PASSED）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | `search-url` 返回 4 个无关 URL（savannah/waterlan 噪声），实际改用官方 tag 归档 |
| lang-preflight (R47) | 语言预检 | detected=mixed | 判定器只按扩展名统计，`.m/.mm` 不在表内；补充 Foundation 探针硬证据 |
| build | 编译构建 | 成功 | 上游 Makefile 为 macOS 专用；可移植分支单条 `clang++` |
| conan-verify | 配方验证 | 通过 | G1/G2/G3/G4 + L2/L4/L5 全 PASS |
| finish | 归档收尾 | 完成 | W3 本地 CI 全门禁 pass；`.ci-result.json` exit_code=0 |
| submit | PR提交+AI检视+CI | PR #9947, CI PASSED | 首轮 CI 因 worker 基础设施故障（`git` 缺 libz.so）红，`/rebuild` 重试后绿 |

### 失败与问题

- **1**: 根因=`'Foundation/Foundation.h' file not found`, 解决方案=OHOS 无 Objective-C 运行时/Foundation，补丁把 macOS 实现保留在 `__APPLE__`，非 Apple 平台提供可移植 C++ 实现
- **2**: 根因=上游 Makefile 用 `-framework Cocoa/Foundation/AppKit`, 解决方案=macOS 专用构建，可移植分支直接用 `clang++` 单 TU 构建
- **3**: 根因=链接 `-lohavsession` 路径不在默认搜索路径, 解决方案=由编译器 realpath 推导 sysroot 并加 `-L`（R33：未依赖 shell 环境变量）
- **4**: 根因=`src/nowplaying.mm` 默认按 Objective-C++ 编译, 解决方案=编译时显式 `-x c++`

### 知识图谱使用情况

- **引用知识条目**: `DRAFT-m1ddc-apple-ddc-transport-boundary`（macOS 私有 API CLI 的可移植双路径模式，已验证先例 PR #7051）
- **新增知识草稿**: `knowledge/drafts/E543-draft-E6ED.{kv,md}`
- **引擎命中情况**: 未命中正式 E 条目（该归类尚无 promote 条目），沿用草稿先例
- **测试统计**: 总计 15, 通过 15, 失败 0, 跳过 0（断言策略：确定性期望 + 控制动词可显式 SKIP）
- **未覆盖的错误模式**: ①“Objective-C(++) + Foundation/MediaRemote 的 macOS 专属 CLI 在 OHOS 无可编译路径”与②“native AVSessionKit 仅有 provider 侧、无系统级 now-playing 查询控制器”这一组合；已按 R31 落草稿 E543-draft-E6ED

### AI 检视结果

- **检视阶段到达**: 变更摘要已生成；AI 检视最终产出 **3 条意见**（1 条 🔴 Critical + 2 条 🟡 Medium）
- **变更摘要评估**: 摘要内容与改动一致（准确描述了 `__APPLE__` 双路径、可移植分支、软件级索引更新与知识草稿），未见需必须修改的点
- **检视意见数量**: **3 条**（`comment_id` 189536597 🔴 Critical，内含量: 1 个 P1 + 4 个 P3；189539656 / 189539658 🟡 Medium，均为 `seek` 边界校验）
- **检视意见处理**: **已全部闭环**（本人人工驱动，commit 291cd1516e）：
  - 189536597 的 P1（`OH_AVSession_Create` 签名“疑似颠倒”，bot 自评置信度 0.4）→ **reject（误报）**：`native_avsession.h:157-158` 声明为 `(sessionType, sessionTag, bundleName, abilityName, out)`，本包调用顺序一致；且本地 clang 编译通过、W3 全门禁 pass、CI #46861 `conan-build-test ✅`、运行时 `OH_AVSession_Create` 实测 rc=0。已在该讨论串内回复驳回理由与证据。
  - 同条内 4 个 P3（`get` 输出契约不一致 / `seek` 未覆盖 NaN·Inf / 测试 7-8 断言过宽 / 审计文件范围失实）→ **accept 并修复**（`f118725f89` 差异表+确定性断言，`291cd1516e` `seek` 边界加固，audit rev3 重算范围），已在该讨论串内回复。
  - 189539656 / 189539658 🟡 Medium → **accept 并修复**（`std::isfinite` + 上界 9.0e15 + 拒绝负数；新增 4 条断言），`resolve-comment` 实测已置 `resolved=True`。
  - 说明：`scripts/gitcode_pr.py monitor-review` 因工具 bug 反复失败（见「自动化补全」第 2 条），submit 的 AI Review 监控在 `获取检视状态失败，重试…` 空转直至人工介入

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（L0/L1/L2/L4/L5 + JC/KC + L1e 破坏性反向验证）
- **远程 CI (PR 校验)**: 通过（最终 **build #46861**，worker OpenHarmonyPCDeveloper-CI-021；`git-clone`/`checkout-pr`/`conan-setup`/`conan-build-test`/`cleanup` 全 ✅）
- **CI 失败原因**: 多轮 build（#46823 / #46841 / #46854）红，根因均为 **CI worker 基础设施故障**——`git-clone` 日志 `eError loading shared library libz.so: (needed by /data/service/hnp/bin/git)`（exit 127），连带 `cleanup` 报 `can't open input file: ci/conan/cleanup.sh`；与本包无关，`/rebuild` 重试即绿

### 效率分析

- **HANDOFF 次数**: 2（`pr_body_incomplete`、`pr_creation_failed`）
- **重试次数**: CI `/rebuild` 共 5 次（4 次撞到坏 worker）；`submit` 因工具缺陷重跑 3 次；检视闭环人工操作 6 次 API 调用
- **关键瓶颈**: ①`create-pr` 只认目标仓分支——分支必须推到上游 `OpenHarmonyPCDeveloper/build_in_harmonyos`（推 fork origin 会报 `Can not find the branch ... in project: build_in_harmonyos`）；②`monitor-review` 工具崩溃导致检视阶段无法机器化推进；③本地 `finish/W3` 会把 `conandata.yml` 临时改写为 gh-proxy 镜像 URL 列表且未还原，提交前须人工复原
- **耗时较长的步骤**: PR 创建失败排查（fork/上游分支定位）与 AI 检视空转等待
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 7 个事件（含 3 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-14T13:34:16 | handoff:pr_body_incomplete | PR body 有 1 处 (待填写占位符) 未填充 \| 请编辑 /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/n/nowplaying-cli/2.1.0/reports/pr-body.md 补充以下内容： \|   - 上游仓库地址（如 conandata.yml 中无） |
| 2026-09-14T13:35:58 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/nowplaying-cli-2.1.0 --target main --title 'feat(nowplaying-cli): 2.1.0 适配完成' |
| 2026-09-14T13:38:14 | skeleton_created | pr_created |
| 2026-09-14T13:38:14 | pr_created | PR #9947 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/9947 |
| 2026-09-14T14:12:55 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-14T14:12:55 | skeleton_exists | resume_pr_exists |
| 2026-09-14T14:42:59 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #9947 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 9947 \| 摘要出现后: python3 scripts/ohc-run.py submit nowplaying-cli 2.1.0 --resume |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`scripts/ohc/preflight.py:570` PF9 判据对 R38 软件级文件必然误报（阻塞级）**：判据 `bad = [f for f in arch if len(f.split("/")) < 5]` 会把 `archives/<字母>/<包>/{commands.json,manifest.yaml,README.md}`（4 段路径）判为“缺版本目录层”。而 PF8 又要求 CLI 包的 `commands.json` 必须含本次版本号，因此**任何符合 R38 的 CLI 包首次适配 PR 都不可能同时通过 PF8 与 PF9**，只能以 `OHC_PREFLIGHT=0` 绕过整道闸门（连带失去 PF7/R52 的保护）。建议：PF9 对这三个软件级已知文件（`commands.json`/`manifest.yaml`/`README.md`）豁免，或仅当**全部**变更都在软件级时才判定“No packages to build”。
2. **`create-pr` 缺 fork 支持**：`body = {"head": args.source, ...}` 直接提交裸分支名，GitCode 在目标仓找不到分支即 400（`Can not find the branch: <branch> in project: build_in_harmonyos`）。CONTRIBUTING 写的是 `git push origin <branch>`（fork），两者矛盾。建议：`create-pr` 自动探测 origin 的 fork owner 并以 `owner:branch` 形式提交 head，或在 Gate 0 提示“分支须存在于目标仓”。
3. **CI/AI 门禁需与分支状态对偶**：R42 说“CI 是评论触发型”，但首次创建 PR 后无人评论 `/rebuild` 则 CI 永不启动；建议 `create-pr` 成功后自动发一次 `/rebuild`（幂等）。

### 模板改进

1. **PR body 模板把“新增测试用例数”错填成“上游用例数”**：自动生成的 `report/pr-body.md` 在“上游库测试用例统计”里填了本包 test_package 的用例数（本次为 10），并写出“是否存在对上游测试用例的修改？是”，与 `MANIFEST.yml` 中真实的上游审计结论（discovered=0）自相矛盾。建议：从 `test_package/MANIFEST.yml` 的 `upstream_tests_exist` / `upstream_test_audit` 取值填充该表，上游无测试时该表固定为 0 并注明“已审计”。
2. **模板自带“已知限制: 无”占位**：当 recipe 存在平台能力缺口（如本例 `get` 无法读取系统播放器信息）时，“已知限制: 无”会形成误导。建议改为从 `notes.md`/`README.md` 的差异表自动提取，或至少在模板中提示“如有平台限制必须如实填写”。
3. **`test-report.md` 与 `manifest.yaml` 的 `build_system` 语义**：`build_system: makefile` 指上游构建系统，但本仓实际执行的是直接编译器调用，容易在审阅时被读作不一致。建议模板提供 `build_system_note` 字段或明确“指上游构建系统”。

### 自动化补全

1. **`finish`/W3 结束后必须自动还原 `conandata.yml`（回归 bug）**：本地 `finish`（W3 跑真实 `build_and_test.sh`）会把 `conandata.yml` 的 `sources.url` 改写成含 `gh-proxy.com` 的镜像 URL **列表**，且运行日志虽打印“已还原为官方 URL”，实际文件仍是镜像列表（本次实测两次复现）。后果：若直接提交，PF7/R39 直接命中（属 579 例同类违规）。建议：在 `finish` 收尾强制校验 `sources.url` 为单一 https 官方 URL，不符即还原并告警。
2. **`scripts/gitcode_pr.py monitor-review` 崩溃（阻塞级）**：`cmd_monitor_review` 抛出 `NameError: name 'unreplied_opinions' is not defined`（引用未定义变量，疑为重构残留）。后果：`submit` 的 AI Review 监控无法机器化，只能人工介入；建议修复为使用 `review_opinions`（或补齐真实变量名），并补一条 handler 级自测。

   **⚠️ 更严重的连带后果：检视闭环校验 fail-open（以 PR #9947 为实证）**。`scripts/ohc/submission.py:1629 _verify_review_closure()`（及 1629–1650 整段）依赖 `monitor-review` 产出的 `unreplied_opinions` 字段；该命令一崩即返回空值，于是闭环校验被当成“无未处理意见”通过，**即便 PR 上存在未回复/未解决的检视意见，submit 仍能走到 success 并上报**。本次实证：PR #9947 当时实有 3 条 atomgit-bot 检视意见（1 条 🔴 Critical 内含 P1 + 4 条 P3、2 条 🟡 Medium），而 `submit` 未见任何阻塞即上报 success（首版 result.json `status=success`）。建议：①`_verify_review_closure()` 在 `monitor-review` 异常时改为 **fail-closed**（宁可阻断也不放行）；②直接从 `/pulls/{n}/comments` 拉取并统计 `resolved == false` 且无 `cumt-7` 回复的意见，不依赖会崩的子命令；③补一条“存在未闭环意见时 submit 必须返回非 0”的回归测试。
3. **`lang-preflight` 语言判定需覆盖 Objective-C(++)**：`.m/.mm` 不在 `_EXT_LANG`/`_C_EXTS`/`_CPP_EXTS` 中，导致 macOS ObjC 工程被判成 `mixed`（依据竟是唯一一个 `.pl` 辅助脚本），结论虽方向正确但证据误导。建议：把 `.m/.mm` 归入 “other/objective-c” 并优先按源码主体占比判，或至少在 evidence 中显式标注“发现 N 个 .m/.mm（未计入统计）”。
4. **`search-url` 噪声**：对 `nowplaying-cli 2.1.0` 返回的 4 个 URL 全部无关（savannah `download.savannah.nongnu.org/releases/nowplaying-cli/...`、`waterlan.home.xs4all.nl/...`），若 AI 盲从会拉到错误源码。建议对候选 URL 做名称/内容存在性校验后再展示。
5. **检视意见 API 三处不生效（第 3 个工具缺陷，附原文）**：
   - **`in_reply_to` 被忽略**：`handle-review-opinion` / `reply-comment` 走 `POST /pulls/{n}/comments` 带 `in_reply_to`，但 GitCode 不回显该字段 —— 实测本人 6 条回复在 API 中 `in_reply_to = None`、`in_reply_to_id = None`，即**全部变成独立评论而非讨论串内回复**（工具内部已有该 warning 分支，但无法自救）。
   - **`resolved` 只能经 `discussion_id` 置位**：`handle-review-opinion` 内部 `PUT /pulls/{n}/comments/{comment_id}` 返回 `404 {"error_message":"discussion not found."}`（本包收到 4 次，含 `trace_id c05db19b…`/`abb87c90…` 等）；改用 `resolve-comment --discussion-id <discussion_id>` 后**成功**（2 条 Medium 实测 `resolved=True`）。建议 `handle-review-opinion` 在拿不到 discussion_id 时回退用 `comment_id → discussion_id` 映射再 PUT。
   - **`get-review-comments` 完全不读 `resolved`**：`scripts/gitcode_pr.py:898` `unresolved = []` 与 `:920` `unresolved.append(...)` 对每条 review 评论**无条件追加**，因此永远输出「待处理审查意见: N 条」。实证：2 条 Medium 已 `resolved=True`，该命令仍报 `待处理: 3 条`。建议按 `resolved == false` 过滤。
   - 另：**部分评论类型平台不可 resolve** —— 对 `189536597`（“#### 代码审查” 汇总评论）执行 `resolve-comment` 返回 `400 {"error_message":"This type of note can not be resolved."}`（`trace_id 1b2014ddd721c2cb5009ae25f7084350`）；此类意见按平台语义只能由审阅人处理，SKILL 的闭环判定应把该类型排除在“必须 resolved”之外（改为“必须已在讨论串回应”）。

### 知识图谱覆盖

1. 建议将本次草稿 `E543-draft-E6ED`（macOS Objective-C “now playing” CLI 的可移植落点：`__APPLE__` 双路径 + 诚实空结果）与既有 `DRAFT-m1ddc-apple-ddc-transport-boundary` 合并提升为正式 E 条目（**Apple 私有 API CLI 在 OHOS 的可移植分支模式**），因为已有两个独立实例（m1ddc / nowplaying-cli）。
2. 建议新增一条工具类知识：**“CI worker `git` 缺 libz.so 导致 git-clone 步骤失败（exit 127）→ 判定为基础设施故障，直接 `/rebuild` 换 worker 重试而非改配方”**，可避免把环境故障误诊为配方问题（R41/R44 已有止损口径，但缺该具体签名的匹配条目）。
3. 建议补一条 **“契约保真度”类知识**：可移植分支若宣称“与上游 1:1/逐字一致”，必须逐项对照上游源码（命令分发条件、参数个数、输出序列化、帮助文本字面量、命令语义）并留下对照表；否则应改为“差异表 + 准确表述”，避免无证据的保真声明（本次审阅即以该点打回）。

---

## 作者

- **姓名**: KomoreBI
- **邮箱**: apfdAmUcwlJi0M55.cumt-7@noreply.gitcode.com
- **Agent ID**: F044
- **生成时间**: 2026-09-14 13:38:14
- **PR 编号**: 9947
- **Git Commit**: c16ddc1739
