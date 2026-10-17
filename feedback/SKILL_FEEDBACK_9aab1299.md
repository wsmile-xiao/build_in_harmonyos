# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_9aab1299.md`

---

## 背景

- **软件名称**: xli
- **版本**: 1.17.0-20061110
- **构建日期**: 2026-10-04
- **构建系统**: makefile（上游为 Imake/Imakefile，OHOS 环境无 imake/xmkmf，改用上游自带 `Makefile.std`）
- **上游仓库**: https://github.com/openSUSE/xli/archive/79edc902e82970411542a0fa7dc38ce1edcae2ec.tar.gz
- **适配路径**: 路径 A（基础适配，无补丁；平台差异以编译参数定向修复）+ 路径 B（知识库扩展：Imake/xmkmf 遗产构建回退）
- **补丁数量**: 0
- **编译依赖**:
- libx11/6.4.0
- libxext/6.4.0
- libjpeg/10
- libpng/1.6.58
- zlib/1.3.1.1
- **最终状态**: 成功（本地 W3 全流程通过；远程 CI 因 worker 基础设施故障未能闭环）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 上游站点已下线，改用 openSUSE fork 快照（commit 79edc902） |
| build | 编译构建 | 成功 | 构建系统: makefile（`Makefile.std` + `-Drindex=strrchr` 定向修复） |
| conan-verify | 配方验证 | 通过 | G0-G4 + L2/L4/L5 全绿；W4 独立审计 verdict=pass（P0/P1=0） |
| finish | 归档收尾 | 完成 | 本地 W3 `conan create` exit_code=0（integrity_hash=7fc4a50610d22a30） |
| submit | PR提交+AI检视+CI | 部分 | PR #14599 已建；AI Review 仅占位（未产出摘要/意见）；CI 5 次尝试全部 worker 侧故障 |

### 失败与问题

- **1**: 根因=`make` 入口即死（找不到 Makefile）, 解决方案=上游 Imakefile 需 imake/xmkmf 生成 Makefile，OHOS SDK/CI 均无该工具（制品仓无对应包）
- **2**: 根因=链接报 `undefined reference to 'rindex'`, 解决方案=OHOS musl libc 未提供 BSD 遗留 `rindex()`（`index/bcopy/bzero/bcmp` 实测存在）
- **3**: 根因=bcopy/bzero 走 libc 兼容符号, 解决方案=老代码使用 BSD 内存函数
- **4**: 根因=`Makefile.std` 的 install 目标只装 xli, 解决方案=上游 install 目标未覆盖 xlito
- **5**: 根因=源码站点不可用, 解决方案=上游 pantransit.reptiles.org 已下线（HTTP 404）
- **6**: 根因=本地沙箱下载需镜像, 解决方案=conandata 手写镜像前缀违反 R39/PF7
- **7**: 根因=CI 远端持续红（5/5 非代码失败）, 解决方案=worker 基础设施故障（3 台 worker、2 类错误），已记于 PR 讨论串并按 loop_pending 上报

### 知识图谱使用情况

- **引用知识条目**: 无（Imake/xmkmf 遗产构建与 musl BSD 遗留符号两类此前无正式条目，本次沉淀为草稿）
- **新增知识草稿**: 4 条（2 个 DRAFT-*.kv + 2 个 .md 伴生；另有 `knowledge/drafts/imake-legacy-x11/` 四件套：检测脚本/复现脚本/README）
- **引擎命中情况**: 草稿目录 2977 条
- **测试统计**: 上游测试套件 N=0（清点证据见 `reports/test-report.md` §1，135 个文件无 test/check 目标）；鸿蒙特有测试 4/4 通过
- **未覆盖的错误模式**: ① worker 侧 `SSH bridge exec failed ... Connection refused (111)`（buildbot 基础设施，非配方）② exec 层 `Resource temporarily unavailable`（clang spawn EAGAIN，Error 127）③ CI 预下载脚本依赖 `curl`，worker PATH 无 curl → 8 次 `[Errno 2] No such file or directory: 'curl'` 后降级为 conan 直连下载 ④ bot 对上述基础设施故障兜底分类为"源码下载超时/网络问题"，误导修复方向

