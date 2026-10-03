# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_6b9a93c4.md`
> **注**：本文件由 AI 按实测结果逐条校正（骨架原预填「CI 通过」等乐观值，与真实结果不符，已改正）。

---

## 背景

- **软件名称**: mm
- **版本**: 1.4.2
- **构建日期**: 2026-09-26
- **构建系统**: autotools
- **上游仓库**: https://cdn.netbsd.org/pub/pkgsrc/distfiles/mm-1.4.2.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 1
- **编译依赖**:
无
- **最终状态**: 成功（归档与配方全绿；远程 CI 经 3 轮修复后 **#61986 校验通过**：
  L0/L1 门禁 + conan test_package 全绿）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 上游站点不可达，改用 pkgsrc distfiles 镜像（双镜像 sha256 交叉校验一致） |
| build | 编译构建 | 成功 | 构建系统: autotools（clang 15.0.4，in-source，`-j1`） |
| conan-verify | 配方验证 | 通过 | G0–G5 全绿；profile `ohos-aarch64`；reference `mm/1.4.2@ohpcd/stable`；含从零 `conan create` |
| finish | 归档收尾 | 完成 | JC 门禁通过、W3 本地 CI 模拟 `.ci-result.json exit_code=0`；Step6 知识图谱与 Step8 `gen_summary` 遗留告警见下 |
| submit | PR提交+AI检视+CI | PR #12928；远程 CI 共 3 轮：第 1 轮 **失败**（L0d 空壳测试）、第 2 轮 **失败**（E114 临时目录不可写）、第 3 轮 **#61986 校验通过** | AI Review: Phase 1 (等待摘要) |

### 失败与问题

- **1**: 根因=`config.guess: unable to guess system type`，configure 直接失败, 解决方案=归档内 `config.guess` 为 2005-12-13 版，不认识本机 uname 输出
- **2**: 根因=`make test` 在 `/tmp/mm.core.<pid>` 处报 `Read-only file system`, 解决方案=`mm.h` 的 `MM_CORE_DEFAULT_FILE` 硬编码 `/tmp`，鸿蒙 PC 上 `/tmp` 只读（知识库 E002）
- **3**: 根因=`make -jN` 报 `jobserver mkfifo ... Operation not permitted`, 解决方案=本机 `mkfifo` 工具不可用，GNU make 的 jobserver 无法建立通信 FIFO
- **4**: 根因=外源构建报 `No rule to make target 'mm_vers.c'`, 解决方案=上游 2006 年生成的 Makefile 无 VPATH / `$(srcdir)` 支持，源码文件只按相对路径查找

以下为流程/工具层面的失败（非上游问题），按发生顺序补录：

- **5（submit 门禁）**: 自检 `packaging_present` FAIL，HANDOFF 为 `self_check_failed`。
  根因：`scripts/ohc/submission.py:210 _check_packaging_present()` 要求 `packaging/*.tar.gz`，
  而 `references/iron-rules.md` 已把 `packaging/` 目录标为「不再生成 / 应删除，Conan 体系替代」。
  实测全仓 11945 个归档中仅 4 个带该产物，说明该门禁在实践上普遍被绕过。
  解决：从真实 conan 包目录生成 `packaging/mm-1.4.2-ohos-aarch64.tar.gz` 与 `-debug.tar.gz`
  （`packaging/` 已被 `.gitignore` 忽略，属本地产物，不进入 PR，故未污染提交集）。
- **6（PR 创建）**: `pr_creation_failed`，报 `PF0 环境闸: preflight 执行异常
  ([Errno 2] No such file or directory: 'git')`。
  根因：本平台 libc 的 `posix_spawn()` 不做 PATH 搜索（POSIX 语义上只有 `posix_spawnp()` 搜索），
  而 CPython 的 `subprocess` 在本平台走 `posix_spawn` 快路径；`scripts/gitcode_pr.py::_git_toplevel()`
  与 `scripts/ohc/preflight.py` 均以**裸名** `["git", ...]` 调用，故必然 ENOENT。
  实测对照：绝对路径 subprocess → rc 0；裸名 subprocess → FileNotFoundError；
  `os.posix_spawnp("git")` → 正常；`shutil.which("git")` → 正常。
  解决：以**运行环境级**垫片（`PYTHONPATH` 注入 `sitecustomize.py`，把裸命令名解析为绝对路径）
  绕过，**未修改只读的 `scripts/`**。
