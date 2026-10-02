# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_711c1d5a.md`

---

## 背景

- **软件名称**: sproxy
- **版本**: 1.02
- **构建日期**: 2026-09-29
- **构建系统**: autotools 包装的纯 Perl 脚本包（无 C/C++ 编译；自动采集记为 custom）
- **上游仓库**: https://download.joedog.org/sproxy/sproxy-1.02.tar.gz（JoeDog 官方下载站）
- **适配路径**: 路径 B（知识库扩展）；自动采集误判为「路径 A（基础适配，无补丁）」
- **补丁数量**: 0（适配全部在配方 `build()` 内完成）
- **编译依赖**: perl/5.42.2.3
- **最终状态**: 本地 conan create + test_package 通过；PR/CI 结果在建 PR 时尚未产生

---

## 情况

### 执行概要

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | `.work` 与 `.orig` 为硬链接，解包后立即断链（E543 做法） |
| lang-preflight | 语言预检 | 通过 | 检测器判 `c`（autotools 元数据，源码统计为「无源文件可统计」），实际是 Perl 脚本包 |
| build | 打包构建 | 成功 | 无编译；配方 `build()` 复刻上游 sed 替换与自带模块安装 |
| conan-verify | 配方验证 | 通过（第 4 次运行） | 前两次 G1 缺补丁调用、G2 test 阶段找不到可用 perl，见下 |
| finish | 归档收尾 | 见 W3 记录 | 提交前 finish 单独执行 |
| submit | PR提交+AI检视+CI | 待提交 | 本报告随 PR 一并提交，检视与 CI 结果不在此列 |

### 失败与问题

- **G1 失败（缺 `apply_conandata_patches`）**：G1 要求配方含补丁应用调用，即使 `patches: []`；补上 `export_conandata_patches` + `apply_conandata_patches` 后通过。
- **G2 失败 #1（`no perl with LWP::UserAgent/HTTP::Daemon`）**：依赖 perl 是 aarch64 musl ELF，x86 runner 无法执行（`aarch64-binfmt-P: Could not open '/lib/ld-musl-aarch64.so.1'`）；`shutil.which("perl")` 在 conanrun 环境下命中的仍是它。处置：候选加入主机 `/usr/bin/perl` 并去重。
- **G2 失败 #2（`Can't load '…/aarch64-linux-thread-multi/auto/…so'`）**：`conanrun` 导出依赖 perl 的 `PERL5LIB`，主机 perl 继承后加载 XS 模块失败。处置：仅对 shebang 所指依赖 perl 继承该变量。
- **CI 连续两轮红（首轮 `Can't locate HTTP/Daemon.pm`，二轮 `Can't locate HTTP/Request.pm`）**：本地主机 perl 自带完整 libwww-perl，掩盖了「依赖 perl 与设备系统 perl 都不带 libwww-perl 栈」。首轮我只补了 Daemon.pm，是没先核对本地缓存里同一份依赖 perl 包的模块清单造成的误判（该包可直接 `find` 到 `@INC` 内容）。二轮修复：包自包含——装上游自带 libwww-perl 5.76 整套纯 Perl + CPAN URI 5.35，并对 `sproxy.in` 插入 `parse_head(0)`（免 HTML::Parser XS），test 断言模块均解析自包内。
- **上游 configure 不可用于交叉构建**：`configure.in` 的 `$PERL utils/modtest <Module>` 需在构建机执行目标 perl，输出为空会使自带模块被静默跳过；改由配方直接从 `lib/JoeDog-Config-1.2.tar.gz` 取出 `Config.pm`。
- **任务书依赖与实际不符**：任务书写 Autoconf/Automake/Libtool，实际上游 configure 已随包预生成，且只做 sed/拷贝，不需要 autotools。

### 知识图谱使用情况

- **引用知识条目**: E544（x86 runner 上 OHOS 动态产物无法运行）、`DRAFT-ohos-perl-script-package-conan-adaptation`（shebang 先例）
- **新增知识草稿**: 1 条（`E14721-draft-GCW8`）；自动采集写「3 条」与实际不符
- **引擎命中情况**: `engine` 对 PERL5LIB/modtest 相关日志只命中 E155、E116（均不覆盖「目标 perl 不可执行」）；conan-verify 的 G2 误命中 E540（shadow-ci PATH 问题，与本次无关）
- **测试统计**: 上游 0/0（1.02 无任何测试，清点见 notes.md）；test_package 10 断言全部通过；自动采集为「总计 0」
- **未覆盖的错误模式**: 「autotools 包装的纯 Perl 包在交叉构建下，configure/Makefile 里执行 `$PERL` 的模块探测返回空、自带模块被静默跳过」与「conanrun 的 PERL5LIB 污染改用的主机 perl」——已沉淀为 E14721 草稿

### AI 检视结果

- **检视阶段到达**: 未到达（建 PR 前生成）
- **变更摘要评估**: 待 PR 建立后由机器人给出
- **检视意见数量**: 待定
- **检视意见处理**: 待定；有必须修的意见时合并为单个 commit 推送

### CI 结果

