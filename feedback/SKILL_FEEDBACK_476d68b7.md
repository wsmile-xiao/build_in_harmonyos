# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_476d68b7.md`

---

## 背景

- **软件名称**: jday
- **版本**: 2.4
- **构建日期**: 2026-09-21
- **构建系统**: autotools（configure + automake + libtool 1.5.6，2004/2005 年版本）
- **上游仓库**: https://jday.sourceforge.net/ （源码包 https://downloads.sourceforge.net/sourceforge/jday/jday-2.4.tar.gz）
- **适配路径**: 路径 A（基础适配）+ 知识库扩展（1 条草稿 E543）
- **补丁数量**: 2（均为 autoconf 辅助脚本 portability 补丁，C 源码零修改）
- **编译依赖**:
无
- **最终状态**: 成功（conan-verify 全门禁通过，W3 `.ci-result.json` exit_code=0）

> 上述背景字段中的构建系统、上游仓库、补丁数量、适配路径四项由本人按实修正，
> 自动采集给出的是 `{BUILD_SYSTEM}`、`(未知)`、`0`、`路径 A（基础适配，无补丁）`——详见「自动化补全」节。

---

## 情况

### 执行概要

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | SourceForge 官方源，sha256 与 `.tarball-sha256` 一致 |
| lang-preflight | 语言预检 | 通过 | detected=c，与任务语言 cpp 属兼容族 |
| build | 手工交叉编译 | 成功 | 补齐 config.sub/config.guess 后 `make` 一次通过，C 源码零修改 |
| conan-verify | 配方验证 | 通过（第 4 次） | 前 3 次失败：package_type 约束、构建机缺 cmake、`-static` 条件未成立 |
| finish | 归档收尾 | 完成（2 步警告） | W2/R36/W3 全过；step5b 知识引用警告、step8 gen_summary 崩溃 |
| submit | PR提交+AI检视+CI | 手动旁路执行 | 详见「AI 检视结果」 |

### 失败与问题

1. **`package_type = "library"` 但未声明 `shared` 选项** → `conan create` 在依赖图计算阶段
   直接 `ERROR: Package type is 'library', but no 'shared' option declared`。
   本包固定静态（上游 configure.ac 自注库极小、随包 libtool 1.5.6 无 linux-ohos 共享库规则），
   改为 `package_type = "static-library"` 后通过。
   - **该失败被知识图谱误匹配到 E540（shadow-ci / runner-path-prepend）**，评分高达 2298/15750，
     推荐动作与真实根因完全无关。
2. **构建机缺 `cmake`**，test_package 的 `CMake.configure()` 报 `/bin/sh: 1: cmake: not found`。
   OHOS NDK 自带 `build-tools/cmake/bin/cmake`（3.28.2），软链到 `/data/service/hnp/bin` 即可。
   `init-build` 的环境检查其实早就报了 `⚠️ cmake: 未找到`，但仅是 warning，直到 `conan create`
   跑完整个包构建、进到 test 阶段才失败。
3. **交叉构建机无法执行交付产物**：产物为动态链接 aarch64-OHOS ELF，x86_64 构建机上
   `aarch64-binfmt-P: Could not open '/lib/ld-musl-aarch64.so.1'`。
   解决：上游用例改用同源 `.o` 静态重链副本在 `qemu-aarch64` 下运行；test_package 的测试
   程序改为静态链接，使 `conan create` 的 test 阶段在两种构建机上都能真实执行。
   - 第一版用 `if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")` 做条件，**条件从未成立**：
     profile 两侧同构 → `cross_building()` 为 False → CMakeToolchain 根本没写
     `CMAKE_SYSTEM_NAME`。改为无条件 `-static` 后通过。

### 知识图谱使用情况

- **引用知识条目**: E007 / E072 / E122 / E205（config.sub、config.guess 不识别 OHOS 三元组系列，用于查重与边界比对）
- **新增知识草稿**: 1 条 —— `knowledge/drafts/E543-draft-419E.{kv,md}`
- **引擎命中情况**: `engine` 对 conan 三元组注入问题命中 E205（部分相关）；`conan-verify` 的 G2 失败三次
  全部误命中 E540（无关条目）
- **测试统计**: 上游 26/26 通过；test_package 7/7 通过；跳过 0
- **未覆盖的错误模式**:
  1. conan OHOS profile 两侧同构 → `cross_building()` 为 False → `AutotoolsToolchain` 不注入
     `--host/--build`、`CMakeToolchain` 不写 `CMAKE_SYSTEM_NAME`（已写成草稿 E543）
  2. `package_type = "library"` 必须声明 `shared` 选项——固定静态的包应写 `static-library`，
     知识库无条目，且被 E540 误匹配掩盖

