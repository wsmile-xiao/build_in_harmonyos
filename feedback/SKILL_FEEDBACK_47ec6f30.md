# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_47ec6f30.md`

---

## 背景

- **软件名称**: sleepenh
- **版本**: 1.8
- **构建日期**: 2026-09-23
- **构建系统**: makefile（上游小型裸 Makefile，无 configure；init-build 误判为 autotools，见"自动化补全"）
- **上游仓库**: https://salsa.debian.org/debian/sleepenh.git（任务指定；源码取 `upstream/1.8` 标签归档，git tree 与作者仓库 https://codeberg.org/nsc/sleepenh 的 `1.8` 标签相同）（自动采集填成了源码归档 URL，已按实修正）
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 1（`0001-sleepenh.c.patch`，+7/-1，无平台宏）
- **编译依赖**:
无（仅 libc）
- **最终状态**: 成功（本地 conan-verify + W3 通过；远程 CI 待 PR 触发）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | salsa `upstream/1.8` 归档，sha256 两次下载一致 |
| build | 编译构建 | 成功 | 构建系统: makefile；首轮因 `program_invocation_short_name` 未声明失败，补丁后零告警 |
| conan-verify | 配方验证 | 通过 | G0-G4 PASS；L2/L4/L5 报"跳过（无 cache 路径）"，由 W3 的 L4/L5 覆盖 |
| finish | 归档收尾 | 完成 | W3 一次通过（L0/KC/JC/L1a/L1b/L1e/L4/L5）；step3 G0 与 step8 gen_summary 为框架侧假失败，见下 |
| submit | PR提交+AI检视+CI | 旁路 | fork 贡献者：手动 push + `create-pr`；PF 本地实跑唯一命中 PF9（软件级 commands.json 等），本报告在建 PR 前定稿 |

### 失败与问题

- **1**: 根因=`sleepenh.c:97:3: error: use of undeclared identifier 'program_invocation_short_name'`——OHOS sysroot 头文件不声明、`libc.so` 只导出 `__progname`，`libc.a` 却有弱别名 `program_invocation_short_name`/`program_invocation_name`；只补 `extern` 时动态链接报 `ld.lld: error: undefined symbol`、`-static` 可过可跑（静态重链验证假阳性）, 解决方案=补丁在 `main()` 中从 `argv[0]` 取 basename 替代，无平台宏；新增草稿 E6402
- **2**: 根因=版本串由 `git describe --dirty` 生成，源码归档无 `.git`，默认构建 `-DVCSVERSION=''`（`--version` 输出 `sleepenh `）, 解决方案=与 Debian rules 相同在 make 命令行传 `vcsversion`（取 `self.version`），test_package F1/F3 校验
- **3**: 根因=上游 Makefile 写死 `CC = gcc`；命令行直接给 `CFLAGS` 会连带覆盖目标专属的 `-DVCSVERSION`, 解决方案=CC 在命令行覆盖、工具链 CFLAGS 走上游 `EXTRA_CFLAGS` 钩子，CPPFLAGS/LDFLAGS 直达内置链接规则（R33）
- **4**: 根因=`install` 目标路径写死 `$(DESTDIR)/usr`, 解决方案=`package()` 直接 copy 二进制与 man 页；只构建 `sleepenh` 目标，避免 `sleepenh.1.gz` 规则依赖 gzip
- **5**: 根因=x86 runner 无 OHOS `/lib/ld-musl-aarch64.so.1`，动态产物无法启动（binfmt qemu 报 `Could not open '/lib/ld-musl-aarch64.so.1'`）, 解决方案=同源同标志 `.o` 静态重链经 qemu 实跑 F1-F8（8/8），test_package 在异架构主机把功能层如实记 SKIPPED，aarch64 CI worker 上必跑
- **6**: 根因=`init-build` 把构建系统判成 `autotools`，`conan-init` 生成 autotools 配方与 CMake 空壳 test_package（CMakeLists.txt + test.c）, 解决方案=按实际裸 Makefile 手写配方，test_package 改为 Python 功能测试，删除 CMake 空壳

### 知识图谱使用情况

