# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_9c93f1cb.md`

---

## 背景

- **软件名称**: pngmeta
- **版本**: 1.11
- **构建日期**: 2026-09-20
- **构建系统**: autotools（configure 由 autoconf 2.13 生成）
- **上游仓库**: https://pmt.sourceforge.io/pngmeta/ （源码为 SourceForge 项目 pmt 的发布 tarball；适配参考 Debian 打包仓库 salsa.debian.org/debian-phototools-team/pngmeta）
- **适配路径**: 路径 B（贡献创新：libpng 私有 API 迁移 + 上游测试适配）
- **补丁数量**: 6（0001 源码迁移；0002-0005 上游测试脚本 diff -c → diff -u；0006 test4 期望输出）
- **编译依赖**:
libpng/1.6.58.3、zlib/1.3.2
- **最终状态**: built；PR #11609 CI 第 1 轮失败（toybox diff 不支持 -c），已修复并重新触发

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: autotools |
| conan-verify | 配方验证 | 成功 | G0-G4 全 PASS；首轮因 test_package 在 x86 runner 上执行 aarch64 动态产物失败，加入可执行性探针后通过 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 部分 | PR #11609 已建；submit 的 git push 因无 origin 凭据失败，改推 fork；create-pr 读超时属假超时（PR 实际已建），经 list-prs 确认。AI 检视无意见；CI 第 1 轮（#57964）因上游测试脚本的 `diff -c` 在 toybox 上不可用而失败，已修复 |

### 失败与问题

1. **CI 第 1 轮（#57964）红：`make check` 4 of 4 FAIL**。四个用例均报 `diff: Unknown option 'c'`——OHOS 的 diff 是 toybox，只支持 unified 输出，上游测试脚本用的 `diff -c` 直接被拒。被测程序本身没问题：同一轮里 `build()` 的探针已在 aarch64 原生机上跑出与期望文件一致的输出。修复为 POSIX `diff -u`（补丁 0002-0005）。本地 x86 runner 用的是 GNU diffutils，W3 无法暴露此问题。
2. **（预防）test_package 的 `os.access(X_OK)` 断言**：HMDFS 模式位固定、X_OK 恒为 False（E524），第 1 轮 CI 在 build() 阶段就失败，尚未走到 test_package；若不改，第 2 轮会在这里再红一次。已删除该断言，改以 ELF 头 + 实际执行结果判断。
3. **test_package / build() 的可执行性探针对「同架构跑不起来」也会 SKIP**：原生 aarch64 机上若二进制因运行时依赖缺失而起不来，会被当成「无法执行目标架构」跳过，等于把 skip 当通过。已改为按 ELF `e_machine` / `settings.arch` 与宿主架构比对：异构才 SKIP，同构判 FAIL。
4. **提交身份漂移**：首轮开工时未核对仓库级 git config，3 个 commit 以上一会话残留的身份提交，与创建 PR 的账号不一致；发现后用 `rebase --exec 'git commit --amend --reset-author'` 改写并随修复一起 force-push。
5. **SKILL_FEEDBACK 与 PR 未同步提交**：手动建 PR 的旁路下，本报告在建 PR 时尚未入库，随第 2 轮修复一并提交。

### 知识图谱使用情况

- **引用知识条目**: E524（HMDFS 上 X_OK 恒为 False）；E402 / E254（toybox 工具差异的同类条目，作为 E601 的 similar_to）
- **新增知识草稿**: E600-draft-D74E（libpng 私有 API 迁移）、E601-draft-4E3E（toybox diff 不支持 -c）
- **引擎命中情况**: 草稿目录 1397 条
- **测试统计**: 上游 4 项——本地 qemu-aarch64（静态链接）4/4 通过；CI 第 1 轮 0/4（toybox diff -c，非程序问题），修复后待第 2 轮；test_package 14 条断言，本地 qemu 实跑全部通过
- **未覆盖的错误模式**: libpng ≤1.2 私有 API 在 libpng ≥1.4 下全面失效（PNG_INTERNAL 失效 / 结构体字段私有化 / png_read_destroy 移除 / png_convert_to_rfc1123 弃用 / png.h 不再内嵌 zlib.h）。engine 对该日志返回无关的 E493（program_invocation_name），index.tsv 中 libpng 条目数为 0。已沉淀草稿 E600-draft-D74E。另：toybox diff 不支持 -c（CI 日志 `diff: Unknown option 'c'`），engine 返回的是 E402（toybox gzip），无 diff 相关正式条目，已沉淀草稿 E601-draft-4E3E

