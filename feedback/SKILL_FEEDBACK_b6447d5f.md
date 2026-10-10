# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_b6447d5f.md`

---

## 背景

- **软件名称**: members
- **版本**: 20080128.1-nmu3
- **构建日期**: 2026-10-01
- **构建系统**: makefile（裸 GNU Makefile，自动采集渲染成 `{BUILD_SYSTEM}`，已手工修正）
- **上游仓库**: https://salsa.debian.org/debian/members（Debian 原生包，源码取自 deb.debian.org pool，自动采集为「未知」，已手工修正）
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
| build | 编译构建 | 成功 | 构建系统: makefile；NDK clang++ 原样编译，无补丁 |
| conan-verify | 配方验证 | 通过 | G1 首轮因缺 `export_sources`/`apply_conandata_patches` 失败（本包无补丁），补上后 G1-G4 全过 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 本报告在建 PR 前定稿 | 尚无检视/CI 结果，不作推测 |

### 失败与问题

本次流程未遇到阻塞性问题

### 知识图谱使用情况

- **引用知识条目**: 无命中（对错误日志跑 `engine` 未命中；本包 G2 一次通过，没有触发 engine 的失败日志）
- **新增知识草稿**: 1 条，`E7300-draft-B41D`（qemu-user 下消费者程序 fork/exec 被测 aarch64 CLI 子进程 rc=127，wrapper 脚本方案）；`draft-review` 判 create，最近似 E307=0.19
- **引擎命中情况**: 无；草稿目录实际 5000+ 个文件，而 finish 输出「2550 个草稿」（按 `.kv` 计数，口径见下「自动化补全」）
- **测试统计**: 上游 N=0 / N′=0（无 tests/、无 check 目标、无 debian/tests）；test_package 消费者用例 1 条，qemu 静态重链实跑 35/35 断言通过（自动采集为 0，已手工修正）
- **未覆盖的错误模式**: 消费者程序 fork/exec 被测 CLI 时 qemu-user 子进程 exec 失败（已写草稿 E7300）；Debian 原生包与 PF7 Debian 池域拦截互斥（属 PF 闸规则问题，见建议）

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 尚未进入检视阶段（建 PR 前定稿）
- **检视意见数量**: 暂无
- **检视意见处理**: 暂无；出现必须修复的意见时再按单 commit 推送

### CI 结果

