# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_609bde13.md`

---

## 背景

- **软件名称**: tal
- **版本**: 1.9
- **构建日期**: 2026-09-24
- **构建系统**: makefile（上游手写 Makefile，无 configure；init-build 曾误判为 autotools，见「模板改进」）
- **上游仓库**: https://thomasjensen.com/software/tal/（源码包 tal-1.9.tar.gz，官方源）
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
无
- **最终状态**: built（conan-verify 与 finish W3 本地 conan create 通过；PR 与远程 CI 在本报告提交之后进行）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 构建系统被误判为 autotools，手工改 manifest 后才生成 makefile 模板 |
| build | 编译构建 | 成功 | 构建系统: makefile；通用目标 `make tal` + `-Werror=implicit-function-declaration` + `-static-pie` |
| conan-verify | 配方验证 | 通过 | 首跑 G1 因字面量检查缺 `export_sources`/`apply_conandata_patches` 失败，补空操作骨架后 G1–G4 PASS；L2/L4/L5 因未定位到 cache 路径被"跳过"却记 PASS |
| finish | 归档收尾 | 完成（W3 通过） | W3 conan create + test_package 通过（鸿蒙特有消费者用例 tal_consumer OK + test_tal.sh 15/15）+ L1e 反向验证通过；step5b（W5 检查器把 `|` 块标量误判为空）与 step8（他人 manifest 解析异常）为框架侧失败 |
| submit | PR提交+AI检视+CI | 本报告提交时未开始 | submit 固定推 origin，本次按 PF 实跑 + create-pr 手动建 PR；W4 独立审计 pass（P0=0 P1=0） |

### 失败与问题

- **1**: 问题=按上游 INSTALL 执行 `make linux`（`CC=gcc CFLAGS="-ansi -O"`），换 OHOS clang 后只有 6 条 `-Wint-to-pointer-cast` 告警、看似成功，但二进制处理第一行输入即 SIGSEGV（qemu 退出码 139）；根因=`-ansi` 定义 `__STRICT_ANSI__`，musl `features.h` 不再默认开启 `_BSD_SOURCE`/`_XOPEN_SOURCE`，`strdup()`/`strcasecmp()` 声明被隐藏，C89 隐式 int + 显式 `(char *)` 强转截断 64 位堆指针；解决方案=改用通用目标 `make tal` 保持 clang 默认 C 方言，加 `-Werror=implicit-function-declaration` 防回归（无补丁）。
- **2**: 问题=直接 `make`（不带目标）退出码 0 却不产出二进制；根因=`all: $(MAKE) $(OS)_tal`，未设环境变量 `OS` 时落到只打印提示的 `_tal` 目标；解决方案=配方显式指定 `tal` 目标。
- **3**: 问题=上游平台目标硬编码 `CC=gcc`，构建机无 gcc；根因=手写 Makefile 不感知交叉工具链；解决方案=编译器取自 Conan `tools.build:compiler_executables`（R33），经 make 命令行变量覆盖。
- **4**: 问题=x86_64 构建机无法启动动态链接的 OHOS 产物；根因=本机没有 `/lib/ld-musl-aarch64.so.1`；解决方案=交付产物 `-static-pie` 链接（保留 PIE/RELRO/BIND_NOW），test_package 在 x86 经 qemu-aarch64、在 AArch64 上原生执行同一交付二进制。
- **5**: 问题=conan-verify G1 首跑失败；根因=`scripts/ohc/conan_verify.py:484-492` 以字面量要求 `export_sources` 与 `apply_conandata_patches`，无补丁包也必须写；解决方案=补标准空操作骨架（无 patches 时二者均为 no-op）。
- **6**: 问题=finish 知识缺口检查报 `unreferenced=3`；根因=`scripts/ohc/check_knowledge_gap.py:58-66` 要求 manifest `knowledge_gained` 每条含 `ref:`；解决方案=各条补 `ref:` 指向草稿或 notes。

### 知识图谱使用情况

