# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_943ae30c.md`

---

## 背景

- **软件名称**: libgtop2
- **版本**: 2.41.3
- **构建日期**: 2026-09-21
- **构建系统**: autotools（tarball 内含预生成 `configure`，无 meson.build）
- **上游仓库**: https://gitlab.gnome.org/GNOME/libgtop（tag `2.41.3` = commit `526a51698173535312f6cab1408ac9a225063c9d`）
- **适配路径**: 路径 B（探索性编译 → 配方固化），含 3 个平台补丁
- **补丁数量**: 3（`0001-config.guess.patch`、`0002-config.sub.patch`、`0003-configure.patch`；由 `track-edit scan` + `refresh-patch --auto` 生成，全部 portability 类、无平台宏）
- **编译依赖**: glib/2.88.3、proxy-libintl/0.5、pkgconf/3.0.6
- **最终状态**: built（conan create / conan-verify / finish W3+W5+W2 全绿；按约定停在提交前，未 commit/push/PR）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 官方源 sha256 `775676df…da8c`，754028 B；`errors=0, warnings=3` |
| lang-preflight | 语言预检（R47） | 完成 | `task=cpp, detected=c`（C 与 cpp 同族，不迁移） |
| build | 编译构建 | 成功 | 构建系统: autotools；`configure`/`make`/`make install` 全 exit 0（迭代 7 处平台问题，见下） |
| conan-verify | 配方验证 | 通过 | `Verdict: PASS`（G0/G1/G2/G3/G4 全 PASS；L2/L4/L5 因取不到包缓存路径跳过） |
| finish | 归档收尾 | 完成 | step5 W3 ✅、step7 W5 ✅、step9 W2 ✅、step10 submit 就绪 ✅，`status=built`，exit 0 |
| submit | PR提交+AI检视+CI | 未执行 | 按任务约定停在提交前；AI Review / 远程 CI 未触发 |

### 失败与问题

上游 tarball 在 OHOS 上共触发 7 处真实失败，逐一记录根因与最小修复（详细命令/输出/退出码见 `archives/l/libgtop2/2.41.3/notes.md` 的 F1–F7 表）：

| # | 首个真实错误 | 根因 | 修复 |
|---|---|---|---|
| F1 | `config.guess: unable to guess system type` | config.guess(2023-06-23) 无 HarmonyOS 分支（E007） | 补丁 0001 |
| F2 | `Invalid configuration 'aarch64-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | config.sub 不认 `ohos`，kernel-os 白名单缺 `linux-ohos*`（E072）；`patch-autotools-ohos.pl` 的 "already present" 系误判 | 补丁 0002（第 3 处人工补） |
| F3 | `cannot run C compiled programs`（`Error loading shared library libgirepository-2.0.so.0`） | configure 需真跑 conftest，缺 glib 的 .so 搜索路径 | 构建期引入 conan run env |
| F4 | `No package 'glib-2.0' found` | `PkgConfigDeps` 的 .pc 未进 `PKG_CONFIG_PATH` | `generate()` 传 `PKG_CONFIG_PATH=<generators>` |
| F5 | `config.status: line 846: ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 上 `umask 077 && mktemp -d` 产出的目录不可写（E011） | 补丁 0003（`umask 077`→`022`） |
| F6 | `read.c:49: incompatible integer to pointer conversion passing 'int' to parameter of type 'const char *'`（`ngettext` 隐式 int） | 源码经 glib 的 `gi18n-lib.h` 无条件 `#include <libintl.h>`，而命中的是 **OHOS SDK sysroot 的空壳 libintl.h**（无 ngettext 声明） | 把 `proxy-libintl/0.5` 提为直接依赖 → Conan 生成的 `glib-2.0.pc` 带 `Requires: intl` |
| F7 | `make install` → `missing: line 81: makeinfo: command not found` / `Error 127` | OHOS 无 texinfo；且补丁刷新 `configure` mtime → `doc/stamp-vti` 判过期 → 触发 texinfo 链；`mdate-sh` 解析失败时 `set` 打印全部变量把 `version.texi` 写成 6094 B 环境转储 | `build()` 在 `apply_conandata_patches()` 前后记录/还原 `configure` mtime |

