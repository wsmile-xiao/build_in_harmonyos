# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_5a08411b.md`

---

## 背景

- **软件名称**: libncurses
- **版本**: 6.6_p20260516
- **构建日期**: 2026-09-18
- **构建系统**: autotools
- **上游仓库**: https://invisible-mirror.net/archives/ncurses/ncurses-6.6.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 5
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
| build | 编译构建 | 成功 | 构建系统: autotools |
| conan-verify | 配方验证 | 通过 | G1/G0/G2/G3 全 PASS，conan create 干净构建成功 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | PR #10975, CI 通过 | AI Review: Phase 1 (等待摘要) |

### 失败与问题

本次流程未遇到阻塞性问题

### 知识图谱使用情况

- **引用知识条目**: E007, E011
- **新增知识草稿**: 无
- **引擎命中情况**: 草稿目录 1082 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**: 非 wide 配置下 ncurses `link_test` 因 `USE_EXT_SP_FUNC_SUPPORT` 漏 `NCURSES_EXT_COLORS` 而无法链接（已随本 PR 新增草稿 `DRAFT-libncurses-6.6-narrow-abi-link-test.kv`）；conan `self.run()` 继承输出流导致编译器静默失败（已新增草稿 `DRAFT-libncurses-6.6-conan-run-log-bound-steps.kv`）

### AI 检视结果

- **检视阶段到达**: Phase 1 (等待摘要)
- **变更摘要评估**: 未能取得——`scripts/gitcode_pr.py monitor-review` 存在 NameError（见「建议」），atomgit-bot 只发布了「正在生成合并请求摘要/AI 代码检视正在进行中」占位评论，无实质摘要
- **检视意见数量**: 0 条实质意见（`get-review-comments` 唯一一条为 bot 的「正在进行中」占位 ⚪ Info）
- **检视意见处理**: 无需处理（无实质意见）；W4 独立审计三轮均 verdict=pass（P0/P1=0）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 通过 (PR 校验)
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 0（W3/finish/submit 均一次通过；无 HANDOFF 块）
- **重试次数**: W3 本地 3 次（1 次 JC 整仓扫描假失败 + 1 次编译器静默失败 + 1 次通过）；远程 CI 2 轮（首轮 lld 缺 libxml2.so.16 → 修复后通过）
- **关键瓶颈**: ① `ConanFile.run()` 输出流继承导致的编译器静默失败，定位耗时最长（需自建探针配方逐项对照）；② 远程 CI 的失败日志只回传末尾 64K 字符，且 `monitor-review` 崩溃使 AI 检视阶段无法自动闭环
- **耗时较长的步骤**: 本地 `conan create` ~8-13 分钟（configure 4 分钟 + make 4 分钟 + check 1 分钟）；`finish` 因 conan-verify 与 W3 各跑一次 conan create 需 ~25 分钟；远程 CI 单轮 ~8-15 分钟

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 4 个事件（含 0 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-19T01:14:46 | skeleton_created | pr_created |
| 2026-09-19T01:14:46 | pr_created | PR #10975 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/10975 |
| 2026-09-19T01:30:12 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-19T01:30:12 | skeleton_exists | resume_pr_exists |
<!-- EVENTS:END -->

---

## 建议

### SKILL 设计改进