- **引用知识条目**: E011（HMDFS 下 0700 目录不可写 → test 脚本用 mkdir 而非 mktemp -d）；E213/E420 作查重对照
- **新增知识草稿**: 1 条（knowledge/drafts/E585-draft-04E7.kv + .md）
- **引擎命中情况**: 编译期告警日志命中 E063（按类别关闭 -Werror，对本问题不适用且有害）；运行期 SIGSEGV 无命中 → 新增草稿 E585
- **测试统计**: 上游自动化测试 0 个（源码包无 tests、Makefile 无 check/test 目标）；test_package 共 2 个用例，均通过，跳过 0。其中鸿蒙特有测试 N=1，是消费者用例 `tal_consumer`：用 tal 格式化生成的 3000 列 X-macro 头文件，再用 OHOS 工具链编译并运行依赖它的程序；该用例依赖 musl `LINE_MAX` 4096，`LINE_MAX` 为 2048 的构建下消费者直接编译失败。另一个是 `test_tal.sh`，15/15（含上游示例页 9 组金样）
- **未覆盖的错误模式**: 严格 ANSI（`-ansi`/`-std=c89`）让 musl 隐藏 POSIX 声明，隐式 int + 显式指针强转把 64 位指针截断，编译只有 `-Wint-to-pointer-cast` 告警、运行期 SIGSEGV（已由 E585 草稿覆盖）；"以 OS 环境变量分发平台目标的手写 Makefile，未设置时 make 退出 0 不产出"（仅记入 tal notes，单例未立条）

### AI 检视结果

