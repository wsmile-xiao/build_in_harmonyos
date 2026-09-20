# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_2cb729ef.md`

---

## 背景

- **软件名称**: kitemmodels
- **版本**: 6.18.0.1
- **构建日期**: 2026-09-16
- **构建系统**: cmake
- **上游仓库**: https://download.kde.org/stable/frameworks/6.18/kitemmodels-6.18.0.tar.xz
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
- qtbase/6.11.1
- qtdeclarative/6.11.1
- ecm/6.26.0
- **最终状态**: 成功

---

## 情况

### 执行概要

全流程：`init-build → 编译 → conan-init → conan-verify → finish（W2 结构 + R36 依赖 + W3 本地 CI）→ W4 独立审计（pass）→ submit → AI Review → CI PASSED → result=success`。

kitemmodels 6.18.0.1 为 `kirigami-gallery` 的前置【依赖项】，目标是把 6.18.0 配方缺失的 QML 模块（`org.kde.kitemmodels`）补进包内，使下游 `kirigami-gallery` 能真机 `import`。

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 上游 tarball `kitemmodels-6.18.0.tar.xz` |
| build | 编译构建 | 成功 | 构建系统: cmake；补 `qtdeclarative/6.11.1` + soname 规则 |
| conan-init | 生成配方/归档骨架 | 完成 | `archives/k/kitemmodels/6.18.0.1` |
| conan-verify | 配方验证 | 通过 | `conan create` 干净构建通过 |
| finish | 归档收尾 | 完成 | W2 结构 + R36 依赖 + W3 本地 CI 全绿 |
| W4 审计 | 独立审计 | pass | P0/P1=0 |
| submit | PR 提交 + AI Review + CI | 完成 | PR #10520，CI PASSED，result=success |

### 失败与问题

- **1（QML 子目录不构建）**: 根因=上游 `src/CMakeLists.txt` 仅 `if(TARGET Qt6::Qml)` 才 `add_subdirectory(qml)`；配方原只 `requires qtbase/6.11.1`，`Qt6::Qml` 不存在 → QML 模块被跳过。解决方案=补 `qtdeclarative/6.11.1` 依赖，使 `Qt6::Qml` 存在并构建 `qml/`。
- **2（OHOS 把相对 `DT_NEEDED` 当路径 → `Cannot load shared library`）**: 根因=OHOS 加载器把插件相对 `DT_NEEDED`（`../../bin/libKF6ItemModels.so`）当**路径**解析。解决方案=用 `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX` 注入 soname 规则修复。
- **3（上游 ctest / 真机验证）**: 上游 ctest **12/12**（含 2 个 QML 用例）；`test_package` 在鸿蒙 PC 真机 `import org.kde.kitemmodels` + 实例化 `KSortFilterProxyModel` + 断言 `rowCount()==5`，通过。

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 6 条
- **引擎命中情况**: 草稿目录 724 条
- **测试统计**: 上游 ctest 12 注册、12 通过、0 失败、0 跳过（含 2 个 QML 用例）；test_package 真机 `import org.kde.kitemmodels` + `KSortFilterProxyModel.rowCount()==5`
- **未覆盖的错误模式**: 上游 QML 子目录的 `if(TARGET Qt6::Qml)` 门控 + OHOS 对相对 `DT_NEEDED` 的路径化解析（建议沉淀 E-entry，见「知识图谱覆盖」）

### AI 检视结果

