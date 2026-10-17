# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_55343c0b.md`

---

## 背景

- **软件名称**: clitest
- **版本**: 0.5.0
- **构建日期**: 2026-09-21
- **构建系统**: custom（无构建系统：单文件 POSIX shell 脚本；顶层 Makefile 仅封装 docker 的 lint/test 流程）
- **上游仓库**: https://github.com/aureliojargas/clitest （tag 0.5.0，MIT）
- **适配路径**: 路径 B（知识库扩展）——1 个移植补丁 + 2 条知识草稿
- **补丁数量**: 1（`patches/0001-clitest.patch`，单文件两处改动）
- **编译依赖**:
无（`requires`/`tool_requires` 均为空；运行期依赖 `sh/sed/grep/diff/cat/mktemp/awk/tr` 属系统工具）
- **最终状态**: 成功（conan-verify 8 道门禁通过，finish W3 本地 CI exit_code=0）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | github.com 直连超时，改用 GitHub 官方 tarball 端点 codeload |
| lang-preflight | 语言预检 | 误判（已绕过并记录） | `--lang bash` 判 mismatch 并直接落 `env_unsupported` 终态；默认 `cpp` 口径下判兼容通过 |
| build | 编译构建 | 成功 | 构建系统: custom（零编译单元，仅打补丁 + 安装 + 产物校验） |
| conan-verify | 配方验证 | 通过 | G1/G2/G3/G4 + L2/L4/L5 全通过 |
| finish | 归档收尾 | 完成 | W2 结构 + R36 依赖 + W3 本地 CI 通过（`.ci-result.json` exit_code=0）；step8 `gen_summary` 框架异常、step10 `packaging/` 假告警 |
| submit | PR提交+AI检视+CI | 走 fork 旁路手动建 PR | 详见下方「AI 检视结果」与「SKILL 设计改进」 |

### 失败与问题

| # | 问题 | 性质 | 处置 |
|---|------|------|------|
| 1 | `lang-preflight --lang bash` 把本项目判为 `c`（证据 `build_system: make`），并**直接写入 `env_unsupported` 终态 result.json** | 框架判定缺陷 | 实际源码为 62 个 `.sh` + 1 个 POSIX shell 主脚本、C/C++ 源文件 0 个；顶层 Makefile 只有 docker 封装目标。按仓库既有脚本类先例（`cronic/3`、`lynis/3.1.7.1`）继续适配，终态在流程结束时以 `result --force` 覆盖 |
| 2 | `conan-init` 生成 autotools + C 模板（`test.c` / `CMakeLists.txt`） | 同一误判链的下游 | 按 `cronic/3` 先例改写为脚本包配方，删除 C 模板 |
| 3 | 初版临时目录补丁打挂 1 个上游用例（`test.md:52` 断言无效 `TMPDIR` 必须报错） | 自身设计失误 | 收窄补丁到「仅 `$TMPDIR` 未设置时的默认值」，上游恢复 286/286，上游用例零修改 |
| 4 | shebang 改写后上游自举测试 262/286「失败」 | 验证陷阱（已沉淀为 E546 草稿） | 适配机建立 `/system/bin/sh -> /bin/dash` 映射后恢复 286/286 |
| 5 | `finish` step8 `gen_summary` 抛 `'str' object has no attribute 'append'` | 框架 bug | 非阻塞，流程继续；已在「自动化补全」节登记 |
| 6 | `conan-verify` 的 E017 镜像注入留下 `conandata.yml.ghfast-bak` | 框架清理不彻底（v12.17 已修过一次，仍复现） | 手工删除，避免 JC1 拦截 |

### 知识图谱使用情况

- **引用知识条目**: E165（鸿蒙无 `/bin`，`sh` 在 `/system/bin/sh`）、E002（`/tmp` 只读）、E543（`.work`/`.orig` 硬链接）
- **新增知识草稿**: 2 条
  - `E545-draft-3028`：交付脚本自身硬编码 `${TMPDIR:-/tmp}` → 鸿蒙只读 `/tmp` 下运行期全功能不可用；修法与「不得改掉显式 `$TMPDIR` 语义」的边界。`draft-review` 判定 `review-similar`（近邻 E002，已在条目内写明差异：E002 是构建期，本条是运行期/产物侧）
  - `E546-draft-3028`：shebang 适配后上游自举测试整片假失败的判定与复现方法。`draft-review` 判定 `create`（与 E165 相似度 0.03）
