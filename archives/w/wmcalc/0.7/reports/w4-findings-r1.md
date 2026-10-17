# wmcalc/0.7 W4 独立审计（r1）— 审计棒 z74-wmcalc-w4 / B 机

**verdict = pass**（P0=0、P1=0、P2=2、P3=7）· bound_head = `9aa56c34ec6e5906821902de3cf31774c77bbd39`
取证件：本目录 `diag1.clean.txt`、`w3-local-ci.log`、`conan-verify-report.md`、`finish-2.log`、`fill_ci.py`、`recipe/`（= `git ls-files archives/w/wmcalc` 10 件原样）。

## 0. 坐标复验
- `git rev-parse HEAD` = `ls-remote origin refs/heads/feat/wmcalc-0.7` = `9aa56c34ec…` ✅；提交 2 枚：`bd24fea1b0`（配方）、`9aa56c34ec`（仅 `notes.md` 19+/2-）。
- PR 净 diff `origin/main...HEAD` = 恰 10 件，全在 `archives/w/wmcalc/`（`diag1.clean.txt:5-20`，812 insertions）。
- CONAN_HOME `~/tmp/ch/home-wmcalc`；证据 `~/tmp/uc2/z74-wmcalc/`（含 official-1/2/3.tar.gz、log-*.txt、create-1..3.log、finish-1/2.log、fill_ci.py）。

## A. W2 结构 / 取源 — 通过
- `0.7/conandata.yml:7-9` 只有 1 条 `sources.url` = 官方址 `https://www.dockapps.net/download/wmcalc-0.7.tar.gz`，无 `patches` 段、⛔ 池址/镜像/`file://`。
- sha256 **设备侧（B 机）实算**：`sha256sum official-{1,2,3}.tar.gz wmcalc_0.7.orig.tar.gz` 四枚全 = `422705d41c2d3a7ff5b88da758a73003fb4dfbab8649e7146bde426cec784040`，与声明逐字一致（`diag1` [sha src] 段）。池件同值 = 同一文件，仅交叉校验，未进 conandata ✅。
- `conanfile.py:97` `package_type="application"`、`:289-293` `libs/includedirs/libdirs` 清空 + `bindirs=["bin"]` + `resdirs` ⇒ 与 dockapp（只交付可执行 + 数据件）事实一致；`commands.json:5` `"type": "tool"`、`:7-10` 版本 0.7/`binary: true`。
- **零补丁属实**：`patches/` 为空目录（`ls -a` 只有 `.`/`..`）、`manifest.yaml:45/47` `patches_applied: []` / `patch_classification: []`（无模板残值）；`conanfile.py:102/243` 的 `export_/apply_conandata_patches` 是 G1 字面要求（`conan-verify-report.md:24-25` ✅ 两项）。
- ⚠ P3-06：`notes.md:77` 写「`patches/` 不存在」，磁盘上是**空目录**。