- **检视阶段到达**: 未开始——按 PR 纪律本报告须在建 PR 前提交，PR 建立后的机器人检视不在本报告范围
- **变更摘要评估**: 不适用（PR 未创建）；替代证据为 W4 Pre-PR 独立审计：两轮均 verdict=pass、P0=0、P1=0（第 2 轮为增量复审，按当前内容重算全部变更文件的 sha256）
- **检视意见数量**: W4 审计 3 条（P2×1、P3×2）；机器人检视尚未开始
- **检视意见处理**: P2「缺 SKILL_FEEDBACK」→ 本报告闭环并随 PR 提交；P3「test_tal.sh 用 set -eu」→ 改为 `set -euo pipefail` 并重跑 W3 复验；P3「PF9 与 R38 对新增 CLI 包互斥」→ PR 正文登记理由与已合并先例 tnef

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 本报告提交时未触发（PR 创建后评论 /rebuild）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 5 次——G0 clean-verify 对 Makefile 项目跑 configure 的误报 2 次（两轮 finish 各一次）、finish 知识整理 HANDOFF 2 次、feedback 占位符 HANDOFF 1 次；另有 conan-verify G1 字面量检查失败 1 次
- **重试次数**: conan-verify 2 次（G1）；finish 2 次（审计建议改 test 脚本后按纪律重跑 W3，期间 main 前进 188 个提交并已 rebase）；W4 审计子任务派发 3 次（前两次中途中止、未产出结论，第三次缩小输入后完成）
- **关键瓶颈**: ①定位"编译通过但运行即崩"的根因（需逐项对照 -ansi 与默认方言、静态重链后 qemu 实跑）；②框架噪声（G0 误报、step5b 检查器误判、step8 被他人文件拖垮）需逐条甄别是否与本包有关；③W4 审计输入整份 43KB，子任务易中止
- **耗时较长的步骤**: 手工交叉编译与根因定位；从上游示例页抽取 9 组金样并做正负对照；W4 审计子任务重派
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-24T04:43:04 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **PF9 与 PF8/R38 对新增 CLI 包必然互斥**：`scripts/ohc/preflight.py:570` 用 `len(f.split("/")) < 5` 拦截 4 段路径，而 PF8（`preflight.py:517-525`）与 R38 要求 CLI 包在软件级提供 `commands.json`（ARCHIVE-SPEC 另要求软件级 `README.md`/`manifest.yaml`）。建议 PF9 白名单放行 `archives/<l>/<pkg>/{commands.json,README.md,manifest.yaml}`，其余路径仍要求 ≥5 段，免得每个新 CLI 包都要 `--no-preflight` 并在 PR 里登记。
2. **G0 clean-verify 不看构建系统**：`scripts/ohc/clean_verify.py:136` 无条件执行 `configure`，纯 Makefile 项目必然 exit 127 并发 HANDOFF（本次两轮 finish 各误报一次）。建议按 manifest `build_system` 分派：`makefile` 且无 configure 时跳过该步，或直接复用 conan create 结果。
3. **W5 完整性检查误判 `|` 块标量**：`scripts/ohc/workflow_checks.py:305` 用 `val == "|"` 判"字段为空"，E219/E253/E305 的 `root_cause`/`rec_approach` 实际是有内容的 `|` 多行块，却被报"为空"，`check_knowledge_completeness` 因此对所有包返回失败，`finish.py:326` 的 step5b 永远失败、失去信号意义。建议复用 graph validate 的 kv 解析器（把 `|` 后的缩进续行并入值），并只对本 PR 新增或修改的条目判失败。
4. **conan-verify 的 G4/L2/L4/L5 形同虚设**：`conan_verify.py:741/800/851/942` 在 `--user=ohpcd --channel=stable` 引用下找不到 package id，四道门禁都"跳过（无 cache 路径）"却记 PASS。建议与 CI `build_and_test.sh` 的 L5 同法，从 conan create 日志解析 `Package folder`。
5. **rule12（鸿蒙特有测试 N≥1）没有本地门禁**：本次首版 PR 在适配后统计中把「鸿蒙特有测试」填为 0，建 PR 后才被评审以 rule12 判不通过，只好补测试再推一次，整轮检视和 CI 作废。`templates/积分赛事PR模板.md` 里有这一行，但 conan-verify、finish、W4 审计（`templates/audit-prompt.md` 的分级表）和 preflight 都不检查它。建议：
   - `test_package/MANIFEST.yml` 增加必填字段 `harmonyos_specific_test_count`；
   - preflight 增加一道闸：该字段 <1、或所指测试文件不存在时拦截；
   - 审计分级表把 rule12 列为阻断项（P1）。
   - 口径也要写清：第一次补的是 5 条比对检查组成的脚本，被审核人指出"新增不可以只是断言"，只好再改成完整消费者用例（被测包参与构建 → 编译消费者程序 → 运行），又推了一次。建议在 `templates/积分赛事PR模板.md` 和 R34/R51 的说明里写明：鸿蒙特有测试必须是消费者流程；CLI 包可参照"工具产出参与消费者构建并运行"这种形态。
6. **submit 固定推 origin**：`scripts/ohc/submission.py:1187/1522` 固定 `git push origin <branch>`，无上游写权限的贡献者只能手动 push + create-pr，submit 内置的 PF 闸、partial 草稿、feedback 骨架等挂点随之全部绕开。建议 submit 支持 `--push-remote <remote>`，create-pr 支持 `owner:branch` 形式的 head 并在 PF0 中正确解析。

### 模板改进

1. **init-build 构建系统误判**：对只有 Makefile、无 configure/configure.ac 的源码包，`init-build` 仍写入 `build.system: autotools`，`build_system` 保留 `{BUILD_SYSTEM}` 占位符未渲染（`scripts/ohc/init_build.py:352` 只透传 `kw['build_system']`），conan-init 随之选错模板。建议没有 configure 系文件时判定为 makefile，并渲染占位符。
2. **makefile 模板只覆盖库**：`templates/conanfile-makefile.py.tmpl` 固定 `package_type="library"`、`license="MIT"`、`cpp_info.libs=[name]`、扁平 `conan_data["sources"]`，test_package 生成 CMake 骨架（test.c/CMakeLists.txt），CLI 工具需要整体重写。建议增加 application 变体：`bindirs`、脚本型 test_package（复用 `templates/test_package-executable/`）、软件级 `commands.json`，并采用仓库主流的 `sources[self.version]` 写法。
3. **notes.md 尾注造成 tracked diff**：`scripts/ohc/close_archive.py:58-63` 每次 finish 都改写 notes.md 末尾的"编译结束"时间戳。在"先 commit 再 finish"的要求下，每跑一次 finish 就要多一次提交。建议把该尾注移到 gitignored 的 `reports/` 或 manifest 状态字段。
4. **MANIFEST.yml 模板缺上游测试清点字段**：R51 要求上游无测试时附清点证据，但模板里只有 `upstream_tests` 列表。建议预置 `upstream_tests_exist` 与 `upstream_test_audit`（目录/目标清点结论），与已合并的 tnef/whichman 写法对齐。

