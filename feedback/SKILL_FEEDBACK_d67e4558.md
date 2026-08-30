# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_d67e4558.md`

---

## 背景

- **软件名称**: ding-libs
- **版本**: 0.7.0
- **构建日期**: 2026-08-29
- **构建系统**: autotools
- **上游仓库**: https://github.com/SSSD/ding-libs/releases/download/0.7.0/ding-libs-0.7.0.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 14
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
| build | 编译构建 | 成功 | 构建系统: autotools |
| conan-verify | 配方验证 | 通过 | G1/G2/G3/G4 全 PASS（2026-08-29 18:01 复验） |
| finish | 归档收尾 | 完成 | | 
| submit | PR提交+AI检视+CI | 完成 | PR #7133；AI Review 阶段 3；bot 意见 3 条已逐条回复 |

### 失败与问题

- **1**: 根因=Autotools 无法识别设备系统, 解决方案=上游 `config.guess/config.sub` 不认识 HarmonyOS 与 `aarch64-unknown-linux-ohos`
- **2**: 根因=configure 临时文件创建失败, 解决方案=HMDFS 对 `umask 077` 生成的目录权限组合不兼容
- **3**: 根因=Check 头文件未找到, 解决方案=上游 dhash 测试目标的 CFLAGS 变量拼写错误且子目录规则未继承 Check flags
- **4**: 根因=Check fork/临时文件测试失败, 解决方案=OHOS 设备的临时目录和 fork 行为与 Linux 不同
- **5**: 根因=INI/path 测试的权限与诊断字符串不同, 解决方案=HMDFS 归一化文件模式；musl/系统路径与 Linux 不同
- **6**: 根因=`open_memstream` 最终大小未发布, 解决方案=OHOS libc 在 `fclose` 前不会自动暴露最终 buffer size
- **7**: 根因=Conan Autotools 工具的 Perl 扩展加载失败, 解决方案=Conan `perl/5.42.2` 的 `Cwd.so` 与设备 Perl ABI 不匹配
- **8**: 根因=Automake 重生成后 OHOS 检测丢失, 解决方案=`--force-missing` 会覆盖已修改的 config.guess/config.sub
- **9**: 根因=`configure: error: working directory cannot be determined`（间歇性，12 次构建中 4 次失败）, 解决方案=OHOS 的 `/bin/sh` 是 toybox ash 且**不导出 `PWD`**，autoconf 在 `CONFIG_SHELL=bash` 下重执行 configure 前跑 `pwd` 探针，bash 只能回退到 `getcwd()`，而 Conan 建好构建树后 HMDFS 上的父目录已不可达 → 配方中显式 `os.environ["PWD"] = self.build_folder`，与仓库内 adms / aribb24 / aircrack 等 37 个配方一致
- **10**: 根因=移除平台宏后回归出 2 个测试失败, 解决方案=重写补丁时从零生成而丢弃了原有 hunk：`path_utils_ut` 的 `_neg` 用例仍指向 `/etc/passwd`（OHOS 的 `/etc` 是符号链接）、`ini_save_ut` 丢了 `cmp -l -b` → `cmp` 的 toybox 兼容改动。**教训：改补丁必须基于原补丁做定向替换，不能整体重生成**

### 知识图谱使用情况

- **引用知识条目**: 无（构建阶段未命中已发布 E-entry，失败均靠现场诊断解决）
- **新增知识草稿**: 9 条
- **引擎命中情况**: 草稿目录 247 条
- **测试统计**: 总计 20, 通过 20, 失败 0, 跳过 0（上游 `make check`）；另 `test_package` 1/1 通过
- **未覆盖的错误模式**: 3 类
  1. **`autoreconf` 重执行 configure 的 `getcwd` 失败**（问题 9）——草稿 `DRAFT-ohos-autotools-configure-re-exec-cwd-env` 已覆盖该模式，但**未进入正式 E-entry**，所以引擎检索不到，只能靠人肉翻草稿目录才发现。这是"草稿已写、图谱未收"导致检索失效的典型。
  2. **HMDFS 权限归一化导致的测试期望值分歧**（问题 5）：实测（umask 022）`0444`/`0600`/`0640`/`0664`/`0660`/`0000` 一律落成 **640**，`0700`→`740`、`0755`→`750`；且**组位实测为 `r--` 而非 `rw-`**。现有 `DRAFT-ohos-hmdfs-owner-check-fails` 只覆盖 owner 检查，未覆盖"测试期望权限位"这一类。
  3. **toybox 命令参数面窄**：`cmp` 不接受 `-b`（问题 10 复现）、`sed` 为 toybox 0.8.12、无 `flock -c`。现有条目散落在各个软件草稿里，没有统一的"toybox 与 GNU coreutils 参数差异"入口。