1. **`ConanFile.run()` 输出流继承问题应在 SKILL 层面固化**：本次 W3 与远程 CI 都命中"clang 首个编译单元静默失败（无诊断、make 只报 Error 1）"，定位花了整整一轮（自建探针配方在同目录逐项对照 5 种调用方式）才发现触发条件是"recipe 进程的输出流被继承"，而非编译器参数/环境/源码。建议在 `templates/conanfile-*.py.tmpl` 与 SKILL 的 R33 附近加一条强制写法：**构建步骤（configure/make/make check/make install）输出一律绑定日志文件**（`self.run(f"{cmd} > {log} 2>&1")`），失败时回显尾部并抛出带路径异常。这能同时消除"静默失败"和"失败无从诊断"两个问题。
2. **`clean-verify`（finish step 3/10）不遵循 `conandata.yml` 的 `patches[].base_path`**：它用 `patch -p1 -i` 从源码根应用补丁，凡带 `base_path`（如 ncurses 的 `ncurses/Makefile.in`）的补丁必报 `Hunk 1 FAILED`。当前虽是非阻塞，但 HANDOFF 文案会误导 AI 去"修补丁"。建议让它读取 base_path（或在存在 base_path 时跳过并标注"该步不适用"）。
3. **PF8 与 PF9 自相矛盾**：PF8 要求 CLI 包（`bindirs` 非空）必须有软件级 `commands.json`，PF9 却因该文件路径层级 <5（`archives/<l>/<pkg>/commands.json`）一律拦截，首适配包必被互相卡住，只能 `OHC_PREFLIGHT=0` 跳过整组硬闸。建议 PF9 对 `archives/<l>/<pkg>/` 下的 `README.md`/`commands.json`/`manifest.yaml` 三个软件级文件做白名单豁免（main 上已有 `archives/a/aiac`、`archives/o/orcania` 等先例）。
4. **`monitor-review` 已失效**：`scripts/gitcode_pr.py:1066` 抛 `NameError: name 'unreplied_opinions' is not defined`，导致 `submit` 的 AI 检视 5 阶段监控每次都"获取检视状态失败，重试"直到超时，AI 检视闭环实际上无法自动完成（本次无法取得变更摘要、也无法确认是否有检视意见）。建议修复该变量（应为 `review_opinions`）后再依赖该阶段做闭环判定。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **`notes.md` 模板应包含"已知框架限制"小节**：诸如 clean-verify 不认 `base_path`、`gen_summary` 抛 `'str' object has no attribute 'append'` 这类非阻塞失败，如果不写进归档，评审会以为作者漏了步骤；写进 PR body 又会让正文冗长。建议模板加一节专门记录"与配方无关但 finish 会报错"的已知项。
2. **PR body 模板的"测试用例对比"表应明确"上游 make check 只编译不运行交互式程序"这类口径的填写方式**：ncurses 的 86 个 `test/programs` 是交互式的，上游 `make check` 只构建不执行；若不说明，作者容易把"构建通过"写成"用例通过"，反而构成夸大。建议模板对"编译期自检"与"运行期用例"给出两种填写范式。
3. **`test_package/MANIFEST.yml` 的 `assertion_count` 建议要求写明口径**：本次 43 条断言里，6 个 metadata 消费者各按"接口路径旗标 + 链接轨迹 + 运行"3 条口径计，而 4 个 C 程序由程序自带 `puts("X/N")` 自报。审计两轮都追问过这个数，建议模板要求注明"口径定义"。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **CI 失败日志应完整回传**：本轮远程 CI 失败只回传末尾 64178 字符（共 380253 字符），真实失败点（`subprocess` 编译 metadata 消费者时 lld 缺 `libxml2.so.16`）恰好落在被截断之外的调用栈里，是靠 ConanException 栈帧字符串才定位到的。建议机器人把 `error|Error|failed` 关键行单独抽一个"错误摘要"段，而不是只给尾部。
2. **`submit` 的 AI 检视阶段应可跳过**：当 `monitor-review` 连续 N 次返回同样的错误（而非"未就绪"）时，应判定为工具故障、跳过该阶段并记录，而不是继续每 5 分钟重试到 30 分钟超时——本次因此白等约 30 分钟。
3. **`reports/` 被 .gitignore 忽略但 PR 必须携带其中文件**：`test-report.md`/`pr-body.md`/`audit-result.json` 都需要 `git add -f`，而 `submit` 的自检只检查本地文件存在，不会提醒"这些文件不会进 PR"。建议 `submit` 增加一项 `reports_tracked` 自检（`git ls-files` 校验三个文件已在版本控制中），否则评审在看 diff 时找不到 test-report。
4. **远程 CI 单轮耗时（~8-15 分钟）已足够便宜**，建议在 SKILL 里把"CI 红 → 修复 → push → resume"的标准循环明确为 2 轮上限的硬性动作，并在 `submit --resume` 输出里直接打印当前轮次计数（R42 已有轮次计数，但 HANDOFF 文案不够显眼）。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. **建议新增 E-entry: conan `ConanFile.run()` 继承输出流导致编译器静默失败**（错误面：`make: *** [Makefile:N: target] Error 1` 且日志无任何 `error:` 行；phase=compilation）。根因是 `conan_run()` 用 `stdout = stdout or sys.stderr` 把 recipe 进程的输出流交给子进程；判据是"同一命令在 shell 里成功、把输出重定向到文件后经同一 `run()` 也成功"。修复动作：每步绑定日志文件。已随本 PR 提交草稿 `DRAFT-libncurses-6.6-conan-run-log-bound-steps.kv`（与既有 E009 的"pipe-bypass"不同：`| cat` 会吞掉 make 的退出码，不可作为修复）。
2. **建议新增 E-entry: `test_package` 里用裸 `subprocess` 编译会丢 conan build 环境**（错误面：`Error loading shared library libxml2.so.16 ... needed by .../lld` → `clang: error: unable to execute command`，phase=linking）。根因与已有 E373 同源但表现不同：E373 讲的是"路径/PATH 丢失"，本条是"**SDK 链接器自身的运行时库路径丢失**"（profile `[buildenv]` 的 `LD_LIBRARY_PATH`）。修复：改用 `self.run(..., env="conanbuild")`（或 `capture_output` 前显式补 LD_LIBRARY_PATH）。本次已在 `test_package/conanfile.py` 用 `VirtualBuildEnv(self).generate()` + `env="conanbuild"` 解决。
3. **建议给 E120/E266 补充"配方内修复"这一实现路径**：两条现有条目都指向"环境变量/换链接器"，但没有说明"在 test_package 或 recipe 内如何确保该环境变量生效"。建议在 `rec_description` 里补上"Conan 侧通过 `env="conanbuild"` 或 `VirtualBuildEnv` 获取"这一条，避免作者去硬编码 SDK 路径。
4. **建议新增 E-entry: `winch()`/`wgetch()` 类光标相关 API 的测试断言陷阱**：`winch(win)` 等价于 `mvwinch(win, getcury(win), getcurx(win))`，在 `waddstr` 之后调用会读到光标处而非刚写的字符，测试会假失败。属"测试自身低错"，建议归入测试类条目（本次实测踩到）。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: Kongling32
- **邮箱**: 308360610@qq.com
- **Agent ID**: 5475
- **生成时间**: 2026-09-19 01:14:46
- **PR 编号**: 10975
- **Git Commit**: d3f46f584b