另有一次门槛误拦（非本包问题）：`finish` 首轮 W3 被 JC1/JC5 拦，拦截对象是 origin/main 中既有的 `archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`（分支无 commit 时 junk_check 退化为整仓 full 模式）。以 CI 同款 prdiff 模式复跑通过。

### 知识图谱使用情况

- **引用知识条目**: E007（config.guess 不识别 HarmonyOS）、E072（config.sub 三元组）、E011（HMDFS umask 077 临时目录不可写）、E212（OHOS 不可用 gobject-introspection）、E490（autotools 辅助脚本可执行位，采纳其建议在 `source()` 补 `+x`）
- **新增知识草稿**: 本任务未手工新增；`conan-verify` 生命周期自动落草稿 3 条（现存于 worktree `knowledge/drafts/`，均已 kv+md 成对）：`DRAFT-libgtop-makeinfo-missing`、`DRAFT-libgtop-glib-libintl-link`、`DRAFT-libgtop-mountlist-mtab-fallback`
- **引擎命中情况**: 草稿目录 1397 条；F5 错误签名的 `engine` 匹配命中 **E011**（Phase B score=6），其余失败按 knowledge_ref 手工定位
- **测试统计**: 上游 20 个 examples 样例 → 通过 19、失败 1（`disk`，`/proc/diskstats` EACCES 平台限制）、跳过 0；test_package 2 用例 / 7 断言全通过（含 1 个鸿蒙特有用例）
- **未覆盖的错误模式**:
  1. `configure: error: working directory cannot be determined`（`getcwd` 失败）—— 出现在 `finish` step3 clean-verify（G0），非阻塞；SKILL v12.17 backlog 已列"autotools configure 重执行 getcwd 失败草稿转正"，本轮再次复现
  2. "补丁刷新 `configure` mtime → `doc/stamp-vti` 过期 → 触发 texinfo(makeinfo 缺失) + `mdate-sh` 解析失败把 `version.texi` 写成 `set` 的环境转储"——知识库未覆盖（仅有上述草稿）
  3. "OHOS SDK sysroot 的 `libintl.h` 是空壳（无 ngettext/gettext 声明），而 glib 的 `gi18n-lib.h` 无条件 include 它"——知识库未覆盖（仅有上述草稿）

### AI 检视结果

- **检视阶段到达**: 未到达（PR 未创建，按约定停在提交前）
- **变更摘要评估**: 不适用——未执行 `submit`，无 AI Review 摘要
- **检视意见数量**: 0（未创建 PR）
- **检视意见处理**: 不适用；已改由本地只读审计（11 项提交前检查）替代，结论：#1–#5、#8–#11 PASS，#6/#7 因**工作树存在非本任务的 `archives/l/libXext` 改动**判 FAIL，故不出具"可以提交"结论

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`reports/w3-local-ci.log`：L0 pass / L1 pass / L1e 反向验证通过 / L2 skip（无 bin）/ L4 warn / L5 pass；`Success: 1`，`Pass rate: 100.0% (1/1)`）；`.ci-result.json` `exit_code=0`，`log_sha256` 与实际日志一致
- **远程 CI (PR 校验)**: 未触发（未创建 PR）
- **CI 失败原因**: 本地首轮 W3 因 junk_check 的 full 模式回退误拦（见"失败与问题"末段），非本包缺陷

### 效率分析

