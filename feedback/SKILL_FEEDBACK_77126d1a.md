# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_77126d1a.md`

---

## 背景

- **软件名称**: clutter
- **版本**: 1.26.4
- **构建日期**: 2026-09-29
- **构建系统**: autotools
- **上游仓库**: https://download.gnome.org/sources/clutter/1.26/clutter-1.26.4.tar.xz
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
- cogl/1.22.8.1
- glib/2.84.0.1
- cairo/1.18.4.1
- pango/1.56.4
- atk/2.38.0.1.1
- json-glib/1.10.6.1
- gles2/2.0.25
- egl/1.0.5
- fontconfig/2.18.1.1
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: autotools |
| conan-verify | 配方验证 | 部分通过 | G1 FAIL（缺 `export_sources()`，单一静态检查项；独立审计定为非阻断 P2，仓内同类已合并配方亦然）；G2 conan create 由 W3 实测 EXIT=0 |
| finish | 归档收尾 | 完成 | W3 本地 CI 通过（exit_code=0，integrity_hash=c0c8eace40d1cee5，真实依赖链 cogl/1.22.8.1） |
| submit | PR提交+AI检视+CI | 完成 | PR [#14164](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/14164) 创建；远程 CI 构建 #66231 **PASSED**（7/7 步骤 ✅，L0/L1 门禁通过） |

### 失败与问题

- **1**: 根因=目标版本 1.27.4 上游不存在, 解决方案=分支名与实际上游不符
- **2**: 根因=configure 报缺 `cogl-pango-1.0`, 解决方案=clutter 硬依赖该 .pc 且无开关可关；制品仓 cogl/1.22.8 用 `--disable-cogl-pango` 裁剪
- **3**: 根因=configure 报 `No package 'cairo-gobject' found`, 解决方案=cairo/1.18.4 配方 `glib=disabled`，不产 cairo-gobject.pc
- **4**: 根因=图解析报 `Version conflict: fontconfig/2.18.1 vs 2.18.1.1`, 解决方案=cairo 钉 2.18.1，pango 要 2.18.1.1
- **5**: 根因=链接报 `libXau.la ... is not a valid libtool archive`, 解决方案=依赖包 libxcb 的 `.la` 其 `dependency_libs` 指向已清理的构建机临时目录
- **6**: 根因=cogl 编译 `cogl-egl-defines.h` 报缺 `EGL/eglmesaext.h`, 解决方案=该头为 Mesa 专有，OHOS SDK 无（已验证）；cogl 公共头硬包含
- **7**: 根因=cogl 启用 EGL 后链接缺 `std::__n1::mutex` 等 C++ 符号, 解决方案=制品仓 egl/1.0.5 为**静态** `libEGL.a`（C++ 实现）
- **8**: 根因=消费者加载 `libclutter-1.0.so` 报 `libjson-glib-1.0.so.0: needed by ...` + 全部 `json_*` 重定位失败（rc=127）, 解决方案=`json-glib/1.10.6` 的 `.so` 其 `.codesign` 段被 OHOS 加载器判无效：`dlopen` 报 **Permission denied**（`chmod 755` 无效，重新 `selfSign` 后 OK；实测对照见下）
- **9**: 根因=test_package 找不到 `cogl/cogl.h`、`json_*` 符号, 解决方案=手工 `-I/-L` 拼接与真实消费者路径不一致
- **操作**: 根因=`dlopen` 结果, 解决方案=
- **`json-glib/1.10.6` 原样 `.so`**: 根因=❌ `Permission denied`, 解决方案=
- **复制副本 + `chmod 755`（不重签）**: 根因=❌ `Permission denied`, 解决方案=
- **复制副本 + 删除 `.codesign` + `binary-sign-tool selfSign`**: 根因=✅ OK, 解决方案=
- **`json-glib/1.10.6.1`（本仓重签版）**: 根因=✅ OK, 解决方案=

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 7 条
- **引擎命中情况**: 草稿目录 2721 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**: 本次新增 7 条草稿，主要为：①`json-glib` 的 `.codesign` 段被 OHOS 加载器判无效致 `dlopen` Permission denied（`chmod 755` 无效、`selfSign` 可解）——知识库无该加载期签名失效模式；②静态 `libEGL.a`（C++ 实现）致 `std::__n1::mutex` 未解析符号，须在 `.pc` 的 `Libs` 中紧跟 `-lEGL` 追加 `-lc++_shared`（顺序敏感）；③Mesa 专有头 `EGL/eglmesaext.h` 缺口与 stub 双路径安装；④`conandata.yml` 经 W3 局部跑后残留 CI 注入的镜像列表（仅跑单包时 CI 不改写，须还原为官方单一 URL）

### AI 检视结果

- **检视阶段到达**: Phase 1（等待变更摘要）——30 分钟超时，未观察到 atomgit-bot 生成变更摘要
- **变更摘要评估**: 无可用摘要（Phase 1 超时 HANDOFF: `ai_review_summary_timeout`）
- **检视意见数量**: 0（`get-review-comments` 实测返回「代码审查意见 (0 条)」）
- **检视意见处理**: 无需处理（无意见）；CI 已 PASSED

### CI 结果

- **本地 CI 模拟 (W3)**: **通过**（exit_code=0；JC/L0/L1/L4/L5 全 pass，L1e 破坏性反向验证通过，Pass rate 100.0% (1/1)）
- **远程 CI (PR 校验)**: **通过**（构建 #66231，Worker CI-034，7/7 步骤 ✅）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 4 次（`self_check_failed`、`pr_body_incomplete`、`pr_creation_timeout`、`ai_review_summary_timeout`）
- **重试次数**: 3 次（`gitcode_pr.py create-pr` 重试 3 次后才成功；前两次分别因无输出静默挂起与 404 分支不存在）
- **关键瓶颈**: ①`create-pr` 的 preflight 以**本地 `main` 分支**为 diff 基线，而本地 `main` 落后 canonical 上游 1252 个 commit → 变更集膨胀到 5451 个文件，逐文件 git 调用导致命令**静默挂起并超时**（无任何输出）；②PR 头分支须位于 canonical 仓库命名空间，本环境 `submit` 把分支推到 fork 远端 `origin`，canonical 上不存在该分支 → `create-pr` 报 404 `Can not find the branch`
- **耗时较长的步骤**: `finish` 的 W3 本地 CI（clutter 全量 autotools 编译，约 20 分钟）；`submit` 的 AI Review Phase 1 轮询（满 30 分钟超时）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 7 个事件（含 4 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-01T15:40:24 | skeleton_created | result_partial |
| 2026-10-01T16:09:57 | handoff:self_check_failed | 自检未通过: ['packaging_present', 'test_report_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit clutter 1.26.4 |
| 2026-10-01T16:12:24 | handoff:pr_body_incomplete | PR body 有 1 处占位符未填充 \| 请编辑 /storage/Users/currentUser/build_in_harmonyos-clutter/archives/c/clutter/1.26.4/reports/pr-body.md 补充以下内容： \|   - 上游仓库地址（如 conandata.yml 中无） |
| 2026-10-01T16:15:00 | handoff:pr_creation_timeout | gitcode_pr.py create-pr 超时，请手动重试或检查网络 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/clutter-1.26.4 --target main --title 'feat(clutter): 1.26.4 适配完成' |
| 2026-10-01T16:35:16 | skeleton_exists | pr_created |
| 2026-10-01T16:35:16 | pr_created | PR #14164 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/14164 |
| 2026-10-01T17:05:22 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #14164 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 14164 \| 摘要出现后: python3 scripts/ohc-run.py submit clutter 1.26.4 --resume |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

本次有两条流程级缺陷值得改进（均有实测复现）：

1. **`gitcode_pr.py create-pr` 的 preflight 基线应取 canonical 上游，而非本地 `main` 分支名**。本 worktree 的 `origin` 是 fork 远端，`main` 分支落后 canonical 上游 1252 个 commit；`run_preflight(..., args.target="main", ...)` 于是把 5451 个文件当作"本次变更"逐个做 git 调用，`create-pr` 直接**静默挂起（无任何 stdout/stderr）直到超时**——极难定位。建议：preflight 改用与 finish/W3 同源的 canonical 基线（`upstream/main`），并对变更文件数设上限，超限时明确报错而不是无限逐文件处理。

2. **`submit` 的 push 目标应与 `create-pr` 的头分支所属仓库一致**。`submission.py` 固定 `git push origin <branch>`，当 `origin` 为 fork 时分支被推到 fork，而 canonical 仓库上没有该分支，`create-pr` 报 404 `Can not find the branch: feat/clutter-1.26.4 in project: build_in_harmonyos`。（对照 PR #13764 的 head repo 即为 canonical 命名空间。）建议：push 前校验/提示远端归属，或在 `origin` 非 canonical 时改用 `upstream` 推送。

3. **`w3-local-ci` 的 junk 门禁在"改动未提交"时回退 full 模式，会对整仓历史存量报红**。`junk_check.sh` 在 `git diff origin/main...HEAD` 为空时回退 `full`（`git ls-files`），于是把 canonical `main` 上**早已存在**的 4 个路标文件（`archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`、`archives/t/thc/3.8/.staging-verified`）报为 `JC1`/`JC5` 违规并阻断 W3。这些文件在 `upstream/main` 中就存在，且不在本 PR 变更内——建议 full 模式跳过 `origin/main`/`upstream/main` 既有产物，或对存量单独分级为警告。

4. **`submit` 前置自检的两项（`packaging_present`、`test_report_present`）没有工具化生成路径**。`reports/test-report.md` 与 `packaging/*.tar.gz` 均被 `.gitignore` 忽略、不进 PR，但又是 `submit` 的硬门禁；而 `finish` 不产出它们，导致必须手工创建才能推进。建议：finish 内自动生成 test-report 与打包产物，或在 submit 中把这两项降级为警告（因 CI 侧并不读取它们）。

5. **`create-pr` 的标题由 `submission.py` 硬编码为 `feat({software}): {version} 适配完成`**，无法满足积分赛的 `【积分赛】` 前缀要求（SKILL §0.2 明确要求标题以关键词为前缀）。本次只能先让 submit 建 PR、再手工 `update-pr` 覆盖标题与描述。建议：支持 `--pr-title`/`--pr-prefix` 或从提示词关键词自动加前缀。

### 模板改进

1. **`pr-body.md` 自动生成的内容与积分赛模板严重不匹配**。`_generate_pr_body()` 把上游测试数写为 `0/0/0`、把 `configure_options` 写成 `默认配置`、`测试结论 > 已知限制` 写成 `无`——与 `test_package/MANIFEST.yml` 里已申报的 `upstream_tests: 111`、`assertion_count: 14` 完全矛盾；且唯一占位符 `(请填写验证命令和结果)` 的来源是 `notes.md` 中不存在 `## 验证结果` 小节，报错提示却指向"上游仓库地址"，误导性强。建议：让 `_generate_pr_body()` 直接消费 `test_package/MANIFEST.yml` 的 `upstream_tests` / `test_package_tests` / `assertion_count`，并让占位符提示语与真实缺失字段一致。

2. **建议为"必须改写 PR 描述"的场景提供一等公民通路**：积分赛模板要求（测试对比表、上游测试修改说明勾选、补全测试说明、验证结果）与自动模板差异很大，建议 `submit` 支持 `--pr-body-file` 直接使用作者准备好的描述，避免"建完再改"。

### 自动化补全

1. `reports/test-report.md` 可依据 `test_package/MANIFEST.yml` 与 `reports/w3-local-ci.log` **自动生成**（上游测试清点表、L0-L5 结果、test_package 断言数均已在文件中结构化存在）。
2. `finish` 结束后可自动把 `conandata.yml` **还原为官方单一 URL**：仅当本次 W3 以多包模式运行且 CI 注入了镜像列表时才会发生，且 CI 实际不改写单包构建——自动还原可避免误提交镜像列表。
3. `submit` 的 preflight 应在执行前打印"基线分支 + 变更文件数"，让此类静默挂起可被立刻识别（本次若早打印 `baseline=main, files=5451` 即可秒级定位）。

### 知识图谱覆盖

1. **`json-glib` 加载期签名失效**：OHOS 加载器判定 `.codesign` 段无效 → `dlopen` 报 `Permission denied`（`chmod 755` 无效，`binary-sign-tool selfSign` 可解；删除 `.codesign` 重签后 OK）。这是**加载期**故障而非编译期，知识库现有条目集中在编译/链接阶段，建议新增 E-entry。
2. **静态 `libEGL.a`（C++ 后端）导致的未解析 C++ 符号**：消费者加载 rc=127，须在生成的 `egl.pc` 的 `Libs` 中**紧跟 `-lEGL`** 追加 `-lc++_shared`（顺序敏感），且必须改 `.pc` 而非 configure 变量。建议沉淀为"OHOS 静态 C++ 依赖库的链接顺序"类条目。
3. **Mesa 专有头缺口**：`EGL/eglmesaext.h` 在 OHOS SDK 缺失，而上游公共头硬包含；当该头无实际符号使用时，可生成最小 stub 并**双路径安装**（`include/EGL/` 与 `include/<pkg>/EGL/`，因上游自带 `.pc` 的 Cflags 为 `-I${includedir}/<pkg>`）。建议作为"平台头缺口 stub 安装"通用模式沉淀。
4. **`conandata.yml` 镜像列表残留判定**：区分"CI 单包构建不改写"与"W3 多包/full 模式改写"两种情形，避免误判为作者违规。建议在 R39 条目中补该判定口径。

---

## 作者

- **姓名**: Inception662
- **邮箱**: 3389004972@qq.com
- **Agent ID**: B81C
- **生成时间**: 2026-10-01 15:40:24
- **PR 编号**: —
- **Git Commit**: 8f49dc9a2d
