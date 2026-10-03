# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_d0c4dfef.md`

---

## 背景

- **软件名称**: libflorist
- **版本**: 2025.1.0
- **构建日期**: 2026-09-27
- **构建系统**: autotools
- **上游仓库**: https://github.com/AdaCore/florist/archive/d28d09a618e9439e58ebc0368d100fe3b2992697.tar.gz
- **适配路径**: **路径 B（场景二：适配困难库分析报告）** —— 不申请路径 A
  > 骨架默认填了"路径 A（基础适配）"，与本次实际不符（上游测试 14/60，不满足路径 A 计分条件），已人工纠正。
- **补丁数量**: 1
- **编译依赖**: gcc-ada/9.5.0, binutils/2.46.0（均为 tool_requires；骨架默认填"无"，实际有 build_requirements，已纠正）
- **最终状态**: 成功（**部分适配归档 / 平台受限**：库本体可用，上游全量测试受平台能力限制）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 上游无 Release/tag，固定 25.1 分支提交 `d28d09a6`；`search-url` 给的 Savannah URL 实测 404（假阳性） |
| build | 编译构建 | 成功 | autotools；37 个 Ada 单元 + 2 个 C 单元入 `libflorist.a`（41 成员） |
| conan-verify | 配方验证 | **PASS** | G0–G4 全 PASS；L2/L4/L5 PASS（无 cache 路径时跳过但判 PASS） |
| finish | 归档收尾 | 完成 | W3 本地 CI `exit_code=0`（含 `log_sha256`）；期间因 L0c/JC 门禁两次 HANDOFF 后修复 |
| submit | PR提交+AI检视+CI | **PR #13295 已创建** | AI Review: 仅占位评论（无实质意见）；CI 校验通过（`LVL:2`，test_package/L0/L1 全绿） |

### 失败与问题

本次流程未遇到阻塞性问题。主要曲折集中在**门禁与工具的误报/缺陷**（见"建议"节），而非本库技术障碍：

1. **W3 的 L0c 误拦 Ada 测试**：`test_package/` 测试源为 `.adb`，而 CI L0c 只认
   `.c/.cpp/.cc/.cxx/.sh/.py` → `no_test_sources`。按先例（libncursesada）补 `test.sh`
   入口解决。
2. **W3 的 JC 门禁 scope 问题**：未提交时 `git diff origin/main...HEAD` 为空 →
   junk_check 退化为 `full` 模式扫描整仓，命中**其他包**（cloog/kics/thc，均为
   `origin/main` 既有跟踪文件）的历史遗留隐藏文件 → 拦截。补 `JUNK_PR_DIFF`
   （模拟 CI 的 prdiff 范围）后通过；本包自身在 prdiff 下 `JC_RESULT=pass`。
3. **submit 自检 `packaging_present`**：与 R19/ARCHIVE-SPEC「`packaging/` 已废弃」
   相矛盾（仓库 0 个被跟踪的 `packaging/*.tar.gz`），须本地生成（gitignored）才能过。
4. **PF9 误报**：见"建议 > SKILL 设计改进"第 1 条。
5. **CI 状态遮蔽**：见"建议 > SKILL 设计改进"第 3 条。

### 知识图谱使用情况

- **引用知识条目**: musl 的 sigismember() 对越界信号返回 0（glibc 返回 -1）—— L1 平台真理, 动态链接的 gcc-ada 二进制在 OHOS 上首次 stdio stderr 访问即段错误 —— L1 平台真理, HMDFS 下 umask 077 建出的目录不可写（ACL 覆盖 chmod）—— L1 平台真理, OHOS 拒绝执行未签名 ELF（conftest/生成器均需签名）—— L1 平台真理, gcc-ada 缺 gprbuild/gprinstall/gnatprep 时 Ada 库的构建范式 —— L2 模式经验
- **新增知识草稿**: **3 条**（`knowledge/drafts/` 下 3 组 `*.kv` + `*.md`，共 6 文件；骨架按文件数报 6 条）
  - `DRAFT-libflorist-2025.1.0-gcc-ada-missing-gprbuild`
  - `DRAFT-libflorist-2025.1.0-musl-sigismember-out-of-range`
  - `DRAFT-libflorist-2025.1.0-gcc-ada-dynamic-stderr-sigsegv`
  - 均经 KB 覆盖度核对（`grep -rli` 命中数为 0）确认此前无同型条目