### AI 检视结果

- **检视阶段到达**: PR 创建完成，等待 atomgit-bot 变更摘要与代码检视（异步，未在本次会话内闭环）
- **变更摘要评估**: 待机器人产出后评估；已按「PR 提交纪律」在建 PR 前完成全部交付物，
  建 PR 后不再推送非必要改动
- **检视意见数量**: 待产出（本报告提交时为 0）
- **检视意见处理**: 后续按周期复查任务逐条处理：合理的修复后标记已解决，不合理的回复原因

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`.ci-result.json` exit_code=0，log_sha256 已写入）
- **远程 CI (PR 校验)**: 第 1 轮 **FAILED**（#57604）→ 修复 → 第 2 轮 **FAILED**（不同类）→ 修复后重新触发
- **CI 第 2 轮失败原因**（config.guess 修复已生效，configure 推进到 config.status 才失败）：
  两个**只在鸿蒙真机出现**的文件系统限制，本地 x86 构建机一路全绿：
  1. `./confstatXXXXXX/subs.sed: Permission denied` → Makefile 生成失败。
     autoconf 2.59 的 config.status 用 `mktemp -d` 建临时目录（权限**硬编码 0700**、
     umask 改不动），HMDFS 存在 UID 映射（目录属主 UID ≠ 进程 UID），0700 对本进程不可写。
     对应知识条目 **E011**；注意 E011 的首选方案「把 `umask 077` 改成 `umask 022`」
     对走 `mktemp` 分支的包**无效**，本次实际可行的是去掉 mktemp 分支、用 `mkdir` + `umask 000`。
  2. `make: jobserver mkfifo: Operation not permitted` → `No targets specified`。
     HMDFS 不支持 mkfifo，GNU Make 4.4+ 的 FIFO jobserver 失败。对应 **E074 / E525**，
     处置为 `MAKEFLAGS=-j1` + 显式 `-j1`（先例 `at/3.2.5`、`ace/8.0.5`）。
- **CI 第 1 轮失败原因**: `configure: error: cannot guess build type`。
  **根因是本地 W3 与远端 CI 的构建机不同源**：本地是 x86_64 交叉构建机（`uname -s`=Linux），
  CI worker 是鸿蒙 PC 真机（`uname -s`=**HarmonyOS**、`uname -r`=`HongMeng Kernel 1.12.0`）。
  首版 `config.guess` 补丁只加了 `aarch64:Linux:*:*` 分支，在真机上永不命中，随后 config.guess
  落到兜底逻辑要往 `$TMPDIR` 写 `dummy.c` 做编译探测，在 HMDFS 上 `Permission denied`。
  修复：补 `aarch64:HarmonyOS:*:* | aarch64:OHOS:*:*` 分支（知识图谱 E007 同源）。
  **本地 W3 全绿但 CI 红，且本地无论怎么跑都复现不了**——这是本次最值得记录的一条。

### 效率分析

- **HANDOFF 次数**: 2（`feedback` 占位符 1 次、`finish` 知识整理提示 1 次）
- **重试次数**: `conan-verify` 6 次（3 次因本地问题失败、1 次通过、2 次为 CI 修复后复验）；
  远端 CI 修复轮次 2 次（第 1 轮红 → 修复 → 第 2 轮红（不同类）→ 修复 → 重新触发）
- **关键瓶颈**:
  1. 构建机缺 cmake 未被前置门禁拦住，代价是一整轮 `conan create`（含完整包构建）
  2. 误装 pip 版 cmake 耗时约 10 分钟，而 NDK 里本来就有 —— 环境自检没有指出这一点
  3. **本地 W3 与 CI 真机不同源导致的假阴性**（见「SKILL 设计改进」第 0 条）——
     本次最大的时间成本：两轮远端 CI + 两轮本地复验，三个失败点（E007 / E011 / E074）
     本地一个都复现不了，只能靠 CI 日志倒推，而且是**一轮只暴露一个**（前一个修好才轮到下一个）
- **耗时较长的步骤**: `conan-verify`（每轮完整 `conan create`），其余步骤均为秒级/分钟级

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-21T08:09:52 | skeleton_created | result_partial |
| 2026-09-21T08:09:52 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