- **7（远程 CI 第 1 轮）**: L0d 门禁拦截，`stub_test_method` —— "test() method has no self.run() call"。
  根因：`ci/conan/build_and_test.sh` 的 L0d 以静态 `grep -q "self\.run"` 判定；
  而 `templates/` 与既有归档的 test_package 范式只用 `cmake.test()`（CTest），不含 `self.run(`。
  **模板与门禁要求不一致**。解决：test() 中在 `cmake.test()` 之外显式
  `self.run(os.path.join(self.cpp.build.bindirs[0], "test_mm"), env="conanrun")`，
  本地 `conan create` 日志实测出现 `(test package): RUN: ./test_mm` 与
  `1/1 Test #1: test_mm ... Passed`（CTest 与显式执行双路径均通过）。
- **8（远程 CI 第 2 轮，本次最隐蔽的一处）**: `make: *** No targets specified and no makefile found`。
  CI 只报「编译失败」，无有效诊断类别；从 PR 评论中的**整段**日志才定位真因：
  `configure` 生成的 `config.status` 写 `./confXXXXXX/*` **全部** `Permission denied`
  （`subs-1.sed` / `out` / `stdin` / `defines.sed` / `config.h`），最终
  `chmod: mm-config: No such file or directory` —— Makefile 与 config.h 都没生成，`make` 自然找不到。
  根因即知识库 **E114**：HMDFS 会给目录强制加 setgid 位，autoconf 的
  `tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\`` 因此得到 `drwx--S---`（group 位 `S` 而非 `s`）
  的临时目录，**连属主都写不进去**；`config.guess` 的三级回退链同样带 `umask 077`，
  故还并行报 `cgXXXXXX/dummy.c: Permission denied` → `unable to guess system type`。
  为何本地不复现：本机 `usr/local/bin/mktemp` 产出 `drwxrws--x`（可写），CI worker 的 PATH 中无此文件，
  退化为平台 `mktemp` → 077 下不可写。**说明本地通过 ≠ CI 通过，环境差异恰好掩盖了该缺陷**。
  解决：配方新增 `_drop_umask_077()`，在 `configure()` 之前就地剥离 `configure` 与 `config.guess`
  中的 `(umask 077 && `（实测命中 2 + 3 处，子 shell 结构保留），未命中则 `output.warn` 而非静默通过。
  这是仓内 **83 个归档**已在用的既有范式（abiword / 4ti2 等），此前未纳入本库配方。

### 知识图谱使用情况

- **引用知识条目**: E002（鸿蒙 `/tmp` 只读 → 默认路径须走 `$TMPDIR`）、E490（autotools 辅助脚本可执行位）
- **新增知识草稿**: 3 条
- **引擎命中情况**: 草稿目录 1774 条
- **测试统计**: 总计 2 个测试程序（上游 `mm_test` 1 个 + 消费者 `test_mm` 1 个），
  通过 2 / 失败 0 / 跳过 0；断言 15（上游 `FAILED_IF`）+ 10（消费者 `CHECK`）= 25
- **未覆盖的错误模式**: 见「知识图谱覆盖」节（5 条建议，均为本次新遇到的平台/工具类模式）

### AI 检视结果

- **检视阶段到达**: Phase 1 (等待摘要)（本轮 submit 在 AI Review 轮询中超时退出，未推进到检视意见阶段）
- **变更摘要评估**: 「变更摘要」由 `atomgit-bot` 正常生成（评论 191721343），内容与本 PR 实际改动一致：
  1 处补丁（`$TMPDIR` 默认路径 + `sprintf`→`snprintf`）、conanfile.py、conandata.yml、manifest.yaml、
  test_package 消费者测试，均与磁盘实际文件相符
