# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_3580f351.md`

---

## 背景

- **软件名称**: mrename
- **版本**: 1.2
- **构建日期**: 2026-09-21
- **构建系统**: none（纯 POSIX shell 脚本，无任何构建系统）
- **上游仓库**: https://salsa.debian.org/debian/mrename （取 `upstream/1.2` tag 的源码归档）
- **适配路径**: 无构建 / 打包族——解释型脚本工具（v12.21 模板变体 C）
- **补丁数量**: 2（均为可移植性修复，无平台宏）
- **编译依赖**: 无（`requires` / `tool_requires` 均为空，W0 无待查条目）
- **最终状态**: 成功（本地 conan create + W3 + test_package 14/14 通过）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | salsa `upstream/1.2` tag，两次独立下载 sha256 一致 |
| lang-preflight | 语言预检 | 判定 `other` | 无扩展名脚本，统计器取不到可计数源文件；按脚本工具族继续（见建议节） |
| build | 编译构建 | 不适用 | 解释型脚本，无编译阶段 |
| conan-verify | 配方验证 | 通过 | G1/G2/G3/G4 + L2/L4/L5 全 PASS |
| finish | 归档收尾 | 完成（2 步告警） | W2 结构 + R36 依赖 + W3 本地 CI 全过；step5b/step8 告警见下 |
| submit | PR提交+AI检视+CI | PR #11843；CI 首轮红 → 修复 1 轮 | AI 代码审查「未发现问题」；CI 构建 #57971 test_package 2 条断言失败（问题 6），修复后重新触发 |

### 失败与问题

> 说明：自动采集节把 `notes.md` 问题表的「根因」与「解决方案」两列写反且漏掉首行，
> 以下按实重写（原始采集输出的失真形态已记入「自动化补全」节）。

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 严格 POSIX shell 下报 `[: ==: unexpected operator`，copy/move/help 全部失效 | shebang 声明 `#!/bin/sh`，实现却用 bash 专有的 `test ==` | 补丁改为 POSIX `=` 并给变量加引号 |
| 2 | 编号恒为空，重命名结果串错 | `$[ ]` 是 bash 早期废弃算术语法，POSIX 未定义 | 改为 `$((number + 1))` |
| 3 | 确认提示串前多出 `-n` | `echo -n` 非 POSIX 行为 | 改为 `printf '%s'` |
| 4 | 含空格的文件名被拆成多个参数 | `find -exec` 与 `cp`/`mv` 的参数未加引号 | 参数加引号 + `--` 终止选项解析 |
| 5 | 安装到非 `/usr/bin` 前缀后辅助脚本找不到，功能静默中断 | 上游用 `find -exec mcpmv`，execvp 按 PATH 查找，而上游假定两个脚本都在 PATH | 配方生成可重定位 wrapper 注入 `libexec` 到 PATH（不改上游逻辑） |
| 6 | OHOS CI 上同一文件被改名两次（`pre2pre1c.log`），构建 #57971 两条断言失败 | 在 `find` 仍在读取的目录里 `-exec` 改名；OHOS 的 toybox find 边读边处理，新名字被再次匹配（GNU find 先读完整个目录，本地不暴露） | 先快照 `find` 结果再逐个处理；测试补"每个文件恰好处理一次"与 200 文件批量断言 |

最隐蔽的一点是**静默失效**：`[` 报错的退出码非 0，脚本顺着 `else` 分支跑完并以 0 退出，
只看退出码的冒烟测试会判「通过」。因此本次测试用断言校验文件系统实际结果，而非退出码。

### 知识图谱使用情况

- **引用知识条目**: 无直接可用条目（`engine` 首位命中 E165，但那是 shebang **路径**问题，处方不适用，见建议节）
- **新增知识草稿**: 2 条（`E543-draft-EE19`：bash 方言；`E543-draft-036F`：toybox find 遍历中改名被重复匹配；均含配套 `.md`）
- **查重证据**: `draft-review E543-draft-EE19 --json` → `verdict=create`，
  最相近条目 E043 的 `signature_overlap=0.0`、`keyword_jaccard=0.17`；
  `draft-review E543-draft-036F --json` → `verdict=create`，最相近 E454 得分 0.03，signature/keyword 重叠均为 0
