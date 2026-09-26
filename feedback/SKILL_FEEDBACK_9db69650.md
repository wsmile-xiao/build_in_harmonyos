# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_9db69650.md`

---

## 背景

- **软件名称**: multisort
- **版本**: 1.1
- **构建日期**: 2026-09-23
- **构建系统**: makefile（三行裸 Makefile，`CC = gcc` 写死，无 configure / install 目标；骨架自动采集为 `{BUILD_SYSTEM}`，已人工更正）
- **上游仓库**: https://www.xach.com/multisort/multisort-1.1.tar.gz
- **适配路径**: 路径 A（基础适配，1 个补丁；骨架自动采集为"无补丁"，已人工更正）
- **补丁数量**: 1（`0001-multisort.c.patch`，+10/-5，无平台宏）
- **编译依赖**:
无（仅 libc）
- **最终状态**: 成功（built：conan-verify G0-G4 通过，W3 通过）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 构建系统被误判为 autotools（实为裸 Makefile） |
| build | 编译构建 | 成功 | make 命令行覆盖 `CC = gcc`；-O3 直接通过，-O0 链接失败（C99 inline） |
| conan-verify | 配方验证 | 通过 | G0-G4 PASS，1 次通过 |
| finish | 归档收尾 | 完成 | 第 1 次 W3 失败（预下载误改写源 URL），修复后第 2 次通过；按 W4 意见修正配方/测试后第 3 次复验通过 |
| submit | PR提交+AI检视+CI | 待执行 | 本报告随首次提交入仓，W4 审计与建 PR 在其后进行 |

### 失败与问题

1. **musl `BUFSIZ` = 1024（glibc 8192）**：上游 `fgets(buf, BUFSIZ)` 在 OHOS 上把 1024 字节以上的日志行切段，续段中的 `[` 被当作日期解析、写入 `\0` 后截断输出；编译零告警，仅运行时出现。补丁改用固定 8192 字节行缓冲。
2. **C99 inline**：gperf 2.7 生成的非 static `__inline in_word_set()` 在 `-O0` 下 `ld.lld: error: undefined symbol: in_word_set`（Release -O3 因内联侥幸通过）。补丁加 `static`。
3. **上游缺陷（非平台）**：排序哨兵 `900000000` 自 2018-12-06 起小于所有时间戳，合并失序并对已关闭的 FILE 读取（x86 glibc 版 SIGSEGV）。补丁改为 `LONG_MAX`。
4. **W3 失败一次**：`FileNotFoundError: .../.build-cache/predl_cache/9b840294_source_9b840294multisort-1.1.tar.gz`。conandata.yml 注释里的下载页 URL 被 W3/CI 预下载当成源码包下载，并以字符串替换改写，连带破坏真实 URL；conan-verify 的 G2 不做预下载所以通过。去掉注释 URL 后通过。
5. **x86 runner 无法运行交付的动态产物**（构建机没有 OHOS 的 `/lib/ld-musl-aarch64.so.1`）：功能验证改用同源同标志的静态重链副本经 qemu 实跑（F1-F7 7/7），test_package 在 x86 上把功能层记 SKIPPED。
6. **W4 审计（首轮 pass，P2×4 / P3×4）后建 PR 前一次性修正**：配方 `url` 模板占位、草稿 `error_signature` 内含括号 `|`（engine 按 `|` 切分后失效）、MANIFEST 残留默认 `make check`、引用了本仓库不存在的条目编号、F5 与哨兵缺陷耦合（改为 1999 年日期并补做补丁消融对照）；随后重跑 W3 与 W4。

### 知识图谱使用情况