- **引用知识条目**: E493（编译错误命中，部分覆盖且推荐方案含 `__OHOS__`，未采用）、DRAFT-ohos-musl-glibc-specific-symbols（compat 定义方案，列为回退）、DRAFT-libfirm-1.22.0-makefile-version-header-tarball（git describe 无 .git，已覆盖问题 2）；功能验证沿用"同源 .o 静态重链经 qemu-aarch64 实跑"的既有做法
- **新增知识草稿**: 1 条（`knowledge/drafts/E6402-draft-6822.kv` + `.md`；自动采集按 manifest 的 knowledge_gained 条数记为 2，已修正）
- **引擎命中情况**: 编译期签名命中 E493；链接期签名 `undefined symbol: program_invocation_short_name` 误命中 E245（vhangup）；draft-review 对 E6402 给出 review-similar → E245（score 0.35，仅"undefined symbol"字面重叠），无同题条目（自动采集填成"草稿目录 1567 条"，已修正）
- **测试统计**: 上游测试 N=0（无 tests/、无 check/test 目标）；test_package 12 项：x86 runner 上 A1-A4 4/4 通过、F1-F8 8 项 SKIPPED；同源静态重链副本经 qemu-aarch64 F1-F8 8/8 通过（自动采集为"总计 0"，已修正）
- **未覆盖的错误模式**: OHOS musl `program_invocation_*` 的静态/动态导出不对称（libc.a 弱别名 vs libc.so 仅 `__progname`）及由此产生的"extern 声明 + 静态重链验证"假阳性——E493 与 DRAFT-ohos-musl-glibc-specific-symbols 均只覆盖"未声明"层；已沉淀为 E6402 草稿

### AI 检视结果

- **检视阶段到达**: —（本报告在建 PR 前定稿并随 PR 首次提交，避免建 PR 后再推送作废检视）
- **变更摘要评估**: 建 PR 前定稿，尚无变更摘要；W4 Pre-PR 独立审计结果见本 PR 说明
- **检视意见数量**: 0（检视尚未开始）
- **检视意见处理**: PR 创建后按检视意见在讨论串内逐条 accept/reject 闭环，确需修改时攒成一个 commit 推送后立即 trigger-ci

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（L0 全过：L0j 首次发布、L0k commands.json type=tool、L0m 结构；KC/JC 通过；L1a/L1b 测试已执行；L1e 破坏性反向验证确认测试依赖被测包；L4 补丁干净；L5 bin/ 有内容）
- **远程 CI (PR 校验)**: 未知（建 PR 后评论 /rebuild 触发）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 3 次，均非真实阻塞：①finish step3 的 G0 HANDOFF（clean-verify 对裸 Makefile 执行 configure，exit 127，假失败）；②finish 收尾的 KNOWLEDGE CONSOLIDATION 块；③首次 `feedback --resume` 报 feedback_incomplete（正文引用了字面占位符被计为待填，改写措辞后通过）。三次都没有进入下方事件时间线（时间线只有 lang_checked 1 条）
- **重试次数**: 0 次门禁重试（conan-verify、finish/W3 均一次通过）；手工编译 2 次（首次 program_invocation_short_name 报错，补丁后通过）
- **关键瓶颈**: ①确认 CI worker 架构与 test_package 形态——需翻已合入先例 PR 的 CI 日志才能确认 worker 是 aarch64 设备（路径 /storage/Users/currentUser）；②program_invocation_short_name 修法选择：知识库 E493 推荐的 `__OHOS__`+`__progname` 违反 R8，需自行做 libc.a/libc.so 符号与静态/动态链接对照实验
- **耗时较长的步骤**: 源码来源核验（salsa upstream/1.8 与 codeberg 1.8 的 tree 哈希比对）、test_sleepenh.py 编写与三组消融（完整配方 8/8、上游 vcsversion 6/8、仅 extern 声明静态 8/8 但动态链接失败）
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-23T20:55:48 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **PF9 与 R38/PF8 对新增 CLI 包必然互斥**（`scripts/ohc/preflight.py:570` `bad = [f for f in arch if len(f.split("/")) < 5]`）：R38 要求软件级 `archives/<l>/<包>/commands.json`，PF9 又把所有 4 段路径判为"缺版本目录层"，任何新 CLI 包都只能 `--no-preflight`。建议 PF9 放行与唯一版本目录同包的软件级 `commands.json`/`README.md`/`manifest.yaml`（whichman !11522 即此形态且 CI 通过、已合入），只拦真正落在包目录外或多包的路径。
2. **finish step [1/10] 每次都把 manifest.yaml 的 `patch_classification` 重置为 `type: auto / platform_only: True / guard: 'pending'`**：已人工标注的分类被覆盖，且在"先 commit 再 finish"的推荐顺序下必然制造一处待还原的改动。建议 refresh-patch 在补丁内容哈希未变时保留既有分类条目（`scripts/ohc/refresh_patch.py` 写 manifest 处）。
3. **finish step [3/10] G0 clean-verify 对裸 Makefile 项目执行 `configure`**（`scripts/ohc/clean_verify.py:136`/`:181`），必然 exit 127 并输出 G0 HANDOFF，而 step4/step5 的 conan-verify 与 W3 均通过，HANDOFF 属假失败。建议 G0 读取配方/manifest 的 `build_system`（本例 `makefile`），无 configure 脚本时跳过或改为直接执行 `conan create` 等价构建。
4. **finish step [8/10] `gen_summary 失败: 'str' object has no attribute 'append'`**（`scripts/ohc/finish.py:340` 调 `ohc/summary.generate_summary`），被 `except` 吞掉后仍记为完成；建议打印 traceback 并定位是哪个 manifest 字段把列表写成了字符串。
5. **PF3/PF4/R52 在"包/版本"结构下静默落空**：`run_preflight()` 把 `_pkg_dirs()`（`scripts/ohc/preflight.py:83-90`，只取到 `archives/<l>/<包>`）直接交给 `check_test_substance` / `check_test_package_files` / `check_deps_in_registry`（`:645-650`），它们查找的 `<包>/test_package/conanfile.py`、`<包>/conanfile.py` 在版本目录布局下都不存在，文件缺失时直接 `return []`（如 `:142-145`）；R52 的 `check_audit_consistency` 同样在软件级找 `.audit-result.json`（`:609`），而 W4 结果写在 `<版本>/reports/audit-result.json`。结果是 preflight 的空壳测试闸、依赖闸与审计一致性校验对所有常规 PR 实际都不生效，"PF 除 PF9 外全过"并不代表它们做过检查（本 PR 的测试实质性由 W3 L1e、零依赖由 W0 与审计另行核实）。建议这三处改为遍历 `_version_dirs(files)`，并在目标文件缺失时报错而不是静默跳过。

