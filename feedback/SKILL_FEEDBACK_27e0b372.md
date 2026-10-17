# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_27e0b372.md`

---

## 背景

- **软件名称**: kjobwidgets5
- **版本**: 5.116.0
- **构建日期**: 2026-09-27
- **构建系统**: cmake
- **上游仓库**: https://download.kde.org/Attic/frameworks/5.116/kjobwidgets-5.116.0.tar.xz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 1
- **编译依赖**:
- kcoreaddons5/5.116.0
- kwidgetsaddons5/5.116.0
- qt5-qtbase/5.15.2.2
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | kjobwidgets-5.116.0.tar.xz（sha256 eac37f7d…dbe87），基线 147 文件 |
| build | 编译构建 | 成功 | 构建系统: cmake；本地 conan create EXIT=0 |
| conan-verify | 配方验证 | 通过 (Verdict=PASS) | G0/G1/G2/G3/G4 与 L2/L4/L5 全绿，见 reports/conan-verify-report.md |
| finish | 归档收尾 | 完成 | W3 本地 CI 通过（.ci-result.json exit_code=0） |
| submit | PR提交+AI检视+CI | 完成 | PR #13273；CI build #62986 PASSED；检视 2 条已逐条回复 |

### 失败与问题

本次流程遇到 3 类需人工介入的问题，均未造成返工性损失：

1. **制品仓 KF5 链 Qt5 基线分裂**（配方层）：`kcoreaddons5/5.116.0` 精确 pin 无 Widgets 的 `qt5-qtbase/5.15.2`，而本包需 Widgets+DBus 的 `5.15.2.2`，图求解直接报 `Version conflict ... originates from kcoreaddons5/5.116.0`。以 `self.requires("qt5-qtbase/5.15.2.2", force=True)` 消解（非 override，保留消费语义以取 package_folder）；副作用是 kcoreaddons5 随 `--build=missing` 从源码重建。
2. **cmake_find_mode=none 依赖的 config 不可发现**：`kcoreaddons5`/`kwidgetsaddons5`/`qt5-qtbase` 均为 `cmake_find_mode=none`（自带 KF5*/Qt5*Config.cmake），CMakeDeps 不再把其 `lib/cmake` 写入 CMAKE_PREFIX_PATH，导致 `find_package(KF5CoreAddons)` 及已安装 config 内的 `find_dependency()` 双双失败。改为遍历 `self.dependencies` 注入 `lib/cmake`/`lib`/`include`（主配方与 test_package 各一处）。
3. **PR head 被解析到上游同名遗留分支**（流程层，最严重）：上游早已存在同名分支 `feat/kjobwidgets5-5.116.0`（calbee21 于 2026-09-18 的 `stage 5.116.0 recipe` 提交 `dcc2ab7e`，未并入 main、落后 3391 个提交、其配方**不含** force=True）。`create-pr` 用裸分支名作 head，被平台解析到上游命名空间，于是 PR #13273 的 head = `dcc2ab7e`，CI 一直构建旧配方并复现版本冲突。而 `submit` 只执行 `git push origin <branch>`（推 fork），对本 PR 无效。最终按人工确认执行 `git push --force upstream HEAD:refs/heads/feat/kjobwidgets5-5.116.0`（OLD `dcc2ab7e` → NEW `6ca7fad6`，留痕）后 CI 转绿。

此外记录两个非阻塞项：`finish` 的 `gen_summary` 报 `'str' object has no attribute 'append'`（SUMMARY.md 未重生成，非致命）；`submit` 自检 `packaging_present` 要求 `packaging/*.tar.gz`（该目录已被 .gitignore 忽略、ARCHIVE-SPEC v3.0 已声明废弃），本次按仓库既有解法从 conan 缓存导出本地产物补齐。

### 知识图谱使用情况