- **检视意见数量**: 0（截至最后一轮轮询，AI 检视为「正在进行中」，无正式意见落盘）
- **检视意见处理**: 无意见需处理；另自行执行了 W4 独立审计并修复 3×P2 + 4×P3（见
  `archives/m/mm/1.4.2/reports/audit-result.json`，verdict=pass，P0=0/P1=0）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`.ci-result.json` `exit_code: 0`）
- **远程 CI (PR 校验)**: 共 3 轮，**最终 #61986 校验通过**（worker CI-040，SHA `e94ec816`）：
  - 第 1 轮 build #61908：**失败**，L0d 静态门禁 `stub_test_method`（`test()` 缺 `self.run(`）
  - 第 2 轮 build #61961：**失败**，`configure`/`config.status` 临时目录 `Permission denied`（E114）
  - 第 3 轮 build #61986：**通过**（`conan-build-test` ✅、L0 门禁 ✅、L1 测试执行 ✅）
- **CI 失败原因**: ①L0d 要求 `test_package/conanfile.py` 含 `self.run(`；②HMDFS setgid 使
  `umask 077` 临时目录不可写（E114）。二者均已修复并复验。
- **结果回流方式的重要发现**: CI bot 并非新增评论，而是**原地编辑同一条评论**。本轮「通过」正文
  （`## CI 校验通过 | PR #12928 | #61986`）与队列通知共用创建时间附近的发布节奏，
  低层 `ci-status` 按 `created_at` 取「最新一条」时选中了紧随其后的「## 构建触发中」（`<!-- LVL:0 -->`）
  队列提示，因而误报 `❓ UNKNOWN`。**判读 CI 结果不能只看最后一条评论的标题**，
  需按 `CI-BOT:pr-<n>-<id>` 分桶、并以同一 build 号（此处 #61986）的终态为准。

### 效率分析

- **HANDOFF 次数**: 2（`self_check_failed`、`pr_creation_failed`；另 `submit` 因 AI Review 30 分钟轮询窗口
  在 280s 命令超时处被截断 1 次，属工具等待而非流程故障）
- **重试次数**: submit 3 次（自检 packaging → preflight git → 成功创建 PR）；conan-verify 3 次
  （配方/消费者测试变更后复验、E114 修复后从零复验）；远程 CI 修复轮 **2 轮**
  （L0d、E114，正好用满 `MAX_CI_REPAIR_ROUNDS=2`，无剩余余量）
- **关键瓶颈**: ①`packaging_present` 死门禁阻断 submit；②本平台 `subprocess` 裸名 ENOENT
  导致 `PF0` 假故障、PR 创建被拦；③远程 CI 为评论触发型且结果仅经 PR 评论回流，
  本地无法同步等待，造成「提交—等评论—再修」的长往返；④**本地环境与 CI worker 的环境差异
  （`usr/local/bin/mktemp` 是否存在）恰好掩盖 E114，导致第 2 轮才发现真因**——
  本地全绿的证据链无法替代 CI 实跑，环境差异类缺陷只能在 CI 暴露