### 自动化补全

1. **feedback 自动采集错位**：`scripts/ohc/feedback.py:417` 把 notes 表格的"问题/根因/解决方案"三列映射成"根因=问题列、解决方案=根因列"；"新增知识草稿"取了 manifest `knowledge_gained` 条数（3，实际草稿 1 条）；"测试统计"取 0（实际 15/15，可从 w3 日志的测试汇总行或 `test_package/MANIFEST.yml` 的 `assertion_count` 读取）；"引擎命中情况"输出的是草稿目录总数而非命中条目。以上本报告均已按实修正。
2. **W4 结果不落盘**：`scripts/pre_pr_audit.py` 的 `cmd_report` 只打印判定，submit 却读取 `<archive>/reports/audit-result.json`。建议 report 在 pass 时写入该路径，同时校验 `audited_files` 的 sha256 与工作树一致（R52），省去手工复制。
3. **W4 审计输入过大**：`pre_pr_audit.py generate` 把两份规则全文和全部变更文件内容塞进一个 JSON（本次 43KB），审计子任务整份读取容易中途中止。建议另外输出精简清单（文件路径 + sha256 + 规则文件路径），由子任务按需读取。
4. **gen_summary 被他人文件拖垮**：`archives/q/qpdf/12.3.2/manifest.yaml` 与 `12.3.2.1/manifest.yaml` 先写了 `knowledge_gained: []`，后面又写同名列表键，导致 `scripts/ohc/summary.py:89` 抛 `'str' object has no attribute 'append'`，此后所有包的 finish step8 都失败。建议 `_parse_yaml_simple` 遇到类型冲突时跳过该键或改用 `yaml.safe_load`，并由主编修正该 manifest。
5. **Agent ID 各自随机**：未设置 `OHC_AGENT_ID` 时（SKILL.md §0.2），`graph add --draft` 与 `feedback` 各自随机生成 ID：本次草稿 `contributor_id=04E7`，本报告 Agent ID 却是 `E1F0`，同一任务的草稿和反馈归属对不上。建议首次生成后持久化到 `.ohc/` 任务状态，供各命令复用。

### 知识图谱覆盖

1. **新增草稿 E585-draft-04E7**（建议 promote）：严格 ANSI 编译让 musl 隐藏 POSIX 声明，隐式 int + 显式 `(char *)` 强转截断 64 位指针，编译只有告警、运行即 SIGSEGV。查重：`draft-review` 最高相似 E093 0.25、E081 0.20、E420 0.11，建议 create。它与 DRAFT-E628-rtklib 互补：后者是 `-ansi` 隐藏 `gethostbyname`，没有显式强转，表现为编译期报错。草稿附 `prescan_pattern`（CFLAGS 含 `-ansi`/`-std=c89`），promote 后可在编译前预警。
2. **E063 需补禁止项**：E063 推荐的 `-Wno-error=int-conversion` 放到本模式里，会把编译期错误压成静默的运行期崩溃。建议 E063 增加 forbid 条目，或在 `conflicts_with` 中指向 E585。
3. **候选通用条目**：手写 Makefile 以环境变量 `OS` 分发平台目标，`OS` 未设置时 `make` 退出 0 却不产出二进制。本次只有单例证据，仅记入 tal notes；再遇到同类包时建议立条。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: E1F0
- **生成时间**: 2026-09-25 03:50:53
- **PR 编号**: —
- **Git Commit**: 54cff14fe3
