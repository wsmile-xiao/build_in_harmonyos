# DRAFT: HMDFS 大小写折叠使「调用方写的 `./configure`」解析到上游手写的 `Configure`——注入的 GNU 长选项被 getopts 白名单判 illegal option，且无 AutotoolsToolchain 的配方连"剪参数面"都不存在

- **草稿**：`knowledge/drafts/DRAFT-iroffer-1.4.b03-hmdfs-case-fold-configure-dispatch.kv`
- **来源**：iroffer 1.4.b03 适配 run（任务号 7512，档位【中】，语言 c），B 机 HarmonyOS PC（HongMeng aarch64），2026-09-27
- **状态**：DRAFT，随 `feat/iroffer-1.4.b03` 分支交付；B 判定 = create，知识库扩展 Issue **#3506**
- **一句话**：不是"参数写错了"，是**被执行的那个脚本不是被点名的那个脚本**。

## 问题现象

框架的干净构建验证（`conan-verify` / `finish` 的 `Step 3/10: G0 干净构建验证`）对本包报红，终端原文：

```
✅ G0: 1 个补丁全部应用成功
❌ G0: configure 失败 (exit 1)
⚠️ G0 干净构建验证失败，请手动检查构建结果
```

它自己的日志（本轮 04:38 实拍，见「证据」节第二条）**第一条真实错误**里同时出现两个脚本名：

```
Configure for iroffer 1.4.b03 [20051213024435]
./configure: illegal option -- -
Usage: Configure [ options ]
   -h           This help
   -e           Print errors while running Configure
```

`./configure` 是**调用方写下的名字**（argv[0]，由 getopts 打进错误信息），`Configure` 是**脚本自己的自称**（usage 里硬编码）。两行并排看才是真相：调用方以为自己在跑 autoconf 产物，实际跑的是 2005 年的手写脚本。

本包源码树里**没有** autoconf 生成的 `configure`（pristine 树 `ls -1` 只有大写 `Configure`），所以这不是"configure 生成了但参数不兼容"。

## 根因（三件事叠加，缺一不可）

1. **HMDFS 大小写不敏感**：`/storage/Users/currentUser` 及其下的 worktree、`CONAN_HOME`、临时验证目录，同一目录内 `./configure` / `./Configure` / `./CONFIGURE` 指向**同一个 inode**，目录项只有一个。对照臂：只放 `BuildOnly` 的目录里调 `./configure` 立刻 `No such file or directory`（rc=127）⇒ 解析差异只由大小写折叠产生，没有任何回退逻辑参与。
2. **上游入口是大写 `Configure`，参数面只有五枚短开关**：手写 POSIX-sh，1098 行；`Configure:45` 是 `while getopts 'hedpw' OPTNAME; do`，`Configure:31-:37` 是 usage（末尾 `exit 1`）。任何 GNU 长选项都进 `illegal option` 分支，它连 `--prefix` 的概念都没有。
3. **调用方无条件按 autoconf 形态跑**：`scripts/ohc/clean_verify.py:130-132` 用小写字面量 `src_dir / "configure"` 做存在性检查并 `chmod(0755)`——**折叠使这个检查对只有 `Configure` 的树恒真**，"configure 存在"被假性确认；`:69` 取 `CONFIG_SHELL`（默认 `/data/service/hnp/bin/bash`）；`:138` 拼成 `$CONFIG_SHELL ./configure --prefix=$DEFAULT_PREFIX`（缺省展开为 `~/usr/local`，本窗 A3 实拍传入 `/storage/Users/currentUser/usr/local`）；`:163-183` 只看退出码 ⇒ `:181` 打印 `G0: configure 失败 (exit 1)`。同族第二调用点在 `scripts/ohc/driver.py:830`（f-string 原样 `sh {self.build_src_dir}/configure --prefix={self.default_prefix}`）。

### 与 `DRAFT-E2167-handwritten-configure-conan-injected-args` 的层次差（为什么不是它的子情形）