### AI 检视结果

- **检视阶段到达**: Phase 1（atomgit-bot 于 11:37:39/11:37:40 发出「正在生成合并请求摘要」「AI 代码检视正在进行中」占位评论后未再产出）
- **变更摘要评估**: 未产出（截至 12:10 评论区无「变更摘要」正文）
- **检视意见数量**: 0（无摘要、无行级检视意见；PR 讨论串 12 条中 bot 消息均为占位/CI 结果）
- **检视意见处理**: 无需处理（无意见）；CI 侧结论已在 PR 讨论串回复并附 worker 故障证据表

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`conan create` 全流程 exit_code=0，10 个依赖全部走预编译二进制）
- **远程 CI (PR 校验)**: 失败——5/5 均为 worker 侧基础设施故障，无一次代码类失败
- **CI 失败原因**: #71301 / #71342（worker CI-019）编译期 clang spawn `Resource temporarily unavailable`（exec EAGAIN，Error 127）；#71306 / #71364 / #71373（worker CI-002、CI-034）`SSH bridge exec failed ... Connection refused (111)`。与配方无关：本地同 profile、同 `conan create` 通过；#71342 中 worker-prep/git-clone/conan-setup 全 ✅、依赖全走二进制、配方为 `make -f Makefile.std -j1`

### 效率分析

- **HANDOFF 次数**: 2（W3 结构项 step5b/step8 告警处置；W4 首轮审计 fail（P1×1+P2×1）后修复复验）
- **重试次数**: 本地 `conan create` 3 次（finish 复验 + P2 修复后复验）；远程 CI `/rebuild` 5 次（全部 worker 侧失败，非修复轮次）
- **关键瓶颈**: ①远程 CI 基础设施故障占本次收尾时长的大头（11:41→12:02 五次尝试全部非代码失败）②worker 无外网 → 源码下载需依赖 conan 缓存/本地播种 ③CI 预下载缺 curl 直接降级
- **耗时较长的步骤**: ①源码获取（上游站点下线 + worker 无外网）②W4 审计两轮（首轮 fail 修复）③CI 重试等待
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-04T10:01:20 | lang_checked | detected=c 与任务 cpp 匹配 |
| 2026-10-04T11:37:59 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

本次遇到的最大问题不是配方，而是"CI 红了但红的原因不在代码上"——SKILL 缺少对基础设施类失败的区分与处置路径：

1. **区分「代码类失败」与「基础设施类失败」**：R42 规定 CI 红后进入修复循环（最多 2 轮），但该机制隐含假设失败源于代码。本次 5 次 CI 失败全部为 worker 故障（SSH bridge 拒绝连接 / clang exec EAGAIN），却仍要按修复轮次消耗预算。建议在 R42 中增加失败类型判别（在 CI 评论内即可判定：`SSH bridge exec failed`、`Resource temporarily unavailable`、`Connection refused`、预下载工具缺失等属基础设施类），命中即直接转 loop_pending 止损上报，不占修复轮次。
2. **finish 的 step5b / step8 在模式 B 下的期望不明确**：`❌ .staging-verified — 需创建 .staging-verified 空文件` 与 `gen_summary 失败: 'str' object has no attribute 'append'` 在手动编译路径下反复出现，但均未阻塞（exit_code=0）。建议：前者在本地 W3 通过后由 finish 自动补写标记，后者补强异常处理并在非致命时降级为 info 级。
3. **comment_create 回包解析失败时缺少幂等复核**：本机两次 `/rebuild` 均返回 `failed to parse AtomGit response: error decoding response body`，但评论实际已落（随后 robot 正常应答并派发构建）。若无复核就会重复触发同一构建。建议在 gitcode_pr.py 的评论/触发路径上加"写后复核"（与 v12.17 create-pr 的 15s 复核同构）。
4. **远程 CI 结论读取通道**：`gitcode_pr.py ci-status` 在本机恒 401（无 `~/.gitcode-token`），CI 状态只能靠读评论；建议提供免凭据的公开 API 读法（本次经 `api.gitcode.com/api/v5/.../pulls/{n}/comments` 无鉴权直读成功），并在输出侧做摘要化（默认只打结果+错误行，避免长日志刷屏）。

