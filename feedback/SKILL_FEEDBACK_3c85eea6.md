# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_3c85eea6.md`

---

## 背景

- **软件名称**: lsw
- **版本**: 0.3
- **构建日期**: 2026-09-22
- **构建系统**: makefile
- **上游仓库**: https://dl.suckless.org/tools/lsw-0.3.tar.gz
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
- libx11/6.4.0
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: makefile |
| conan-verify | 配方验证 | 通过 | G1/G2/G3/G4 全 PASS，L2/L4/L5 无 cache 路径跳过；`reports/conan-verify-report.md`（2026-09-23T01:15:38，Profile ohos-aarch64） |
| finish | 归档收尾 | 完成 | 状态 built；Step6/Step8 有非阻塞告警（见"效率分析"与建议） |
| submit | PR提交+AI检视+CI | 未执行 | 本报告填于 submit 之前，PR 由 submit 阶段创建；AI Review: — |

### 失败与问题

- **1**: 根因=config.mk 烧死 `CC = cc`，设备无 cc, 解决方案=suckless 惯例（cc/cc89 链接），OHOS 只有 clang
- **2**: 根因=config.mk 把 X11INC/X11LIB 烧死为 /usr/X11R6，设备无该目录, 解决方案=上游硬编码 X11 安装前缀
- **4**: 根因=设备与 CI 均 headless（无 X server、无 Xvfb 可发布），无法正程运行 lsw, 解决方案=XOpenDisplay 必然失败

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 2 条
- **引擎命中情况**: 草稿目录 1469 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**: 3 类。① `Xlib.h:44:10: fatal error: 'X11/X.h' file not found`——X11 协议头属 xorgproto 包而 `Xlib.h` 属 libx11，配方只注直接依赖 `includedirs[0]` 必缺头，易误判为"xorgproto 未发布"；`draft-review` 实跑 verdict=create，TOP3 相似度仅 E108 0.22 / E248 0.16 / E346 0.10，故已落 `DRAFT-lsw-0.3-suckless-baked-paths-makevar-override`。② 新建 `CONAN_HOME` 缺 `remotes.json` ⇒ `preflight_check.sh` 把已发布的 `libx11/6.4.0` 误报成未发布（补齐 remotes.json+global.conf 后通过）。③ `finish` Step 3 的 G0 clean-verify 对 makefile-only 包报 `configure 失败 (exit 127)`（`finish3.log` L33），属工具侧假失败而非配方缺陷。

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 未生成——AI Review 由 submit 阶段触发，本报告填于该阶段之前（非"评估为空"）
- **检视意见数量**: 0（尚未进入 AI 检视阶段）
- **检视意见处理**: 不适用；提审前由 CIW 按四件套对逐条意见回复并 resolve

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 时间线计 0 次（harness 事件仅 lang_checked、skeleton_created）；另有 1 次未被 EVENTS 统计的非阻塞 G0 HANDOFF（`finish` Step 3，`finish3.log` L63-74），失败后流程继续、由 Step 4 的真验证给出判决
- **重试次数**: 全链路门禁重跑 3 轮（初验 → W4 整改 `06ae33cbc1` → 测试 spool 整改 `cf97c306ad`），第 3 轮 conan-verify 与 finish 各 1 次通过（`~/tmp/uc2/lsw-0.3-round3/verify3.log`、`finish3.log`）；配方 `build()` 迭代 2 次（先覆盖 `CC`，再改为覆盖聚合变量 `INCS`/`LIBS` 并遍历全部 host 依赖）
- **关键瓶颈**: 第三层缺头（`X11/X.h`）的定位——它是本包最隐蔽的一层，判错方向就会把任务转手成【等依赖】；靠两步判别（读 `archives/l/libx11/6.4.0/conanfile.py` 的 xorgproto requires + 跑 `preflight_check.sh`）才排除"依赖未发布"
- **耗时较长的步骤**: 构建本身不慢（第 3 轮 `finish` 十步 01:15:34→01:15:55，约 21s）；耗时在跨轮整改与证据补齐（09-22 10:20 lang_checked → 09-23 01:15 finish 通过）以及证据日志的选型甄别
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-22T10:20:58 | lang_checked | detected=c 与任务 cpp 匹配 |
| 2026-09-23T01:03:40 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **verify/finish 之后应明确"哪份日志算构建证据"（本包实测）**：`conan-verify` 的 G2 与 `finish` Step 4 都会跑 `conan create`，命中 binary cache 时**覆盖** `reports/conan-create.log`——本轮该文件实测 `Calling build()` 计数 0、`Building from source` 计数 0、`Cache` 出现 30 次，只能证明"可解析/可安装"；真重建证据只在 `reports/w3-local-ci.log`（L195 `Building from source`、L203 `Calling build()`、L205 `RUN: make CC=… INCS=… LIBS=… lsw`、L280 `ALL 2/2 CONSUMER ASSERTIONS PASSED`）。而 `conan-verify-report.md` 的 G2 行仍指向 `reports/conan-create.log`。建议 SKILL 在 verify 报告/HANDOFF 指引里明确标注证据选型，别让下一个 agent 拿 cache 命中日志当"编译通过"证据。
2. **G0 clean-verify 与 Conan 配方注入面不一致**：`finish` Step 3 用裸 `configure`/`make` 复现构建，对 suckless 这类"必须靠 make 命令行覆盖变量才建得起来"的包必然 `exit 127` 假失败并打印 HANDOFF（`finish3.log` L29-33、L63-74）。建议 makefile-only / 无 configure 的包跳过 G0 或改读配方 `build()` 的真实命令，否则 HANDOFF 噪声会被误读为配方缺陷。
3. **G0 临时目录落家根（框架级，建议单独框架 PR 处理，不在配方侧绕）**：设备 `/tmp` 只读、`TMPDIR=$HOME`，而 `scripts/ohc/clean_verify.py:82` 用裸 `tempfile.mkdtemp(prefix=f"ohc-verify-{software}-")` ⇒ 每次 G0 往家根生成 `ohc-verify-lsw-<rand>`（`finish3.log` L30 实测 `/storage/Users/currentUser/ohc-verify-lsw-e4eaw3ox`；家根现存 28 个他包同类遗留目录）。与本仓"临时产物唯一去处 `~/tmp/`、家根禁止落新散文件"冲突。

