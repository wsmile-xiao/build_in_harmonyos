# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_00df57a8.md`

---

## 背景

- **软件名称**: libpktriggercord
- **版本**: 0.85.1-20221221181244
- **构建日期**: 2026-09-17
- **构建系统**: makefile（上游裸 Makefile，无 configure/CMake/meson）
- **上游仓库**: https://github.com/asalamon74/pktriggercord（commit c1177a48，Makefile VERSION=0.85.01）
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
无
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: makefile；首个错误为 Makefile `CFLAGS ?=` 被环境顶掉 |
| conan-verify | 配方验证 | 通过（2 轮） | 首轮 G2 FAIL：conan 2 的 copy() 无 root 参数；修复后 G1/G2/G3 PASS |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 完成（需手工旁路） | PR #10564，AI Review「未发现问题」，CI #49434 PASSED。submit 的 create-pr 与 monitor-review 两条路都因框架缺陷不可用，见建议 |

### 失败与问题

本次流程遇到 6 类阻塞/缺陷，其中 5 类属 SKILL/框架侧（非包内容问题）：

1. **R47 lang-preflight 假阳性**：`_manifest_scan` 对 gradle/maven 用全树文件名集合、对 CMake/meson 用顶层集合，含 `android/build.gradle` 子工程的纯 C 库被误判 `mixed` → 自动落终态 `env_unsupported`（exit 2）。未改框架，按真实适配范围复跑得 `c`。建议 gradle/pom 判定同样限定顶层（或加「子工程目录」排除），否则所有带 Android 包装的 C 库都会被错误拒收。
2. **init-build 崩溃**：HMDFS 拒绝 `copytree(copy_function=os.link)` 后，copy2 回退跟随自指符号链接（`android/jni/src -> ../..`）抛 `Symbolic link loop` 整进程崩。建议回退路径加 `symlinks=True`。
3. **W3 预下载改写 conandata.yml 未还原**（复现 2 次）：`build_and_test.sh` 注入 gh-proxy 镜像列表后 restore 未覆盖，工作树残留镜像 URL 会被 PF7/R39 判 P1。本包提交前手工还原。**这是会系统性制造 R39 违规的陷阱**。
4. **PF0 环境闸在本机必然失败**：Python 无法按 PATH 查找执行任何命令（`subprocess.run(['git'|'ls'|'sh'|'clang', …])` 全部 `FileNotFoundError`，绝对路径与 `shell=True` 正常）→ `preflight.py:changed_files()` 必抛，create-pr 被 fail-closed 拦截，**任何包都无法建 PR**。已获授权用 `--no-preflight` 旁路，PF1-PF9 等价事实由 W3（L0/L1/L4/L5 + JC1-JC6 全绿）与 W4 独立审计（pass，P0/P1/P2=0）核验。建议 preflight 的 git 调用统一走 `shell=True`/绝对路径。
5. **`gitcode_pr.py cmd_monitor_review` NameError**（`unreplied_opinions` 未定义，第 1066 行）：`submit --resume` 的 AI Review 五阶段监控整体不可用，只会循环打印「获取检视状态失败，重试…」。本次改用 `ci-status`/`get-comments`/`get-review-comments`/`trigger-ci`/`reply-comment` 手工闭环。
6. **`submit` 自检 `packaging_present` 仍要求 DESTDIR 时代产物**（`packaging/*.tar.gz`），而 `package_builder.py` 未在 `ohc-run.py` 注册子命令；且 `_writeback_submit_state()` 写 `<repo_root>/.submit-state.json`，`submission._load_submit_state()` 读 `ver_dir/.submit-state.json` —— 两处路径不一致，手工 create-pr 后无法 `--resume`。

### 知识图谱使用情况

- **引用知识条目**: 无有效引用（conan-verify 首跑失败时引擎误命中 E538/harfbuzz shared 冲突，与本包零依赖事实无关，已弃用）
- **新增知识草稿**: E429（Makefile `CFLAGS ?=` 被环境顶掉 → vendored include 丢失，附 prescan_pattern）
- **引擎命中情况**: 草稿目录 859 条
- **测试统计**: 总计 15（上游功能冒烟 2 + test_package 断言 13）, 通过 15, 失败 0, 跳过 0
- **未覆盖的错误模式**: ① Makefile `?=` 语义与环境变量的交互（已提草稿 E429）；② `conan.tools.files.copy()` 无 `root` 参数导致 package() TypeError；③ CI 预下载改写 conandata.yml 后未还原 → 触发 R39/PF7；④ PF0/python PATH-exec 环境级失效。②③④ 建议各自入库为 E 条目

### AI 检视结果