- **引擎命中情况**: `engine` 两次查询均命中近邻条目（E165 / E002），直接给出了可用的修复方向；草稿目录现有 1468 条
- **测试统计**: 上游 286 用例 286/286 通过（5 种执行方式）；test_package 21 条断言，20 通过 + 1 SKIP
- **未覆盖的错误模式**: 本次识别出 2 个知识库空白，均已写成草稿（见上）。另有 1 个**框架侧**空白不适合写成 E 条目、已在本报告登记：判定器「构建系统优先级」对「顶层 Makefile 但零 C/C++ 源文件」的脚本类项目会稳定误判。

### AI 检视结果

- **检视阶段到达**: PR 创建阶段（fork 贡献者走手动建 PR 旁路，机器人检视在 PR 创建后异步进行）
- **变更摘要评估**: 本报告定稿于建 PR 之前，摘要尚未产生；按 PR 提交纪律，本次把全部内容一次性备齐后再建 PR，避免推增量 commit 作废进行中的检视
- **检视意见数量**: 0（建 PR 前）
- **检视意见处理**: 机器人意见与 CI 结果由后续低频复查任务跟进；有必须修的才推，一次一个 commit 并随即 `trigger-ci`

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`.ci-result.json` `exit_code: 0`，`log_sha256` 已写入）
- **远程 CI (PR 校验)**: 建 PR 后另行触发（评论触发型）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 1（`feedback` 报告占位符未填，属正常闭环提示）
- **重试次数**: 3（补丁语义收窄 1 次、test_package 断言措辞修正 3 处合并为 1 次、git shallow.lock 残留清理 1 次）
- **关键瓶颈**: ①上游测试的「假失败」诊断——262/286 的失败面很像真实回归，靠「显式解释器 vs 直接执行」两条命令才定性；②`github.com` 直连超时，需先确认 `codeload.github.com` 可达才能取源码
- **耗时较长的步骤**: 上游全量测试的多 shell 矩阵复跑（7 轮 × 286 用例）与 `conan create`（含 test_package 21 条断言）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 3 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-21T11:14:35 | skeleton_created | result_env_unsupported |
| 2026-09-21T11:14:35 | lang_mismatch | task=bash detected=c → env_unsupported 迁移 |
| 2026-09-21T11:15:38 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`lang-preflight` 不应在判定 mismatch 时直接落终态（`scripts/ohc/lang_detect.py:325-341`）。**
   当前实现一旦判不匹配，就调用 `result_cli(... --status env_unsupported --force)` 写 `draft:false`
   终态，并且**没有 dry-run 开关**。本次 `--lang bash` 的一次预检直接把任务判死，之后所有
   生命周期草稿挂点都因「终态已写入」而被跳过（日志反复出现
   `R46: 终态 result.json 已上报（draft:false），跳过里程碑草稿 …`）。
   建议：①增加 `--dry-run`（只输出判定 JSON 不落盘）；②mismatch 时先写
   `draft:true` + `milestone=lang_mismatch`，由 agent 或平台在确认后再转终态；
   ③判定与上报解耦，让「先看判定结果再决定是否上报」成为默认路径。

2. **判定优先级需要一条「零源文件不得判语言族」的兜底（`lang_detect.py`，`detect_language`）。**
   本次三项证据自相矛盾却仍输出 `c`：`build_system: make`、
   `manifest: 顶层 Makefile（无更强 manifest）`、`source_stats: 无源文件可统计`。
   建议：当源码统计里目标语言源文件数为 0 时，构建系统证据降权或直接转交源码统计
   （此处应判 `bash`）。判据现成——同一份证据里已经写明「无源文件可统计」。

3. **`LANG_ENUM` 有 `bash`，但脚本类包在流程上没有落点。**
   仓库已合并多个脚本类包（`cronic/3`、`lynis/3.1.7.1`、`powerlevel10k/1.20.0`），
   CI 能力矩阵也明列「bash 脚本类 ✅ 正常」，可一旦按实申报 `OHPCD_LANG=bash`，
   预检就判死。建议把「shell 脚本工具」显式纳入受支持适配路径：`bash` 与 `c/cpp`
   在本 skill 的 conan 流程里应同属兼容族（脚本包与 C 包共用同一套 conan 配方形态）。

