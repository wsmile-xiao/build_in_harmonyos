# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_448d7831.md`

---

## 背景

- **软件名称**: looktxt
- **版本**: 1.4.1
- **构建日期**: 2026-09-19
- **构建系统**: makefile
- **上游仓库**: https://gitlab.com/soleil-data-treatment/soleil-software-projects/looktxt/-/archive/v1.4.1/looktxt-v1.4.1.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 1
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
| build | 编译构建 | 成功 | 构建系统: makefile |
| conan-verify | 配方验证 | 通过（G1/G2/G3 PASS，G0 知识图谱预查询 + G4/L2/L4/L5 同轮执行，末行「配方验证通过」退出码 0） | 文档/元数据改正后又完整复跑 3 次（包修订 79b7af22 → 113feb8b → 5b65f66e），每次均 `Test OK` + 15/15 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | PR #11244 已创建（Gate 0–4 全通过；`OHC_PREFLIGHT=0` 逃逸 PF9 误报） | AI Review 与远程 CI 在提交本文件时仍在闭环中，结果见下一节更新 |

### 失败与问题

- **1**: 根因=`make test` / 任何扫描含数据区的文本文件的调用无限挂起（设备 100% CPU，永不返回）, 解决方案=`file_scan()`（looktxt.c L2336–L2700）用 `char c`（L2382）承接 `c = lk_tolower(getc(...))`（L2419）并与 `EOF` 比较（L2422、`while (c != EOF)` L2692）。OHOS clang 目标 `aarch64-unknown-linux-ohos` 的 plain char **默认无符号**（实测 `CHAR_MIN=0`、预定义 `__CHAR_UNSIGNED__`），EOF(-1) 经 char 转换后变成 255，比较永不成立，扫描主循环失去唯一出口
- **2**: 根因=构建不可复现：Makefile 自动探测宿主 `/usr/include/napi.h` 头文件, 解决方案=`NEXUS_NAPI = $(shell [ -f /usr/include/napi.h ] && echo -DUSE_NEXUS -lNeXus \
- **3**: 根因=R33：Makefile 用 `${CC}`, 解决方案=CI worker 上 shell 无 `CC`，`make` 会退化为内建 `cc`（交叉编译静默失效）
- **4**: 根因=上游 `make install` 报 `install: inaccessible or not found`, 解决方案=上游 install 目标依赖 `install(1)`，OHOS/toybox 不提供
- **5**: 根因=消费者测试若按「非零即失败」断言会全错, 解决方案=`main()` 返回的是**已处理文件数**：无输入 → rc=0（仅告警）、不可读文件 → rc=0、两个输入 → rc=2、覆盖保护触发时仍 → rc=1；`--test` 模式强制 ret=0
- **6**: 根因=不加 `--fast` 时数值错位（`1.0 2.0 3.0 / 4.0 5.0 6.0` → `1 1 2 / 3 4 5`）, 解决方案=上游慢路径（逐字符回填）既有缺陷：用**未打补丁**的源码 + `-fsigned-char` 亦逐字复现 → 与本次 EOF 补丁无关，非适配引入；上游 `make test` 为干跑模式，不比对数值，故上游自身从未暴露
- **8**: 根因=本地 CI 门禁（`ci/conan/build_and_test.sh`）L1 失败：`NotADirectoryError: .build-cache/predl_cache/acb8fbe0_looktxt/-/archive/v1.4.1/looktxt-v1.4.1.tar.gz`（同一配方在 conan-verify 下 G1/G2/G3 PASS、整体「配方验证通过」）, 解决方案=conandata.yml **注释**里写了项目主页裸 URL，而它是 `sources.url` 的严格前缀；预下载步骤先按正则抓出全部 URL（含注释），再对每个 URL 执行 `content.replace(url, 'file://<缓存文件>')`，注释 URL 在文件中先出现 → 真实 URL 被改写为 `file://<GitLab 主页 HTML><剩余路径>` 这种不存在的路径
- **9**: 根因=首次 `finish` 在 Step 4 conan-verify 抛 `ConanException: Patch file does not exist: .../0001-fix-eof-infinite-loop-int-c.patch`，W3 因此未执行（无 `.ci-result.json`）, 解决方案=finish Step 1 的 `refresh-patch --auto` 以 work 目录的编辑追踪器（`.edit-tracker.json` 的 `edited` 永久累积，基线不刷新）为输入，按 `{序号}-{变更文件路径}` 规则重新生成并**改名**补丁（`0001-looktxt.c.patch`，内容与手工命名版逐字节相同），但不改 `conandata.yml`；同时把 manifest 的 `patch_classification` 重置为工具默认（`type: auto` / `platform_only: True` / `guard: pending`）
- **10**: 根因=W4 独立审计（提 PR 前）判 P1：全部交付文档把死循环的位置写成 `data_get_double()`，与源码事实矛盾, 解决方案=早期定位时把两件事混为一谈：`data_get_double()`（L2056–L2154）确实有 README 所说的 fast/slow 两条数值路径（L2075 `fscanf` 快路径 / L2108 `fread+sscanf` 慢路径），但它**不含任何 getc/EOF**；全文件唯一的 `getc()` 在 `file_scan()` 的扫描主循环里（L2419），唯一 `char c;` 在 L2382。审计代理重新下载官方归档、grep 函数边界后指出矛盾
- **11**: 根因=交付文档中 `patch_type: "bugfix"` 与 code_style §12（`patch_type` 固定 `"portability"`）不符，`patch_description` 也是多行折叠段而非空一格词组, 解决方案=只按「这是上游 bug」的直觉取值，未对照 §12 与同类归档的实际写法（实测本仓库 conandata.yml 的 `patch_type` 取值：全仓 `portability` 6406 次 vs `bugfix` 253 次；`archives/a/*` 611 vs 38，少数包仍写 bugfix 属存量差异）