### AI 检视结果

- **检视阶段到达**: 3（`review_phase: 3`，PR #7133 已产出结构化检视意见）
- **变更摘要评估**: bot 给出 1 条 High + 2 条 Medium。High 指向 `patches/` 中出现 `#ifdef __OHOS__` 平台宏（认为违反 R8）；2 条 Medium 分别针对 `0009-ini_parse_ut.c`、`0005-ini_config_ut.c` 的权限期望值改法，建议改用 `fstat` 回读实际模式作为期望值。
- **检视意见数量**: 3（bot）；另有提交者本人先前的 4 条自我回复
- **检视意见处理**: 
  - **R8（High）— 采纳并已整改。** 复核后确认 `references/iron-rules.md:265` 是权威口径（"源码中可以使用，但 **patches/ 补丁文件中不应引入** `#ifdef __OHOS__`"），而 `SKILL.md:338 §1.3` 与 `.gitcode/review-memory.md:41` 的表述与之冲突且更宽松。按"门禁取严"原则整改：9 个补丁重写为平台无关实现——
    - gettext 组（`0007`/`0008`/`0010`/`0013`）：`#ifdef __OHOS__` 改为标准 `#ifdef ENABLE_NLS` 守卫（配方已带 `--disable-nls`，`config.h` 里 `ENABLE_NLS` 本就未定义），并为 `path_utils.h` / `path_utils.c` 补 `#include "config.h"`，让头文件自身自洽；
    - 权限组（`0004`/`0005`/`0009`/`0011`）：保留上游期望 mode 不动，只给 `access_check` 传 mask 限定比较位（0440/0640/0600/0640），并补一段说明 HMDFS 归一化的注释；
    - `0014`：探测目标从 `/etc/passwd` 改为 `/usr/bin/env`（OHOS 的 `/etc` 是符号链接，`find_existing_directory_ancestor()` 不解链接），`_neg` 用例同步改；
    - `0001-build-config.guess` **保留** `__OHOS__`：该处位于生成的 C 探针程序内部、紧邻上游自己的 `__ANDROID__` 分支，作用是识别 libc 本身，无 POSIX 等价替代，已在 PR 上说明理由。
    - 结果：补丁后源码 `.c`/`.h` 中 `__OHOS__` 命中数为 0（仅 `0001` 的生成探针除外），`make check` 仍 20/20、`conan-verify` G1–G4 全 PASS。
  - **P2 destroy 签名（bot 附带论断）— 不采纳，已举证反驳。** bot 称 destroy 系列为双指针，实际 `ini_configobj.h:512` 为 `void ini_config_destroy(struct ini_cfgobj *)`、`:617` 为 `void ini_config_file_destroy(struct ini_cfgfile *)`，均单指针；仅 `:2077` 的 `ini_errobj_destroy(struct ini_errobj **)` 是双指针。
  - **fstat 回读方案（2 条 Medium）— 部分采纳。** 平台宏已按 R8 移除（这部分意见成立）；但 fstat 方案未采纳：`chmod` 后 `fstat` 回读再拿回读值当期望值，断言退化为永真，测试失去意义。改用上游 `access_check_int()`（`ini/ini_fileobj.c:1521`）与 `config_access_check()`（`ini/ini_metadata.c:380`）**已有的 mask 参数**——语义是"要比较哪些位"而非"忽略哪些位"（`else mask &= ...; if ((mode & mask) != (st_mode & mask)) fail`），本就是为这类差异准备的正规接口。
  - 7 条 PR 回复（3 条回复 bot + 4 条更正提交者自己先前基于错误口径的回复）已全部发布。

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（RC=0，1/1 包；L0 pass / L1 pass / L2 skip（无 bin/）/ L4 warn（补丁中含危险函数，非阻塞）/ L5 pass）
- **远程 CI (PR 校验)**: 待复跑——整改提交 `4432b42d76` 已推送到 `origin/feat/ding-libs-0.7.0`，尚未针对该提交触发新一轮 CI
- **CI 失败原因**: 无（首轮 W3 本地 CI 于 2026-08-29 14:49 通过）