- **引用知识条目**: E321-draft-9758（C99 inline 缺外部定义）、DRAFT-8543-conandata-comment-url-predl-rewrite（注释 URL 被预下载改写）
- **新增知识草稿**: E6401-draft-9A43（OHOS musl BUFSIZ=1024 导致 fgets 静默切段长行）
- **引擎命中情况**: 3 次查询 0 次命中正确条目——C99 inline 链接错误误命中 E245（vhangup），BUFSIZ 现象误命中 E493（program_invocation_name），W3 预下载报错命中 E333（连字符截断，根因不同）
- **测试统计**: test_package 共 10 项：x86 runner 上 A1-A3 3/3 通过、F1-F7 7 项 SKIPPED（无 OHOS loader）；静态重链副本 F1-F7 7/7 通过；补丁消融对照：未打补丁 4/7、仅行缓冲修复 5/7、仅哨兵修复 6/7；上游测试 N = 0（骨架自动采集为"总计 0"，已人工更正）
- **未覆盖的错误模式**: musl `BUFSIZ` 1024 与 glibc 8192 的行长度差异（已沉淀草稿 E6401-draft-9A43）；其余两类已有草稿但未入正式库，engine 无法命中

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 不适用——本报告在首次提交 PR 前完成并随 PR 入仓，提交时 AI 检视尚未开始
- **检视意见数量**: 不适用（提交时为 0，检视尚未开始）
- **检视意见处理**: 不适用；检视意见将在 PR 讨论串内逐条处理

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（第 2、3 次；L0 pass / L1 pass / L2 skip（无 --version）/ L4 warn（`fgets` 被误判为 `gets`）/ L5 pass）
- **远程 CI (PR 校验)**: 提交本报告时尚未触发
- **CI 失败原因**: 无（本地 W3 首次失败原因见"失败与问题"第 4 条）

### 效率分析

- **HANDOFF 次数**: 1 次（finish Step5 `w3_local_ci_failed`）
- **重试次数**: finish 3 次（第 1 次 W3 失败，第 2 次通过，W4 修正后第 3 次复验）；conan-verify 1 次（finish 内另跑 2 次）；W4 审计 2 轮（首轮 pass 后修正 P2/P3 再审）；手工交叉编译 3 种标志组合各 1 次
- **关键瓶颈**: 构建系统误判导致 conan-init 生成的 autotools 配方、CMake 空壳 test_package、manifest 占位符全部要重写；G2 与 W3 的预下载行为不一致，多了一轮 finish
- **耗时较长的步骤**: test_package 功能用例设计与 qemu 静态重链验证（含未打补丁对照）；finish 单次约 4 分钟（W3 conan create 本身不到 1 分钟）
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-23T18:36:07 | lang_checked | detected=c 与任务 cpp 匹配 |
| 2026-09-23T18:47:28 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **构建系统判定只看 URL**：`scripts/ohc/init_build.py:80-86` `_guess_build_system()` 按 URL 关键词猜测，兜底返回 `autotools`。裸 Makefile 包因此被判 autotools，连带 conan-init 选错模板、G0 clean-verify 跑 `./configure`。而同一流程里的 `lang-preflight` 已从源码树判出 `build_system: make`。建议解包后按源码树判定（configure / configure.ac → autotools，CMakeLists.txt → cmake，meson.build → meson，只有 Makefile → make），或直接复用 lang_detect 的结果。
2. **G0 clean-verify 对非 autotools 包必然失败**：`scripts/ohc/clean_verify.py:69,136-181` 无条件执行 `./configure`，裸 Makefile 包报 `configure 失败 (exit 127)`，finish 把 step5b 记为失败步骤，容易诱导误判。建议按构建系统分派；make 类包跳过 configure，或直接以 conan create 结果为准。
3. **finish 每次冲掉补丁分类**：`scripts/ohc/refresh_patch.py:531-548` 用 `re.sub(r'\npatch_classification:.*', '', content, flags=re.DOTALL)` 从该键删到文件末尾，再追加 `type: auto / guard: pending`。按提示补写的分类每次 finish 都会丢失，排在它后面的键（如 `knowledge_gained`）也会被一并删掉（本次实际发生）。建议补丁集合未变时保留已有分类，并改用 YAML 解析只替换该键。
4. **G2 与 W3/CI 的源码获取路径不一致**：conan-verify G2 直接用 conandata.yml，W3/CI 先做预下载改写，所以出现"conan-verify 通过、W3 失败"。建议 conan-verify 复用同一预下载步骤，或在 G1 对 `sources` 之外出现的 http(s) URL 报警。