- **HANDOFF 次数**: 2（① `finish` W3 JC full 模式误拦 HANDOFF；② `feedback` 占位符未填 HANDOFF）。手动处理的平台失败 7 处未产生 HANDOFF（探索阶段自行定位）
- **重试次数**: `configure` 4 轮（F1→F2→F3→F4/F5 收敛）、`make` 2 轮（F6）、`make install` 3 轮（F7 的 makeinfo + 时间戳方案对比）、`conan create` 2 次（第 1 次 `package_info()` 要求直接依赖出现在 `cpp_info.requires`）
- **关键瓶颈**: ① F6/F7 两处属于"环境里缺东西（OHOS sysroot 空壳头文件 / 无 texinfo）+ 工具链隐式耦合（configure mtime → texinfo 链）"，定位耗时最长；② W3 的 JC 模式回退使本地门禁无法直接反映 CI 语义，需人工构造 `JUNK_PR_DIFF` 才能复现 CI 判定
- **耗时较长的步骤**: 依赖前置核验（23 包 × `conan download` + `conan install --build=never` 权威复核）、上游 20 个样例逐个运行（其中 `timings` 约 60s，首轮 15s 超时误判为失败）、两次完整 `conan create`（各含 test_package 编译与运行）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-21T02:05:53 | skeleton_created | result_partial |
| 2026-09-21T02:05:53 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`junk_check.sh` 的 full 模式回退会扫到 origin/main 既有垃圾，导致"未 commit 的本地 W3"对任何包必然失败**。脚本以 `git diff origin/main...HEAD` 判模式，分支无 commit 时退化为整仓 `git ls-files`；本轮拦截的 3 个文件（`archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`）均来自 main 的历史 bot PR，与本包无关。建议：full 模式限定扫描范围为"未跟踪文件 + 已修改文件"（即 `git ls-files -o --exclude-standard` ∪ `git diff --name-only`），或在回退时直接打印"未 commit → 建议用 `JUNK_PR_DIFF=<pr.diff>` 走 CI 同款 prdiff 模式"的修复命令。证据：本轮 29 号日志（fail，full）与 31/32/33 号日志（pass，prdiff）；同工作区另一任务的 notes.md 对话 #6 记录了同一坑（说明这是可复现的框架缺陷，不是偶发）。
2. **`finish` 缺少"工作树是否混入非本包改动"的显式告警**。step9 的 W2 检查在本场景输出 `✅ 无变更文件`（因为无 commit/staged），而工作树实际存在 `archives/l/libXext/{README.md,manifest.yaml}` 的异库修改，只能靠人工审计发现。建议 W2/step9 增加一条：对 `git status --porcelain` 中位于 `archives/` 且**不属于当前包**的条目输出 ⚠️ 告警（不阻塞）。
3. **`feedback` 的自动填充字段基本为空**（本轮骨架中 `构建系统: {BUILD_SYSTEM}`、`补丁数量: 0`、`上游仓库: (未知)`、`测试统计: 0/0/0/0`、`本地 CI 模拟: 未知` 全与事实相反）。建议直接从 `manifest.yaml` + `conandata.yml` + `.ci-result.json` + `reports/w3-local-ci.log` 渲染这些字段——目前它们只是模板占位符，反而会误导阅读者（本次需人工全部改写）。

### 模板改进

1. **autotools 配方模板建议内置"补丁 → `configure` mtime → texinfo 链"防护**。`templates/conanfile-autotools.py.tmpl` 目前只做 `apply_conandata_patches()` + configure/make；对任何 tarball 内含 `doc/*.info` + `info_TEXINFOS` 的项目（libgtop2 即是），打补丁刷新 `configure` 的 mtime 会让 `doc/stamp-vti` 判定过期并调用 `makeinfo`（OHOS 无 texinfo），且 `mdate-sh` 解析失败时会把 `version.texi` 写成 `set` 的环境变量转储。建议模板在 `build()` 默认写入"记录/还原 `configure` mtime"的注释块（本轮验证：纯净 tarball + 3 补丁下 configure/make/install 全 exit 0）。
2. **`conan-init` 生成件的质量**：本轮 `conandata.yml` 生成时 `sha256` 为 `REPLACE_WITH_ACTUAL_SHA256`、`manifest.yaml` 生成时 `software: "{software}"` / `build_system: "{BUILD_SYSTEM}"` / `status: published`（字段未渲染、状态还是 published 占位），`test_package/test.c` 为空壳（仅 `printf`，会被 PF3/L0c 拦）。建议生成器把已知值直接渲染，并把 test_package 默认骨架改为"调用被测包 API 的最小断言"（R34 要求），减少每包都要手改的固定动作。
3. **`test_package/MANIFEST.yml` 模板**的 `upstream_tests` 段只有单条 `- file: <TODO>` 示例，对上游有多个可执行入口的项目（本轮 20 个 examples）需要手工扩成 20 条；建议在模板中给出"多入口 + 逐项结果"的表格化写法示例。