- **测试统计**: 18 条断言；本地 18/18 通过。OHOS CI runner 没有 dash，dash 轮次如实输出 skip、不计入通过数
  （此前写的「没有任何跳过项」只对本地 runner 成立，已在 notes.md 更正）
- **未覆盖的错误模式**: ①「shebang 路径正确但语法是 bash 方言」——本次已沉淀为草稿；
  ②`gen_summary` 因他人归档的 YAML 重复键崩溃——属框架解析缺陷而非编译错误模式，
  不适合做 E 条目，已在建议节登记

### AI 检视结果

- **检视阶段到达**: 本报告在建 PR 之前完成并 commit，检视阶段尚未开始
- **变更摘要评估**: 待 PR 创建后由机器人产出
- **检视意见数量**: 0（尚未开始）
- **检视意见处理**: PR 建立后逐条判断，合理的修复、不合理的回复理由

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`.ci-result.json`: `exit_code=0`，含日志 SHA256）；修复后复验通过
- **远程 CI (PR 校验)**: 首轮构建 #57971 失败（`passed=11 failed=2`）→ 修复后重新触发
- **CI 失败原因**: test_package 断言失败（问题 6）。CI 侧分类为「未知」，`diagnose` 本地二次归类为「网络问题」——属误判，见「自动化补全」第 6 条

### 效率分析

- **HANDOFF 次数**: 0（conan-verify 与 finish 均一次通过）
- **重试次数**: 1（refresh-patch 重跑一次——首轮全文替换顺带改到注释行，
  还原注释后重生成，使补丁只含 7 行功能改动）
- **关键瓶颈**: ①语言预检判定与仓库既定实践冲突，需要人工确认口径才能继续；
  ②`gen_summary` 崩在他人归档数据上，排查耗时但与本包无关
- **耗时较长的步骤**: `conan create`（conan-verify 的 G2 与 finish 的 W3 各跑一次完整构建 + test_package 实跑）
- **CI 修复轮次**: 1/2。定位耗时主要在复现：x86 runner 默认 GNU find 不暴露问题，
  需换用 toybox find 并把目录放大到上百个文件才能在本地 ext4 上稳定复现

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-21T09:59:39 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **R47 语言预检与「无构建/打包族」自相矛盾，且失败方式是不可逆的终态写入。**
   `scripts/ohc/lang_detect.py::_source_stats` 只按扩展名计数（`_EXT_LANG` 映射），
   本包两个脚本没有扩展名 → `total=0` → `detect_language` 落到
   `detected = "other"`（`notes: 无可统计源文件`）→ `lang_preflight_cli` 判不兼容，
   **直接调 `result_cli(... --status env_unsupported --force)` 写终态并退出**。
   但 SKILL v12.21 明确为该族类提供了 `templates/conanfile-headeronly.py.tmpl` 变体 C
   （解释型脚本工具打包），仓库里 `package_type="application"` + 空 `build()` 的
   已合并包有 38 个（如 `archives/a/acme.sh/3.1.3` 纯 shell CLI）。
   建议：`detected == "other"` 且 `build_system == "none"` 且源码中存在带 shebang 的
   可执行脚本时，判为脚本工具族并放行；至少不要在这种情形下直接写终态——
   改为告警 + 要求 notes 登记，把终态权交回主流程。否则同类任务会被
   「上游只有脚本、没有 .sh 后缀」这种纯形式的原因判死。

2. **`finish` 会覆盖人工填写的补丁分类。**
   step[1/10] 的 `refresh-patch --auto` 无条件重写版本级 `manifest.yaml` 的
   `patch_classification`，本次把人工填好的
   `type: portability / platform_only: false / guard: none`
   覆盖回 `type: auto / platform_only: True / guard: 'pending'`
   （`platform_only: True` 与事实不符——两个补丁都不含平台宏）。
   而工具自己在日志里又提示「补丁分类标注已写入 manifest.yaml（请 AI 补充 type/guard）」，
   形成「让你填 → 再帮你改回去」的循环。
   建议：仅当字段缺失或 `guard == 'pending'` 时写入，已人工分类的条目保持不动。