- **本地 CI 模拟 (W3)**: 由 finish 写入 `.ci-result.json`（不入仓）
- **远程 CI (PR 校验)**: 连续两轮失败（test_package 缺 libwww-perl 栈），二轮修复后待重跑
- **CI 失败原因**: 依赖 perl 无 `HTTP/Daemon.pm`、`HTTP/Request.pm`（整个 libwww-perl 栈）；设备系统 perl 无 `LWP/UserAgent.pm`

### 效率分析

- **HANDOFF 次数**: 0（conan-verify 失败 3 次均为配方/测试问题，直接读日志修复）
- **重试次数**: conan-verify 共 4 次运行（G1 失败 1 次、G2 失败 2 次、通过 1 次）
- **关键瓶颈**: 「无模板 + 无同类 Perl 库先例」的测试设计——需要一个真正把包内脚本跑起来的消费者流程，而依赖 perl 在 x86 runner 上不可执行，只能选主机 perl
- **耗时较长的步骤**: G2 conan create（含 perl 依赖下载）；其余为人工设计 test_package
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-29T07:19:47 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. `lang_detect.detect_language` 对「autotools 元数据 + 无 C 源码、实为脚本」的包判 `c`（本次 `source_stats='无源文件可统计'` 却仍判 c）。建议当源码统计为空/主体为 `.in` 脚本模板时判 `other` 并在 `notes` 里提示「疑似脚本包」，避免后续按 C 库套 `autotools` 模板。
2. `conan-verify` 的 G1 对 `patches: []` 仍要求 `apply_conandata_patches` 调用，但报错只写「缺少: 补丁应用调用」。建议报错直接给出需要加的两行（`export_conandata_patches` / `apply_conandata_patches`），并说明空补丁也要保留。
3. G2 失败时 `engine` 把 test 阶段的 perl 报错误匹配为 E540（shadow-ci PATH）；`run_engine` 的关键词粗筛应把「test() 阶段」与「configure/make 阶段」分开加权。

### 模板改进

1. `conan-init` 在本次运行前的 `init-build` 输出「conandata.yml / conanfile.py / test_package 模板不可用（autotools）」，构建系统被识别为 autotools 但模板名解析失败。建议 `init_archive` 对纯脚本包回退到 `conanfile-headeronly.py.tmpl` 的「脚本工具」变体（`templates/conanfile-headeronly.py.tmpl`），并同步给出 `commands.json` 骨架。
2. `templates/notes.md` 的占位符 `{cmake|autotools|…}` 与验证用例表没有「上游无测试」的现成写法；建议在模板里给出 R51「清点证据」小节骨架。
3. `templates/test_package-executable` 只有 `test.sh.tmpl`，缺「拉起长驻服务 + 客户端交互 + 校验日志文件」的消费者测试骨架，本次 `test_sproxy.py` 可作范例。

### 自动化补全

1. `feedback` 自动采集：`适配路径` 写死「路径 A」（本任务为路径 B）、`新增知识草稿` 统计到 3 条（实际 1 条，疑似把 `knowledge/drafts/` 里含 perl 的存量草稿计入）、测试统计恒为 0、`失败与问题` 把 notes.md 表格列错位（「根因」取成「问题」列，「解决方案」取成「根因」列）。建议按表头名而非列序解析，并从 `MANIFEST.yml` 读 `assertion_count`。
2. `init-build` 末尾的环境检查对纯脚本包报「clang/cmake/autoconf 未找到」为错误（`errors=1` 实为 TMPDIR 未设置）；建议按 `build_system=script` 跳过编译器/构建工具检查，只保留 TMPDIR。
4. 本地 x86 runner 的主机 perl 通常自带完整 libwww-perl，会掩盖设备/CI 上的模块缺口。建议 perl 脚本包模板/文档给出「列出依赖 perl 包 `@INC` 内可用模块」的一行命令（`find <perl 包>/lib -name '*.pm'`），并要求测试脚本断言所需模块解析自包内（sproxy 的 test_sproxy.py 可作范例）。
3. `.work` 与 `.orig` 硬链接的断链（E543）仍需手动 `cp --remove-destination`；建议 `init-build` 解包后自动断链。

### 知识图谱覆盖

1. 建议 promote 本次草稿 `E14721-draft-GCW8`：autotools 包装的纯 Perl 包在 x86 构建机/runner 上目标架构 perl 不可执行——上游 `$PERL utils/modtest` 探测为空使自带模块静默缺失、`conanrun` 的 `PERL5LIB` 污染主机 perl。`draft-review` 结果为 `review-similar`（最相近 E155，0.35；灰区，差异见草稿头注释）。
2. 上游 Makefile.am 的 `install-exec-hook` 里 `test $(havesmime) = "no"`（应为 `havemime`）这类「变量名笔误使分支永假」的问题，可在 prescan 规则里加一条 `have[a-z]+` 与 `AC_SUBST` 名称不一致的检查（`knowledge/graph/pre-scan-rules.yaml`）。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: C6D9
- **生成时间**: 2026-09-29 07:29:18
- **PR 编号**: —
- **Git Commit**: 60ed502492
