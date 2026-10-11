# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_adbbb374.md`

---

## 背景

- **软件名称**: yuview
- **版本**: 2.14
- **构建日期**: 2026-10-02
- **构建系统**: qmake
- **上游仓库**: https://github.com/IENT/YUView/archive/refs/tags/v2.14.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 6
- **编译依赖**:
- qtbase/6.11.1.3
- **最终状态**: PR 已提交（#14455），远程 CI 受平台基建故障阻塞，配方侧验证全绿

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 官方源 tag v2.14，SHA256 cde4e572… |
| build | 编译构建 | 成功 | 构建系统: qmake；11/11 上游 QtTest 通过 |
| conan-verify | 配方验证 | 通过 | G1-G4 全 PASS，G2 干净 conan create 成功；report 见 `archives/y/yuview/2.14/reports/conan-verify-report.md` |
| finish | 归档收尾 | 完成 | status=published；W3 本地 CI 模拟通过（L0/L0i/L0j/L0k/L0m + KC + JC 全过） |
| submit | PR提交+AI检视+CI | PR 已建，CI 受阻 | PR #14455；AI Review 30 分钟内未产出摘要/意见；远程 CI 2 轮红（平台基建故障），AI Review: 未产出意见 |

### 失败与问题

本次流程未遇到阻塞性问题

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 7 条
- **引擎命中情况**: 草稿目录 2721 条
- **测试统计**: 上游 11/11 通过 + 消费者 4 断言通过（本报告自动解析出 0，见「模板改进」——`_extract_test_summary` 仅识别 `| 通过 | N |` 形式的表格，未适配本包 test-report.md 的写法）
- **未覆盖的错误模式**: 三类本次实测但图谱未命中（引擎对 G0/G2 报错返回的是不相关条目 E540/E219 等）：①QMake 项目在 `CONFIG+=testcase` 下触发 `qt_functions.prf` 的宿主系统白名单校验，非 Linux/Windows/macOS 宿主一律 `error("Operating system not supported.")`，需以 `QMAKE_HOST.os=Linux` 显式声明（OHOS 宿主名 HarmonyOS 不在白名单）；②Qt6 moc 产物以非限定名引用内部命名空间（如 `q20::identity`），项目把 `#include "X.moc"` 放在自有 `namespace` 内即编译失败，须移到命名空间之外；③Qt Base 构建为 `FEATURE_opengl=OFF` / `QT_NO_SSL` 时，消费方 `.pro` 的 `QT += opengl` 与源码中 `QNetworkAccessManager::sslErrors`/`connectToHostEncrypted` 需要以 `qtHaveModule()` / `QT_CONFIG(ssl)` 条件化，而非删除模块。

### AI 检视结果

- **检视阶段到达**: Phase 1（仅机器人占位评论「正在生成合并请求摘要…」「AI 代码检视正在进行中…」，30 分钟后仍未产出摘要或检视意见，按流程超时直接进入 CI 阶段）
- **变更摘要评估**: 未产出——`atomgit-bot` 在 30 分钟窗口内只留下两条占位评论，PR 描述与评论均无摘要内容；无法评估
- **检视意见数量**: 0 条（仅有 2 条机器人占位评论，无实际检视意见；`monitor-review` 工具本身抛 `NameError: unreplied_opinions` 无法使用，改用 API 直接轮询确认）
- **检视意见处理**: 无需处理（无实际意见）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 失败（连续 2 轮同一错误，判定为平台基建故障，非配方缺陷）
- **CI 失败原因**: `worker-prep` / `git-clone` / `cleanup` 三步在 0.003–0.004s 内以 `exit code -1` 退出，报 `SSH bridge exec failed: connect failed: connection lost before ready: Connection was refused by other side: 111`；`conan-build-test` 从未执行（故与源码下载、配方内容无关）。佐证：同期同项目其它 PR（如 #14406）以同款 `exit=-1` / `elapsed≈0.0037s` 失败，属跨 PR 的共享基建抖动。CI 看板已按 R44 用 `gitcode_pr.py diagnose` 二次归类，结论亦为「网络问题」但归类粒度不足（真因是 worker SSH 桥接，而非源码 URL 不可达——本包 URL 为官方源且 CI 自带镜像 fallback）。

### 效率分析