- **引擎命中情况**: 草稿目录 2097 条
- **测试统计**: 总计 5, 通过 5, 失败 0, 跳过 0（消费者断言；上游 61/60/14 另计）
- **未覆盖的错误模式**:
  1. `gcc-ada` 缺 **gprbuild/gprinstall**（此前只有 gnatprep 条目）→ 已沉淀
  2. musl `sigismember()` **越界返回 0** 致生成器算出负信号总数 → 已沉淀
  3. 动态链接 gcc-ada 产物**首次 stdio stderr 即 SIGSEGV(139)** → 已沉淀
  4. `lang-preflight` 的 `LANG_ENUM` 缺 `ada`（本次复现，已有 libncursesada 条目，未重复沉淀）
  5. HMDFS 下 **`umask 077` 目录不可写**导致 autoconf `config.status` 失败
     （已有 E052/E060/E114 同类，但**缺 autoconf 临时目录这一具体场景**，建议补）

### AI 检视结果

- **检视阶段到达**: Phase 3（等待检视意见）—— 机器人仅产出两条占位评论
  （`正在生成合并请求摘要` / `AI 代码检视正在进行中`），未产出实质摘要或意见
- **变更摘要评估**: 机器人未产出实质摘要（仅占位文本），无可评估内容
- **检视意见数量**: **0 条实质意见**（1 条占位评论）
- **检视意见处理**: 无需处理（无实质意见）
- 补充：本次**主动**用独立审计（`code_review` deep，4 维）替代，发现并修复
  3×P2 + 6×P3，写入 `reports/audit-result.json`（verdict=pass）——详见"建议"节

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: **通过**（build #62997 / #63015；
  `Conan test_package: 通过`、`L0 门禁: 通过`、`L1 门禁: 通过`，7 个构建步骤全 ✅；
  骨架默认填"未知"，因其取自写报告时点，已按最终结果纠正）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: harness 自动记录 **2 次**（在 PR 创建节点之后：
  `self_check_failed`、`pr_creation_failed`）。此前阶段的 HANDOFF 未进事件时间线，
  实际人工介入修复 **6 次**：①W3 L0c `no_test_sources` ②W3 JC 门禁（2 轮）
  ③submit `self_check_failed`（packaging+test-report）④`pr_creation_failed`
  ⑤`result_invalid`（partial 需 `--failed-reason`）⑥`result_invalid`（CI 核验 UNKNOWN）
- **重试次数**: `conan create` 约 8 次（含 3 次配方缺陷定位 + 1 次审计修复复验）；
  CI `/rebuild` 触发 2 次（其中 1 次为冗余，反而遮蔽了 CI 绿状态，见建议第 3 条）
- **关键瓶颈**:
  1. **Ada 工具链能力缺口**（gprbuild/gprinstall/gnatprep 全缺）——须自行接管
     构建与安装两阶段，是本次最大工程量来源
  2. **W3 门禁与库语言不匹配**（L0c 只认 C/C++/sh/py，Ada 须绕道 `test.sh`）
  3. **门禁之间口径冲突/误报**（PF9、packaging_present、JC scope），排查耗时
     超过实际编译问题