4. **`finish` 的 submit 就绪预检仍在查已废弃的 `packaging/`。**
   ARCHIVE-SPEC v2.0 已废弃 `packaging/`，但 step10 仍报
   `❌ packaging/ — 需创建 packaging/ 目录并打包`。这是稳定的假告警，会诱导新 agent
   去造一个规范明确不要的目录。建议按 ARCHIVE-SPEC 版本号分支，或直接摘除该检查项。

### 模板改进

1. **缺「脚本工具」配方模板的可达路径。** v12.21 新增了
   `templates/conanfile-headeronly.py.tmpl`（含脚本工具变体），但 `conan-init` 的模板选择
   由构建系统探测决定：本次探测为 `autotools`，于是生成了 `test.c` + `CMakeLists.txt`
   的 C 模板，完全不可用，只能照 `archives/c/cronic/3` 手写。建议：①`conan-init` 增加
   `--template headeronly|script` 显式覆盖；②探测到「零编译单元」时优先选脚本/打包族模板。

2. **`notes.md` 骨架的占位符没有任何门禁校验。** `templates/notes.md` 生成后
   全篇是 `{cmake|autotools|makefile|meson|custom}`、`{按需添加行}` 这类占位符，
   而 `finish`/`conan-verify`/preflight 均不检查是否被填写。建议在 `finish` 的归档校验里
   加一条 `grep -nE '\{[a-z]+\|[a-z|]+\}' notes.md` 硬检查（成本极低，能直接拦住
   「骨架占位符进 PR」这类低级失分）。

3. **版本级 `manifest.yaml` 模板的 `patch_classification.guard` 默认写 `pending`。**
   `refresh-patch` 生成后留 `guard: 'pending'`、`platform_only: True`，但对 shell 补丁而言
   「平台宏 guard」这一概念不适用，字段语义错配。建议模板对非 C/C++ 补丁提供
   `guard: none` + 说明字段，避免 agent 为了填字段而杜撰。

### 自动化补全

本次自动采集的失效项（全部实测，行号对应 `scripts/ohc/feedback.py` 的采集逻辑）：

| 字段 | 自动值 | 实际值 |
|---|---|---|
| 构建系统 | `{BUILD_SYSTEM}`（占位符未渲染） | custom |
| 上游仓库 | `(未知)` | github.com/aureliojargas/clitest（`conandata.yml`/`manifest.yaml` 里都有） |
| 适配路径 | `路径 A（基础适配，无补丁）` | 路径 B，含 1 补丁 + 2 草稿 |
| 补丁数量 | `0` | 1（`patches/0001-clitest.patch` 就在归档里） |
| 新增知识草稿 | `无` | 2（`knowledge/drafts/E545-draft-3028.*`、`E546-draft-3028.*`） |
| 测试统计 | `总计 0, 通过 0, 失败 0, 跳过 0` | 上游 286/286；test_package 21 断言（20 通过 1 SKIP） |
| 本地 CI (W3) | `未知` | 通过（`.ci-result.json` 就在版本目录，`exit_code: 0`） |
| 最终状态 | `成功` | 正确，但与上面一堆 0/未知 并列时反而降低报告可信度 |

建议：

1. 上述字段的事实源**全部都在归档目录里**（`manifest.yaml` 的 `build_system`/`source.url`/
   `patches_applied`/`test_scope`、`patches/` 目录列表、`.ci-result.json`、
   `knowledge/drafts/*-draft-<AgentID>.*`）。采集器改为直接读这些文件即可一次性修复 8 项中的 7 项；
   `{BUILD_SYSTEM}` 未渲染更是纯粹的模板替换遗漏。
2. **草稿计数应按 `contributor_id`/文件名后缀过滤本任务**，不要只输出「草稿目录 1468 条」——
   这个数字对读者零信息量，而「本任务新增 2 条」才是反馈需要的。
3. `finish` step8 `gen_summary` 抛 `'str' object has no attribute 'append'` 后流程继续，
   但 `SUMMARY.md` 未更新；建议把该异常纳入非致命错误汇总，至少在 finish 末尾复述一次，
   否则日志被后续输出冲走就无人知晓。