- **检视阶段到达**: Phase 5 (完成)
- **变更摘要评估**: 确认 `qtdeclarative/6.11.1` 依赖 + soname 规则修复与 `kirigami-gallery` 的 QML 需求匹配。
- **检视意见数量**: 1 条（atomgit-bot，结论「✅ 未发现问题」）
- **检视意见处理**: 核对为"✅ 未发现问题"，无修改点；因平台 `handle-review-opinion` resolve 恒 404，闭环由主管按 CI 实证终态。

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`exit_code=0`）
- **远程 CI (PR 校验)**: 通过（PR #10520）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 4（`self_check_failed`（`manifest_complete`）×2、`ai_review_opinions` ×1、`review_closure_incomplete` ×1）
- **重试次数**: 2（submit 自检 `manifest_complete` 人工补 `build_date` 后重跑 ×1；submit `--resume` 续环 ×1）
- **关键瓶颈**: OHOS 相对 `DT_NEEDED` 路径化解析的定位与 soname 规则修复；review 闭环平台 404
- **耗时较长的步骤**: 上游 ctest 全量 + 真机 QML `import` 验证；AI Review 轮询
- **协作教训**: 同一 worktree 曾被并发 worker 写入；主管因 slug 拼写（单 m/双 m）误判"归档丢失"（权威 slug 为 `kitemodels`，`kitemodels` 为遗留 typo，`conanfile.name`/L0m 门禁为准）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 9 个事件（含 4 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-17T03:04:17 | skeleton_created | result_partial |
| 2026-09-17T11:25:43 | handoff:self_check_failed | 自检未通过: ['manifest_complete'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit kitemmodels 6.18.0.1 |
| 2026-09-17T11:26:55 | handoff:self_check_failed | 自检未通过: ['manifest_complete'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit kitemmodels 6.18.0.1 |
| 2026-09-17T11:29:05 | skeleton_exists | pr_created |
| 2026-09-17T11:29:05 | pr_created | PR #10520 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/10520 |
| 2026-09-17T11:34:10 | handoff:ai_review_opinions | atomgit-bot 已发布 1 条检视意见，请逐条评估并处理： \|  \| ⚠️ 注意：检视意见不一定正确，需严格判断是否合理后再修改！ |
| 2026-09-17T15:11:54 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-17T15:11:54 | skeleton_exists | resume_pr_exists |
| 2026-09-17T15:11:55 | handoff:review_closure_incomplete | PR #10520 有 2 条检视意见未回复（闭环未完成）： \|  \|   - comment_id: 190131508: #### 代码审查  ✅ 未发现问题     - comment_id: 190131916: 🔁 @2301_77929998 已收到 /rebuild，CI 调度处理中…  |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

本次 klibc / kcoreaddons5 / kconfig5 / kitemodels 四库串行执行，暴露以下 harness 缺陷（逐条）：

1. **`junk_check.sh` 在归档未提交时退化为 full 模式**：`git diff origin/main...HEAD` 为空 → 回退 `git ls-files` 全仓扫描，把 main 中他人归档的历史垃圾 `archives/c/cloog/0.21.1/{.build-closed,.staging-verified}`（`906cc59ae` 误提交）算作本包失败，阻断首次 finish。规避：**finish 前先提交本次归档**（走 incremental，与 CI 的 prdiff 语义一致）。建议 full 模式限定本次 `CI_PACKAGES` 路径，并另开清理 PR 移除 cloog 那两个文件。
2. **`gitcode_pr.py monitor-review` 的 `unreplied_opinions` 未定义 → NameError**：该子命令每次崩溃，submit Phase 1 永久"获取检视状态失败"直到 30min 超时（09-03 poster 任务也踩过同一处）。已本地热修。
3. **`submission.py::_call_monitor_review` 把 `--json` 传在子命令之前**（`--json` 是子命令级参数）→ JSON 永不输出、`--- JSON ---` 标记不出现 → 即使修了 #2 仍失败（`_verify_review_closure` 的顺序是对的，两处不一致）。已本地热修。
4. **`handle-review-opinion` 的平台侧 discussion resolve 恒 404**（`discussion not found`）：回复落不进讨论串 → `_verify_review_closure` 永远判"未闭环"；最终只能按"CI 实证绿 + 零实质缺陷"由主管写终态。建议 resolve 失败时降级为普通评论，并把闭环判定与"意见是否实质需要修改"解耦。
5. **`classify_comment` 把 CI 调度通知误判为检视意见**：ohpcd-robot 的"🔁 已收到 /rebuild，CI 调度处理中…"被算成 `review_opinion` → 闭环里多出必须回复的假意见。
6. **`create-pr` 假超时**：klibc 首次报超时并 HANDOFF，`list-prs` 证实 PR 未创建，重跑即成功。建议区分"请求已提交但响应超时"与"未创建"，并在重试前自动 `list-prs` 校验。
7. **PF8 ⟷ PF9 自相矛盾**：PF9 要求变更路径 ≥5 段（`archives/<字母>/<包>/<版本>/...`），而 PF8/R38 要求 CLI 包**必须**有软件级 `archives/<字母>/<包>/commands.json`（仓库 2110 个先例）→ 新 CLI 包 PR 必被 PF9 拦。用户拍板走 `OHC_PREFLIGHT=0`（PR 正文写明理由留痕）。
8. **`submit` 的 PR 标题硬编码** `feat(<包>): <版本> 适配完成`，无 `--title` 入口 → §10.2 要求的 `【积分赛】/【依赖项】` 前缀只能建 PR 后 `update-pr --title` 改。
9. **`preflight` R52 读带点前缀的 `.audit-result.json`**，与 `submission.py:1028` 的权威路径 `reports/audit-result.json` 不一致 → R52 反欺骗闸永不触发。
10. **环境噪音**：`G0 clean-verify` 固定走 autotools `./configure`，对 CMake/Kbuild 包必然 exit 127（非阻塞但噪音大）；`step5b/step8`（知识图谱他人条目空字段、gen_summary `'str' object has no attribute 'append'`）非致命。

环境/协作教训：
- Windows OpenSSH 会吞双引号，复杂远端命令一律本地写 `.sh`/`.py` 再 scp，避免引用被拆坏。
- 本机 HMDFS 读抖动 + SSH 偶发 `banner exchange` 超时，需失败重试 2–3 次；`git ls-tree` 曾间歇返回空，导致主管误判"归档丢失"，实为**包名 slug 与 worktree 目录名不一致**造成的拼写误导——本库尤其典型：worktree 目录名 `kitemodels5-wt` 是单 m 历史拼写，权威 slug 为双 m `kitemodels`（`conanfile.name` 实证），核对包名一律以 `conanfile.name`/L0m 门禁为准。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

- `manifest.yaml` 模板统一 `build_date` 与 `created_at` 字段（消除 #11 的错配，见「自动化补全」）。
- PR body/title 模板增加 `【积分赛】/【依赖项】` 前缀入口（#8），避免建 PR 后 `update-pr --title` 补改。
- test-report 模板的"测试统计"解析（`_collect_situation`）依赖 `总测试数`/`PASS`/`FAIL`/`SKIP` 行，本批 4 库均被解析为 `总计 0` → 建议模板固定表格列名，或让 collector 直接读取结构化 `reports/*.json`。
- 执行概要表建议内置 `conan-init` / `W4 审计` 行，减少占位符残留。
- 建议在任务书/模板中以 `conanfile.name` 作为包名唯一权威，worktree 目录名不参与任何路径拼接（#20 教训）。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

11. **`_REQUIRED_MANIFEST_FIELDS` 要 `build_date`，而 `conan-init`/finish 只生成 `created_at`** → kcoreaddons5 / kitemodels 的 submit 自检 `manifest_complete` 直接 FAIL（本库连续两次），需人工补字段。建议 init 时同时写入 `build_date`，或校验时兼容 `created_at`。
12. **submit 自检 `packaging_present` 是 v3.0 遗留**（要 `packaging/*.tar.gz`，而 `packaging/` 又被 `.gitignore` 不入 PR）→ 每个库都要手工 `tar czf` 才能过闸。建议删除该检查，或改为从 conan cache 校验归档内产物。
13. **`conan_verify.py` G4 用 `listing["Local Cache"][software][ref]` 解析 `conan list --format=json`**，Conan 2.29 无该层级 → `_cache_path` 丢失 → **L2/L4/L5 静默跳过**（kconfig5 已手工复跑补齐）。建议按 Conan 2.29 schema 解析，且对"解析不到"显式报错而非静默跳过。
- 建议把"finish 前自动提交本次归档"与"submit 自检字段自动补全"做成默认行为，减少人工介入。
- `create-pr` 超时后自动 `list-prs` 校验并幂等重试，避免假超时 HANDOFF。
- `test-report` 的解析结果应回写并自检：若统计为"总计 0"而归档内实际有用例，应告警而非静默。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

- **E-entry**：上游 QML 子目录常被 `if(TARGET Qt6::Qml)` 门控；配方未 `requires qtdeclarative` 时 `Qt6::Qml` 不存在 → QML 模块（`qmldir`/插件）被静默跳过。补 `qtdeclarative/<ver>` 依赖即可启用。（kitemodels）
- **E-entry**：OHOS 把插件相对 `DT_NEEDED`（如 `../../bin/libKF6ItemModels.so`）当**路径**解析 → `Cannot load shared library` → 用 `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX` 注入 soname 规则修复。（kitemodels）
- **E-entry**：OHOS 强校验 `.codesign`；CMake install 期 `file(RPATH_CHANGE)` 原地改写 `DT_RUNPATH` 致签名失效 → `dlopen` `Permission denied` → `symbol not found`（Error 127）。规避 `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`。（kcoreaddons5/kconfig5，E537 类）
- **E-entry**：HarmonyOS 无 CMake platform module，`CMAKE_SYSTEM_NAME=HarmonyOS` 会使 `CMAKE_SHARED_LIBRARY_RUNTIME_*_FLAG` 为空、ECM 的 RPATH 被 `if(UNIX)` 包裹 → 需显式设置 `CMAKE_SHARED_LIBRARY_RUNTIME_{C,CXX}_FLAG=-Wl,-rpath,` 与 `CMAKE_INSTALL_RPATH=$ORIGIN/../lib;…`；同时**不要覆盖 `CMAKE_SYSTEM_NAME`**，否则 `CMAKE_CROSSCOMPILING=TRUE` 会丢掉 `kconfig_compiler` 等 host 工具用例。（kconfig5）
- **E-entry**：HarmonyOS 内核加载器要求本机 ELF 带 `.codesign` 段；strip 会删除该段导致 rc=126 → 禁用 strip，并优先用 `ld.lld`。（klibc）

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: 2301_77929998
- **邮箱**: gmh5787317@163.com
- **Agent ID**: 1101
- **生成时间**: 2026-09-17 03:04:17
- **PR 编号**: 10520
- **Git Commit**: 518e4751d