### 知识图谱使用情况

- **引用知识条目**: E419（plain char 作为有符号 8 位样本，本案与之同源不同症）、E011/E129（HMDFS 与只读 `/tmp` 约定）、E007/E160（显式 triplet）、E480（build 目录约定）、E415（镜像 fallback 原地改写 worktree conandata.yml）；铁律口径 R8/R33/R9/R38/R39/R51/R52
- **新增知识草稿**: 10 条
- **引擎命中情况**: 草稿目录 1211 条
- **测试统计**: 总计 21, 通过 21, 失败 0, 跳过 0
- **未覆盖的错误模式**:
  1. 以 plain char 承接 getc()/fgetc() 返回值后再与 EOF 比较：在 plain-char-unsigned 目标（aarch64 OHOS / ARM / RISC-V）上哨兵值不可表示，扫描状态机在文件末尾失去出口 → 100% CPU 永久挂起，测试表现为 timeout rc=124 而不是断言失败（→ 草稿 DRAFT-8543-plain-char-eof-sentinel-infinite-loop）。图谱仅有 E419 覆盖「数值差 256 但数据仍在」的另一种症状，无「哨兵值不可表示 → 控制流丢失」条目。
  2. conandata.yml **注释/描述文本**里的裸 URL 会被 CI 预下载步骤逐个 str.replace 成缓存路径，前缀型 URL 先被替换会拼出不存在的路径，conan 在 source() 抛 NotADirectoryError，而 conan-verify 走 HTTPS 直连因此全绿（→ 草稿 DRAFT-8543-conandata-comment-url-predl-rewrite）。
  3. refresh-patch --auto 会按「序号-变更文件路径」重命名补丁但不回写 conandata.yml，导致重跑 finish 在 Step 4 抛 "Patch file does not exist"，并把 manifest 的 patch_classification 重置为占位值（→ 草稿 DRAFT-8543-refresh-patch-rename-conandata-desync）。

### AI 检视结果

- **检视阶段到达**: Phase 1 (等待摘要)
- **变更摘要评估**: 待 AI Review 摘要到达后回填（PR #11244）。
- **检视意见数量**: 待回填。
- **检视意见处理**: 待回填（按 RV-27 要求逐条回复或标已解决后方可置 success）。

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 进行中（`/rebuild` 已发出，等待 ohpcd CI 结果评论）
- **CI 失败原因**: 暂无（W3 本地 CI 模拟 exit 0，integrity_hash 9db166f8264865ba）

### 效率分析

- **HANDOFF 次数**: 0（全程未触发 HANDOFF 落盘）
- **重试次数**: 高。finish 重跑 3 次（补丁改名问题）、W4 独立审计 5 轮（1 P1 + 1 P1 + 1 P1，两轮 pass 后仍继续落实 P2/P3）、conan create 端到端复跑 4 次、本地 CI 门禁在 conandata 注释问题修复后重跑 2 次。
- **关键瓶颈**: 交付文档与源码事实的对齐（3 次 P1 全是「文档写错位置/写错数量」，而非构建问题）；其次是共享设备上 conan 全局锁被他人任务长期占用（最后一轮端到端复跑等待 6 分钟后跳过）。
- **耗时较长的步骤**: W4 独立审计循环（每轮需重新下载官方归档并逐行核对引用）、conandata 注释 URL 导致的本地 CI 排障、以及 refresh-patch 改名与 conandata 脱钩造成的 finish 返工。
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-19T15:39:14 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->