0. **W3「本地 CI 模拟」与远端 CI 构建机不同源，且 SKILL 未在任何地方声明这一点——
   这是本次唯一一轮 CI 红的直接成因。**
   W3 在 x86_64 交叉构建机上跑（`uname -s`=Linux），远端 CI worker 是鸿蒙 PC 真机
   （`uname -s`=**HarmonyOS**、`uname -r`=`HongMeng Kernel 1.12.0`、`uname -m`=aarch64）。
   凡是依赖 `uname` / 原生可执行性 / 文件系统语义（HMDFS 权限）的构建逻辑，**本地 W3 恒为
   假阴性**：本次 `config.guess` 只加 `aarch64:Linux` 分支，本地四轮 `conan create` 全绿，
   到了真机直接 `cannot guess build type`。建议两件事：
   - 在 `references/` 里给出**构建机能力对照表**（本地 W3 vs CI worker 的
     `uname -s/-m/-r`、可否原生执行目标产物、`$TMPDIR` 文件系统与权限语义），
     让适配者在写 autotools/uname 相关补丁时能主动对表；
   - 对 autotools 包，在 W3 里加一道**真机 uname 模拟**（PATH 前置一个假 `uname`，
     复刻真机三项输出，跑一遍 `config.guess` / `config.sub` 并要求输出可被规范化）。
     本次修复正是靠手搓这个 mock 才在本地验证了真机分支——这类校验应当由框架提供，
     而不是每个适配者自己想到才做。

   **更进一步：给老 autotools 包一份"真机三件套"静态自查。** 本次两轮 CI 红踩到的
   三个点全部有知识条目（E007 / E011 / E074+E525），却分两轮才试出来，因为它们
   **本地一个都复现不了**。建议在 `prescan` 里针对 autotools 源码直接输出检查清单：
   ① `config.guess` 是否含 `HarmonyOS` 分支（否则 E007）；
   ② `configure` 的 config.status 段是否用 `mktemp -d`（是则 E011，且要提示
   E011 首选的 `umask 022` 方案对 mktemp 分支无效）；
   ③ 配方是否强制 `-j1`（否则 E074/E525）。
   三条都是纯文本可判定，完全可以在**首次提交 PR 之前**一次性拦下来，
   而不是每包消耗两轮真机 CI。

1. **把「构建工具可用性」从 warning 升级为 conan-verify 的前置硬检查。**
   `scripts/ohc/init_build.py` 的 check-env 已经能报 `⚠️ cmake: 未找到`，但只是 warning；
   `conan_verify.py::gate2_conan_create`（scripts/ohc/conan_verify.py:546）直接跑
   `conan create`，包构建完才在 test_package 阶段因缺 cmake 失败。
   建议：G1（配方完整性）之后增加一条 G1b —— 当 `test_package/CMakeLists.txt` 存在时，
   检查 `cmake` 是否在 PATH，缺失则直接 HANDOFF 并提示
   `ln -sf <NDK>/build-tools/cmake/bin/cmake /data/service/hnp/bin/cmake`。
   本次为此多花一轮完整构建 + 约 10 分钟无谓的 pip 安装。

2. **`finish` 的 submit 就绪预检把废弃项与必需项混在一起输出。**
   `finish` step[10/10] 同时报 `❌ test-report.md`、`❌ packaging/`、`❌ .staging-verified` 三项，
   但 `packaging/` 已按 ARCHIVE-SPEC v2.0 废弃，且 `.gitignore:2` 就忽略了 `packaging/`。
   建议：删除 packaging 检查项，或在输出里显式标注「已废弃，忽略」，避免协作者去补一个
   不该存在的产物。

3. **`finish` 会把人工填好的 manifest 字段覆盖回模板默认值。**
   step[1] 的 `refresh-patch --auto` 重写 `patch_classification`，把已填的
   `type: portability` / `guard: '...'` 覆盖成 `type: auto` / `guard: 'pending'`。
   建议：仅在字段为 `auto`/`pending` 时写入，已被人工修改过的不覆盖（或写到单独的
   `patch_classification_auto` 键，人工键优先）。

### 模板改进

1. **`templates/notes.md` 的占位符没有任何门禁校验。**
   生成的骨架含 `{cmake|autotools|makefile|meson|custom}`、`{BUILD_SYSTEM}`、`{software}` 等，
   而 `finish`/`submit` 全链路都不检查它们是否被替换（W2 只查文件存在性）。
   建议：在 `finish` step[5] 的结构检查里加一条
   `grep -nE '\{[a-z]+\|[a-z|]+\}|\{[A-Z_]+\}' notes.md manifest.yaml` 必须无输出，
   与 `feedback` 对自身占位符的处理保持一致。