## B. 测试质量（rule4/rule12）— 通过
- 上游申报 0 的一手依据复算：`configure.ac` 只有 `AM_INIT_AUTOMAKE([foreign])`/`AC_CONFIG_SRCDIR`/三个 `PKG_CHECK_MODULES(X11|XEXT|XPM)`/`AC_SEARCH_LIBS([pow],[m])`/`AC_CONFIG_FILES([Makefile])`（设备 grep，`diag1` [13] 段），**无测试宏**；`Makefile.am` `grep -c check` = 0；发布包 `find -type f` 恰 **30** 个文件（实拍清单已入 `diag1` [13]：4 `.c` + 6 `.h` + 3 `.xpm` + 1 `.xbm` + autotools 生成物 + README/COPYING/ChangeLog/wmcalc.1/wmcalc.conf/wmcalc.desktop/wmcalc.png），无 `tests/`/`test/`/`t/`、无 `test_*`/`*_test`。
- 消费者 6 条**真执行产物**：`w3-local-ci.log:355` `Running test()`、`:357-362` A1-A6 全 PASS、`:363` `SUMMARY assertions=6/6 passed, 0 failed`。A2/A4/A5 走 `show_usage()`（`wmcalc.c:836-850` 实拍 `printf(" %s %s\n",app_name, PACKAGE_VERSION)` + `exit(OKAY)`，`:138/:146` 调用点在 `XOpenDisplay` 之前）⇒ 版本串来自编译期宏，非脚本回显。
- **A6 是真失败形态、不吞错**：`test_wmcalc.sh:71-73` 要求 `rc != 0` **且** 输出匹配 `display`；一手代码链 `wmcalc.c:153-154` → `error_handler(ERR_X_DISPLAY, …)` → `:895` `Could not open display on %s` → 尾 `exit(err_code)`；`wmcalc_err.h:25` `ERR_X_DISPLAY 1105` ⇒ shell rc = 1105 & 0xFF = **81**（实测 `rc=81`）。无「跳过即通过」。
- 鸿蒙特有能力面 ≥1 且分母如实：A6 即「设备无真实 X display」这一平台能力面；申报口径为「上游 0 + 消费者 6」，未写「上游测试全通过」。
- ⚠ **P2-02**：`notes.md:123-125`（及 `test_wmcalc.sh:3-5`）申报「同口径四处」含 `reports/test-report.md` —— 实测该文件 **不存在**（其余三处 `MANIFEST.yml:30`、`notes.md:121-122`、`manifest.yaml:59` 与日志逐字一致）。
- ⚠ **P3-03**：`notes.md:106` 写 `exit(81)`，与 `ERR_X_DISPLAY=1105` 表面矛盾（真值来自 8 bit 截断），推导未落文。

## C. W3 证据自洽 — 通过
- `sha256sum archives/w/wmcalc/0.7/reports/w3-local-ci.log` = `655d6a6255a9d7f68a200a4aaee602913031847d2ee32a03ba2f30178ecbd0ed` == `.ci-result.json.log_sha256` **逐字相同**；`exit_code=0`、`integrity_hash=ff83811d6752d58b`。
- 真跑判据在位：`w3-local-ci.log:209` `wmcalc/0.7: Building from source`、`:219` `wmcalc/0.7: Calling build()`、`:392` `All packages built and tested successfully ✅`。
- JC 模式：`:76` `检查模式: incremental (10 个文件)`、`:86` `JC5: archives 隐藏文件白名单检测...`、`:95` `JC_RESULT=pass`。⇒ **P3-09**：委托方「第一轮回落 full 命中他包 cloog/kics 而红」的叙述在 notes/日志中**无载体**（`cloog|kics|全量|full` 0 命中），不作为缺陷，但不得当已证事实转述。
- HEAD 绑定（`.ci-result.json` 无 HEAD 字段）以**配方不变性**传递：`git diff --name-only bd24fea1..9aa56c34 -- archives/w/wmcalc/0.7/conanfile.py archives/w/wmcalc/0.7/conandata.yml | wc -l` = **0**（`diag1` [2]），第二枚提交只动 `notes.md`（[3]）。
- profile 复验（委托方留的雷）：`~/tmp/ch/home-wmcalc/profiles/` **现在仍为空**（`ls -la` 只有 `.`/`..`；`find` home 顶层无 default）⇒ 唯一来源是显式 `-pr:h/-pr:b` 指仓库件 `ci/conan/profiles/ohos-aarch64`（sha256 `7ebd43d28468fe5795bd149ccf81b42429eb5ef63965914388eea2e9d711b793`，`git status` 未显示改动），W3 日志 `:7-8`（Importing profile 绝对路径）与 `:11/:18`（`profile: ohos-aarch64`）实拍使用 ⇒ 叙述成立，`notes.md:8/150-151` 的警示如实入文，无「已发布误判成未发布」的痕迹。
- ⚠ **P2-01**：`0.7/manifest.yaml:56` `log: "reports/conan-create-log.md"` 指向不存在文件（实物 `reports/conan-create.log`，`conan-verify-report.md:33` 亦如此）。
- ⚠ P3-04/05：`conan-verify-report.md:8-15` G0 披露「已知风险 E490 未在配方中处理」而 notes 未交代为何不适用（配方用 `/system/bin/sh` 承载 configure，`conanfile.py:140-150/220-224`，且 `:275-285` 交付件硬校验通过）；`:42-49` L2/L4/L5 实为 `⏭️ 跳过（无 cache 路径）`，汇报口径「✅」需改述。