### 模板改进

1. **feedback 模板新增「CI 环境故障」小节**：记录 worker 名、构建号、失败类型（SSH bridge/exec EAGAIN/工具缺失），便于跨任务聚合 worker 健康度。
2. **版本级 manifest.yaml 建议增加 `ci` 段三态**：`passed` / `infra_blocked` / `code_failed`，并记录最后一次构建号；当前模板只能表达本地状态。
3. **test_package/MANIFEST.yml 增加"用例类型"字段**：本次为"消费者脚本（headless，规避 SIGPIPE）"，与上游测试缺失场景配合时，评审需要立刻看到"鸿蒙特有测试的形态与覆盖面"。
4. **conandata.yml 模板对"上游站点下线"给出 fork 快照的规范写法**：本次用 openSUSE fork 的 commit 归档 URL，已在 PR 说明来源与理由，但模板缺少引导（R39 允许官方托管 fork）。

### 自动化补全

1. **W0 预检加入「CI 工具可用性」核对**：CI 的预下载脚本依赖 `curl`，本次 worker 无 curl（8 次 `Errno 2` 后降级）；若 W0 阶段能扫出"本包流程所需工具在 CI 缺失"，可提前决定走缓存直传路径。
2. **W0 预检输出「上游构建工具缺失清单」**：Imake 类项目在 CI 必然没有 `imake/xmkmf`（制品仓亦无该包），建议 W0 直接把"上游生成器缺失→需 Makefile.std 回退"作为可预期路径提示，而非等 `make` 失败后再排查。
3. **CI 失败评论内嵌「worker 健康探针」**：当前 bot 对 SSH bridge 故障给出"源码下载超时/网络问题"的兜底分类，误导修复方向。建议在失败诊断前先做 worker 自检（SSH bridge 连通性、spawn 可用性），命中即输出"基础设施故障（请稍后 /rebuild）"。
4. **多包/单包止损的自动化（已部分落地）**：本次为单包任务，止损动作（result 上报 + PR 讨论串留证）仍靠 agent 手动执行；建议 result 命令支持 `--blocker infra` 语义，自动在 PR 讨论串回填故障证据表。

### 知识图谱覆盖

本次新增（`knowledge/drafts/`）：

1. `DRAFT-xli-1.17.0-imake-absent-makefile-std-fallback`（+ `knowledge/drafts/imake-legacy-x11/` 检测脚本 `detect_imake_legacy.py`、复现脚本 `reproduce.sh`、README）——Imake/xmkmf 遗产 X11 工程在无 imake 环境的构建回退策略。
2. `DRAFT-xli-1.17.0-ohos-musl-missing-rindex-bsd-legacy`——musl 缺 BSD 遗留 `rindex()` 的定向修复（`-Drindex=strrchr`，优于启用 `-DSYSV` 牵出 F_FREESP/stropts.h）。

建议补充为正式条目：

1. **CI/构建环境类错误模式**（建议独立 category，如 `ci-environment`）：SSH bridge `Connection refused`、exec `EAGAIN`、CI 预下载工具缺失——这些模式目前的知识库条目全部面向"配方/源码"层面，环境类无覆盖，导致同一现象每次都要重新判读。
2. **"bot 误分类"模式**：bot 将基础设施故障归类为"源码下载超时/网络问题"时的辨识要点（看 worker-prep/git-clone 步骤是否 ❌、看是否所有步骤同因失败），可用于自动过滤误判。
3. **musl 符号缺口查证方法**：`nm -D libc.so | grep <sym>` 的实测口径（本次实测 `rindex` 缺失而 `index/bcopy/bzero/bcmp` 存在，避免了整块启用 `-DSYSV` 的过度修复）。

---

## 作者

- **姓名**: weijiapan
- **邮箱**: weijiapan@noreply.gitcode.com
- **Agent ID**: BD2F
- **生成时间**: 2026-10-04 11:37:59
- **PR 编号**: #14599
- **Git Commit**: f6eafad112