### 自动化补全

1. **W3 的 junk_check 模式应由 harness 显式选择**：本地未 commit 时自动以"未跟踪 + 已修改文件"构造等价 `pr.diff` 并设 `JUNK_PR_DIFF`，使"本地 W3 ≡ CI 判定"，消除人工构造（本轮为通过门禁手工构造了 `JUNK_PR_DIFF`，属人工介入环节）。
2. **`conan-verify` 的 G2 失败知识图谱命中**已自动（本轮 F5 命中 E011），但 **F6/F7 这两类"缺东西/隐式耦合"型失败在探索阶段没有自动引擎匹配入口**：建议在 `build`/`init-build` 失败路径也调用一次 `run_engine()`（现仅 conan-verify G2 触发），把"OHOS sysroot 空壳头文件遮蔽""mtime 触发 texinfo"这类模式尽早暴露给 AI。
3. **`examples/` 类上游入口的批量运行脚本**：本轮 20 个样例需人工决定"哪些需要参数（`netload wlan0`）、哪个需要更长超时（`timings` ~60s）"，首轮 15s 超时把 `timings` 误判为失败后又复跑。建议在 `init-build` 或 `finish` 提供一个"发现并逐个运行 noinst_PROGRAMS 样例"的辅助，输出逐项退出码表（R51 所需的统计口径即可直接产出）。

### 知识图谱覆盖

1. **建议新增 E-entry：`autoconf ≥2.70` 项目打补丁后 `doc/stamp-vti` 过期触发 texinfo（OHOS 无 makeinfo）+ `mdate-sh` 失败污染 `version.texi`**。根因：`doc/stamp-vti` 依赖 `$(top_srcdir)/configure`；补丁刷新其 mtime → 重建 `version.texi` → 重建 `libgtop2.info` → 调 `makeinfo`（缺失，exit 127）；且 `mdate-sh` 解析 `ls -L -l -d -n` 失败时 `set \`…\`` 无输出，`set` 打印全部 shell 变量把 `version.texi` 从 103 B 写成 6094 B 环境转储。解法：打补丁前后 `os.stat`/`os.utime` 记录还原 `configure` mtime。已有草稿 `DRAFT-libgtop-makeinfo-missing`（kv+md 成对）可作底稿。
2. **建议新增 E-entry：OHOS SDK sysroot 的 `libintl.h` 为空壳，glib `gi18n-lib.h` 无条件 include 它导致 `ngettext` 隐式声明**。现象：clang 报 `incompatible integer to pointer conversion passing 'int' to parameter of type 'const char *'`（`-Wint-conversion`）。解法（已实测）：把提供带声明 `libintl.h` 的 `proxy-libintl/0.5` 提为**直接依赖**，Conan `PkgConfigDeps` 会在生成的 `glib-2.0.pc` 中补 `Requires: intl`，其 include 目录随 `GLIB_CFLAGS` 进入编译行；符号 `g_libintl_*` 已静态链接进 `libglib-2.0.so`（`llvm-nm -D` 实测导出），无需额外链接参数。已有草稿 `DRAFT-libgtop-glib-libintl-link`。
3. **建议转正"autotools configure 重执行 getcwd 失败"**（SKILL v12.17 backlog 已列）：本轮 `finish` step3 clean-verify 再次复现 `configure: error: working directory cannot be determined`（`getcwd: cannot access parent directories`），属 HMDFS 路径语义限制；建议明确该检查在 OHOS 上"非阻塞、可跳过"并给出提示，避免每次 finish 都当作待处理失败。

---

## 作者

- **姓名**: ran060619
- **邮箱**: ran060619@noreply.gitcode.com
- **Agent ID**: 517E
- **生成时间**: 2026-09-21 02:05:53
- **PR 编号**: —
- **Git Commit**: 42a8cc8fd8