### 模板改进

1. **`templates/notes.md` 的占位符没有任何门禁校验。**
   骨架里 `{cmake|autotools|makefile|meson|custom}`、`{published|built|failed}`
   等占位符如果没填，`finish`（含 step[10/10] submit 就绪预检）与 preflight 全都不报。
   建议在 submit 就绪预检里加一条硬检查：
   `grep -nE '\{[a-z]+\|[a-z|]+\}' notes.md` 有输出即判未就绪——
   这是零成本拦截，却能挡住相当一部分「骨架直接进 PR」的低质量归档。

2. **缺少脚本工具族的 test_package 样板。**
   `templates/test_package` 与 `templates/test_package-executable` 都是给编译型包的，
   而 v12.21 已承认「无构建族」占 26%。这类包需要的样板是：
   用 `sh` 执行随包测试脚本 + `MANIFEST.yml` 里如实申报「上游零测试 + 清点证据」。
   本次的 `archives/m/mrename/1.2/test_package/`（含 `assertion_count` 与
   `upstream_test_inventory` 字段）可直接作为底稿。

3. **`templates/manifest-version.yaml` 的构建系统枚举缺 `none`。**
   注释写的是 `cmake | autotools | makefile | meson | custom`，
   但既有包（acme.sh 等）与本包实际使用 `none`，软件级模板里也确有 `none`。
   建议版本级模板注释补上，避免适配者在两个枚举间来回猜。

### 自动化补全

1. **「失败与问题」采集把 notes 表格列写反且漏首行。**
   本次原始输出形如
   `- 2: 根因=$[$number+1] 在非 bash shell 下不展开…, 解决方案=$[ ] 是 bash 早期废弃语法…`
   ——后半句才是根因，两列互换了；且从第 2 行起，表格第 1 行被吞掉。
   建议 `scripts/ohc/feedback.py` 解析 notes 问题表时按**表头列名**定位
   （`问题`/`根因`/`解决方案`），而不是按固定列序，并从表头之后第一行开始取。

2. **测试统计恒为 0。**
   采集器输出 `总计 0, 通过 0, 失败 0, 跳过 0`，而实际是 14/14 全通过。
   原因是它只认 ctest/pytest 风格输出，不认 `test_package` 自定义断言。
   建议：优先读 `test_package/MANIFEST.yml` 的 `assertion_count`，
   并兼容 `passed=N failed=M` 这类结尾行。

3. **W3 状态没读现成的结果文件。**
   报告里 `本地 CI 模拟 (W3): 未知`，而同一归档目录下
   `.ci-result.json` 明明写着 `exit_code: 0` 与 `log_sha256`。
   建议直接读该文件填充，避免「工具自己写的证据自己不认」。

4. **草稿计数口径不准。**
   报告写「新增知识草稿: 3 条」，实际本次只新增 1 条（`.kv` + `.md` 为一对）。
   建议按 `.kv` 去重计数，且只统计本次任务新增（可用 git 暂存区/未跟踪状态判定）。

5. **`gen_summary` 会被单个坏数据整体打挂（建议加容错）。**
   `scripts/ohc/summary.py:89` 的
   `data.setdefault(current_list_key, []).append(item)`
   假设同名 key 只出现一次；一旦某个 manifest 里同一 key 先以 inline 形式
   （`knowledge_gained: []`）出现、后又以块列表形式出现，
   `data[key]` 已是字符串，`.append` 立刻抛
   `AttributeError: 'str' object has no attribute 'append'`。
   实测全仓 7467 份版本级 manifest 中有 2 份命中该形态，
   结果是**所有包的 `finish` step[8/10] 都生成不了 SUMMARY.md**（本次即是如此）。
   建议两处改动：①`_parse_yaml_simple` 在 `.append` 前判类型，非 list 则转成
   `[原值]` 再追加；②`_scan_archives_dir` 对单个 manifest 的解析异常做
   try/except 跳过并记告警，不要让一份坏数据决定全仓输出。