- **引用知识条目**: E537（OHOS CMake 平台无 soname 标志 → DT_SONAME/RUNPATH 修复）、E540（沙箱工具路径缺失同类）、E298/E383/E438（消费端 CTest/CMake 配置注入）——均按 manifest.yaml 的 knowledge_ref 挂载
- **新增知识草稿**: 本次实际新增 `knowledge/drafts/E429-draft-AC34.{kv,md}`（KF5 链 Qt5 基线分裂 + find_mode 依赖不可发现）；报告工具统计的“7 条”为草稿目录累计计数，非本次独占
- **引擎命中情况**: 草稿目录累计 2095 条；本次两处踩坑在 pre-scan 阶段**未被提前告警**（见「知识图谱覆盖」建议）
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0（上游 ctest 注册数为 0，套件为空；测试覆盖由 test_package 补全承担）
- **未覆盖的错误模式**: (a) KF5 5.116.0 链的 **Qt5 基线分裂**（同链不同包 pin 了 `5.15.2` 与 `5.15.2.2` 两个变体）→ `Version conflict: Conflict between qt5-qtbase/5.15.2 and qt5-qtbase/5.15.2.2`；(b) **cmake_find_mode=none 依赖的 CMakeDeps 副作用** → `Could not find a package configuration file provided by "KF5CoreAddons"`。二者已沉淀为 E429 草稿，但尚未提升为正式条目、也未被 pre-scan-rules.yaml 覆盖，导致本次在本地 W3 阶段才暴露（重复踩坑）。

### AI 检视结果

- **检视阶段到达**: Phase 1~4 完成（变更摘要 → 检视意见 → 逐条处理 → 进入 CI 监控）
- **变更摘要评估**: 摘要对配方本体（依赖声明、OHOS 适配项、消费者测试）识别准确；但其中 `test_package/kjobwidgets5_test.cpp`、`conandata patches 为空数组`、`archives/k/kjobwidgets5/manifest.yaml（status: draft）` 均属被覆盖的旧 head（`dcc2ab7e`）批次，与实际提交不符——这是 head 错位的连带影响，已随强推修正
- **检视意见数量**: 2 条（P2 ×1、P3 ×1；无 P0/P1，平台侧显示“阻塞 0 / 建议 1”）
- **检视意见处理**: 2 条全部 **reject**（讨论串内回复 comment 191791428，附逐条证据）。两条均针对旧提交 `dcc2ab7e` 的文件名与内容：P2 称“test 无断言、失败分支同样 app.quit()、退出码仅超时路径非 0”——现版本 `test.cpp` 含 **16 条 `check()`** 断言并以 `return g_failed == 0 ? 0 : 1` 映射退出码；P3 称“未注入 `$<TARGET_FILE:KF5::JobWidgets>`、SONAME/RUNPATH/offscreen 断言缺失”——现版本 `CMakeLists.txt:23` 已注入 `KJOBWIDGETS_SO_PATH="$<TARGET_FILE:KF5::JobWidgets>"`。故无需代码改动，并以 CI 用正确 SHA 通过（#62986）作为佐证。

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`.ci-result.json` exit_code=0；L1e 破坏性反向验证通过）
- **远程 CI (PR 校验)**: 通过（build #62986，conan-build-test / L0 结构完整性 / L1 测试执行验证 全绿）
- **CI 失败原因**: 首轮 #62956 失败，根因**非配方内容**而是 head 错位——CI checkout 到上游遗留提交 `dcc2ab7e`（无 force=True），复现 `Version conflict`。R44 `diagnose` 二次归类为“网络问题”属误判，实际由评论内嵌完整日志中的 `Version conflict ... originates from kcoreaddons5/5.116.0` 与 `head.repo=OpenHarmonyPCDeveloper` 交叉定位。

### 效率分析