### AI 检视结果

- **检视阶段到达**: Phase 5（检视完成）
- **变更摘要评估**: 摘要准确概括了配方、补丁、test_package 与知识草稿，无需修改
- **检视意见数量**: 0（代码审查：未发现问题）
- **检视意见处理**: 无待处理意见

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（Pass rate 100%；L2 skip：`--version` 按上游设计退出 1；L4 warn：扫描到的是补丁上下文行里的上游 sprintf）
- **远程 CI (PR 校验)**: 第 1 轮 #57964 失败 → 修复后重新触发
- **CI 失败原因**: 上游测试脚本 `diff -c` 在 OHOS toybox diff 上不可用（Unknown option 'c'）；CI 侧与 `diagnose` 均将其归类为「编译失败」，实为测试比对工具不兼容

### 效率分析

- **HANDOFF 次数**: 6（W3 junk_check 整仓模式误伤、W4 审计未执行、self_check packaging_present、git_push_failed、resume_no_state、result 已存在需 --force）+ CI 红 1 轮
- **重试次数**: conan-verify 2 次、finish 4 次、submit 3 次、CI 修复 1 轮
- **关键瓶颈**: x86 runner 无法执行动态链接的 aarch64 OHOS 产物（OHOS musl loader 在 qemu-user 下入口即 SIGSEGV），导致上游测试与 test_package 的运行时验证都需绕道静态链接 + qemu 才能取得真实结果；同理，x86 runner 上的 GNU userland 也掩盖了 OHOS toybox 的工具差异，只能靠 CI 暴露
- **耗时较长的步骤**: git fetch origin main --deepen=500（多次超时，且超时被杀后残留 .git/shallow.lock 需手工清理）、三轮 conan create（每轮约 2 分钟）

---

## 建议

### SKILL 设计改进

1. **PF9 与 PF8/ARCHIVE-SPEC 直接冲突，首次适配必然被拦**：PF9 要求 archives 变更全部落在
   `<包>/<版本>/` 目录（`len(path.split('/')) < 5` 即拦），但 PF8 强制 CLI 包必须有**软件级**
   `commands.json`，ARCHIVE-SPEC v3.0 §2.1 还要求软件级 `manifest.yaml` / `README.md`。
   首次适配的新包这三个文件必然新增、必然出现在变更列表，两闸不可能同时满足，只能走
   `--no-preflight`——而这又会触发 R52「审计 pass 但硬闸命中 = 审计失真」的嫌疑。
   建议：PF9 增加软件级文件白名单（`README.md` / `manifest.yaml` / `commands.json`），
   或改为「至少有一个版本目录变更」而非「所有变更都在版本目录内」。

2. **W3 的 junk_check 在无 commit 的分支上回退整仓模式，误伤他人存量脏文件**：
   `junk_check.sh` 的 incremental 模式依赖 `git diff origin/main...HEAD`，分支尚未 commit 时
   diff 为空 → 回退 full 模式扫全仓，于是扫出 `archives/c/cloog/.build-closed` 等**他人已合并**
   的脏文件并阻塞本包 W3。协作者按红线不能碰他人归档，只能先 commit 再跑 finish。
   建议：finish 在调 W3 前检测「当前分支相对 origin/main 无提交」并提示先 commit，
   或让 junk_check 在 CI_PACKAGES 已指定时始终按定向模式扫描。

