# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_3da940a6.md`

---

## 背景

- **软件名称**: precomp
- **版本**: 0.4.7
- **构建日期**: 2026-09-04
- **构建系统**: cmake
- **上游仓库**: https://github.com/schnaader/precomp-cpp/archive/refs/tags/v0.4.7.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 1
- **编译依赖**:
无
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | sha256 b4064f9a… 校验一致 |
| build | 编译构建 | 成功 | 构建系统: cmake |
| conan-verify | 配方验证 | 通过 | G0-G4+L2/L4/L5 八门禁全 PASS；G4 无 cache 包 ID 故 L2 走等效手动探测（--version/--help rc=0 留证）；test_package 5/5（HMBS total=5 passed=5） |
| finish | 归档收尾 | 完成 | 警告均已闭环：packaging 缺 tar 用 PackageBuilder 补齐、notes 结束标记与知识引用已补、conandata.yml.ghfast-bak 镜像注入残留已删除（git add -n 自查拦截） |
| submit | PR提交+AI检视+CI | PR #8196, CI 通过 | AI Review: 代码审查「未发现问题」+ 逐条回复闭环；CI 构建 #39115 全绿 |

### 失败与问题

- **1**: 根因=CMake 4.x 拒绝配置：Compatibility with CMake < 3.5 has been removed, 解决方案=上游 cmake_minimum_required(VERSION 3.2)
- **2**: 根因=if(UNIX) 分支不生效，代码走 Windows 路径（windows.h/conio.h）, 解决方案=本机 cmake 自动探测 CMAKE_SYSTEM_NAME=HarmonyOS，CMake 对该系统名不设 UNIX 变量（实测 UNIX 为空），-DUNIX/-DLINUX/C99/Threads 全不生效
- **3**: 根因=conan-verify L2 冒烟（--version/--help 探测 rc）失败：precomp 把长选项当输入文件名，exit(1), 解决方案=上游无 GNU 风格长选项；无参/usage 路径均 exit(1)
- **4**: 根因=`-r` 还原默认输出名 = PCF 头内原文件名，输出已存在时交互式询问覆盖（脚本化卡死风险）, 解决方案=上游交互设计

### 知识图谱使用情况

- **引用知识条目**: knowledge/doc/E092.md, knowledge/doc/E503.md, knowledge/drafts/DRAFT-precomp-cli-scripting-traps.kv, knowledge/drafts/DRAFT-precomp-roundtrip-test-design.kv
- **新增知识草稿**: 5 条
- **引擎命中情况**: 草稿目录 117 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0（上游无测试套件；test_package 消费者测试 5/5 通过，另见 MANIFEST.yml assertion_count=5）
- **未覆盖的错误模式**: ①refresh-patch 流程外的编辑器全文件尾随空白清理会污染大源文件补丁（8320 行 precomp.cpp 首版 +50/-36）——知识库无「补丁污染检测/防护」条目；②gitcode_pr.py monitor-review 的 `unreplied_opinions` NameError（gitcode_pr.py:1066）导致 submit Phase 1 恒定「获取检视状态失败」直至 30 分钟超时——工具缺陷类模式无条目；③CI 评论迟迟不出现时需手动 /rebuild 触发（本次 PR 创建 45 分钟无 CI 动静，trigger-ci 后 5 分钟内出结果）——CI 触发时序模式无条目

### AI 检视结果