### 效率分析

- **HANDOFF 次数**: 0（事件时间线仅 `skeleton_created` / `skeleton_exists`，无 step_failed）
- **重试次数**: 构建 4 次失败重试（均由问题 9 的间歇性 `getcwd` 失败引发）；补丁回归后重跑 2 次（`make check` 从 18/20 修回 20/20）
- **关键瓶颈**: 
  1. **问题 9 的间歇性**最耗时间——表现为随机失败而非必现，`/bin/sh` 不导出 `PWD` 这一点必须实测 `env | grep -c "^PWD="` 才能定位，光看报错信息会误判成 HMDFS 权限问题；
  2. **补丁重写的回归**——从零生成补丁丢弃了 2 个必需 hunk，且测试日志不在 `ini/`、`path_utils/` 子目录而在 build-release 根目录，找日志本身花了时间；
  3. **R8 口径三方冲突**——`iron-rules.md` / `SKILL.md §1.3` / `.gitcode/review-memory.md` 说法不一，仲裁需要先确定信息源优先级再动手改代码。
- **耗时较长的步骤**: 
  - `build`（autotools bootstrap + `make check`，`make -j1` 固定并行度）
  - 检视意见整改轮（9 个补丁重写 + 全量复验 + 7 条 PR 回复）
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 5 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-08-29T13:57:02 | skeleton_created | result_partial |
| 2026-08-29T14:41:45 | skeleton_created | result_partial |
| 2026-08-29T15:57:13 | skeleton_exists | resume_pr_exists |
| 2026-08-29T18:21:29 | skeleton_exists | resume_pr_exists |
| 2026-08-29T18:51:40 | ci_passed | PR #7133 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **统一 R8 口径，消除三方冲突。** 现状：`references/iron-rules.md:265` 明确"源码可用、`patches/` 不可用 `#ifdef __OHOS__`"，而 `SKILL.md:338 §1.3` 只要求"有实质适配逻辑"、不区分源码与补丁，`.gitcode/review-memory.md:41` 则更宽松（两处都允许）。三者并列时，适配者会按最宽松的一份执行，检视 bot 按最严格的一份扣分——本次 PR 的 High 意见正源于此。建议：在 `SKILL.md §1.3` 直接写明"以 `references/iron-rules.md` 为准，且 `patches/` 属禁止面"，并给 `review-memory.md` 加一行反向指向，避免形成第二份真相。
2. **给 R8 补一个"合规改造路径"清单。** 目前只说"不能用平台宏"，没说改用什麼。本次摸出的三条通用替代可以制度化：`ENABLE_NLS` 守卫替代 gettext 宏、用上游已有的 **mask/flag 参数**缩小比较面替代"按平台改期望值"、用**无争议的探测目标**（`/usr/bin/env` 而非 `/etc/passwd`）替代路径假设。把这类"平台无关改写模式"沉淀进 `knowledge/operations/ohos-adaptation-patterns.md`，能显著降低"为了过检视而写宏"的比例。
3. **检视意见应区分"门禁违规"与"实现建议"。** 本次 bot 把 R8（有明文规则、可判定）与 fstat 方案（无明文、属风格建议）都标成必改，适配者难以判断哪些可以让步。建议检视模板给每条意见标注 `rule_ref`（有出处）或 `suggestion`（无出处），后者允许合理拒绝。

### 模板改进