| 面 | E2167 | 本条 |
|---|---|---|
| 错误签名 | `Unknown option --oldincludedir`（**脚本自己**打印的白名单拒绝） | `./configure: illegal option -- -`（**getopts** 打印，且脚本自称 `Configure`） |
| 根因 | 手写脚本校验**注入参数**白名单（`.kv:6`） | 调用方点名的脚本**被大小写折叠换掉了**（`.kv:6` 里没有这一半） |
| 处方 | `generate()` 里 `tc.update_configure_args({"--oldincludedir": None})`（`.kv:7`、`.md:14-:21`，API 行在 `.md:19`） | 本包 `conanfile.py:57-58` 的 `generate()` 是 `pass`、**不经 `AutotoolsToolchain`** ⇒ 没有注入参数面，那句 API 调用在本包字面不可执行 |
| 边界 | `.md:23` 把"平台识别问题"划给 E160 类补丁 | 名字解析层，两方都没覆盖 |

即：**同一物理家族（手写 configure 不吃 GNU 长选项），但触发层与处方层都不同**。判 hit 的口径是"根因与解法两条都覆盖本包"，本包两条都不覆盖 ⇒ create。

## 方案空间

**正解（本包实物）**：绕开框架的 configure 步骤，按上游脚本的**真实拼写与自有参数面**驱动，并把判据从退出码换成生成物存在性。

- `archives/i/iroffer/1.4.b03/conanfile.py:72`：`CC="/data/service/hnp/bin/clang" sh ./Configure`（零长选项；编译器按 R33 从 `tools.build:compiler_executables` 取绝对路径、以命令行 `var=value` 形态传入）
- `archives/i/iroffer/1.4.b03/conanfile.py:76`：`make all CC="/data/service/hnp/bin/clang" -j1`（R9 恒 `-j1`，见 E074）
- 判据：退出码 **+** `Makefile` 与 `src/iroffer_config.h` 是否出现（上游在 OS 白名单落空时打印 `***ERROR***: This OS is not supported` 后是**裸 `exit`**，`Configure:104-:106` ⇒ 实测 rc=0 且零生成物；单看退出码必假绿。该"裸 exit ⇒ exit 0"事实与 E363 同源，但载体从测试 harness 换成构建入口）
- G0 那条红**如实定性为框架码路错配**写进 notes，用 W3 的 `conan create` 真编译取证，不改框架、不为本包加第二枚补丁

**⛔ 反模式一：补一个小写 `configure` 桩**（实拍见「证据」节 A4）——同名目录内两种拼写是同一 inode，写桩即**覆盖上游脚本本体**，目录项仍只有 `Configure`；而在大小写敏感的 CI 容器上同一配方又会得到两个文件 ⇒ 同一份代码两侧行为不一致。

**⛔ 反模式二：为这类包引入 `AutotoolsToolchain`** 去"生成一个能用的 configure"，或去改 `clean_verify.py` 迁就本包——前者把一个纯 make 包改写成 autotools 包（范围外改动，且参数面问题依旧），后者波及其它包、属框架级改动须单独 PR。

**退路**：若某手写入口确实需要目录类参数，先跑它自己的 usage 分支取**它的**参数面（本包 `sh ./Configure -h`，实拍返回 rc=1 并打印 `Configure:31-:36` 的五行清单），再逐项映射到 `package_folder`；⛔ 不得把 GNU 长选项硬塞给 getopts。

## 查重（四范围多轴）

`draft-review` 的相似面只取 `knowledge/graph/index.tsv`、**不扫 `knowledge/drafts/`** ⇒ 范围 2 手工补做（`grep -riE "大小写不敏感|case-insensitive|case fold|HMDFS|Configure"` 全量）。