3. **`.orig` 与 `.work` 是硬链接，原地写入会污染基线，refresh-patch 静默少生成补丁**：
   init-build 用硬链接建 `.work`，用原地写的编辑器改源码会连带改掉 `.orig`，
   `refresh-patch --auto` 于是只对「用 sed -i 等断开链接的方式改过的文件」生成补丁——
   本次 pngmeta.c 的补丁第一次就这样丢了，只剩 test4.xpt 的补丁，且**没有任何告警**。
   建议：refresh-patch 在发现 `.orig` 与 `.work` 中同名文件 inode 相同时直接告警；
   或 init-build 改用 copy-on-write / 普通拷贝建 `.work`。

4. **本地 W3 无法暴露 OHOS userland（toybox）差异**：x86 runner 上的 `diff` / `head` / `gzip` 都是
   GNU 实现，而 CI 原生机上是 toybox，于是 `diff -c`、`head --bytes=-N`、`gzip --force` 这类问题只能靠 CI
   第一轮暴露，每次白白消耗一轮 CI。建议：W3 执行测试阶段时，若本机有 toybox/busybox，就把它置于 PATH
   前面模拟 OHOS userland；或把这类选项加入预扫描（E601 草稿已附 `prescan_pattern`，E402 同理）。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **conan-init 对 CLI 工具包仍套用库模板**：生成的是 `package_type = "library"` +
   `options={"shared": ...}` + `test_package/{CMakeLists.txt,test.c}`，而 pngmeta 是纯命令行
   工具，上述文件全部要删改重写；`description` 默认填成 `"<name> <version>"`、
   `license` 默认 `MIT`、`homepage`/`url` 留空也都得改。
   建议：conan-init 增加 `--type application` 或依据 init-build 阶段的产物探测自动选模板
   （已有 `templates/commands.json.template`，缺的是配方与 test_package 的 application 变体）。

2. **版本级 manifest.yaml 模板留下的是占位符而非可用骨架**：`software: "{software}"`、
   `build_system: "{BUILD_SYSTEM}"`、`sha256: ""` 均未被 conan-init 填充，而这些值
   init-build 与 conandata.yml 里都已经有了。建议直接回填已知字段。

3. **submit 自检要求 `packaging/*.tar.gz` 但全流程无任何步骤产出它**：`packaging/` 已被
   .gitignore（不入 PR），R19 又禁止手动打包，结果是协作者必须自己从 conan 包目录 tar 一份
   才能过自检，语义上很别扭。建议由 finish 在 conan create 成功后自动从 package folder 生成
   该留档 tarball，或把该自检项降级为 warning。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **create-pr 的读超时未做假超时兜底**：SKILL v12.17 声称「POST 失败延时 15s 后 list 复核
   防重复建 PR」，但本次 `gitcode_pr.py create-pr` 直接抛出 `TimeoutError` 堆栈退出，PR 其实
   已经建成（#11609）。若协作者据此重试就会建出重复 PR。建议把该兜底逻辑补到 create-pr 的
   异常分支里，并在超时退出时明确打印「请先用 list-prs 确认是否已创建」。

2. **PR 经 create-pr 直连创建时不写 `.submit-state.json`，`submit --resume` 无法接续**：
   本次 push 与 create-pr 都走了手工路径（原因见下条），结果 resume 报 `resume_no_state`，
   只能手工重建状态文件。建议 create-pr 成功后无条件回写 `.submit-state.json`
   （PR 号 / 分支 / commit），使其成为所有建 PR 路径的共同出口。

3. **submit 的 git push 只认 origin，且不感知 fork 工作流**：协作者通常没有上游 push 权限，
   push 会以 `could not read Username for 'https://gitcode.com'` 失败。仓库里已经配好了
   `fork` remote，但 submit 不会尝试它，也不会使用已配置的 GitCode 凭据。
   建议：push 失败时自动回退到 `fork` remote + token，并把 PR head 自动改写为
   `<fork-owner>:<branch>`。