### 模板改进

1. **构建系统探测只看 URL**：`scripts/ohc/init_build.py:77-86` `_guess_build_system()` 仅按 URL 关键字判断，其余一律回落 `autotools`，于是 `conan-init` 为裸 Makefile 生成 autotools 配方 + CMake 空壳 test_package（CMakeLists.txt/test.c，要整套重写并手动删除）。`lang-preflight` 已从源码树正确得出 `build_system: make`，建议 init-build 解压后按文件探测（configure/configure.ac → autotools，CMakeLists.txt → cmake，meson.build → meson，仅 Makefile → makefile）或直接复用 lang_detect 结果，并为 makefile 族提供模板（命令行覆盖 CC、EXTRA_CFLAGS 钩子、package() copy）。
2. **conandata.yml 模板非版本键且 sha256 未填**：生成的是 `sources: {url, sha256: "REPLACE_WITH_ACTUAL_SHA256"}`（`templates/conandata.yml.tmpl:8`、`scripts/ohc/conan_recipe.py:301`），而仓库绝大多数配方用 `sources: {"<版本>": {...}}` + `self.conan_data["sources"][self.version]`；init-build 已在 `.orig/.tarball-sha256` 算好哈希却未传入。建议模板改为版本键并自动填入该哈希。
3. **版本级 manifest.yaml 模板渲染不全**：生成物残留 `software: "{software}"`、`build_system: "{BUILD_SYSTEM}"`，`notes.md` 骨架的 `{cmake|autotools|...}` 占位符也没有任何门禁校验；建议 conan-init/finish 对这两个文件跑占位符 lint（`\{[a-zA-Z_|]+\}`）并在 W2 结构检查中阻断。
4. **test_package/MANIFEST.yml 模板默认 `upstream_check_command: "make check"`**：上游没有 check 目标时该默认值本身就是错误声明；建议 conan-init 先 `make -n check/test` 探测，探测失败时留空并提示补清点证据（R51）。

### 自动化补全