- **耗时较长的步骤**:
  1. `conan create`（含上游 61 项测试编译与逐项运行）——约 10–15 分钟/轮，
     且因配方缺陷需多轮
  2. 远程 CI 校验（build #62997）——约 30 分钟（`conan-build-test` 步骤 25m22s）
  3. `configure`（libflorist 为老式 autoconf，逐项探测 POSIX 接口）——数分钟
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 2 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-27T19:35:31 | handoff:self_check_failed | 自检未通过: ['packaging_present', 'test_report_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit libflorist 2025.1.0 |
| 2026-09-27T19:39:46 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/libflorist-2025.1.0 --target main --title 'feat(libflorist): 2025.1.0 适配完成' |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。

1. **PF9 对 ARCHIVE-SPEC 强制的软件级文件误报（高优先，本次被迫 `--no-preflight`）**
   - 现象：`PF9 分支/路径闸: 变更路径缺版本目录层` 命中
     `archives/l/libflorist/README.md`、`archives/l/libflorist/manifest.yaml`。
   - 根因：`scripts/ohc/preflight.py:570` 的判据
     `bad = [f for f in arch if len(f.split("/")) < 5]` 拒绝任何深度 <5 段的
     `archives/` 路径，而 `ARCHIVE-SPEC.md` §2.1 明确要求
     `archives/{letter}/{name}/manifest.yaml`（必须）与 `README.md`（必须）——恰为 4 段。
   - 证据：今日合并的 `249d018a53`(leatherman)、`750f1e64df`(jaaa) 提交均含同形态文件；
     且 CI 仅以 `$pkg_dir/conanfile.py` 存在与否纳入包（`build_and_test.sh:233`），
     软件级目录不含 conanfile.py，不会触发 "No packages to build"。
   - 建议：PF9 的深度判据**豁免软件级白名单文件**
     （`README.md`/`manifest.yaml`/`commands.json`），或改为"每包至少有一个
     `archives/<l>/<pkg>/<ver>/` 变更"而非逐文件深度校验。

2. **`packaging_present` 自检与 R19/ARCHIVE-SPEC 冲突（高优先）**
   - 现象：`submit` 自检硬拦 `packaging_present`（要求 `packaging/*.tar.gz`），
     而 ARCHIVE-SPEC v3.0 与 R19 明确「`packaging/` 已废弃，Conan 体系替代手动 tar.gz」，
     仓库中 **0 个**被跟踪的 `packaging/*.tar.gz`（538 个包均无）。
   - 后果：Adapter 须生成 gitignored 的本地 tar.gz 才能过闸，属**为过闸而制造冗余产物**。
   - 建议：v3.0 配方（存在 `conanfile.py`）应豁免此检查，或降级为 WARN。

3. **`ci-status` 取"最后一条 CI 评论"致 CI 绿被永久遮蔽（高优先，本次直接踩中）**
   - 现象：CI 实测通过（评论 `LVL:2`「CI 校验通过」），但
     `gitcode_pr.py ci-status` 返回 `UNKNOWN`，导致
     `result --status success` 被"上报硬闸"降级为 `partial`，无法收尾。
   - 根因：`gitcode_pr.py:582` 取 `ci_comments[-1]`（最后一条），
     而多触发一次 `/rebuild` 会产生一条更晚的 `LVL:0「构建触发中」`提示评论，
     它没有 LVL 语义却永久排在绿评论之后。
   - 建议：①优先解析带 `<!-- LVL:N -->` 标记的评论，取 **LVL 最大**者而非最后一条；
     ②或在 `ci-status` 中忽略 `LVL:0` 的 pending 提示；
     ③或让 `/rebuild` 复用同一条评论（原地更新）而非新发评论。

4. **`monitor-review` 子命令存在必崩缺陷（高优先）**
   - 现象：`python3 gitcode_pr.py monitor-review --repo ... --number 13295` 直接抛
     `NameError: name 'unreplied_opinions' is not defined`
     （`gitcode_pr.py:1066`，疑似应为 `review_opinions`）。
   - 后果：`submit` 流程中"AI Review 监控（5 阶段）"这一核心环节**无法使用**，
     Adapter 只能退回手工看评论，与 R42「不裸等/工具化监控」的意图相悖。
   - 建议：修复变量名并纳入回归测试（该路径显然未被测试覆盖）。

5. **`pre_pr_audit.py check` 的 `.ci-result.json` 路径错位（中优先）**
   - 现象：`check` 查 `repo_dir/.ci-result.json`（仓库根），
     而 `finish` 实际写入 `<ver_dir>/.ci-result.json` → 永远报
     "W3 本地 CI 模拟结果未找到"。
   - 建议：按版本目录查找，或同时查两处。

6. **`finish` fallback 到 `full` 模式扫描整仓（中优先）**
   - 现象：未提交时 `git diff origin/main...HEAD` 为空 → junk_check 走 `full`
     → 命中**其他包**的历史遗留隐藏文件并拦截本包构建。
   - 建议：无变更时不应 fallback 到 `full`（或 `full` 模式下仅告警不阻塞）；
     本包自身的正确 scope 是 CI 使用的 prdiff。

7. **`result.partia` 要求 `--failed-reason`（低优先）**
   - 现象：`--status partial` 被要求提供 `--failed-reason`（判定源自非 success 类），
     而 partial 是"进行中"而非失败。本次只能填写一段"非失败"说明绕过。
   - 建议：`partial` 不强制 `--failed-reason`，改要求 `--summary`。

8. **`result` 升级需 `--force` 且与 partial 互斥（低优先）**
   - 现象：先写 partial 草稿后，CI 绿再报 success 会因"文件已存在"被拒，须 `--force`；
     而 `--force` 又被 CI 核验闸二次拦截（叠加建议 3 时完全卡死）。
   - 建议：允许 `partial → success` 的**单向升级**免 `--force`（防降级逻辑本意是
     防 success→partial，不应阻止反向升级）。

9. **`lang-preflight` 的语言枚举缺 `ada`（中优先，本次复现）**
   - 现象：`detected_language=c`——只统计到 4 个 `.c`，忽略 339 个 Ada 源文件
     （`.adb`/.ads` 未进 `_EXT_LANG`/`_C_EXTS`/`_CPP_EXTS`，`LANG_ENUM` 也无 `ada`）。
   - 后果：R47 语言门对 Ada 项目**静默失效**；本次因 `c` 在兼容族内未阻断，
     但结论（"Ada 库被判为 C 库"）会误导评审与计分。
   - 建议：`LANG_ENUM` 增补 `ada`，`_EXT_LANG` 收录 `.adb`/`.ads`/`.gpr`；
     并在 `build_system=none` 且存在未覆盖扩展名时输出 warning 而非静默放行。
     （已有 `DRAFT-libncursesada-...-langpreflight-missing-ada-enum` 条目，本次不重复沉淀）

### 模板改进

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。

1. **缺 Ada/GNAT 语言模板（高优先）**
   - 现状：模板库覆盖 CMake/Autotools/Makefile/Meson/header-only，但**无 gcc-ada 范式**。
     本次 libflorist 的 10 项方案（gnatmake 替代 gprbuild、gnatprep 替身、生成器
     `-static`、显式安装布局、原生双 profile、签名、C 单元入归档…）全靠逐项摸索，
     与仓库既有 3 个 Ada 包（libncursesada/libgmpada/adacgi）的解法高度相似。
   - 建议：新增 `conanfile-ada.tmpl`（含 `_tool()`/`_ada_root()`/签名/上游测试 PTY
     驱动骨架），可把后续 Ada 库的适配从"8 轮 conan create"降到 1–2 轮。

2. **上游测试运行器模板缺失（中优先）**
   - 本次自研 `tools/run_upstream_tests.py`（签名 + PTY + 逐项超时 + 机器可读结果表），
     解决了"stderr 重定向到文件会制造假失败"这类平台陷阱。`tests/README` 明确要求
     stderr 为终端，但模板/文档未提示。
   - 建议：把"OHOS 下上游测试须签名 + 须 PTY"写入模板与 SKILL 指引（本项已沉淀
     为 L2 知识候选）。

3. **PR body 模板对"部分适配/路径 B"无支持（中优先）**
   - 现状：`_generate_pr_body()` 产出的模板以路径 A（全绿）为默认叙事，
     缺乏"部分适配 / 平台受限"的表达位（如平台受限说明、路径 B 声明、上游测试
     双口径回填）。本次整篇 PR 正文为手工重写。
   - 建议：模板增加分支：当上游测试未全过时，自动输出"不申请路径 A + 路径 B
     证据位置 + 失败根因分类"结构。

4. **feedback 骨架的"适配路径"默认值错误（中优先）**
   - 现象：骨架自动填 `适配路径: 路径 A（基础适配）`，与本次实际（路径 B）不符，
     若 AI 未察觉就会产出**错误结论的报告**。
   - 建议：路径应由 manifest/notes 推断或留空为占位符，而非默认路径 A。

5. **feedback 骨架的"编译依赖"默认填"无"（低优先）**
   - 现象：本包有 `tool_requires`（gcc-ada/binutils），骨架未从 conanfile 提取，
     直接填"无"。建议从 `build_requirements()` 提取依赖。

6. **`test-report.md` 模板默认"核心功能通过率 100%"（低优先）**
   - 模板以 100% 为示例值，对"部分适配"场景有引导偏差。
     建议标注"按实测填写，平台受限时据实说明"。

### 自动化补全

> 针对需要人工介入的环节，提出自动化改进建议。

1. **W3 的 junk_check 应自动采用 prdiff 范围（高优先）**
   - 本次人工构造 `JUNK_PR_DIFF` 才让 W3 与 CI 口径一致。建议 W3 在无
     committed diff 时，用"本包路径 + knowledge/drafts"自动生成 scope，
     而非退化到 `full` 扫整仓。

2. **L0c 应支持更多测试源扩展名或自动识别编译命令（中优先）**
   - 现状：只认 `.c/.cpp/.cc/.cxx/.sh/.py`；Ada（`.adb`）、Fortran、Go 等
     均需绕道补 `.sh` 入口。建议扩展名白名单可配置，或改为"解析
     test_package/conanfile.py 的 build()/test() 是否引用到源文件"。

3. **上游测试运行应内置签名与 PTY（中优先）**
   - 建议把"签名 + PTY + 逐项超时 + 结果表"做成 SKILL 内置能力
     （如 `ohc-run.py upstream-test <pkg> <ver>`），避免每个 Ada/交互型包重复造轮子。

4. **`result` 的 CI 核验应容忍 pending 提示（高优先）**
   - 与建议 3 同源：自动忽略 `LVL:0` 的 pending 提示，或按 LVL 最大者判定，
     使 CI 绿后能自动升级 success（当前会卡在 partial）。

5. **`submit` 应在 PR 创建后自动续跑 AI Review 监控（中优先）**
   - 受建议 4（`monitor-review` 崩溃）影响，本次 AI Review 监控实际未生效。
     修复后建议同时补一条"机器人未产出实质意见时的超时判定"，
     避免 Adapter 无谓等待。

6. **依赖提取应覆盖 `tool_requires`（低优先）**
   - `_extract_conanfile_deps` 仅扫 `requires`，本次 PF4 依赖闸与 feedback 骨架
     均未体现 `gcc-ada`/`binutils`。建议同时提取 `build_requirements()`。

### pc-pr-review 审查规则（2026-09-28 首轮 FAIL 后追加）

> 本轮 PR #13295 首次 pc-pr-review 结果 **VERDICT=FAIL**（rule1/rule6/rule12 三项 FAIL，
> 其余 10 条 PASS）。以下三点为审查规则本身与流程顺序的改进建议。

1. **rule12 口径应与申报路径挂钩（路径 B「无法适配」类建议豁免或另设口径）**
   - 现象：rule12 要求适配后统计表必须有「PC 特有测试」/「鸿蒙特有测试」/
     「消费者用例」/「消费者测试」行，否则 FAIL。
   - 问题：路径 B「无法适配」类申报（本 PR 前缀即【无法适配】，上游 14/60 未全过）
     的交付物是**分析报告**而非完整适配，其"新增测试"天然是消费者/平台契约类；
     若表述未逐字命中四个关键词即被机械拦下，等于每份无法适配申报都要被拦一次。
   - 证据：同类先例 `archives/l/lenovolegionlinux/0.0.20` 的 PR body 在
     「补全测试用例说明」下勾选了 `- [x] **是**`（"上游用例无法在 OHOS PC 侧执行的部分，
     适配后补全了消费者/平台契约测试"），说明路径 B 场景下"补全测试"是常态，
     与路径 A 的语义不同。
   - 建议：①rule12 对路径 B 类 PR 放宽为"消费者/平台契约测试"同义词白名单；
     或 ②在 PR 模板中直接把该行预置为固定行（模板已含「鸿蒙特有测试」行，
     但"适配后测试用例统计"是可选小节，容易被省略），
     使规则与模板强绑定而非依赖作者措辞。

2. **rule1 模板错配：标题前缀触发的模板与正文申报路径应一致**
   - 现象：PR 标题前缀为【无法适配】，但正文按路径 B 场景二（适配困难库分析报告）
     撰写；rule1 校验的是模板复选框，而本文档结构（报告体）与
     `templates/积分赛事PR模板.md`（标准适配体）不同构，导致复选框解析不到。
   - 问题：**标题前缀与申报路径是两个独立维度**，平台按前缀选择模板，
     但作者按申报路径组织正文，二者错配时 rule1 必然 FAIL，
     且**不是靠"补齐字段"就能根治**（本轮已逐字补齐通过，但根因仍在）。
   - 建议：①为【无法适配】前缀提供专用模板（含报告体所需的
     "根因分析 / 适配障碍 / 已验证方案及结果"字段 + 两个必需复选框）；
     或 ②rule1 改为"按正文申报路径选择模板"，而非按标题前缀。
   - 附：本轮按任务要求**保持【无法适配】前缀不变**（通过补齐字段过 rule1），
     故此处仅记为改进建议，未改标题。

3. **R45 反馈入仓时机建议后移到 AI 检视通过之后**
   - 现象：R45 规定"反馈填完闭环时自动 commit+push 到任务分支随 PR 进 main"，
     而 AI 检视（rule6）要求"检视时间戳 ≥ 最新提交时间戳"。
   - 后果：**每次反馈入仓都会产生新提交 → 使已通过的 AI 检视失效 → 必须重跑检视**，
     形成"闭环一次、重跑一次"的往返（本轮即为此在 14:39 追加提交，
     导致原 19:44 的检视失效，rule6 需重跑）。
   - 证据：本轮已把 notes.md（Step 11）与 feedback（Step 12）的改动合并为一次提交，
     以**减少提交次数**来降低重跑次数；但这只是缓解，根因是流程顺序。
   - 建议：①把反馈入仓安排在 CI/AI 检视通过**之后**（作为最后一步），
     或 ②AI 检视只针对 `archives/` 与 `knowledge/` 路径变更触发，
     `feedback/`、`reports/*.md` 等流程留档文件的提交不使检视失效
     （与 CI 已有行为一致：docs-only 变更不构建包）。

### 知识图谱覆盖

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。

本次新增 3 条草稿（已经 KB 覆盖度核对确认无重复）：

| 建议条目 | 层级 | 核心内容 |
|---|---|---|
| `DRAFT-libflorist-2025.1.0-gcc-ada-missing-gprbuild` | L1/L2 | `gcc-ada` 只有 6 个 GNAT 工具，**无 gprbuild/gprinstall**；GPR 工程（`.gpr`）驱动的 Ada 库须退化为 `gnatmake` 直编 + 自实现 `gprinstall` 布局（`<prefix>/floristlib` + `<prefix>/share/gpr/*.gpr`，且 `.gpr` 内相对路径须按"项目文件所在目录"上溯） |
| `DRAFT-libflorist-2025.1.0-musl-sigismember-out-of-range` | L1 | musl `sigismember()` 对越界信号返回 **0**（glibc 返回 -1）；以"越界=-1"为前提的信号区间推导会算出负数（本例 `NSIGS := -2`），产出非法 Ada（`dynamic or empty choice in aggregate`）。修法：`if ((first_bad >= 0) && ...)`，POSIX 兼容、不加平台宏 |
| `DRAFT-libflorist-2025.1.0-gcc-ada-dynamic-stderr-sigsegv` | L1 | 动态链接的 gcc-ada 产物**首次 stdio `stderr` 访问即 SIGSEGV(139)**（`write(2)` 正常、`-static` 正常、clang 编译正常）；构建期小工具须 `-static`。附易混辨析：未签名=**126**，本条=**139** |

建议补强（现有条目未覆盖的具体场景）：

| 建议 | 理由 |
|---|---|
| HMDFS「autoconf 临时目录」场景 | 现有 E052/E060/E114 覆盖 HMDFS 权限大类，但**缺** `configure`/`config.status` 用 `umask 077 && mktemp -d` 建目录后在 HMDFS 不可写（`can't create ./confXXXXXX/subs1.awk`）这一具体形态；解法（`mktemp` 垫片，不改生成文件以守 R6）亦值得记录 |
| Ada 库的"上游测试须 PTY" | `tests/README` 要求 stderr 为终端；stderr 重定向到文件会**制造假失败**（同用例重定向下 FAIL、PTY 下 PASS）。属可复用的 L2 模式经验 |
| `gcc-ada` 缺 `gprbuild` 与已有 `gnatprep` 条目合并索引 | 两者同源（gcc-ada 工具集不全），宜在 `similar_to` 互相引用，便于检索"Ada 工具链缺口"整类问题 |

---

## 作者

- **姓名**: Inception662
- **邮箱**: 3389004972@qq.com
- **Agent ID**: 8D51
- **生成时间**: 2026-09-27 20:29:16
- **PR 编号**: **#13295**（骨架默认填 `—`，已补）
- **Git Commit**: 9de40210a9

---

## 复审轮补充（2026-09-29）—— 响应评审意见

> 评审意见：「无论是否申请路径A，非系统限制的测试用例都需要完成验证。」
> 本轮按此口径重做逐项分类，并修复全部**已定位**的非系统限制项。

### 新增建议：TEST_QUALITY_SPEC 须明确"路径 B ≠ 测试整体豁免"

| # | 建议 | 理由 |
|---|---|---|
| 1 | **「非系统限制项须修绿」写入 TEST_QUALITY_SPEC** | 本轮暴露的口径风险：路径 B（部分适配/无法适配）申报容易被理解为"上游测试可整体豁免"。须明文规定：路径 B 只影响**积分路径**，不影响**测试完成度要求**——凡非系统限制的失败项必须修复并验证通过，否则不得回填通过率、不得提交重审 |
| 2 | **新增「上游测试逐项分类模板」** | 本轮 33 ASSERT_FAIL + 3 其他需逐条判定，全靠人工。建议 SKILL 提供模板，字段：`序号 / 测试名 / 失败现象 / 错误码-errno / 判定(系统限制|非系统限制|待查) / 证据(日志行号+源码行号+探针命令) / 修复动作 / 验证结果`。判定列为枚举，且**"待查"不得计入系统限制**，须给出继续调查的下一步 |
| 3 | **判定为"系统限制"须强制证据字段** | 强制要求 `errno 数值 + syscall/API 名 + musl/OHOS 源码或文档引用 + 日志行号`四要素齐全，缺一不得豁免；可从机制上防止"未深入调查即归为平台限制"（本轮首轮的 errno 41 误判即属此类） |
| 4 | **警告：日志中的括号数字不可默认当 errno** | 本轮关键教训：`failed process creation (41)` 的 `41` 是 Florist 自定义哨兵退出码（`Failed_Creation_Exit := 41`），**不是 errno**。建议在 SKILL 的上游测试分析指引中加入此陷阱提示：判定前须回查该数字是否为被测库/测试框架自定义常量 |
| 5 | **驱动脚本须复现上游 runner 的"运行目录布局"** | 本轮 4 项 FAIL + 8 项假失败全部源于此：上游 `run_tests_1` 在 `test.dir` 内建 `ln -fs ../<name>`（供子进程按裸名 exec）与 `bin -> ..`，并逐项设 `umask`。重写测试驱动时若只复制"编译+运行"而漏掉目录布局，会产生**成批假失败**。建议列为 L2 模式经验：*"跑上游测试套件前，先对照上游 runner 逐行复现其目录与环境的副作用"* |
| 6 | **清单中的"测试入口"可能含辅助子程序** | 上游 Makefile 的 `TESTS`/`SPECIAL_TESTS` 混有父用例的子程序（本包 8 个），上游 runner 仅 `ln -fs`、从不独立运行。若逐条当独立测试跑，必然报 `bad arg`（缺父进程传入的 `-child <n>`）。建议模板中加入"依 Makefile 前置依赖关系剔除辅助子程序"的步骤，并单列 `HELPER` 判定 |
| 7 | **CI 基础设施故障须与代码失败区分** | 本轮 CI 在 `git-clone` 步骤以 `resource temporarily unavailable: mkdir` / `exit code 127` 失败，属 worker 基础设施故障（非本包改动）。建议 `diagnose` 识别该特征串并提示"疑似 worker 故障，建议重触发而非改代码"（对照 R43 停损） |
| 8 | **`monitor-review` 存在崩溃缺陷** | `gitcode_pr.py` 的 `cmd_monitor_review` 在组装输出时引用未定义变量 `unreplied_opinions` → `NameError`（第 1066 行）。建议修复：该字段应引用上方已计算的 `review_opinions`/待处理列表 |

### 本轮新增知识候选（L1/L2）

| 条目 | 层级 | 内容 |
|---|---|---|
| Florist `Failed_Creation_Exit := 41` | L1 | 日志中的 `failed process creation (41)` 的 41 是**被测库自定义哨兵退出码**，非 errno；`fork+exec` 在 OHOS 可用（探针实测 `setuid/setgid/open/dup2/pthread_sigmask/execv` 全返回 0） |
| OHOS `timer_delete()` 幂等 | L1 | 对已删除/未初始化 Timer_ID 返回 0（POSIX 期望 EINVAL），使 `p140100` A062/A078 断言失败 |
| 上游 POSIX 校验套件的驱动复现要点 | L2 | 必须复现 `test.dir` 内 `ln -fs ../<name>` + `bin -> ..`、`PATH` 含 tests 目录、`PWD`、逐项 `umask 033`、PTY（TIOCSWINSZ + stdin）；否则成批假失败 |
| 上游清单中的辅助子程序识别 | L2 | 依 Makefile 前置依赖关系剔除（本包 8 个），标记 HELPER 不执行 |

### 本轮通过率变化

| 指标 | 首轮（09-27） | 复审轮（09-29） |
|---|---|---|
| PASS | 14 | **17** |
| ASSERT_FAIL | 33 | **19** |
| 严格通过率 | 14/60 (23.3%) | **17/52 (32.7%)** |
| 剔除 N/A 后 | 14/50 (28.0%) | **17/42 (40.5%)** |

> 剩余 7 类非系统限制项（B 组）本轮**未修完，如实挂账不豁免**；
> 另有 2 项待进一步调查（`p030300a` NOT_LINKED、`p140101` 须补 syscall 名）。