- **本地 CI 模拟 (W3)**: 未知
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 0（`finish` 末尾的 KNOWLEDGE CONSOLIDATION 块是 exit 0 的提示，不计）
- **重试次数**: 1（conan-verify G1 补 `export_sources` 后重跑）；本地 qemu 验证 1 次（消费者子进程 exec 失败 → 换 wrapper）
- **关键瓶颈**: 设计可在 x86 上验证的消费者用例——qemu-user 无 binfmt，消费者 fork/exec 被测 CLI 失败，花了一轮定位（已沉淀草稿 E7300）
- **耗时较长的步骤**: 无；`conan create` 单包 < 30 秒，`finish` 的 W3 < 1 分钟

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-01T07:18:03 | skeleton_created | result_partial |
| 2026-10-01T07:18:03 | lang_checked | detected=cpp 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **PF7 与 Debian 原生包互斥**（`scripts/ohc/preflight.py:361`、`:379`）：`_PF7_DEBIAN_HOSTS` 把 `deb.debian.org` 一律判「Debian 下游重打包源」，但 `debian/source/format` 为 `3.0 (native)` 的包（如 members）没有 Debian 之外的上游，pool tarball 就是唯一官方源，只能靠 `--no-preflight` 绕过。建议 PF7 遇 Debian 域时先判断是否为 native 包（tarball 内 `debian/source/format` 含 `native`，或 URL 文件名无 `.orig`、无 `-N.debian` 分离补丁包），native 包放行并在 PF 输出里提示登记。
2. **`conan-verify` G1 对无补丁包硬要求补丁调用**（`scripts/ohc/conan_verify.py:491-492`）：`export_sources` / `apply_conandata_patches` 不存在即 FAIL，无补丁包也必须写这两行空转代码。建议仅当 `conandata.yml` 含 `patches:` 时才要求，或降级为 P3 提示。
3. **`finish` 的 step [5/10] 之后仍输出过期预检项**：`packaging/`、`.staging-verified`、`reports/test-report.md` 已不属于 ARCHIVE-SPEC v2.0 之后的交付物，却在 Step 10 以「❌ 需创建」输出，容易诱导在归档里补垃圾文件。建议与 `finalize-archive` 一同移除对 `packaging/` tar.gz 的检查。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **`init-build` 对裸 Makefile 工程选错模板且多处「模板不可用」**：构建系统被识别成 `autotools`（`init-build` 日志「conanfile.py 模板不可用（autotools）」），`scripts/ohc/init_archive.py:262` 按 `test_package-conanfile-autotools.py` 找 test_package 模板，但 `templates/` 下实际只有目录 `test_package/`、`test_package-executable/` 和 `conanfile-autotools.py.tmpl`，文件名对不上，`conandata.yml`（`init_archive.py:241`）、`conanfile.py`（`:253`）、`test_package`（`:273`）、`MANIFEST.yml`（`:306`）四项全部被跳过，得到一个带 `{software}` / `{BUILD_SYSTEM}` 占位符的 manifest。建议：(a) 识别顶层只有 Makefile、无 configure 的工程为 `makefile` 并走 `conanfile-makefile.py.tmpl`；(b) 修正模板文件名映射；(c) CLI 包默认选 `test_package-executable`。
2. **模板 `conanfile-makefile.py.tmpl` 的 `get(self, **self.conan_data["sources"], ...)`** 与仓库 830/860 份配方的「版本键」写法不一致（`sources: {"<版本>": {url, sha256}}`），`templates/conandata.yml.tmpl` 同样是扁平写法；建议统一为版本键。
3. **模板缺「CLI 包消费者用例」范式**：`test_package-executable/test.sh.tmpl` 只是 shell 脚本，而 rule12 明确把检查脚本排除在外。建议补一份「CMake 编译消费者 C/C++ 程序 + 运行被测 CLI」的 test_package 模板（本包 `test_package/` 可作底稿），并在模板里加「非 aarch64 宿主只编译链接、不假装通过」的分支。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **feedback 自动采集**：构建系统渲染成 `{BUILD_SYSTEM}`、上游仓库「未知」、测试统计 0/0/0/0 均与实际不符（本报告已手工修正）；测试统计应读 `test_package/MANIFEST.yml` 的 `upstream_tests_total` / `assertion_count`，构建系统应读归档 `manifest.yaml` 的 `build_system`。
2. **`finish` 的 `gen_summary` 失败**：输出「gen_summary 失败: 'str' object has no attribute 'append'」，属非阻塞但每次必现，`SUMMARY.md` 未更新；请查 `scripts/ohc/finish.py:336` 起的 `step6_gen_summary` 调用链中某字段由 list 被写成 str。
3. **草稿数口径不一致**：`finish` 输出「发现 2550 个草稿待审」，而 `knowledge/drafts/` 下实际文件 5000+（`.kv` 与 `.md` 各一份、命名两种）；建议按 `*.kv` 去重计数并与 `ls` 口径一致，避免作者怀疑漏读。
4. **`init-build` 对环境变量缺失仅告警不影响后续**：`TMPDIR` 未设置标红 ❌ 却 `exit 0` 且不阻塞，容易误以为环境有问题；建议区分「必需」与「仅手工编译需要」。
5. **本地 W3 对 x86 宿主无法执行 aarch64 消费者没有统一口径**：各 `test_package` 各写各的跳过逻辑（有的 `can_run`、有的直接 ELF 魔数检查）。建议 `finish` W3 日志里固定输出「消费者是否实际执行」一行，供 PR 正文统计「本地未实跑、由 CI 执行」时直接引用。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. 已新增草稿 `E7300-draft-B41D`：x86 runner 上 qemu-user 无 binfmt 时，消费者程序 fork/exec 被测 aarch64 CLI 子进程失败（rc=127），用 `#!/bin/sh exec qemu-aarch64 <static> "$@"` wrapper 作被测路径。与 `E544-draft-7C1A`（动态产物缺 musl loader）互补但层次不同，建议主编 promote 后在二者 `similar_to` 里互相引用。
2. **OHOS 用户库行为**：已有草稿说明 OHOS 应用 uid 可能无 passwd 条目（`DRAFT-mairix-0.24-ohos-musl-getpwuid-app-uid-no-passwd`）。members 这类读 `getgrnam/getpwent` 的 CLI 在 OHOS 上的实际输出取决于运行环境的组数据库，建议补一条「读用户/组库的 CLI 工具，test_package 必须以 libc 为 oracle 而非硬编码期望值」的方法论条目。
3. **上游悬空 else / 跳过首条 getpwent 这类「上游既有行为」**：本包不改动它们，而是在消费者用例里按既有行为断言（写入 notes「注意事项」）。建议知识库增加「适配不修复上游行为缺陷，用例按既有行为断言并在 notes 登记」的原则条目。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: AA9C
- **生成时间**: 2026-10-01 07:18:03
- **PR 编号**: —
- **Git Commit**: 255e506963