---

## 建议

### SKILL 设计改进

1. **W4 审计应以「文档↔源码事实核对」为独立必检项**。本包 3 次 P1 全部是文档口径错误（函数归属、格式数量、外部哈希断言），而配方与补丁从头到尾是对的；现有提示更偏向欺骗/配方质量，缺少「凡引用行号/数量/外部凭据必须有可复现命令」这条硬要求。建议在 audit 模板里加一节机械核对清单：每个 `L<行号>`、每个「共 N 项」、每条「与 X 逐字一致」都要附取证命令。
2. **PF9 路径闸对软件级文件一刀切**（`archives/<l>/<包>/README.md|manifest.yaml|commands.json` 被判「缺版本目录层」），而 ARCHIVE-SPEC 要求这些文件必须存在，只能靠 `OHC_PREFLIGHT=0` 逃逸。建议白名单放行软件级三件套。
3. **门禁失败信息应指向真正的失败点**：refresh-patch 改名后 conandata 未同步，报错是 conan 的 "Patch file does not exist"，让人先怀疑 conanfile.py。建议 finish 在改名时同步 conandata.yml 的 `patch_file`，或在报错里打印「补丁名由 refresh-patch 生成，请同步 conandata.yml」。
4. `check-knowledge-gap` 只统计 manifest 的 knowledge_gained 引用，不校验 notes 问题表编号是否存在，写错锚点不会被发现；建议顺带校验 `notes.md#<锚点>` 可解析。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **PR body 模板应把测试计数改成从 `MANIFEST.yml` 读取**：`submit` 自动生成的正文按 `ci-metadata.json` 填「单元测试 0 / 集成测试 0」，与真实的 6 + 15 条不符，必须人工整体覆盖（本包已覆盖），否则评审看到的就是假数字。
2. `notes.md` 模板的「遇到的问题」表把 根因/解决方案 直接灌进 SKILL_FEEDBACK 时截断了长行（第 2 条的 `\|` 转义把内容切断），建议转储前先做单行化/转义清洗。
3. 模板里的「适配路径 A/B」与 notes 里的「模式 A/B」口径不一致（本包 notes 写模式 B，反馈表自动填成路径 A），建议统一术语。
4. `SKILL_FEEDBACK` 预填了「远程 CI: 通过」「submit: CI 通过」这类**尚未发生**的结果，若作者不逐行核对就会提交虚假状态（R34 风险）。建议默认写成「进行中/待回填」。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **交付前自动核对交付文档里的每个 `L<行号>` 与数量断言**：把归档内的 `L\d+`、`共 N 项`、`N 种格式` 抓出来，与 `patches/` 对应的源码做一次 grep 级校验（本包 3 次 P1 都能被这种机械检查拦住，成本远低于人工审计）。
2. **外部凭据自动留痕**：凡是「与某发行版一致」「同一 sha256」的断言，建议由工具把比对来源（URL + 抓取的哈希行）自动落到 notes，避免只剩结论。
3. conan-verify/CI 之后**自动校验 conandata.yml 与 HEAD 逐字节一致**（本包已确认门禁会原地改写镜像列表/预下载路径），当前要人工 `git diff` 才放心。
4. **共享 conan 锁排队可见化**：`ps` 轮询只能看到「忙」，建议 submit/verify 前打印持有者与预计剩余时间，减少空等（本包最后一次复跑因等待 6 分钟未执行）。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

已提交 3 条草稿（`knowledge/drafts/DRAFT-8543-*`）：plain char 承接 EOF 导致无出口挂起、conandata 注释 URL 被预下载改写、refresh-patch 改名与 conandata 脱钩。建议评审在提升为 E-entry 时补充两条同类可归并项：
1. 「Makefile 只读 `$(CC)`/自定义变量、不读 CFLAGS/EXTRA_CFLAGS」——用编译选项做对照实验时，若通过 make 变量注入会静默失效并得出**相反结论**（本包实测踩过，`make NEXUS_NAPI=-fsigned-char` 根本没生效，改用直接调用编译器才拿到正确对照）。
2. 「能力清单以交付物实际宣传/行为为准」——上游源码的文件头注释（looktxt.c L70 只列 7 种格式）与 `--help` 实际清单（8 种）不一致，文档照抄注释即错。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: kasumizawa-miyuu
- **邮箱**: 241250031@smail.nju.edu.cn
- **Agent ID**: 9C4A
- **生成时间**: 2026-09-19 23:41:00
- **PR 编号**: 11244
- **Git Commit**: 98ba6756c