- **范围1**：正式条目 540 条（`knowledge_check.sh` KC5 读数 `index.tsv 540 = .kv 540`）。draft-review 对本条的三态建议与分数见 `.kv` 与本节末「读数」。
- **范围2（手工）**：`DRAFT-E2167-…`（上表）、`DRAFT-cmake-target-dir-hmdfs-case-collision`（`.kv:41` 标题 / `:68` 处方 `rename-colliding-target-keep-output-name`：碰撞物是 CMake autogen **目录**、显式报错）、`DRAFT-liboggz-1.1.1-hmdfs-patches-collision`（`.kv:8/:11/:30`：conan 解包时 `PATCHES` 文件 vs `patches/` 目录、`IsADirectoryError`、处方 `excludes-filter-in-get`）、`libdisasm-0.23-hmdfs-script-exec-denied-sh-configure`（`.kv:14` 签名 `sh: .*/configure: Permission denied`、`:18-:26` 根因是 **execve 被 HMDFS 拒**、`:28` 处方 `invoke-configure-through-shell`——即使用 `sh` 调用，名字照样会被折叠，所以它是本条的**使用前提**而非覆盖）、`DRAFT-hfsm2-beta73-uppercase-tag-version-slug`（`:16` 是命名规范，无因果）。
- **范围3**：`knowledge/doc/` 内谈大小写不敏感的只有 E021/E193/E416/E470 四条；E193 的处方在**测试层**（`:24-:27` `skip-case-sensitive-tests`），E416 在**归档命名层**，E470 在 **CMake build 目录层**，E021 是 autoconf 自查文件系统大小写敏感性的 conftest ⇒ "**构建入口脚本被替换**"这一面**零条**。
- **范围4（同根先例）**：姊妹草稿 `DRAFT-vor-0.5.8-hmdfs-case-insensitive-pc-alias-self-reference` 与本条**同根不同面**——它处理 pkg-config 的 `.pc` 别名自引用（`already in requires chain` + `--cflags/--libs` 取空），本条处理构建入口派发；该件在分支 `feat/vor-0.5.8`，本 PR 基线 `origin/main` 内尚无该文件 ⇒ 按名引用、不给行号。
- 七轴结论：`exact_duplicate=false`｜`causal_duplicate=false`（E2167 只覆盖"参数被拒"，未覆盖"名字被换"）｜`trigger_overlap=true`（与 E193/vor 同根）｜`solution_overlap=false`（"绕开框架 configure 步骤、按真实拼写驱动 + 生成物判据"在正式库与草稿池均无先例）｜`combination_novelty=true`｜`boundary_novelty=true`｜`test_migration_novelty=false` ⇒ **create**。
- 通用池近邻：`DRAFT-PKG-VER-custom-configure-only-cli-args-no-env`（lzip 1.24.1 实证，Windows 侧 `经验文档/B草稿库/`，不在本仓检索面）——那条讲"手写 configure 只认命令行 `var=value`、忽略同名环境变量"，脚本**名字解析正常**；本条讲"名字根本没被按拼写找到"，且上游 `Configure` 连 `var=value` 形态的目录参数都不接受。两条互补、不重复。

## 证据（B 机 2026-09-27 实拍，三条独立）

### 证据一：`.kv` 的 `verification_cmd` 原样执行（`sh -n` RC=0、`VC_RC=0`）

取串与执行口径（读者可原样复算；本棒实测 `SH_N_RC=0`、`VC_RC=0`）：

    D=$(mktemp -d 2>/dev/null); [ -n "$D" ] || { D="$HOME/tmp/uc2/iroffer-kc-$$"; mkdir -p "$D"; }   # 本命令自建的全新目录，不落任何他棒路径
    KV=knowledge/drafts/DRAFT-iroffer-1.4.b03-hmdfs-case-fold-configure-dispatch.kv
    python3 -c 'import sys;sys.path.insert(0,"scripts");from ohc.models import parse_kv_file;open(sys.argv[2],"w",encoding="utf-8").write(parse_kv_file(sys.argv[1])["verification_cmd"]+chr(10))' "$KV" "$D/vc.sh"
    sh -n "$D/vc.sh"; echo "SH_N_RC=$?"
    sh "$D/vc.sh" 2>&1; echo "VC_RC=$?"