- **耗时较长的步骤**: submit 内的 AI Review 轮询（Phase 1 每 5 分钟、超时 30 分钟）；
  从零 `conan create` 取证（为验证 `$TMPDIR` 补丁与 E114 修复主动清缓存重建）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 6 个事件（含 2 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-26T17:22:14 | handoff:self_check_failed | 自检未通过: ['packaging_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit mm 1.4.2 |
| 2026-09-26T17:24:13 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/mm-1.4.2 --target main --title 'feat(mm): 1.4.2 适配完成' |
| 2026-09-26T17:26:49 | skeleton_created | pr_created |
| 2026-09-26T17:26:49 | pr_created | PR #12928 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/12928 |
| 2026-09-26T18:52:02 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-26T18:52:02 | skeleton_created | resume_pr_exists |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`packaging_present` 自检与现行规范自相矛盾，应删除或降级为 WARN。**
   `references/iron-rules.md` 明确 `packaging/` 已废弃、应删除；但
   `scripts/ohc/submission.py:210` 仍对 `status ∈ {published, built}` 硬性要求 `packaging/*.tar.gz`，
   且同一逻辑在「报告路径」（Check 9/11）记为 WARN、在「submit 门禁路径」记为 FAIL —— **同一检查两套判定**。
   建议：门禁路径与报告路径统一为 WARN，或直接移除该检查（并清理 `_TEMP_FILE_PREFIXES` 中的遗留项）。
2. **所有外部命令调用应统一走 `find_executable()`，禁止裸名。**
   `scripts/ohc/feedback.py:39` 已用 `_GIT = find_executable("git")`，但
   `scripts/gitcode_pr.py:242/271` 与 `scripts/ohc/preflight.py:75/320/578` 仍用裸名 `["git", ...]`；
   本平台 libc 下裸名必然 ENOENT（见「失败与问题 6」），会把环境缺陷伪装成「PF0 环境闸」硬拦 PR。
   建议：全局替换为 `find_executable(...)`，或在 `run_preflight` 入口处把 PATH 类命令预解析为绝对路径。
3. **PR 标题的赛事前缀应在生成阶段注入，而非事后手工修。**
   `scripts/ohc/submission.py:1158` 附近硬编码 `feat(<软件>): <版本> 适配完成`，
   而 `SKILL.md §0.2` 要求含「积分赛」等关键词时必须以 `【积分赛】` 为前缀。
   本次只能建 PR 后用 `atomgit_pr update` 事后改标题（在线 PR 标题已修正为
   `【积分赛】feat(mm): 1.4.2 适配完成`），属流程缺口。
   建议：`submit` 接收/推断赛事关键词并直接生成带前缀标题，避免「先错后改」。
4. **`finish` 的 Step6/Step8 遗留告警应修复或明确降级。**
   本次终态 `EXIT_REASON=finish_success`、`EXIT_CODE=0` 但 `Step6 知识图谱`（manifest
   `knowledge_count=3 unreferenced=3`、1667 草稿待审）与 `Step8 gen_summary` 报
   `'str' object has no attribute 'append'` 使 `finish` 进程 exit=1。二者与制品质量无关，
   但会让调用方误判失败。建议：`gen_summary` 修 bug；知识图谱未引用项改为 WARN。
5. **反馈骨架预填乐观值有误导风险。** 本次骨架在未拿到远程 CI 结果时就写入
   「submit | PR #12928, CI 通过」「远程 CI: 通过」「CI 失败原因: 无」，
   而真实结果是 CI 第 1 轮 L0d 失败。建议骨架对应字段留空或标注「待回填」。

### 模板改进

1. **test_package 模板与 L0d 门禁不一致（本次实际拦截点）。**
   模板/既有归档范式只写 `cmake.test()`，而 CI L0d 以静态 `grep "self\.run"` 判定空壳。
   建议模板默认给出「CTest + 显式 `self.run(测试二进制, env="conanrun")`」双路径写法，
   并说明 `self.cpp.build.bindirs[0]` 的取法；否则每个新适配者都会撞一次 L0d。
2. **`test_package` 模板应默认覆盖「补丁实际改动的代码路径」。**
   本次原测试只走显式后备文件路径，未覆盖补丁改的 `file == NULL` 默认路径
   （W4 审计 P3/R40 提出），补丁行为在消费者侧无可验证性。建议模板加一条提示。
3. **模板的 `assertion_count` 应与代码实测联动。** 本次骨架/报告曾出现声明值与
   `grep -c` 实测值不一致（22 vs 6/10），属易错字段，建议由脚本计数生成。
4. **PR 正文模板缺 `## 三方库信息` 标题时需自动补。** 本次
   `archives/m/mm/1.4.2/reports/pr-body.md` 需手工补该一级标题才能与
   `templates/积分赛事PR模板.md` 对齐（`submission.py:479 _generate_pr_body()` 缺大赛章节）。

### 自动化补全

1. **`submit` 应提供「不等 AI Review」的开关。** 当前 AI Review 轮询（5 分钟/次、超时 30 分钟）
   使 `submit` 远超常规命令超时，调用方只能截断；建议加 `--no-wait-review` 或把轮询改为可恢复后台任务。
2. **远程 CI 结果应可通过脚本同步查询，且必须按 build 号判读。** CI 为评论触发、结果回流的
   方式是**原地编辑同一条机器人评论**而非追加新评论；`gitcode_pr.py ci-status` 现按 `created_at`
   取「最新一条」，会把紧随其后的 `## 构建触发中`（`<!-- LVL:0 -->`）队列提示当成终态，
   实测因此把已通过的 #61986 误报为 `❓ UNKNOWN`，并连带使 `result --status success`
   被降级为 `partial`（见 `result_report.py::_verify_ci_green`）。
   建议：解析时按 `<!-- CI-BOT:pr-<n>-<id> -->` 分桶、忽略 `LVL:0`，以同一 build 号的终态为准；
   并提供 `ohc ci-status <pr>` 直接读看板 `https://ohpcd.atomgit.com/ci` 返回结构化结果。
3. **`packaging/` 产物可自动生成。** 若门禁短期不撤，建议由 `finish`/`submit` 从 conan 包目录
   自动打包（含 `objcopy --only-keep-debug` 生成的调试包），免去手工补产。
4. **`--resume` 覆盖 PR 创建后的 CI 修复轮。** 目前 CI 修复需手工 `git commit + push + 评论 /rebuild`，
   建议纳入 `submit --resume` 自动闭环。

### 知识图谱覆盖

建议新增以下 E-entry（均为本次实测、具备跨软件复现性）：

1. **`subprocess` 裸命令名 ENOENT（平台级）**：本平台 libc 的 `posix_spawn` 不搜 PATH，
   CPython subprocess 走该快路径 → 裸名调用必失败；表征为 `PF0 环境闸` 假故障。
   规避：应用绝对路径或 `find_executable()`。**高优先级**（会直接阻断 PR 创建）。
2. **L0d `self.run` 空壳门禁**：test_package 的 `test()` 必须含 `self.run(`（静态 grep），
   `cmake.test()` 不被识别。规避写法见上。
3. **GNU make jobserver 需 `mkfifo`**：本机 `mkfifo` 不可用 → 并行 make 报
   `jobserver mkfifo ... Operation not permitted`；规避为 `-j1`。
4. **老 autotools 无 VPATH 支持**：2000 年代 Makefile 无 `$(srcdir)` → 外源构建报
   `No rule to make target '<generated>.c'`；规避为 in-source 构建（`folders.build = "."`）。
5. **`packaging/` 门禁与规范冲突**：归档 `status=built/published` 时 submit 自检要求
   `packaging/*.tar.gz`，但该目录已废弃；规避为生成真实 tar.gz（本地忽略、不入 PR）。
6. **HMDFS setgid × autoconf `umask 077` 临时目录不可写（E114，已有条目，本次补强）**：
   HMDFS 给目录强制加 setgid，使 `(umask 077 && mktemp -d "./confXXXXXX")` 得到 `drwx--S---`
   的目录而属主也写不进 → `config.status` 全线 `Permission denied` → 无 Makefile →
   `make: *** No targets specified and no makefile found`；`config.guess` 同级回退链同病。
   规避：`configure()` 前就地剥离 `configure`/`config.guess` 中的 `(umask 077 && `。
   **注意本地可能因 PATH 中存在可用的 `mktemp` 而不复现**，必须在 CI 侧验证。
7. **CI 结果评论的原地编辑语义**：机器人**编辑**既有评论而非追加，故「最后一条评论」不等于
   「最新终态」；判读须按 `CI-BOT:pr-<n>-<id>` 与 build 号分桶，忽略 `LVL:0` 队列提示。

---

## 作者

- **姓名**: evol
- **邮箱**: evol@noreply.gitcode.com
- **Agent ID**: 5EFA
- **生成时间**: 2026-09-26 17:26:49（校正时间 2026-09-26 19:05，回填远程 CI 终态）
- **PR 编号**: 12928
- **Git Commit**: 837604d535（修复提交：3197305857 → e94ec8162b，CI #61986 通过）
