# lr 1.5.1 测试报告

> **项目**: lr（"list files, recursively"，递归文件列表命令行工具）
> **任务**: 平台贡献任务 #8564 · 分支 `feat/lr-1.5.1` · 路径 A（基础适配，零补丁）
> **测试日期**: 2026-09-19
> **测试环境**: HarmonyOS 6.1.0.117（HongMeng Kernel 1.12.0，aarch64 / armv8，HAD-W32/W24 真机）
> **编译配置**: clang 15.0.4（OHOS SDK 26.0.0.18 native/llvm，目标三元组 aarch64-linux-ohos），Release，Conan 2.29.1（OHOS 适配版），profile `ohos-aarch64-device`
> **测试类型**: 上游官方测试套件（**0 例，上游不携带测试**）+ 适配补全行为回归（43 条断言）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 | 说明 |
|:----:|:----:|:------:|------|
| 上游测试用例总数 | **0** | — | 上游 tarball 不含任何测试（清点证据见第二节） |
| 上游通过 / 失败 / 跳过 | 0 / 0 / 0 | — | 不存在"上游通过率"，不以任何自建用例冒充 |
| 适配补全回归（test_package，最终脚本） | **43** | 100% | `test_package/test_lr.sh`（A01–A43），真实执行安装后的二进制 |
| 其中 `conan create` 内执行 | 43/43 | 100% | 见本报告第四节引用的 `1..43` / `pass=43 fail=0` 输出 |
| 设备侧独立执行（4 种跑法，与上表同版本脚本） | 43/43 ×4 | 100% | toybox `sh` 与 harmonybrew `bash`，各跑"设置 / 不设置 `LR_PACKAGE_FOLDER`"两种，全部 rc=0；fixture 目录由 `trap` 清理，残留 0 |
| 破坏性自检（本地复刻 CI L1e） | 35/43、36/43 失败 | — | 把 `lr` 换成"空输出且 exit 0"的 stub → 35 条 not ok、rc=1；从 PATH 移除 `lr` → 36 条 not ok、rc=1。证明套件真实依赖被测包，不会因产物缺失而空洞通过 |

**核心结论**: ✅ **通过**。lr 1.5.1 在 HarmonyOS PC（aarch64）上**零补丁**交叉编译成功并可执行；第三节 43 条断言所覆盖的能力（递归遍历与排序、遍历控制、过滤表达式、输出格式与说明符、颜色开关、退出码语义、交付物完整性）在真机实测与上游文档一致。**未纳入断言的上游能力**（`-X` OSC 8 超链接、`-S` stat 风格输出、`-H`、`-x` 跨文件系统边界、`-C [COLOR:]PATH` 自定义着色、`@file` 参数、`-TA/-TC/-TM` 时间戳选择、`%y %l %R %e %C*` 说明符）仅为人工抽查或未验证，不宣称已覆盖。

---

## 二、上游测试清点（R51 第一步：先清点，再运行）

| 清点项 | 结果 | 证据（可逐字复核） |
|--------|------|--------------------|
| 测试目录 | 0 | `tar tzf lr-1.5.1.tar.gz` 共 14 个条目 = 12 个普通文件 + 2 个目录项（`lr-1.5.1/`、`lr-1.5.1/contrib/`）：LICENSE、Makefile、NEWS.md、README.md、`_lr`、contrib/{lr.el,lr.vim,lrls,lrocate}、lr.1、lr.c、lr.png。单一顶层目录，故配方 `strip_root=True` 正确 |
| 构建系统测试目标 | 无 | `grep '^[a-zA-Z_.-]*:' Makefile` → `all:`、`clean:`、`install:`、`FRC:`；无 `test`/`check` |
| 测试框架注册数 | 0 | 无 `CMakeLists.txt`、`meson.build`、`configure.ac`；ctest / meson test / pytest 无可枚举注册项 |
| 文件名匹配 `*test*` | 0 | 解压目录内 `find . -iname '*test*'` 命中 0 |
| 上游文档 | 无测试入口 | `README.md` 的 Installation 一节仅 `make all` / `make install` |

**判定**：上游确实无测试（而非"没有环境跑不了"）。按赛事规则第 6 条补全行为回归套件，清点证据同时登记在 `test_package/MANIFEST.yml` 的 `upstream_test_inventory_evidence`。

---

## 三、适配补全回归明细（43 条，全部通过）