- **检视阶段到达**: Phase 5 完成（变更摘要 + 检视结论均已产出）
- **变更摘要评估**: 准确。正确描述了「上游无库目标→配方自建 .so/.a」「包范围限定库、排除 GTK2 GUI 与 CLI」「13 项消费者断言由 result 文件解析」三点关键信息，无需要求修改的项
- **检视意见数量**: 0 条需处理（atomgit-bot 结论「✅ 未发现问题」，Info 级，不可 resolve）
- **检视意见处理**: 已在讨论串内回复说明（note_id 190556926，登记 PF0/monitor-review 两项框架事实）；`resolve-comment` 对 bot Info note 返回 400「This type of note can not be resolved」，属正常

### CI 结果

- **本地 CI 模拟 (W3)**: 通过 — JC pass(prdiff 11 文件) / L0 pass / L1 pass(含 L1e 破坏性反向验证) / L4 pass / L5 pass / L2 skip(纯库无 bin)，Pass rate 100%
- **远程 CI (PR 校验)**: ✅ PASSED — 构建 #49434（Worker OpenHarmonyPCDeveloper-CI-012），7 个步骤全绿，Conan test_package / L0 / L1 门禁通过
- **CI 失败原因**: 无（首跑即绿）

### 效率分析

- **HANDOFF 次数**: 6 次（w4_audit_not_done、self_check_failed:packaging_present、pr_creation_failed:PF0、feedback 占位符、G0 clean-verify 假设有 ./configure、lang-preflight env_unsupported）
- **重试次数**: conan-verify ×3（含 1 次配方 bug 修复）、finish/W3 ×3（L5a soname、prdiff 模式、最终复验）、init-build ×2（网络 + copytree 崩溃）
- **关键瓶颈**: 框架侧不可用点串联（W3 改写 conandata → W4 判 P1 → 返工；PF0 拦死 create-pr；monitor-review 崩 → 需手工驱动 CI 闭环），包本身技术难度低（零依赖、无补丁）。约 60% 额外耗时来自框架缺陷
- **耗时较长的步骤**: ① W4 独立审计两轮（含 P1 返工）≈ 35 min；② 远程 CI 排队到出结果 ≈ 21 min（16:10 触发 → 16:31 通过）；③ submit/W3 的 conan create 复验 ×3 ≈ 6 min；④ init-build 下载重试（github.com 连接超时）≈ 3 min

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 10 个事件（含 4 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-17T13:04:47 | skeleton_created | result_env_unsupported |
| 2026-09-17T13:04:47 | lang_mismatch | task=cpp detected=mixed → env_unsupported 迁移 |
| 2026-09-17T13:06:24 | lang_checked | detected=c 与任务 cpp 匹配 |
| 2026-09-17T13:59:19 | handoff:w4_audit_not_done | W4 Pre-PR 审计未执行，请先完成审计 \| python3 scripts/pre_pr_audit.py generate --repo-dir /storage/Users/currentUser/tttt/bih-pktriggercord --package libpktriggercord --version 0.85.1-20221221181244 \| 审计子任务完成后将结果保存为 reports/audit-result.json |
| 2026-09-17T14:55:43 | handoff:self_check_failed | 自检未通过: ['packaging_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit libpktriggercord 0.85.1-20221221181244 |
| 2026-09-17T15:00:11 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/libpktriggercord-0.85.1-20221221181244 --target main --title 'feat(libpktriggercord): 0.85.1-20221221181244 适配完成' |
| 2026-09-17T16:03:16 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-17T16:03:16 | handoff:resume_no_state | 状态文件 .submit-state.json 中无 PR 编号 \| 请重新提交: python3 scripts/ohc-run.py submit libpktriggercord 0.85.1-20221221181244 |
| 2026-09-17T16:05:04 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-17T16:05:04 | skeleton_exists | resume_pr_exists |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **PF0 环境闸必须能在鸿蒙 PC worker 上工作**：`scripts/ohc/preflight.py` 里所有
   `subprocess.run(["git", …])` 改为 `shell=True` 或绝对路径解析（本机 Python 按 PATH 查找执行任何命令都会
   `FileNotFoundError`，绝对路径/shell 正常）。现状等于「所有包都建不了 PR」，只剩 `--no-preflight`
   一条逃生口，把安全闸变成了普遍性绕过——比没有闸更危险。
2. **`gitcode_pr.py:cmd_monitor_review` 修 NameError（1066 行 `unreplied_opinions`）**：
   R42/R44 的自动闭环依赖它；本次只能手工用 `trigger-ci`/`ci-status`/`get-comments` 驱动，
   且 `submit --resume` 因此完全不推进状态。
3. **W3 预下载改写 `conandata.yml` 必须还原**（`build_and_test.sh` 的 trap 未覆盖该路径，本次复现 2 次）：
   残留的 gh-proxy 镜像 URL 会被自己的 PF7/R39 判 P1，形成「SKILL 制造违规、SKILL 的审计再打回」的闭环浪费。
4. **`lang-preflight` 的 manifest 判定统一按顶层目录**（或对 `android/`、`examples/`、`tests/` 等
   子工程加排除），否则任何带 Android/Java 包装的 C/C++ 库都会被误判 `mixed` 并自动写 `env_unsupported` 终态，
   直接损失一次适配任务。
5. **`_writeback_submit_state()` 与 `_load_submit_state()` 路径不一致**（repo 根 vs `ver_dir`）：
   手工 `create-pr` 之后 `submit --resume` 必然「状态文件中无 PR 编号」。建议统一为 `ver_dir`，
   并让 create-pr 成功时若无状态文件也回写（ktextwidgets #7104 的教训只修了一半）。
6. **`submit` 自检 `packaging_present` 与 conan 流程脱钩**：`package_builder.py` 没有注册子命令，
   DESTDIR/staging 又已被 R20 废弃。要么把 `package` 子命令接回 `ohc-run.py`，要么在纯 conan 流程下
   改为「存在 conan 包产物即视为满足」。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. `templates/conanfile-makefile.py.tmpl` 应显式提醒：**上游 Makefile 里的 `X ?= …` 形式变量必须用
   make 命令行变量覆盖**，并给一段「保住上游默认值」的示例（本次就是 `-I$(JSONDIR)` 被环境顶掉）。
2. `templates/conanfile-makefile.py.tmpl` 与 `conan-init` 生成的骨架仍在 `package()` 里给了
   `copy(..., root=True)` 这类 conan 1 写法（本次 G2 首跑即崩）。模板需按 conan 2 API 全量校订。
3. **裸 Makefile 且上游不产出库** 的情形没有模板（本次要点是把 `SRCOBJNAMES` 对象集自建成 `.so/.a`
   并显式 `-Wl,-soname`，否则 L5a 必挂）。建议新增 `conanfile-makefile-lib.tmpl` 变体。
4. `templates/test_package/conanfile.py.tmpl`（CMake 版）应替换/补充 direct-cc 版：OHOS 上 CMake
   编译器 ID 探测有已知失败面（critnib 已有先例），direct-cc + 解析被测程序 result 文件的模式应成为库类默认。
5. **PR 正文自动填充把上游/适配后用例数全填成 0**（本包真实值 2 与 15），需人工整段重写；
   建议从 `test_package/MANIFEST.yml` 的 `upstream_test_case_count`/`assertion_count` 与
   `HMBS_*` 标记直接取数，避免 R51 关注的「如实回填」靠人肉。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **自动为「上游无测试框架」的包生成 R51 清点证据**：本次手工跑 `find`/`grep Makefile 目标` 并手抄退出码。
   可复用 `prescan` 能力输出一份「测试入口清单」（tests/ 目录数、`test|check` 目标数、ctest/pytest 注册数、
   CI script 段里的功能命令），直接灌进 MANIFEST.yml 与 PR 正文。
2. **`finish` 的 G0 clean-verify 应按构建系统分派**：本次它无条件跑 `./configure`（exit 127），
   对 makefile/headeronly 类项目必然假失败，只留噪音。
3. **把 CI 闭环做成可重入的状态机**：当 `monitor-review` 不可用时，submit 应能降级到
   `trigger-ci` + `ci-status` 轮询（本次手工做了这件事，`pktc-ci-poll.sh` 可作为参考实现），
   而不是打印一次失败后死循环到 30 分钟超时。
4. **`gen_summary` 修复 `'str' object has no attribute 'append'`**（本次 finish step 8 失败）。
5. **`resolve-comment` 对 bot Info note 返回 400** 的分支应识别为「无需 resolve」而非错误，
   避免检视闭环校验把这类意见算成未处理。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. 已提草稿 **E429**（Makefile `CFLAGS ?=` 被环境顶掉 → vendored include/-lm 丢失；含
   `prescan_pattern: CFLAGS\s*\?=\s*.*-I\$\(`，可让预扫描在立项阶段就提示）。建议优先转正。
2. 建议新增「`conan.tools.files.copy()` 无 `root` 参数（conan 1 → 2 API 漂移）」条目：
   签名 `TypeError: copy() got an unexpected keyword argument 'root'`，影响所有沿用旧模板的配方。
3. 建议新增「CI/W3 预下载把 `conandata.yml` 改写成镜像列表未还原」条目（现象：PR 里出现
   `gh-proxy.com/https://…`，被 PF7/R39 判 P1；根因在工具侧而非提交者）。
4. 建议新增「鸿蒙 PC 上 Python 不能按 PATH 查找执行命令」环境条目（现象：任意
   `subprocess.run(['<name>', …])` → `FileNotFoundError`，绝对路径与 `shell=True` 正常；
   影响所有非 shell 的框架内调用，含 PF0）。
5. 建议为 `DT_SONAME` 缺失（`clang -shared` 默认不写 SONAME → CI L5a 拦截）补一条小条目：
   本包配方自建库时踩到，属高频可复用陷阱。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: werly
- **邮箱**: yqihuiqhh@qq.com
- **Agent ID**: F647
- **生成时间**: 2026-09-17 13:04:47
- **PR 编号**: —
- **Git Commit**: 3e9c9ae236