- **检视阶段到达**: 完整走完（摘要生成 → 意见产出 → 逐条响应）
- **变更摘要评估**: 摘要准确概括本次适配（配方参数注入解决 CMake 4.x/平台分支问题、GNU 长选项补丁、5 项消费者断言、零依赖 vendored 结构、知识草稿沉淀），与实际交付一致，无需修改的点
- **检视意见数量**: 1 条（Info 级，「代码审查 ✅ 未发现问题」，无 Blocker/Suggestion 级意见）
- **检视意见处理**: handle-review-opinion accept 回复（确认无待修复项及依据），API 对该普通评论类型不支持 resolve 标记（服务端 400 "This type of note can not be resolved"），回复已留痕，RV-27 闭环达成

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 通过 (PR 校验)（构建 #39115，worker OpenHarmonyPCDeveloper-CI-020：Conan test_package 通过、L0 门禁通过、L1 门禁通过，全部 7 步 ✅）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 4 次（pr_creation_failed 预期型 → resume_no_state 状态文件位置 → ai_review_summary_timeout 工具缺陷型 → feedback_placeholders_remain 当前阶段）
- **重试次数**: 3 次 submit --resume（状态文件移位 1 次、Phase1 超时重入 2 次）；外加手动 trigger-ci 1 次
- **关键瓶颈**: ①monitor-review NameError 使 Phase 1 状态查询 100% 失败，白等 30 分钟×2 轮（约 60 分钟纯等待）；②CI 评论不自动出现，需人工识别并 /rebuild；③review_phase 状态机依赖 monitor-review 输出，其崩溃后只能人工读评论推进 phase（本次手动置 5 跳过）
- **耗时较长的步骤**: AI Review 等待（摘要 12:30→实际已生成但检测不到，等待与重试合计约 60 分钟）、CI 触发等待（45 分钟无动静→手动触发）、补丁污染事故修复（orig 还原 + 字节级替换 + 重验证，约 25 分钟）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 11 个事件（含 3 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-04T12:28:39 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/precomp-0.4.7 --target main --title 'feat(precomp): 0.4.7 适配完成' |
| 2026-09-04T12:32:22 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-04T12:32:22 | handoff:resume_no_state | 状态文件 .submit-state.json 中无 PR 编号 \| 请重新提交: python3 scripts/ohc-run.py submit precomp 0.4.7 |
| 2026-09-04T12:32:29 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-04T12:32:30 | skeleton_created | resume_pr_exists |
| 2026-09-04T13:02:34 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #8196 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 8196 \| 摘要出现后: python3 scripts/ohc-run.py submit precomp 0.4.7 --resume |
| 2026-09-04T13:19:21 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-04T13:19:21 | skeleton_exists | resume_pr_exists |
| 2026-09-04T13:29:07 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-04T13:29:07 | skeleton_exists | resume_pr_exists |
| 2026-09-04T13:29:09 | ci_passed | PR #8196 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **修复 gitcode_pr.py monitor-review NameError**（gitcode_pr.py:1066 `unreplied_opinions` 未定义）：这是 submit 状态机 Phase 1/3 的唯一状态来源，崩溃导致 30 分钟盲等超时。建议变量改为 `review_opinions` 或补定义，并在 CI 对 scripts/ 的回归里加一条 `--json monitor-review` 冒烟。
2. **submit-state 位置提示**：`resume_no_state` HANDOFF 未说明状态文件应位于版本目录（archives/p/{pkg}/{ver}/.submit-state.json）而非仓库根——首次踩坑只能靠读源码。建议 HANDOFF 文案补充完整路径模板。
3. **CI 触发看护**：PR 创建后若 N 分钟无 ohpcd-robot 评论，submit 应自动尝试 trigger-ci（/rebuild）再进入轮询，避免人工识别空窗（本次空窗 45 分钟）。
4. **preflight PF0 通道缺陷**：gitcode_pr.py 内嵌 preflight 子进程在本机解析不到 'git'（PATH/posix_spawn symlink 问题），而独立运行同脚本可通过——建议与 preflight 相同的 `shutil.which` 解析模式。

### 模板改进

1. **pr-body.md 自动填充的统计表**：上游无测试套件时「适配后统计」仍全 0、「是否修改上游测试」误填「是」、notes.md 的表格行会泄漏进「上游测试用例修改说明」小节——建议 submit 生成时对 `type: none` 的 test_results 走「无套件」分支（统计表填 test_package 断言数、修改说明勾「否」），并按标题切分 notes 注入而非整段拼接。
2. **manifest patch_classification 被 refresh-patch 重置**：二次 refresh-patch 会把人工分类（type/platform_only/guard）回写为 pending 默认值，覆盖先前编辑——建议 refresh-patch 合并而非覆盖既有 classification 段。
3. **conan-init 对 vendored 依赖的识别**：conan-init 依源码顶层形态误判 autotools（本例实为 CMake）——建议增加 CMakeLists.txt 探测权重。

### 自动化补全

1. **ghfast-bak 残留清理自动化**：conan-verify 自动注入镜像后留下的 conandata.yml.ghfast-bak 在 finish/submit 前应自动删除或在 git add 阶段自动排除（本次靠 git add -n 人工自查拦截）。
2. **W4 审计结果注入**：pre_pr_audit.py generate 产生的审计输入已含全部变更内容，AI 审计后写 audit-result.json 仍需人工对齐 povray 格式——建议提供 `--self-audit` 骨架生成（含 checks 四段结构）减少手写 JSON。
3. **补丁污染检测**：refresh-patch 前对源文件做「非目标文件的空白级 diff 占比」检查（本次 +50/-36 中 45 行为无关空白清理），超阈值即告警，防止编辑工具全局清理混入补丁。

### 知识图谱覆盖

1. **建议新增「编辑器空白清理污染补丁」条目**（草稿候选：E-patch-whitespace-pollution）：症状=refresh-patch 产出远大于功能改动的 diff；根因=编辑工具对大文件做全局尾随空白/缩进规整；解法=orig 基准还原 + 字节级 replace 重做修改 + `git apply --stat` 行数核对。本次实际发生且修复成本 25 分钟。
2. **建议新增「CI 评论未触发需 /rebuild」条目**：症状=PR 创建后 ohpcd-robot 长时间无评论；解法=gitcode_pr.py trigger-ci 手动触发后 ~5 分钟出结果。与 worker 环境缺陷类（先例多起）不同，这是触发时序问题。
3. **E503（CLI 无 --version/--help）本次精确命中**，其 jshn 先例指引的补丁模式（exit(0) + help_requested 布尔）可直接复用——建议在 E503 中补充 precomp 案例（round-trip 工具的 usage 路径 exit 语义改造）。
4. **DRAFT-E321（CMAKE_POLICY_VERSION_MINIMUM）与 E092（CMAKE_SYSTEM_NAME=Linux）组合命中**：CMake 4.x + HarmonyOS 双问题叠加场景已两次出现（abcmidi、precomp），建议考虑合并为「CMake 平台/版本双适配」复合条目或在两条目互加交叉引用。

---

## 作者

- **姓名**: ningyu
- **邮箱**: 405888464@qq.com
- **Agent ID**: 78EB
- **生成时间**: 2026-09-04 12:32:30
- **PR 编号**: 8196
- **Git Commit**: 4a3a488fd6