套件在一次性 fixture 目录（`lr-test.$$`，最深 3 级目录、含空格文件名、点文件与点目录、3×1024=3072 字节文件、悬空符号链接）中运行，结束由 `trap` 清理；凡涉及大小、权限、文件系统类型的期望值都**运行时由 `wc -c`/`find`/`awk` 独立反查**，并配负向对照，不写死平台常量。

| # | 断言 | 覆盖能力 |
|---|------|----------|
| A01 | PATH resolves lr to the package bin/ and lists all N entries | 确认执行的是被测包产物（防宿主同名命令串扰），并以其输出条目数与 `find` 独立统计相等作为全套件的非空前置 |
| A02 | default output traverses recursively | 三层递归遍历（`skipme/inner/x`） |
| A03 | the traversal root . is listed | 根条目语义 |
| A04 | default output is sorted by name | 默认排序与字节序全路径排序一致 |
| A05 | `-d` lists only the starting point | 不进入目录 |
| A06 | `-1` does not go below one level | 深度限制 |
| A07 | `-A` hides dot files and does not descend dot directories | 1.5.1 的唯一修复项：`-A` 不再下降隐藏目录（`.hidsub/secret` 不出现） |
| A08 | dot file and dot directory contents are listed without `-A` | 反向对照（`.hidden.txt` 与 `.hidsub/secret` 均在默认输出中） |
| A09 | `-t 'type == f'` selects regular files only | 类型过滤器 |
| A10 | `-t 'type == d'` selects directories only | 类型过滤器（目录） |
| A11 | `-e` filters by basename regex | 快速名称过滤 |
| A12 | filter operator `~~` globs names | fnmatch glob 运算符 |
| A13 | filter operator `=~` matches POSIX ERE | ERE 运算符（lr 字符串不支持反斜杠转义，见 notes 问题表 #5） |
| A14 | filter operator `===` is case insensitive | 大小写不敏感比较 |
| A15 | numeric filter `size > 1000` | 数值属性过滤 |
| A16 | `%s` prints the byte size (3072) | 期望值来自 `wc -c`，与 `stat(2)` 真值一致 |
| A17 | `%d` prints the path depth | 深度说明符 |
| A18 | `%n` and `%i` report links and inode | 硬链接数 / inode 格式与取值 |
| A19 | `%m` octal mode round-trips **and is discriminating** | 模式说明符 + `mode =` 过滤 + 负向对照（`mode = 000` 不得命中） |
| A20 | `-0` separates entries with NUL | 原始流零换行 |
| A21 | `-0` output holds the same entries | NUL→换行还原后集合一致 |
| A22 | `-F` marks directories with `/` | 类型标记 |
| A23 | `-Q` shell-quotes names with spaces | `'wei rd.txt'` |
| A24 | `-P` uses dollar-quoting | `$'wei rd.txt'` |
| A25 | `-l` prints mode and ISO date | 长格式（`ls -l` 风格模式 + ISO 8601 时间戳） |
| A26 | `-h` prints the human readable size (3.0K) | 期望值由 `awk` 从 `wc -c` 反算，非取自 lr 自身输出 |
| A27 | `-s` strips the argument prefix | 前缀剥离 |
| A28 | `prune` keeps the entry but stops descending | 三元表达式 `? :` + `prune` 动作 |
| A29 | `-os` sorts by increasing size | 排序串 |
| A30 | `-oS` sorts by decreasing size | 大写反转，期望值来自 `wc -c` |
| A31 | `-U` lists the same number of entries | 遍历即输出（不排序） |
| A32 | `-D %t` root total covers the 3072 byte file | 深度优先累计（单位为 KiB 块数）与真实字节量下界对照 |
| A33 | symlink reported as type l | 符号链接类型 |
| A34 | `-L` tolerates a dangling symlink | 悬空链接下列出而不失败（上游 `lr.c` 解析分支对 ENOENT/ELOOP 均有 lstat 回退） |
| A35 | `%Y` reports a filesystem name (hmdfs), **not a bare device number** | 挂载表解析；断言排除纯数字（上游 `fstype()` 查不到挂载时回退打印设备号），故可作为 OHOS 上 `mntent` 分支真实工作的证据 |
| A36 | `-` reads file names from stdin | 标准输入文件名语义 |
| A37 | package ships man/lr.1 and the `_lr` completion | 交付物完整性；包目录缺省时由 PATH 上 `lr` 的位置反推，使 `sh test_lr.sh` 单独可复现 |
| A38 | exit status 1 for a missing path, 2 for a usage error | 退出码语义（且 Usage 走 stderr、stdout 为空） |
| A39 | `-W` prints during traversal yet keeps name order | 1.5 引入的 `-W`：断言其输出序列与默认排序完全一致；"边遍历边输出"的时机无法从输出侧证明，故不作断言 |
| A40 | `-B` lists the same entries breadth first | 广度优先遍历不丢条目 |
| A41 | `-t 'depth = 1'` selects exactly the top level entries | `depth` 属性过滤，条目数与 `find -maxdepth 1` 独立对照，且结果不含 `/` |
| A42 | NO_COLOR disables color even with `-GG` | `$NO_COLOR` 语义（https://no-color.org ，上游 NEWS 1.3 原文为 http 形式） |
| A43 | `-GG` forces colorized output | 颜色的 A42 正向对照（存在 ESC 序列） |