（`parse_kv_file` 解出的 `verification_cmd` 是**一行**命令、无尾换行，落成 `.sh` 时补一个行尾换行，内容不改。第 2 轮整改 Z75E-01 后该串自身只依赖两样东西：`mktemp -d` 出来的全新工作目录（为空则回退 `$HOME/tmp/uc2/iroffer-kc-$$` 并 `mkdir -p`），以及 `conandata.yml:14-:15` 的 url+sha256 ⇒ 上面四行在任意一台能出网的机器上都按字面跑得通。）
2026-09-27 独立审计第 1 轮整改（Z75KA-01）之前该字段写作 `verification_cmd: 竖线` 块标量，按字段取出的串 28 行、
首字符是 `|`、`sh -n` 报 `syntax error: unexpected 竖线` ⇒ 本节主张按字段不可复现；现字段只留一行可执行命令，
原先吞在字段里的**期望读数 / 判读 / 非判别噪声**三段全部迁到本节（下方引文块与其后的要点就是那三段）。

实跑件随 PR 提交：`archives/i/iroffer/1.4.b03/reports/verification-cmd-run.log`（20 行 / 960 B / sha256 `e429952088dea742e0748ff23a3bcd0e1fbf032267c6f1817c3cf8897de83da0`，
B 机 HarmonyOS PC aarch64 于 2026-09-27 06:40:46 实拍，B 交付棒 主理-75）。该件记的是**第 1 轮整改版字段**那一次（工作目录写死他棒暂存目录、A3 靠带外捞取），下列逐字引它；第 2 轮整改 Z75E-01 后，除 `W=` 与 `A3_src=` 两行的路径、以及 `A3_fetch`/`A3_lines` 两枚新增读数外，**判别读数与下列逐字相同**（干净环境复跑读数见本节末该条）：

```
A1_ls=[Configure ]
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not a tty
HANDWRITTEN-Configure-ran argv0=./configure args=--prefix=/x --bindir=/y --oldincludedir=/z
A1_rc=0
A1_unique_inodes=1
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not a tty
/data/service/hnp/bin/bash: ./configure: No such file or directory
A2_rc=127
A2_ls=[BuildOnly ]
A3_src=/storage/Users/currentUser/tmp/uc2/z75u-iroffer/src/iroffer-1.4.b03.orig/Configure sha=67568ea73310
A3_rc=1
A3_hits=[Configure for iroffer 1.4.b03 [Unknown]|./configure: illegal option -- -|Usage: Configure [ options ]|]
A3_Makefile=no A3_config_h=no
A3_own_surface_getopts=1
A4_ls_after_shim_write=[Configure ]
A4_Configure_first2=[#!/bin/sh|echo LOWERCASE-SHIM-ran|]
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not a tty
LOWERCASE-SHIM-ran
A4_rc_third_spelling=0
VC_RC=0
```

- A1/A2 是**只差大小写**的一对对照（同 shell、同参数）：前者把 `./configure` 解析进 `Configure`（三种拼写同 inode），后者 `No such file or directory`（rc=127）。
- A3 用真实上游 `Configure` 复现框架的调用形态：rc=1、两条错误信息、**零生成物**。
- A4 证伪"补小写桩"：写完桩后目录项仍是 `Configure`、`head -2 Configure` 已是桩内容、`./CONFIGURE` 跑出来的是桩。
- `shell-init: … getcwd …` 四臂都打（含对照臂）⇒ **非判别噪声**，与本机制无关（hnp bash 启动期读 cwd 失败）；不要据此改判，也不要拿它当根因。
- A3 的 banner 是 `[Unknown]`：本 `verification_cmd` 只 `cp` 单个 `Configure`、未带 `.cset_number`。已实拍确认这一差异的来源——上游 `Configure:13-:15` 读 `.cset_number`，同一脚本补上该文件后 banner 变为 `[20051213024435]`（与框架日志一致），与参数面、退出码无关。
- 本节的**期望读数、判读、噪声说明**原先以块标量混写在 `.kv` 的 `verification_cmd` 字段内，2026-09-27
  整改时迁到此处；字段侧只留一行命令，故上面的取串口径与本次实跑任何拿到本 PR 的人都可复算。