1. **conanfile 模板内置 HMDFS `PWD` 处理。** 本次问题 9 需要手动加 `os.environ["PWD"] = self.build_folder`，而仓库里已有 37 个配方重复写了同一段（adms / aribb24 / aircrack / atari800 / backuppc-rsync …）。建议直接进 `templates/conanfile-autotools.py.tmpl`，或在 `Autotools` 调用点统一注入，省掉每次踩坑再抄。
2. **test-report 模板补"平台宏审计"字段。** 建议增加一行 `patches/ 中 __OHOS__ 命中数` 与 `补丁后源码 .c/.h 中 __OHOS__ 命中数`，由 `conan-verify` 自动填充。本次是靠手工 grep 验证的，做成门禁字段可避免回归。
3. **pr-body 模板补"检视意见整改"小节。** 当 PR 进入整改轮后，正文应有一节列出"意见 → 采纳/不采纳 → 理由/证据"，与本次在评论区写的内容同源。现在正文一旦提交就与评论区脱节，reviewer 没法一眼看到整改进展。

### 自动化补全

1. **补丁改写必须提供 diff-based 校验。** 本次从零重生成补丁导致静默丢弃 2 个 hunk、`make check` 从 20/20 掉到 18/20。建议提供 `ohc patch-refactor` 类工具：输入"原补丁 + 定向替换规则"，输出新补丁并**自动 diff 出新旧补丁的 hunk 集合差异**，丢失 hunk 直接报错，而不是等到测试红才发现。
2. **测试日志定位应统一。** `path_utils_ut.log` / `ini_save_ut.log` 不在对应的 `ini/`、`path_utils/` 子目录，而在 build-release 根目录，`make check` 失败后要手动找。建议 `finish` 阶段自动收集所有 `*.log` 汇总到 `archives/<l>/<sw>/<ver>/reports/test-logs/`。
3. **`configure` 重执行环境的自动加固。** 问题 9 的根因是 toybox `sh` 不导出 `PWD`。建议在 `ohc init-build` 时就对目标构建环境探测一次 `env | grep -c '^PWD='`，为 0 则自动在配方注入 `PWD` 修正，而不是等间歇性失败后再诊断。

### 知识图谱覆盖

建议新增 3 条 E-entry：

1. **`CONFIGURE_REEXEC_GETCWD_FAILED`**（对应问题 9）：现象 `configure: error: working directory cannot be determined` 并伴随大量 `shell-init: error retrieving current directory: getcwd: cannot access parent directories`，且**间歇出现**。根因：OHOS `/bin/sh`（toybox ash）不导出 `PWD` → autoconf 在 `CONFIG_SHELL=bash` 下重执行前跑 `pwd` 探针 → bash 回退 `getcwd()` → HMDFS 父目录不可达。定位命令 `env | grep -c "^PWD="`（返回 0 即为本症）。修法：`os.environ["PWD"] = self.build_folder`。**现有草稿 `DRAFT-ohos-autotools-configure-re-exec-cwd-env` 已写好，建议转正。**
2. **`HMDFS_MODE_NORMALIZATION_TEST_EXPECT`**（对应问题 5）：现象为 `access_check` / `chmod` 相关测试失败，实际模式与请求模式不符。实测归一化表（umask 022）：`0444`/`0600`/`0640`/`0664`/`0660`/`0000` → `640`；`0700` → `740`；`0755` → `750`；组位实测 `r--`。**注意：AGENTS.md「知识库已知过期与冲突」表中的 HMDFS 条目记录的是 `700→760`、`000→660`、组位 `rw-`，与本次实测不符，该条目已过期需更正。** 修法：优先用上游 mask/flag 参数缩小比较面，不要改期望值也不要 fstat 回读。
3. **`TOYBOX_COREUTILS_ARG_GAP`**：OHOS 的 toybox 版 `cmp` 不接受 `-b`、`sed` 为 0.8.12、`flock -c` 不支持、`/bin/sh` 无 `[[ ]]`/数组/`pipefail`。目前散落在各软件草稿中，建议收敛成一条按命令索引的对照表，测试类补丁尤其高频命中。

---

## 作者

- **姓名**: Awstme
- **邮箱**: awstme@qq.com
- **Agent ID**: 97E0
- **生成时间**: 2026-08-29 14:41:45
- **PR 编号**: 7133
- **Git Commit**: 4432b42d76