fixture 还包含隐藏目录 `.hidsub/` 及其内的 `.hidsub/secret`，因此 A07/A08 覆盖的是 `-A` 在 1.5.1 的真实回归点——"不再下降隐藏目录"，而不只是"隐藏文件不列出"。

补充真机观察（人工抽查，未列为断言）：`-l`/`%x` 在 HMDFS 上输出 `@`（该文件系统确实报告 user.* xattr），说明 lr 的 `#ifdef __linux__` 分支编译进二进制且实际工作；`%e`（目录条目数）与 `-D` 累计同批抽查通过。

---

## 四、验证链与证据

### 4.1 `conan create` 内 test_package 的真实输出（TAP）

以下为 `conan create` 内 `test_package` 的**完整** TAP 输出（脚本为含 `.hidsub` fixture 与强化 A01/A35/A43 判据的最终版本；`<pkg>` 代 conan 包目录，`$CONFIG_SHELL` 为 profile 注入的 harmonybrew bash）：

```text
lr/1.5.1 (test package): RUN: LR_PACKAGE_FOLDER="<pkg>" $CONFIG_SHELL test_lr.sh
ok - PATH resolves lr to the package bin/ and lists all 17 entries
ok - default output traverses recursively
ok - the traversal root . is listed
ok - default output is sorted by name
ok - -d lists only the starting point
ok - -1 does not go below one level
ok - -A hides dot files and does not descend dot directories
ok - dot file and dot directory contents are listed without -A
ok - -t 'type == f' selects regular files only
ok - -t 'type == d' selects directories only
ok - -e filters by basename regex
ok - filter operator ~~ globs names
ok - filter operator =~ matches POSIX ERE
ok - filter operator === is case insensitive
ok - numeric filter 'size > 1000'
ok - %s prints the byte size (3072)
ok - %d prints the path depth
ok - %n and %i report links and inode
ok - %m octal mode (0640) round-trips and is discriminating
ok - -0 separates entries with NUL
ok - -0 output holds the same entries
ok - -F marks directories with /
ok - -Q shell-quotes names with spaces
ok - -P uses dollar-quoting
ok - -l prints mode and ISO date
ok - -h prints the human readable size (3.0K)
ok - -s strips the argument prefix
ok - prune keeps the entry but stops descending
ok - -os sorts by increasing size
ok - -oS sorts by decreasing size
ok - -U lists the same number of entries
ok - -D %t root total (89 KiB) covers the 3072 byte file
ok - symlink reported as type l
ok - -L tolerates a dangling symlink
ok - %Y reports a filesystem name (hmdfs), not a bare device number
ok - - reads file names from stdin
ok - package ships man/lr.1 and the _lr completion (PKG=/storage/Users/currentUser/.conan2/p/b/lrc3e1b17886cb3/p)
ok - exit status 1 for a missing path, 2 for a usage error
ok - -W prints during traversal yet keeps name order
ok - -B lists the same entries breadth first
ok - -t 'depth = 1' selects exactly the 10 top level entries
ok - NO_COLOR disables color even with -GG
ok - -GG forces colorized output (no inherited NO_COLOR)
# lr functional assertions: pass=43 fail=0 total=43
```

> 说明：本块由 W3 阻塞门禁日志原样导出（43 行 `ok -`、0 行 `not ok -`），行号与 `test_lr.sh` 的 A01–A43 一一对应；A01 的 "lists all 17 entries" 即 `.hidsub/` 目录加入后的实际条目数，可作为该轮改动已生效的直接证据。

设备侧独立复现（不依赖 conan，直接对交叉编译产物 + 已安装布局跑同一脚本）：