### 模板改进

1. **裸 Makefile 模板存在但选不中，且本身有缺陷**：仓库已有 `templates/conanfile-makefile.py.tmpl` 与 `templates/test_package-executable/`，但 `scripts/ohc/conan_recipe.py:143-173` 的 `_detect_build_system()` 先读 manifest 的 `build.system`（由 init-build 按 URL 猜出的 `autotools` 写入），源码扫描兜底（能判出 `makefile`）永远轮不到，于是生成了 `package_type = "library"`、`cpp_info.libs = ["multisort"]`、R26 `--enable-static` 的 autotools 配方，以及只 `printf("OK")` 的 CMake 空壳 test_package。建议 conan-init 以源码扫描结果为准（与 manifest 冲突时告警）。makefile 模板本身也写着 `url = ""  # CI fills this`（`templates/conanfile-makefile.py.tmpl:36`），而 `.gitcode/code-style.md` §5 把这一行列为禁止残留的占位符，模板与审计规则自相矛盾，本次被 W4 记为 P2；建议模板直接填仓库 URL，并把 `package_type` 做成按产物（库/CLI）二选一。
2. **conandata.yml 骨架**：生成扁平 `sources: {url, sha256}`，sha256 为 `REPLACE_WITH_ACTUAL_SHA256`。但 init-build 已算出 tarball 的 sha256（`.orig/.tarball-sha256`），可以直接填入，并按仓库主流写成加引号的版本键（`"1.1":`）。
3. **manifest.yaml 占位符未渲染**：init-archive 生成的版本级 manifest.yaml 留有 `software: "{software}"`、`build_system: "{BUILD_SYSTEM}"`、空 sha256；notes.md 骨架的 `{cmake|autotools|...}` 占位符也没有任何门禁校验（本次靠手工 grep 清零）。建议渲染这些字段，并在 finish Step 6 或 L0 增加占位符检查。

### 自动化补全

1. **feedback 骨架字段不刷新**：骨架在 conan-init 时生成，之后运行 `feedback`（非 --resume）只刷新事件时间线，不重新采集背景和情况字段。本次骨架停在 `构建系统 {BUILD_SYSTEM}`、`补丁数量 0`、`适配路径 无补丁`、`W3 未知`、`测试统计 总计 0`，与实际（makefile / 1 个补丁 / W3 通过 / test_package 10 项）不符，已人工更正；时间线也漏记了 W3 的 `w3_local_ci_failed` HANDOFF。建议 `feedback` 每次重新执行 `scripts/ohc/feedback.py:290-345` 的采集函数，只保留人工填写的建议节；finish 的 HANDOFF 也应写入事件时间线。
2. **预下载误改写源 URL（DRAFT-8543 已记录，仍在复现）**：`ci/conan/build_and_test.sh:1202` 的正则抓取 conandata.yml 全文所有 http(s) URL，`:1293` 再用 `str.replace` 全局替换。注释里的下载页 URL 恰好是真实源 URL 的前缀，替换后真实 URL 被改成 `file://.../9b840294_source_9b840294multisort-1.1.tar.gz`。建议改为 `yaml.safe_load` 只取 `sources.*.url`，并按键精确回写。
3. **L4 危险函数误报**：`ci/conan/build_and_test.sh` L4 的 `grep -rlE '(strcpy|sprintf|gets|strcat)\b'` 缺少词首边界，把补丁中安全的 `fgets(..., LINEBUF_SIZE, ...)` 当作 `gets`，报 `L4_RESULT=warn`。建议改为 `\b(strcpy|sprintf|gets|strcat)\s*\(`，且只扫补丁的 `+` 行。
4. **Agent ID 不固定**：未预设 `OHC_AGENT_ID` 时每条命令随机生成（本次 conan-init、conan-verify、feedback 骨架分别为 9A43、C8B4、56CD），result 草稿、知识草稿和本报告的归属对不上。建议首次生成后持久化到 `.ohc/`。
5. **finish 附带故障**：Step 8 报 `gen_summary 失败: 'str' object has no attribute 'append'`，与包无关，每次复现。Step 7 报"发现 1465 个草稿待审"并记为 1 类问题（存量草稿与本包无关），且只认行内含 `ref:` 的 knowledge_gained 条目（`scripts/ohc/check_knowledge_gap.py:59-66`）。建议修复前者；后者放宽为识别 `E\d+` / `DRAFT-` 编号，或在文档中写明这一约定。
6. **pre-commit 调用方式**：`ci/conan/hooks/pre-commit` 是 Python 脚本，SKILL.md 的 "Pre-commit Hook" 节只给了 cp 安装方式。手动运行时用 bash 调用会报语法错误（本次踩到），建议注明 `python3 ci/conan/hooks/pre-commit`。