2. **版本级 `manifest.yaml` 模板缺 `tests:` 小节**，而 R51 要求 PR 如实回填
   上游 N/N′ 与通过率。本次参照 `archives/a/aalib/1.4p5/manifest.yaml` 手写了
   `tests.upstream` / `tests.adapted`，但该先例文件本身末尾两行缩进是坏的（第 43-44 行，
   两条 `- "..."` 悬挂在 `tests:` 下）。建议模板直接给出 tests 小节骨架。

3. **`test_package/MANIFEST.yml` 模板只给了 `upstream_tests` 单条槽位**，
   而实际项目常同时存在「有断言的测试」「只打印的巡检脚本」「其它语言的示例测试」三类
   （jday 分别是 `RunTest` / `Testdbd` / `JdayTest.pl`）。建议模板增加 `category` 字段
   （asserted / smoke-only / not-applicable），让 R51 的清点口径机器可读，而不是靠描述文字。

### 自动化补全

`feedback` 骨架的自动采集在本次有 6 处取值错误，全部需要人工修正（建议逐项修复采集逻辑）：

| 字段 | 自动采集值 | 实际值 | 疑似原因 |
|---|---|---|---|
| 构建系统 | `{BUILD_SYSTEM}` | autotools | 模板占位符未替换，`manifest.yaml` 里 `build.system: autotools` 可直接取 |
| 上游仓库 | `(未知)` | jday.sourceforge.net | 未读 `conanfile.py` 的 `homepage` / `conandata.yml` 的 `sources.url` |
| 补丁数量 | 0 | 2 | 未统计 `patches/*.patch`（目录就在归档里） |
| 适配路径 | 路径 A（基础适配，**无补丁**） | 路径 A + 知识扩展 | 由错误的补丁数=0 推导而来，错误级联 |
| 新增知识草稿 | 无 | 1（E543-draft-419E） | 只统计了 `DRAFT-*` 命名，漏了 `E###-draft-<AgentID>` 命名（两种命名 SKILL.md §5.5 都有登记） |
| 测试统计 | 总计 0 / 通过 0 | 26+7 全通过 | 未读 `reports/test-report.md` 与 `test_package/MANIFEST.yml` 的 `assertion_count` |

此外 **`finish` step[8] `gen_summary` 崩溃**：`gen_summary 失败: 'str' object has no attribute 'append'`，
每次适配都会出现，属实打实的框架缺陷（不过 `SUMMARY.md` 是协作者只读文件，崩溃反而避免了误提交）。

还有一处小问题：`feedback --resume` 的占位符校验是全文纯文本扫描，正文里**引用**占位符字面量
（哪怕包在反引号里、用于描述这个机制本身）也会被判为未填写，导致报告写得越具体越容易卡住。
建议跳过代码块与行内代码（`` ` `` 包裹）内的匹配。

### 知识图谱覆盖

1. **建议采纳本次草稿 `E543-draft-419E`**：conan 的 OHOS profile 被同时用作 `-pr:h`/`-pr:b`，
   `cross_building()` 恒为 False，导致 `AutotoolsToolchain` 不注入 `--host/--build`、
   `CMakeToolchain` 不写 `CMAKE_SYSTEM_NAME`。已有 E007/E072/E122/E205 只覆盖
   「config.sub/config.guess 不认识 ohos 三元组」，未覆盖这个 conan 侧成因，
   且 E205/E122 的「禁止 `--build/--host`」口径会把交叉构建机场景一并误伤——
   草稿给出了边界判定命令 `grep -c ac_fn_c_try_run configure`。

2. **建议新增条目：`package_type` 与 `shared` 选项的一致性约束。**
   错误面明确（`Package type is 'library', but no 'shared' option declared`），
   修复也确定（固定静态的包写 `static-library`；提供 shared 的写 `library` + options），
   知识库现无对应条目。

3. **E540 存在明显的误匹配面。** 本次三次 G2 失败（依赖图计算错误、cmake 缺失、
   test 执行失败）全部命中 E540（评分 2298 / 15750 / 3750），而 E540 讲的是
   shadow-ci 的 runner PATH 问题。建议收紧其 `match_keywords`（当前含 `/data/service/hnp/bin/clang`
   这类会出现在**任何** OHOS 构建日志里的通用串），否则它会持续淹没真实根因。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: F69B
- **生成时间**: 2026-09-21 08:09:52
- **PR 编号**: —
- **Git Commit**: 48d9cee684