| 跑法 | 结果 |
|------|------|
| toybox `sh` + 设置 `LR_PACKAGE_FOLDER` | `1..43` / `pass=43 fail=0 total=43` / rc=0 |
| toybox `sh` + 不设置该变量（脚本由 PATH 自洽反推包目录） | 同上，rc=0 |
| harmonybrew `bash` + 设置 `LR_PACKAGE_FOLDER` | 同上，rc=0 |
| harmonybrew `bash` + 不设置该变量 | 同上，rc=0 |
| fixture 目录残留（`trap` 清理后统计） | 0 个 |

破坏性自检（本地复刻 CI L1e 口径，证明断言不是空转）：把 PATH 上的 `lr` 换成"无任何输出、exit 0"的 stub 时 `pass=8 fail=35 total=43`、脚本 rc=1；从 PATH 完全移除 `lr` 时 `pass=7 fail=36 total=43`、rc=1。A01 承担"非空前置"：它要求 `lr` 默认输出的条目数等于 `find . ! -path .` 独立统计值 +1（根条目），因此 A04/A07/A20/A21/A31/A39/A42 这类"等式/缺失即真"的比较在产物被破坏时不会空洞通过。

### 4.2 门禁结果

本地与平台同源门禁 `zsh ci/conan/build_and_test.sh archives/l/lr/1.5.1`（profile `ohos-aarch64-device`）输出行：

```text
G0_RESULT=pass
KC_RESULT=pass
JC_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
[ok] L1e: Negative test confirmed — test genuinely depends on lr
L2_RESULT=skip: lr version/help failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
```

> 注：这里的 `G0_RESULT` 是 CI 脚本自身的第 0 阶段汇总，与 `conan-verify` 报告里的 G0"预构建风险评估"同名不同物，后者在设备上的结论是"构建系统未被识别 → 跳过预查询"。

`finish` 的 W3 阻塞门禁（step [5/10]，内部执行 `setup.sh` + 上述 `build_and_test.sh`）通过，`.ci-result.json` 由工具写入：`step=W3_local_ci`、`exit_code=0`、含 `integrity_hash` 与 `log_sha256`（该文件按 code-style §24 不入仓）。`conan-verify` 的 G0–G4 与 L2/L4/L5 明细同理由工具生成于 `reports/conan-verify-report.md`（本地证据，未入 PR；关键结论：G1/G2/G3/G4 PASS，L2/L4/L5 在设备侧为 `skip: 无 cache 路径`，G0 因上游为纯 Makefile 未被识别为 cmake/autotools 而跳过预查询）。

### 4.3 上游与平台事实核验

- 语言预检 R47：`lang-preflight` exit 0（detected=c，build-system=make，源文件 1 个占比 100%，c↔cpp 兼容族）
- 源码身份：`conandata.yml` 的 sha256 与两条独立通道（设备 codeload、本机 github.com）下载结果一致
- 上游 CLI 事实：`getopt` 串 `01ABC:DFGHLQPST:UWXde:f:lho:st:x`（含字符 `l`，即 A25 断言的 `-l` 长格式，不接参数），无 `--version`/`--help`；`-h` 是"人类可读大小"开关而非帮助（用法摘要仅在未知选项时打印到 stderr 并 exit 2）
- 产物：`bin/lr`（ELF64 / AArch64 / DYN=PIE）、`share/man/man1/lr.1`、`share/zsh/site-functions/_lr`；配方 `build()` 内另有 ELF 魔数与 `e_machine == 0xB7` 的架构断言

---

## 五、已知限制

| 项 | 技术原因 | 影响 |
|----|----------|------|
| CI L2 冒烟（`--version`/`--help`）skip | 上游 1.5.1 无长选项（`-h` 是人类可读大小而非帮助），未知选项以 rc=2 打印 Usage；上游设计如此 | 非阻塞；由 `build()` 内真实执行冒烟 + A38 退出码断言替代 |
| `-l` 属主/组与 `%x` 标记随宿主而异 | OHOS 使用 HarmonyOS 账号体系 uid/gid；HMDFS 不强制 `chmod(2)`（E046） | 断言不写死这些值（A19 用运行时反查 + 负向对照） |
| `fstype` 过滤 / `%Y` | 上游要求按平台实现 `scan_filesystems`；OHOS 走 `__linux__` 分支 | 实测返回 `hmdfs`；A35 已排除"退化为设备号"的假阳性 |
| 未断言的上游能力 | 见第一节末段清单 | 如实登记为未覆盖，不宣称全部可用 |
| zsh 补全 `_lr` | 仅对 zsh 生效，OHOS 默认 shell 非 zsh | 按上游原样安装 |

---

*报告生成时间: 2026-09-19 · 路径 A（零补丁交叉编译 + 补全 43 条行为回归）*