- A3 的取源臂在 2026-09-27 独立审计第 2 轮（Z75E-01）改为**自带取源**：原先靠 `find $HOME/tmp/uc2 $HOME/tmp -maxdepth 4 -type f -name Configure` 去捞**别的棒**解包出来的带外 pristine 原件（第 1 轮只排除了本命令自造的 `$W/*` 并要求内容含 `iroffer`），换一台没有那些暂存目录的机器就静默退化成 `A3_skipped` ⇒ "逐字相同"只在已解包过的机器上成立。现字段自己按 `conandata.yml:14-:15` 的 url 下载 `.orig`、先核 `sha256` 逐字等于 `03a6ea4e…e507` 才 `tar -xzf … iroffer-1.4.b03.orig/Configure` 取用 ⇒ 取到的必是上游原件且**与读者的机器无关**；下载失败或哈希不符时显式打 `A3_skipped=download-or-sha-mismatch got=[…]`（可判别，不再"捞不到就跳过"）。
- 工作目录同样改为**本命令自建**：`W=$(mktemp -d 2>/dev/null)`，为空时回退 `W=$HOME/tmp/uc2/iroffer-kc-$$` 并 `mkdir -p`；原先打在暂存目录上的 `rm -rf $W` 整条删除 —— `mktemp -d` 每次给全新目录，既不需要清，也不再往任何他棒目录里写。设备侧实测本环境 `mktemp -d` 落在 `/storage/Users/currentUser/tmp/tmp.XXXXXX`（HMDFS 会把该目录的 `0700` mode 改写，四臂仍全部可跑、判别读数不受影响）；只有 `$HOME/tmp` 也不可用时才走回退分支。
- 干净环境复跑（B 机 2026-09-27，第 2 轮收尾棒 主理-75；取串口径同上；本棒另把那份 21 行原始输出留在设备临时目录 `$HOME/tmp/uc2/z75l-iroffer-close/vc-run-2.log` 备查，它**不随 PR、也不当证据件引用** ⇒ 读者按上面四行自跑即可复现）：`sh -n` RC=0、`VC_RC=0`，与随 PR 的 `reports/verification-cmd-run.log` 比对，**全部判别读数逐字相同**（`A1_ls=[Configure ]`、`A1_rc=0`、`A1_unique_inodes=1`、`A2_rc=127`、`A2_ls=[BuildOnly ]`、`A3_rc=1`、`A3_hits=[Configure for iroffer 1.4.b03 [Unknown]|./configure: illegal option -- -|Usage: Configure [ options ]|]`、`A3_Makefile=no A3_config_h=no`、`A3_own_surface_getopts=1`、`A4_ls_after_shim_write=[Configure ]`、`A4_Configure_first2=[#!/bin/sh|echo LOWERCASE-SHIM-ran|]`、`A4_rc_third_spelling=0`）；差异只有四处且全是路径或新增读数 —— 新增 `W=` 行、新增 `A3_fetch=pool-url-sha256-verified(conandata.yml:14-:15)` 行、`A3_src=` 由带外路径改为本命令 `mktemp` 目录内路径（其 `sha=67568ea73310` 仍逐字等于本节「证据三」首条记的 pristine 哈希）、`A3_own_surface_getopts` 行尾追加 `A3_lines=1098`；`A3_skipped` **不再出现**。字段改写后经 `parse_kv_file` 复算，键数仍 **42**、`verification_cmd` 仍是单行（1876 字符）。

### 证据二：框架自己那一次真实运行的日志（随 PR 于 `reports/`，即 `archives/i/iroffer/1.4.b03/reports/g0-configure.log`）