6. **`diagnose` 会把任何未命中其它规则的失败归成「网络问题」。**
   `scripts/gitcode_pr.py` 的 `_FAILURE_TABLE` 里网络规则是
   `timed out|timeout|Connection reset|...`，而**每一份** CI 日志的 buildbot 前导行都带
   `h in dir .../build (timeout 14400 secs) (maxTime 14400 secs)`。
   本次构建 #57971 实际是 test_package 断言失败（`Error in test() method` + 两行 `FAIL`），
   但测试类规则 `test\(\).*self\.run` 要求两者在同一行，实际日志里分在两行，没命中；
   `classify_failure_log` 于是只剩网络规则一票，输出
   「本地归类: 网络问题 / 修复要点: …再失败按 external_dependency 停损」，
   证据行正是那条 buildbot 前导行。按这个指引走，会把一个可修的测试失败当成外部阻塞去止损。
   建议：①网络规则跳过 buildbot 头部行（以 `h ` 开头、或含 `(timeout N secs)` / `maxTime`）；
   ②新增测试失败规则，如 `Error in test\(\) method|^\s*o?\s*FAIL\b|failed=[1-9]`，
   修复要点写「看 test() 输出的 FAIL 行，用目标平台同款工具（toybox 等）在本地复现」；
   ③证据行只有头部行时降级为「未知」，别给出止损建议。

7. **`finish` step[3/10] 的 G0 干净构建对无构建系统的包也跑 `configure`。**
   manifest 已声明 `build_system: none`，G0 仍执行 configure，得到
   `G0: configure 失败 (exit 127)` 并输出 G0 HANDOFF，finish 进程退出码因此为 1，
   而同一次运行的结论却是 `EXIT_REASON: finish_success`、W3 通过。
   退出码与结论不一致，脚本化调用方会误判失败。
   建议 G0 读到 `build_system: none` 时直接记 skip（该类包的干净构建由 G2 `conan create` 覆盖）。

### 知识图谱覆盖

1. **本次新增草稿 `E543-draft-EE19`**：脚本 shebang 声明 `#!/bin/sh` 却使用
   bash 方言（`test ==`、`$[ ]`、`echo -n`），在 OHOS 的严格 POSIX shell 下
   报 `[: ==: unexpected operator` 并**静默失效**（退出码仍为 0）。
   条目含 `prescan_pattern`，promote 后可直接派生预扫描规则，在选型阶段就发现。

2. **覆盖缺口**：现有 shell 相关条目 E037 / E043 / E049 / E143 / E165 全部围绕
   **shebang 路径**（解释器不存在）或 **bash 变量**（`${BASH_SOURCE}` 取空），
   没有一条覆盖**语法方言**这一类。而本仓待适配对象里有大量 Debian 下游维护的
   遗留脚本工具，这类包普遍在 bash 上开发、声明 `/bin/sh`，属高频模式。

3. **E165 的处方对本场景有误导性**：用本次错误串查询 `engine`，首位命中 E165，
   给出的推荐动作是把 shebang 改成 `/data/service/hnp/bin/bash` 或 `/system/bin/sh`。
   对本场景而言，前者会把一个零依赖脚本包变成依赖 bash、且把构建机软链路径写进
   交付产物；后者也没解决语法问题（`==` 在 `/system/bin/sh` 下照样报错）。
   建议在 E165 的 doc 里补一条互斥说明：**先判断是路径问题还是方言问题**，
   方言问题应走 POSIX 化而非改 shebang。

4. **CI 修复轮新增草稿 `E543-draft-036F`**：在 `find` 仍在读取的目录里用 `find -exec` 改名/复制，
   OHOS 的 toybox find 边读边处理，改名后的新名字被再次匹配（同一文件改名两次）；
   GNU find 先读完整个目录，所以桌面 Linux 上完全不暴露。知识库现有 toybox 条目
   （E010/E106/E188/E254）都是**选项/行为不兼容、直接报错**的类型，没有覆盖这类
   「不报错、退出码 0、结果错」的遍历语义差异。条目附带本地复现方法
   （x86 上换 toybox 静态二进制 + 上百文件目录）与测试写法建议，promote 后
   `prescan_pattern` 可在选型阶段提示 `find ... -exec mv/cp` 风险。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: 00F5
- **生成时间**: 2026-09-21 09:59:39
- **PR 编号**: —
- **Git Commit**: 48d9cee684