### 模板改进

1. **test_package 模板缺"副产物落盘位置"约定**：模板默认让测试脚本写 `self.build_folder`，而 test package 的 build_folder 就是 `archives/<l>/<pkg>/<ver>/test_package/` 本身 ⇒ 测试副产物直接落进归档目录。本包即因此把 `lsw-test-out.txt`（内含设备绝对路径）带进过分支（`e477bc6800` 引入、`06ae33cbc1` 移除）。建议模板给出归档外的默认落点。
2. **模板里裸 `mkdtemp()` 在本设备上不合规**：`/tmp` 只读、`TMPDIR=$HOME` ⇒ `tempfile.mkdtemp()` 会把副产物写进家根。建议模板给两级择路示例（优先 `~/tmp/`，不可写才退系统临时目录）。本包 `test_package/conanfile.py` 的 `_spool_dir()` 已按此实现，实测副产物目录为 `/storage/Users/currentUser/tmp/lsw-test-dy_hxbx4`（`w3-local-ci.log` L277）。
3. **feedback 骨架不区分"未执行"与"漏填"**：submit 之前生成的骨架把 PR/AI 检视类字段留成裸 `—` 或待填占位符，填表人容易把它们写成看起来像结论的值。建议阶段未到达时输出 `未执行（<阶段> 未触发）`，只有真正需要 AI 判断的槽位才留占位符。

### 自动化补全

1. **构建日志自动定性**：`conan create` 结束时可在日志首部落 `BUILD_MODE=from-source|cache`（判据即 `Building from source` 与 `- Cache` 的计数），免去人工 grep 判断哪份日志可作 W3 证据。
2. **`gen_summary` 崩溃**：`finish` Step 8 实测抛 `gen_summary 失败: 'str' object has no attribute 'append'`，导致失败步骤记为 `step5b, step8`（`finish3.log` L141、L152）。属框架侧缺陷，建议在 `finish` 内修，不要在配方侧补产物。
3. **`finalize-archive` 告警口径与 CI/preflight 判据不同源**：本轮 Step 6 报"软件级缺失 README.md / 缺少 release tar.gz / 缺少 debug tar.gz"（`finish3.log` L112-114，RC=2 为警告码），但经验汇总 §12.82 已实证这三项对 CI 三脚本与 `pre_pr_audit` 非阻塞，且**新增软件级 README.md 反会撞上本地 PF9**（`check_branch_and_paths()` 按 `len(path.split("/")) < 5` 拦 `archives/<l>/<pkg>/` 下任何软件级文件）。建议把该步必填清单与 CI/preflight 判据同源化（降为提示或工具自动产出），免得每轮人工判定"这个警告要不要补文件"。
4. **preflight 依赖结论的自愈检查**：新建 `CONAN_HOME` 缺 `remotes.json` 时 `preflight_check.sh` 会把已发布依赖报成未发布，可能直接诱导错误地把上游依赖转手成【等依赖】。建议 preflight 入口先自检 `remotes.json`/`global.conf` 并红牌提示"环境未初始化"，而不是给出依赖结论。

### 知识图谱覆盖

- 建议把 `DRAFT-lsw-0.3-suckless-baked-paths-makevar-override` 纳入正式 E 条目：`draft-review` 实跑 verdict=create，TOP3 相似度 E108 0.22 / E248 0.16 / E346 0.10，全部低于判重量级；本条贡献的是池件未写明的**第三层症状**（`X11/X.h` 属 xorgproto 协议头包 ⇒ 必须遍历全部 host 依赖含传递，且 `cpp_info.includedirs`/`libdirs` 是相对 `package_folder` 的路径，须 join 成绝对路径再喂 make）与"缺头 ≠ 依赖未发布"的两步判别法。
- 建议新增环境侧条目：① 新建 `CONAN_HOME` 缺 `remotes.json`/`global.conf` ⇒ preflight 误报依赖未发布；② `conan download --only-recipe` 在本远端报 `system acceleration policy not enabled`，故不可用作 binary 存在性判据（W0 判据需按远端区分）。这两类错模式图谱无命中，靠读文档与试跑才发现。
- 无 X 环境的确定性错误路径断言（`cannot open display`）属 E471 家族 hit，不另计新增知识。

---

## 作者

- **姓名**: wanderlust_0823
- **邮箱**: wanderlust_0823@noreply.gitcode.com
- **Agent ID**: 9B91
- **生成时间**: 2026-09-23 01:03:40
- **PR 编号**: —
- **Git Commit**: cf97c306ad