`archives/i/iroffer/1.4.b03/reports/g0-configure.log`（12 行 / 647 B / sha256 `5a0f609a515e36006762264906ee13a535f08549d79e71c5d3f4b56444d37648`，2026-09-27 04:38）。该件原件在临时目录 `$HOME/tmp/ohc-verify-iroffer-6965g_fq/g0-configure.log`，2026-09-27 整改时按字节原样复制入仓（cp 未改内容，复制件 sha256 与原件逐字相同），故读者现在可在 PR 内直接数行。第 5–7 行原文（即该日志的第一条真实错误）：

```
Configure for iroffer 1.4.b03 [20051213024435]
./configure: illegal option -- -
Usage: Configure [ options ]
```

同目录解包出的 `iroffer-1.4.b03.orig/` 里 `ls -1` 只有 `COPYING Configure Makefile.config README WHATSNEW dynip.sh iroffer.cron sample.config src` ⇒ **无小写 configure**，与证据一的 A1 同型。（该临时目录不随 PR；同一事实由证据一 A1/A2 两臂与 `conandata.yml:13-15` 的取源哈希独立成立。）

### 证据三：上游实物与配方坐标（PR 内可解析）

- pristine `Configure`：sha256 `67568ea73310d1bf5763b72824e6b950a904ae8f1add5407f66ff23dd918276c`，1098 行；`:8 VERSION=1.4.b03`、`:13-:15` 读 `.cset_number`、`:29-:38` usage（`:31` 自称 `Configure`、`:37 exit 1`）、`:45 while getopts 'hedpw' OPTNAME; do`、`:104-:106` 的 `*) echo "***ERROR***: This OS is not supported"; exit`（裸 exit）。
- 配方：`archives/i/iroffer/1.4.b03/conanfile.py:57-58`（`generate(): pass`）、`:72`、`:76`；单源件与取源哈希在 `conandata.yml:13-:15`，`:17-:21` 是 `patches:` 块（`:21` 的 `da68036f…` 实测 == `sha256sum patches/0001-Configure.patch`，该补丁 1521 B / 56 行 / 2 hunk / `+11 -1` ⇒ 是补丁完整性字段，**不是第二个源件**）。
- 门禁口径照实：本轮 `conan-verify` rc=0 但**真实覆盖仅 G1–G3**（G0 跳过预查询、G4 `无法找到程序包 ID`、L2/L4/L5 跳过；G2 是缓存命中 `Already installed! (1 of 1)`）；真实编译在 `finish` 的 W3（`Success: 1 / Failed: 0`，`test.sh` 真跑 3 次均 `PASS 16/16`）。⇒ 本条机制的定性不依赖 G2，也不把 G0 的红当成本包构建失败。

## 关系

- **不是** E2167 的子情形（层不同、处方在本包不可执行）；对照关系见上表。
- 与 E193 同根（HMDFS 大小写折叠），E193 管测试层、本条管构建入口派发层。
- 与同 run 的 M4（无测试老 CLI 的负向分支可达性）**不随本 PR 申报**（AGENTS §9「一 PR 一知识」），M4 已入通用池 `经验文档/B草稿库/DRAFT-iroffer-1.4.b03-neg-branch-reachability-zero-test-cli.{kv,md}`。
- 姊妹条目（同根不同面，防被审成重复）：`DRAFT-vor-0.5.8-hmdfs-case-insensitive-pc-alias-self-reference`（pkg-config `.pc` 别名）、`DRAFT-cmake-target-dir-hmdfs-case-collision`（CMake 目录）、`DRAFT-liboggz-1.1.1-hmdfs-patches-collision`（conan 解包）、`libdisasm-0.23-hmdfs-script-exec-denied-sh-configure`（脚本 execve 被拒）。
- 判据取向承接 E363（裸 `exit` ⇒ rc 0 假绿 ⇒ 要 generated artifact 才算成功），载体由测试 harness 换成构建入口脚本。