1. **feedback 自动采集多处失真**（`scripts/ohc/feedback.py`）：上游仓库取成源码归档 URL（`:270-278`）；新增知识草稿按 manifest `knowledge_gained` 条数计为 2（`:388`，实际 1 条草稿）；"引擎命中情况"填的是全局草稿目录总数（`:397`）；测试统计为"总计 0"（`:446`），而 `reports/test-report.md` 与 W3 日志的 `RESULT:` 行已有 4 通过 / 8 跳过；conan-verify 结果留成待填占位符，但 `reports/conan-verify-report.md` 已有 `Verdict: PASS`。本报告已逐项按实修正。建议：草稿数取 `git diff origin/main...HEAD -- knowledge/drafts/*.kv`，测试统计解析 test_package 的 RESULT 行，conan-verify 读报告 Verdict。
2. **R46 生命周期草稿被跨任务残留整体屏蔽**：`$HOME/ohpcd-ai-worker-result.json` 里是上一个任务（另一个软件）的终态（draft:false），本任务 lang-preflight/conan-init/conan-verify/finish 每一步都打印"终态 result.json 已上报，跳过里程碑草稿"（`scripts/ohc/result_report.py:787`）。建议"终态不降级"判断先比对 pkg/ver，不同软件的终态文件视为残留并按手写/残留规则处理。
3. **refresh-patch 固定 10 行上下文**（`scripts/ohc/refresh_patch.py:30` `_CONTEXT_LINES = 10`）：补丁里空行与 Tab 缩进的上下文行被 `git diff --check` 报 trailing whitespace / space before tab（本补丁 22 处，multisort 先例同样存在），使提交前的 `git diff --check` 自检失去意义。建议改为标准 3 行上下文，或在 `.gitattributes` 为 `archives/**/patches/*.patch` 设置 `-whitespace`。
4. **finish 就绪预检与 finalize 仍要求已废弃的 packaging/**：step10 报"❌ packaging/ — 需创建 packaging/ 目录并打包"（`scripts/ohc/finish.py:377`），finalize-archive 报缺 release/debug tar.gz，均与 ARCHIVE-SPEC v2.0 废弃 packaging/ 冲突，建议删除这两项检查。
5. **init-build 环境检查噪声**：报"TMPDIR 未设置（必需）"为 error、"clang 未找到"，而后续全部构建经 conan profile 的 `/data/service/hnp/bin/clang` 正常进行；建议交叉构建场景改为检查 profile 中 `tools.build:compiler_executables` 指向的编译器。
6. **非 submit 阶段的 HANDOFF 不进事件时间线、Agent ID 不稳定**：本次 finish 与 feedback 共 3 次 HANDOFF，EVENTS 块仍是"0 次 HANDOFF"；同一任务里 feedback 作者节 Agent ID 为 8896、知识草稿 contributor_id 为 6822（均未设 `OHC_AGENT_ID`，由 `scripts/ohc/utils.py:112` `get_agent_id()` 各自取得）。建议 finish/feedback/clean-verify 的 HANDOFF 也经同一事件咽喉记录，Agent ID 首次取得后写入任务状态文件复用。

### 知识图谱覆盖

1. **建议 promote E6402**（`knowledge/drafts/E6402-draft-6822.kv`）：OHOS musl `program_invocation_short_name`/`program_invocation_name` 头文件无声明、libc.so 只导出 `__progname`、libc.a 有弱别名；"extern 声明"在 `-static`/静态重链验证下可过可跑、交付的动态链接失败。附 llvm-nm 与探针程序验证命令，推荐 argv[0] basename 方案（无平台宏）。
2. **修正 E493**：`error_signature` 只含 `program_invocation_name`，建议补 `program_invocation_short_name` 及链接期签名；推荐方案"`__OHOS__` 下改用 `__progname`"与 R8/PF5 冲突且 `__progname` 同样无头文件声明，建议改为 argv[0] 方案或指向 E6402；另 `knowledge/graph/E493.kv:3,80` 的 `doc_file` 写成 `doc/E213.md`，与条目编号不符。
3. **engine 误匹配**：链接期错误 `ld.lld: error: undefined symbol: program_invocation_short_name` 命中 E245（vhangup，Phase B 仅凭 "undefined symbol" 字面），E6402 转正后应能正确命中；G0 预扫描对本项目报 E490（autotools 脚本权限），源于构建系统误判，属连带误报。

---

## 作者

- **姓名**: lkjing2021345
- **邮箱**: 1908499668@qq.com
- **Agent ID**: 8896
- **生成时间**: 2026-09-23 21:30:03
- **PR 编号**: —（本报告在建 PR 前定稿，随 PR 首次提交）
- **Git Commit**: 0292d7d009