- **HANDOFF 次数**: 5 次（`w3_local_ci_failed` ×1、`self_check_failed:packaging_present` ×1、`pr_body_incomplete` ×1、`finish_success` 知识整理 ×2；后两者中 3 次需人工介入修复）
- **重试次数**: 本地 `conan create` 迭代 **7 轮**（版本冲突 → 补丁 hunk 不匹配 → KF5CoreAddons config 未发现 → test_package find_dependency → AUTOMOC 缺 Qt5::moc → 沙箱加载 rc=127 → 符号校验 mangled name 写错）；CI 重跑 **3 次**（#62956 红 → #62962 绿 → #62986 绿）
- **关键瓶颈**: (a) 制品仓 KF5 链基线分裂，需 force=True 并触发 kcoreaddons5 源码重建；(b) **PR head 错位到上游同名遗留分支**——`submit` 只推 origin(fork)，对本 PR 完全无效，白跑一轮 CI（#62956）后才发现；(c) 本地沙箱不解析 `LD_LIBRARY_PATH` 且拒绝执行用户路径 ELF（rc=127），导致 test_package 的 16 条断言无法在本地断言级验证，只能走链接级兜底证明。
- **耗时较长的步骤**: `submit` 的 AI Review/CI 监控（首轮通过评论未标 SHA、其后又紧跟一条 pending 评论，`_monitor_ci` 取“最后一条”得到 UNKNOWN，success 被误降级 partial，须补一次干净重跑才转 PASSED）；其次是 `finish` 的 W3 本地 CI 与配方 7 轮调试。

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 6 个事件（含 2 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-27T18:24:37 | handoff:self_check_failed | 自检未通过: ['packaging_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit kjobwidgets5 5.116.0 |
| 2026-09-27T18:29:05 | handoff:pr_body_incomplete | PR body 有 1 处待填空字段未填充 \| 请编辑 /storage/Users/currentUser/build_in_harmonyos-kparts5/archives/k/kjobwidgets5/5.116.0/reports/pr-body.md 补充以下内容： \|   - 上游仓库地址（如 conandata.yml 中无） |
| 2026-09-27T18:31:01 | skeleton_created | pr_created |
| 2026-09-27T18:31:01 | pr_created | PR #13273 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/13273 |
| 2026-09-27T18:34:33 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-27T18:34:33 | skeleton_exists | resume_pr_exists |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

**问题**：`submit` 只执行 `git push origin <branch>`（推 fork），但 PR 的 head 可能落在**上游同名分支**上——本 PR #13273 即如此（上游已存在 `feat/kjobwidgets5-5.116.0`，属 calbee21 的遗留提交）。结果是：本地把修正后的提交推到了 fork，PR head 却始终指向上游旧提交，CI 持续构建错误内容（#62956 复现旧配方的 Version conflict），而 `submit --resume` 完全无法自愈——“检查 CI → 失败 → HANDOFF”循环空转。

**建议**：在 R42/R50 增加 **head remote 探测**：
1. `create-pr` 成功后立即 `GET /pulls/{n}`，比对 `head.repo.full_name` 与本地 `origin` 的 owner/repo；
2. 不一致时**明确告警**并给出两条可选路径（`--push-to=upstream` 强推覆盖同名分支，或改用显式 `head=owner:branch` 重建 PR）；
3. `submit --resume` 的 CI 失败分支在调用 diagnose 前，先做该探测——避免把“head 错位”误诊成编译/网络问题（本次 diagnose 归为“网络问题”即为误判）。

附带一条同类问题：`junk_check.sh` 的 incremental 模式以 `git diff origin/main...HEAD` 为范围，而 fork 的 `origin/main` 可能是严重滞后的引用（本次落后 1432 个提交），导致 JC6 误报“本 PR 涉及 301 个软件包”、JC5 误报他人遗留的 `.staging-verified`。建议该模式在 `origin/main` 明显落后（或存在 `upstream/main`）时自动切换到 `upstream/main` 或 prdiff 模式。

### 模板改进

**问题**：积分赛 PR 模板的「测试用例对比」表在**“上游 ctest 注册数为 0 + 适配后由 test_package 补全”**这一常见场景下（KF5 系包大量如此）缺少标准填法：上游“单元/集成测试”该填 0 还是填“交互式演示程序数”？“鸿蒙特有测试”是否应把 test_package 的断言口径计入？当前只能靠 AI 自由发挥，不同包统计口径不一致，评审难以横向比较。

**建议**：`templates/积分赛事PR模板.md` 增补“场景三变体”示例——上游无正式测试框架（ctest 注册数 0，含交互式 GUI 演示不可自动化）时的标准填法，并明确：
- 「上游用例数」以 **ctest/pytest 注册数**为准，交互式演示单列“其他测试”并注明不可自动化；
- 「鸿蒙特有测试」明确以 test_package 的**断言条数**计；
- 增补“断言级未观测时如何如实申报”的写法（如本次：链接级 N/N 符号证明 + 断言定义数 + 环境限制的技术原因），避免诱导 over-claim（W4 审计已因此判过一次 P1）。

### 自动化补全

**问题（P1，直接导致 success 被误降级）**：`_monitor_ci` / `_verify_ci_green` 取“**最后一条** CI 评论”判定状态。本次时序为：通过评论（build #62962，**未标 SHA**）→ 紧随其后一条“构建触发中 SHA 6ca7fad6”pending 评论 → 于是核验取到 pending → 判 UNKNOWN → `result --status success` 被自动降级 `partial`。虽然 CI 实际已绿，但上报状态错误，需人工补一次干净重跑（让通过评论成为末条）才恢复。

**建议**：改为「**取最新 PASSED/FAILED 且 SHA 与 head SHA 匹配**的评论」，而非“最后一条”；同时让通过评论**无条件携带 SHA**（pending 评论已带，通过/失败评论未带，是本次歧义之源）。

**问题二（自动化缺口）**：`submit` 自检 `packaging_present` 要求 `packaging/*.tar.gz`，但该目录已被 `.gitignore` 忽略、ARCHIVE-SPEC v3.0 已声明废弃、`package_builder.py` 也未注册为 `ohc-run.py` 子命令——每个纯 conan 包都必须手工从缓存导出产物才能过闸（本次即如此）。

**建议**：二选一——(a) `finish` 在 W3 通过后自动从 conan 缓存导出 `packaging/<name>-<ver>-ohos-aarch64.tar.gz`（数据与路径均已具备，可完全自动化）；(b) 对 conanfile.py 配方改为「存在 conan 包产物即视为满足」。(a) 更佳，可同时消除人工步骤与口径不一致。

**问题三（小）**：`finish` 的 `gen_summary` 在本次报 `'str' object has no attribute 'append'`，SUMMARY.md 未重生成；非致命但会掩盖索引一致性，建议加类型防御。

### 知识图谱覆盖

**问题**：本次两处踩坑（KF5 链 Qt5 基线分裂、cmake_find_mode=none 依赖的 config 不可发现）已在本地做出修复并沉淀为 `knowledge/drafts/E429-draft-AC34.{kv,md}`，但：
1. 仍是**草稿**未提升为正式条目，检索（engine/pre-scan）不生效；
2. `knowledge/graph/pre-scan-rules.yaml` **未挂载**该模式，`pre-scan`/`init-build` 的 G0 预评估无法提前告警——这解释了为何本次要到本地 W3/conan create 才暴露冲突；
3. KF5 5.116.0 已经是本仓的**群体性场景**（kconfig5、kcoreaddons5、kitemviews5、kwidgetsaddons5、kguiaddons5 等同链包均涉及），同类踩坑风险高。

**建议**：
1. 将 `E429-draft-AC34` 提升为正式条目（`graph promote`），并在 `pre-scan-rules.yaml` 挂 `prescan_pattern`，匹配 `Conflict between qt5-qtbase` 与 `Version conflict:`、`Could not find a package configuration file provided by "KF` 等特征；
2. 条目内固化两条处置口径：force=True 统一基线（禁止 override=True，会致 package_folder=None）、遍历 `self.dependencies` 注入 `lib/cmake`（覆盖 config 内 find_dependency 链）；
3. 若主编认为 E429 与既有 E541/E537 等条目高度相关，可在 promote 时合并/挂 `similar_to` 关系，便于引擎一次性命中整类问题。

---

## 作者

- **姓名**: Inception662
- **邮箱**: 3389004972@qq.com
- **Agent ID**: 35EB
- **生成时间**: 2026-09-27 18:31:01
- **PR 编号**: 13273
- **Git Commit**: 6ca7fad623