## D. harness 回写与杂件 — 通过
- 占位符全包扫描 `pending|TODO|占位|\{[A-Z_]+\}|xxxx|FIXME|PLACEHOLDER` ⇒ 命中 2 处且均噪音：`reports/w3-local-ci.log:53-54`（KC2 检查名，`reports/` 被 ignore）、`.knowledge-done:2` `pending=0`（门禁件）。`build_system: autotools`、`type: tool`、`patches_*: []` 皆实值，无 `{BUILD_SYSTEM}`/`auto`/`pending`/空串；唯一空串 `conanfile.py:95 url = ""  # CI fills this` = 仓库约定（`archives/` 内 `grep -rl "CI fills this" | wc -l` = **1269** 先例）。
- `git ls-files -o --exclude-standard -- archives/w/wmcalc | wc -l` = **0** ✅；运行时件逐件 `check-ignore -v`：`.ci-result.json`→`.gitignore:238`、`.build-closed`→`:247`、`.conan-verified`→`:174`、`.handoff.json`→`:254`、`.knowledge-done`→`:255`、`ci-metadata.json`→`:213`、`test_package/conanbuild*.sh`→`:184`、`reports/`→`:96`、`packaging/`→`:2` ✅。
- ⚠ P3-08：worktree 有**他包**未提交回写 `M archives/l/libXext/{README.md,manifest.yaml}` 与根级 `?? .build-cache/`（check-ignore 均 NOT-IGNORED）⇒ 不在本 PR 的 10 件内，让渡后复用本 worktree 时勿顺手 `git add`。

## E. B 证据三问（只交证据，不下 B 结论）
候选机理：「`AC_ARG_VAR` 值写在 configure 命令行 ⇒ 引号被 `config.status` 原样烘进 Makefile ⇒ clang 收到单个带引号 `-I` 并静默忽略，症状只是 `X11/Xlib.h: No such file`」。委托方自述只扫 `knowledge/graph/*.kv` ⇒ 本窗升为**全 `knowledge/` 树 + `archives/*/*/*/*.md`**：

| 检索 | 命中 | 关键样本 |
|---|---|---|
| `grep -rl AC_ARG_VAR knowledge/` | **2 文件**（12 行） | 全部落在 `knowledge/drafts/DRAFT-libxp-1.0.4-configure-pkgconfig-printproto-module-removed.{md,kv}`；graph/ 544 条目内 0 |
| `grep -rn "静默忽略\|silently ignore\|带引号\|原样" knowledge/` | 21 | DRAFT-12801-keepkey(py2 `__metaclass__` 静默忽略)、E287、DRAFT-6050 —— 无一条涉及 Makefile 引号烘入 |
| `grep -rn config.status knowledge/` | 509 | E011（`umask 077→022`，= 本包问题 3）、E052（HMDFS 临时目录）—— 均不覆盖该机理 |
| `grep -rn "X11/Xlib.h" knowledge/` | 26 | DRAFT-ohos-egl-headless `.kv:37`、DRAFT-irsim-9.7.104 `.kv:13`（error_signature `X11/Xlib.h.*file not found`） |
| `grep -rn CPPFLAGS knowledge/` | 287 | E065（export CPPFLAGS 补 -I）、E467（AutotoolsDeps 污染 conftest ⇒ rc=77）、DRAFT-E571 `:52`（`clang -I"$…" ` 带引号写法） |
| `ls knowledge/*.tsv knowledge/index*` | **0（文件不存在）** | 审计书里的 `index.tsv` 在本仓不存在；已改按目录全扫 |
| archives 同症状先例 | 3 | `archives/b/baka/2.0.4/notes.md:36`（`.pc prefix=/` 使 `-I` 失效 ⇒ CPATH，且「CPATH 必须冒号拼接，conan 空格拼接多路径导致整个变量失效」）、`archives/a/actiona/3.11.1/conanfile.py:176-185`、`archives/b/barrier/2.4.0/notes.md:63` |
| 同逃逸口的既成先例（archives 层） | 2 | `archives/a/adcli/0.9.2/conanfile.py:261` `pre-set KRB5_CFLAGS/KRB5_LIBS (AC_ARG_VAR precious variables…)`、`notes.md:80` |