### 知识图谱覆盖

1. **新增草稿 E6401-draft-9A43**：OHOS musl `BUFSIZ` = 1024 导致 `fgets(buf, BUFSIZ)` 静默切段长行。查重结果：engine 误命中 E493；draft-review 最高相似度 0.03（E388，verdict=create）；正式条目与草稿中均无 BUFSIZ/fgets 行长度条目（E302 仅在 open_memstream 验证命令里提到 BUFSIZ）。草稿带 `prescan_pattern: fgets\s*\([^;]*\bBUFSIZ\b`，promote 后 PreScanner 可以在编译前提示同类风险。建议 promote。
2. **C99 inline 链接错误**：engine 把 `ld.lld: error: undefined symbol: in_word_set` 误命中 E245（vhangup）；该根因已由 E321-draft-9758 覆盖，但尚未入正式库。建议 promote，并在 match_keywords 补 `gperf`、`in_word_set`、`-Wstatic-local-in-inline`（gperf ≤ 2.7 的输出是这一模式的高频来源，而且只在 -O0/Debug 暴露）。
3. **预下载误改写 URL**：engine 把 `FileNotFoundError ... predl_cache/<hash>_source_<hash><name>.tar.gz` 命中为 E333（URL 连字符截断，根因不同），真正对应的是 DRAFT-8543-conandata-comment-url-predl-rewrite。建议 promote 并在签名上与 E333 区分：`_source_<hash>` 前缀拼接是本模式的特征。
4. **x86 runner 无法运行 OHOS 动态产物**：binfmt qemu 报 `Could not open '/lib/ld-musl-aarch64.so.1'`，只能用同源 `.o` 静态重链副本做功能验证，test_package 需要"异架构主机仅在加载器/格式标记下记 SKIPPED"的规则。这是每个 CLI 包在 x86 构建机上都会遇到的情况，但正式条目与草稿中都没有对应条目（最接近的 DRAFT-yosys-0.66-ohos-aarch64-local-run-missing-fd-chk 讲的是借用 Alpine musl loader 时缺 `__fd_chk`）。建议新增条目，统一"静态重链 + 如实 SKIPPED"的做法。
5. **文档数据错误**：`knowledge/musl-glibc-full-comparison-iso-posix.md:412` 把 musl 的 `BUFSIZ` 记为 4096，与 OHOS SDK 头文件（及上游 musl）的 1024 不符，建议随 E6401 promote 一并更正。

---

## 作者

- **姓名**: lkjing2021345
- **邮箱**: 1908499668@qq.com
- **Agent ID**: 9A43（骨架自动生成时记为 56CD，见"自动化补全"第 4 条）
- **生成时间**: 2026-09-23 18:47:28
- **PR 编号**: —（本报告在首次提交 PR 前完成）
- **Git Commit**: 89a5562012