- **HANDOFF 次数**: 8 次（记录在时间线的 4 次：submit 自检 `packaging_present`、PR body 占位符、PR 创建失败 ×2；另 4 次发生在 feedback 事件累积启动前：finish W3 的 JC 门禁失败 ×2、conan-verify G2 的 ghfast.top 镜像超时 ×1、submit 的 PF9 前置闸拦截 ×1）
- **重试次数**: 有效重试 6 次（conan-verify ×2、finish ×4、submit ×4、CI `/rebuild` ×2）
- **关键瓶颈**: ①`submit` 自检 `packaging_present` 沿用 DESTDIR 时代口径（R20 已废弃），v3.0 conan 流程必须手工补 `packaging/*.tar.gz` 才能过闸（仓库多地 notes 已登记，如 libpktriggercord）；②PF8 要求 CLI 包在软件级放 `commands.json`，PF9 又要求所有 `archives/` 变更路径 ≥5 段，二者对同一文件互相矛盾（box64 记作框架缺陷 #7/#24，canfigger 记 P1-2），只能 `OHC_PREFLIGHT=0` 留痕通过；③`submit` 建 PR 时 `--source` 传裸分支名在上游项目查不到 fork 分支，须传 `Inception662:feat/yuview-2.14`（工具已按裸名建档并写死，需人工介入）；④W3 收尾会把 `conandata.yml` 改写为 `gh-proxy.com` 镜像 URL 列表，且回滚依赖 `.orig` 备份——本次两次被 W4 审计与人工巡检判为 R39/P0 违规
- **耗时较长的步骤**: ①W3/finish 的 `conan create` 每次约 9–11 分钟（YUViewLib 236 个 cpp + App + 11 个测试目标，`make -j8`）——本次因多轮修复共重跑 4 次；②AI Review Phase 1 空等约 30 分钟无产出；③CI 两轮各约 4 分钟，但均为秒级基建失败

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 4 个事件（含 4 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-03T15:05:54 | handoff:self_check_failed | 自检未通过: ['packaging_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit yuview 2.14 |
| 2026-10-03T15:08:53 | handoff:pr_body_incomplete | PR body 存在 1 处待填写占位符未填充 \| 请编辑 /storage/Users/currentUser/build_in_harmonyos-yuview/archives/y/yuview/2.14/reports/pr-body.md 补充以下内容： \|   - 上游仓库地址（如 conandata.yml 中无） |
| 2026-10-03T15:10:44 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/yuview-2.14 --target main --title 'feat(yuview): 2.14 适配完成' |
| 2026-10-03T15:14:04 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/yuview-2.14 --target main --title 'feat(yuview): 2.14 适配完成' |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`packaging_present` 自检应区分 v3.0 conan 流程**：`_check_packaging_present()` 仍按 DESTDIR 时代口径要求 `packaging/*.tar.gz`，而 R20 已明确废弃 DESTDIR、产物由 `conan create` 管理。建议：配方存在 `conanfile.py` 时直接判 PASS（与 `finish.check_prerequisites` 已有的 v3.0 分支一致），否则要求每轮适配手工造 tar.gz 纯属返工，且该包体量大（30MB）只会拖慢流程。
2. **PF8 与 PF9 的冲突应机械消解**：PF9 的「路径 ≥5 段」规则应豁免 `archives/<字母>/<包>/commands.json` 与 `README.md` 这类 R38 明文要求存在的软件级文件，否则 CLI 包必然二选一失败（本次三个 worktree 先例均以 `OHC_PREFLIGHT=0` 留痕绕过）。建议先修闸，再在文档中删掉「可 `--no-preflight` 跳过」这条被滥用的逃生口。
3. **`submit` 的 PR head 需按 fork 限定**：`cmd_submit` 传 `--source <branch>` 裸名，而仓库约定是 fork(origin)→上游(upstream) 的 PR，GitCode API 在上游项目下查不到该分支（报 `Can not find the branch ... in project`），必须 `--source <fork_owner>:<branch>`。建议由工具从 `git remote get-url origin` 自动推导 owner 拼 head，避免每次人工试错（本次因此多消耗 3 次 HANDOFF）。
4. **AI Review 超时应缩短并有明确出口**：Phase 1 空等 30 分钟且机器人只留占位评论，实际无任何产出。建议 10 分钟无摘要即判 `review_timeout` 并直接进 CI 阶段，同时把 result 的 milestone 标为 `review_pending`，避免把预算耗在空轮询上。
5. **`monitor-review` 子命令存在致命缺陷**：`cmd_monitor_review` 第 1066 行引用未定义变量 `unreplied_opinions`（应为 `review_opinions`），命令必抛 `NameError` 完全不可用，导致只能退回手工 API 轮询。

### 模板改进

1. **PR body 模板应覆盖「上游有测试」场景**：`_generate_pr_body()` 从 `test-report.md` 正则抽 `| 通过 | N |`，本次报告用的是「总测试数」/「通过 (PASS)」等中文表述与上游/适配后双表格，解析结果全为 0，导致 PR 描述写成「上游 0 个测试」，与实际 11/11 严重不符（评测口径 R51 直接要求如实回填）。建议：放宽解析（同时识别上游/适配后两张表）、或在 `test-report.md` 模板中固定字段名并在生成器侧共享同一份模板常量。
2. **`test-report.md` 应提供机器可读摘要块**：建议在模板顶部加一段固定格式的 `<!-- TEST-SUMMARY: total=11 passed=11 failed=0 skipped=0 -->`，让生成器取注释块而非猜表格格式，彻底消除解析漂移。
3. **PR 描述的上游仓库地址应取仓库页而非归档 URL**：conandata 的 `sources.url` 是 tarball 直链，直接被填进「上游仓库地址」字段（本次显示为 `.../archive/refs/tags/v2.14.tar.gz`），语义错误。建议从 URL 反推 `https://github.com/<owner>/<repo>`，或在 manifest 增加 `homepage` 字段优先取用。
4. **`pr-body.md` 的「补丁说明」应取 `patch_description`**：本次生成的内容是文件名重复两次（`0001-...patch: 0001-...patch`），未读取 conandata.yml 里已写好的英文描述，属明显可自动填充项。

### 自动化补全

1. **W3 收尾的镜像改写应改为「不改写官方源」**：`conan_verify` 与 `build_and_test.sh` 都在 `conanfile`/`conandata` 层面临时注入 `ghfast.top` / `gh-proxy.com`，收尾再靠 `.orig` 备份回滚。本次该机制两次留下镜像 URL（一次被人工发现、一次被 W4 独立审计判为 R39/P0），且备份文件残留污染包目录。建议改为在 Conan 客户端侧配置镜像（remote/`tools.files.download:download_cache` 或 CI 侧 `DOWNLOAD_CACHE`），配方文件始终只保留官方单源。
2. **`QMAKE_HOST.os` 判定可自动化**：OHOS 宿主名 `HarmonyOS` 不在 Qt 白名单，属「任何 QMake 项目 + `CONFIG+=testcase` 都必然触发」的系统性坑。建议在 `build-systems.md` 的 QMake 章节补一节，或由 recipe 模板默认注入 `QMAKE_HOST.os=Linux`（OHOS 与 Linux 分支同族）。
3. **`exit=-1` + 秒级耗时应自动归类为基建故障**：`diagnose` 目前把这类失败归为「网络问题/源码下载超时」，与日志真因（`SSH bridge exec failed: Connection refused`，`git-clone` 未执行）不符，会误导 AI 去改源码 URL。建议增加判据：`elapsedTime < 5s` 且 `worker-prep` 失败 → 归类 `infra_failure`，直接写 `loop_pending` 草稿等平台恢复，不进入配方修复循环。
4. **`/rebuild` 触发时机可观测化**：CI 为评论触发型，本次需人工评论两次；建议 `submit` 在 push 后自动触发，并在检测到 `infra_failure` 时指数退避重试而非立即再触发（本次两轮间隔 4 分钟，落在同一故障窗口内）。

### 知识图谱覆盖

建议新增以下 E-entry（本次实测均未命中，且已有草稿方向可合并）：

1. **E-qt-host-os-whitelist**：QMake `qt_functions.prf` 的 `QMAKE_HOST.os` 白名单不含 `HarmonyOS` → `Project ERROR: Operating system not supported.`；修复：`qmake ... "QMAKE_HOST.os=Linux"`。`root_cause`：`testcase.prf` → `qtAddTargetEnv()` 仅接受 Windows/Linux 族/Darwin/AIX 等枚举值。适用范围：所有在 OHOS 上跑 `CONFIG+=testcase` 的 QMake 项目（yuview、algobox 系）。
2. **E-qt6-moc-inside-namespace**：Qt6 moc 产物以非限定名引用 `q20::identity` 等内部命名空间；项目若把 `#include "X.moc"` 置于自有 `namespace` 内 → `no type named 'identity' in namespace <proj>::q20`。修复：将 moc include 移到命名空间外。与已有 `DRAFT-0001-qt6-to-qt5-api-compat.kv` 互补。
3. **E-qt-base-feature-gated-consumer**：Qt Base 以 `FEATURE_opengl=OFF` / `QT_NO_SSL` 构建时，消费方必须条件化而非删除：`.pro` 用 `qtHaveModule(opengl){ QT += opengl }`，C++ 用 `#if QT_CONFIG(ssl)`。补充要点：YUView 这类上游声明了 opengl 但代码从不调用它的项目，条件化即可零功能损失。
4. **E-release-archive-version-injection**：发布归档非 git 仓库，qmake `$$system("git describe --tags")` 返回空导致版本宏退化为 0；修复：保留上游回退再用 `VERSION=` 注入（与 `build-systems.md` 的 QMake 存量要点同源）。
5. **E-w3-mirror-rewrite-leaks**:W3 收尾的镜像 URL 改写未回滚会留 P0 级 R39 违规（本次实例：`conandata.yml` 出现 `gh-proxy.com` 列表 + `.orig`/`.ghfast-bak` 残留）。建议合入上述「自动化补全 #1」的配方侧零改写方案。

---

## 作者

- **姓名**: Inception662
- **邮箱**: 3389004972@qq.com
- **Agent ID**: 2B67
- **生成时间**: 2026-10-03 15:59:01
- **PR 编号**: 14455
- **Git Commit**: 6ca88826f5