- **近似命中读原文判因**：`DRAFT-libxp-1.0.4-*` 的因是「`printproto.pc` 模块从生态消失/并入新包」，解法姿势是 `env.define("XPRINT_CFLAGS", …)`（第 124 行，即**环境变量注入**，与 wmcalc 同形），全文无「命令行写值 ⇒ 引号烘进 Makefile ⇒ 静默忽略」这层机理 ⇒ **不同因**（委托方叙述成立）。
- 但**同症状家族**确有既成条目：`knowledge/doc/E075.md`（签名含 `fatal error:.*\.h: No such file`，根因是 `C_INCLUDE_PATH` 使 pkg-config 过滤 `-I`，方法 env-var-remove，不同因）+ DRAFT-irsim-9.7.104 同签名 ⇒ 是否按「家族命中」升 B，交主窗按 `手册/03` 裁。
- ⚠ **P3-07**：`notes.md:179` / `manifest.yaml:69` 的 `knowledge_ref: 无` 依据文字只写了 `knowledge/graph/*.kv`，需改写为全树依据并披露 E075 与 archives 同症状先例。
- **dockapp/XPM 先例一致性**：`archives/a/asmix/1.5/conandata.yml:10` 明写补丁因由「libxpm 未发布：移除 XPM 图标依赖」，`patches/0001-asmix.c.patch:14/41/43/182` 实拍剔除动作；wmcalc 的「libxpm/3.5.17 已发布 ⇒ 不剔 XPM」与先例的**条件互补、不打架** ✅。

## F. 门禁 / 仓库约定 — 通过
- `commands.json` 形状被 L0k 接受：判据实现 `ci/conan/hooks/pre-commit:335-385`（`check_commands_json`：仅当 conanfile 含 `bindirs` 或 `package_type="application"` 才强制；要求软件级 `commands.json` 存在、`type=tool`、name/版本匹配），本包在 W3 中实跑通过：`reports/w3-local-ci.log:38` `[step] L0k: Checking commands.json for CLI tools (R38)...` → `:39` `[ok] commands.json valid (type=tool)`；同轮 `:53-54` KC2 占位符检测通过、`:95` JC_RESULT=pass。
- 软件级 `archives/w/wmcalc/manifest.yaml`（26 行，含 `key_points` 5 条与 `common_dependencies` 4 条）与版本级 `0.7/manifest.yaml` **齐**，二者 `source.url`/`sha256`/依赖四件逐字一致；`README.md`（57 行）与本版本一致（81、6 条、零补丁、依赖轨、`/tmp`+`/etc` 局限均如实）。

## 收口前最欠（≤3 件，均不阻塞让渡）
1. **W4-r1-01/02（P2）**：把 `manifest.yaml:56` 的 `reports/conan-create-log.md` 改成实物名，并把 `notes.md:125` 的「四处」改成实际三处（或补出 `reports/test-report.md`）。纯文字改，不动配方 ⇒ 不触发 W3 重跑。
2. **W4-r1-03/07（P3）**：`notes.md:106` 补 `exit(1105) → rc = 1105 & 0xFF = 81` 一行；`knowledge_ref: 无` 的依据从 `graph/*.kv` 改写为全树（并披露 E075 同签名家族与 baka/actiona/barrier/adcli 先例）。
3. **W4-r1-04（P3）**：`notes.md` 注意事项补一句 E490 为何不适用（`/system/bin/sh` 承载 configure + 交付件硬校验 + create rc=0）。