4. **`git fetch --deepen` 超时被杀后残留 `.git/shallow.lock`，后续所有 fetch 全挂**：
   本次连续两次 fetch 超时，留下孤儿锁，报错信息只说「另一个 git 进程可能在运行」，
   需要人工确认无进程后手工删锁。建议在 W1 步骤里做一次「无活跃 git 进程则清理孤儿锁」的
   自愈处理。

5. **`diagnose` 把测试失败归为「编译失败」**：本次 CI 日志里编译、链接都成功了，失败的是 `make check`
   （`FAIL: test1` … `4 of 4 tests failed`，根因行为 `diff: Unknown option 'c'`），但 CI 侧与 `diagnose` 的本地
   二次归类都给出「编译错误 (make/gcc)」与「对照上游源码修 include/宏/类型」的修复要点，方向完全不对。
   建议：`diagnose` 识别 `FAIL: <test>` / `N of N tests failed` / `Unknown option` 等特征，归入「测试 / 工具兼容」类，
   并在证据行里给出触发的那一行命令。

6. **提交身份没有任何门禁**：同一台 runner 被多个账号轮流使用时，仓库级 git config 很容易残留上一会话的身份，
   而 token 已切到另一个账号——commit 作者与 PR 创建者不一致，只能事后 rebase 改写 + force-push，
   代价是检视与 CI 全部重跑。建议 submit 在 push 前比对 `git log origin/main..HEAD` 的作者邮箱与 token
   所属账号（`GET /api/v5/user` 的 email），不一致即 HANDOFF。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. **建议 promote 本次草稿 `E600-draft-D74E`**：libpng ≤1.2 私有 API 在 libpng ≥1.4 下全面
   失效。该模式在知识图谱里完全空白（`index.tsv` 中 libpng 条目数为 0），而它影响的是一整类
   1998-2005 年的 PNG 工具；错误表象分散（几十行互不相同的报错），最容易被误判成「缺头文件」
   而走上逐行 `#ifdef` 的歧路，正需要一条「整体迁移」的处方。草稿已附 `prescan_pattern`，
   可在源码风险预扫阶段直接命中。

2. **建议补一条「交叉构建机无法执行目标架构产物」的条目**：本次 qemu-user 能跑静态 OHOS
   二进制、却在 OHOS musl 动态加载器入口 SIGSEGV，这直接决定了上游测试与 test_package 能不能
   拿到真实结果。现有知识库没有这条，导致每次适配都要自己试一遍（试错成本约 20 分钟）。
   处方应包含：静态链接绕道验证、`-L <sysroot>` 的局限、以及「绝不把 skip 写成通过」的口径。

3. **建议把 pngnq 归档笔记里的 libpng 经验提升为条目**：`archives/p/pngnq/` 早就记录过
   「libpng ≥1.5 的 png.h 不再内嵌 zlib.h」，但只停留在归档笔记层面、不进检索路径，
   于是本次适配又重新踩了一遍。这类「已被写下但检索不到」的经验建议定期扫描归档 notes 并
   转成 E-entry（`kb-report --scan-logs` 已有类似机制，可扩展到 notes.md）。

4. **建议 promote `E601-draft-4E3E`（toybox diff 不支持 `-c`）**，并与 `DRAFT-toybox-diff-e-ed-script`
   合并为「toybox diff 选项覆盖」一条：`-u` / `-U` 可用，`-c` / `-C`、`-e` 不可用。后者称 toybox diff
   "implements -u/-c style output"，本次 CI 日志表明 `-c` 并不被接受，合并时需以此更正。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: FBD3
- **生成时间**: 2026-09-20 10:50:14
- **PR 编号**: 11609
- **Git Commit**: 42a8cc8fd8