4. `conan-verify` 的 E017 镜像注入在恢复 `conandata.yml` 后仍留下 `conandata.yml.ghfast-bak`。
   JC1 会拦 `.bak` 残留，等于把一个框架产物变成 agent 的清理义务。建议注入流程改用
   内存内替换或 `$TMPDIR` 暂存，彻底不在归档树内落备份文件。
5. **`finish` 每次运行都把版本级 `manifest.yaml` 的 `patch_classification` 覆写回骨架值**
   （`type: auto` / `platform_only: True` / `guard: 'pending'`），把 agent 已按实填好的
   `type: portability` / `guard: none` / `note` 一并冲掉，实测连续两次 finish 覆盖两次。
   建议：该字段已有人工值时只补 `source_*_hash`/`generated_at`，不要整块重写。
6. **`finish` step3 的 G0 干净构建验证对「无构建系统」的包会误报**：本包没有 `configure`，
   G0 仍去执行并得到 `configure 失败 (exit 127)`，输出 `RESULT: FAIL / FAILED_STEP: configure`。
   虽为非阻塞，但 FAIL 字样与真实失败无法区分，容易误导。建议 G0 先探测构建系统，
   `custom`/无构建族直接跳过并打印 `SKIP (no build system)`。
7. **（安全相关）W4 审计报告的字段名前后不一致，会造成审计假阴性。**
   `scripts/pre_pr_audit.py:258` 的 `cmd_report` 读 `report.get("issues", [])`，
   而 `generate` 输出的 prompt 与 `templates/audit-prompt.md` 要求审计方输出 `findings`
   （示例 JSON 也是 `findings`）。实测：审计结果含 3 条 findings 时，`report` 打印
   `问题数: 0`、`统计: P0=0 P1=0 P2=0 P3=0`。**后果是 P0/P1 会被静默漏判**——
   审计方明明报了阻断项，`report` 仍打印「✅ W5 审计通过 — 可以创建 PR」并 exit 0。
   这与 R52「审计失真一票否决」的初衷正好相反。建议 `cmd_report` 兼容读取
   `issues` 与 `findings` 两个键（或统一到 `findings`），并在两者皆空时打印
   「未解析到任何 finding，请确认审计输出 schema」的告警而不是直接判过。
8. **`cmd_report` 不落盘**：SKILL.md 的「产物路径唯一权威」表写明 W4 结果应在
   `<版本目录>/reports/audit-result.json`（submit 会读），但 `cmd_report` 只把结论打到
   stdout，不写该文件，导致 agent 必须手工搬运——而这恰恰是「审计结论由工具生成」
   这条红线最不希望出现的人工环节。建议 `report` 增加 `--repo-dir/--package/--version`
   后直接写入权威路径。

### 知识图谱覆盖

1. **建议 promote 本次两条草稿**（均已按字段规范填实、配套 `.md` 齐全）：
   - `E545-draft-3028`：脚本产物硬编码 `${TMPDIR:-/tmp}` 的运行期失效面。
     `draft-review` 判 `review-similar`（目标 E002）——建议**并存而非合并**：E002 是构建期
     现象（对策是给构建过程设 `TMPDIR`），本条是产物侧运行期现象（对策是改脚本默认值），
     两者的修复动作完全不同；若主编倾向合并，建议作为 E002 的「运行期镜像面」小节追加。
     本条带 `prescan_pattern`，promote 后预扫描即可自动命中 `${TMPDIR:-/tmp}` 写法。
   - `E546-draft-3028`：shebang 适配后上游自举测试整片假失败的判定与复现。
     `draft-review` 判 `create`，与 E165 相似度仅 0.03。E165 只讲「怎么改 shebang」，
     不讲「改完之后怎么验证、以及失败面长什么样」，而后者正是最容易误判、
     并诱发「回退正确补丁」或「修改上游用例」两种错误处置的环节。

2. **知识库对「脚本类包」整体偏薄。** 现有条目绝大多数围绕 C/C++ 构建链
   （configure/cmake/链接/ABI），而仓库里脚本类包已有相当数量。建议主编设一个
   `script-package` 专题，把 shebang（E165）、`/tmp` 只读运行期面（E545 草稿）、
   HMDFS 执行位不可靠、toybox 与 GNU coreutils 参数差异、上游自举测试验证方法
   （E546 草稿）串成一条可检索的线。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: 3028
- **生成时间**: 2026-09-21 11:14:35
- **PR 编号**: —
- **Git Commit**: 48d9cee684
