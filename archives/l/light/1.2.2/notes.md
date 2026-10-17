# light 1.2.2 适配笔记

## 元信息

- 软件：light 1.2.2（命令行背光 / LED 亮度调节工具，sysfs 后端）
- 构建系统：autotools（`configure.ac` + 两级 `Makefile.am`），语言 C（**实测 6 个 `.c`**：
  `src/main.c`、`src/light.c`、`src/helpers.c`、`src/impl/sysfs.c`、`src/impl/util.c`、
  `src/impl/razer.c`；共 30 个文件。上游预扫曾记"11 个 `.c`"，本版本实测为 6，以本行为准）
- 外部依赖：**零**（`configure.ac` 只有 `AC_PROG_CC` / `AC_PROG_INSTALL` / `AC_HEADER_STDC`，
  无 `PKG_CHECK_MODULES`；源码不 `dlopen`、不 `-ludev`）
- 构建期工具依赖：`automake/1.18`（`tool_requires`，制品仓已发布，见 W0）
- 编译日期：2026-09-25 ｜ 编译器：clang 15（`/data/service/hnp/bin/clang`）｜ profile：`ci/conan/profiles/ohos-aarch64`
- 构建主机：B 机（鸿蒙 PC 真机，aarch64），worktree `~/qzy/主理-32-light-1.2.2`，`CONAN_HOME=~/tmp/ch/home-light`

**适配路径**: 路径 A（直接适配，配方侧处置 + 零源码补丁）＋ **路径 B 判定 = create**（本 PR 主张 1 条新知识：sysfs 类别目录枚举被策略拒 ⇒ 枚举型工具在发现阶段失败，见下三行）
**使用知识库**: 命中 `DRAFT-autoconf269-config-shell-unset-not-empty`（configure 的 `exec $CONFIG_SHELL` 重执行 + HMDFS getcwd → `working directory cannot be determined`）、
`DRAFT-6507-cln-mktemp-0700-hmdfs`（`config.status` 的 `mktemp -d` 0700 临时目录在 HMDFS setgid 父目录下不可写，E011 家族的 mktemp 变体）、
`E386`（noexec/HMDFS 下 shell 直跑与 getcwd 诊断不可只信退出码）、`archives/a/abiword-plugin-*/3.0.8`
（`automake` 走 `tool_requires` + `VirtualBuildEnv` 注入 PATH 的先例）。四条件对照见下"B 判定"节。
**知识库扩展**: `knowledge/drafts/DRAFT-light-1.2.2-sysfs-readdir-eacces-honest-degradation.kv`（+ 同名 `.md`）
**关联 Issue**: **#3361 已创建** —— https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3361 （正文含一手探针读数、正对照臂、未执行臂与作用域边界；建 Issue 时即把证据写全，避免后续无更新入口）

## 编译环境

- 构建系统：autotools（自举型：发布树无 `configure`）
- 编译日期：2026-09-25
- 编译器：clang / （无 C++）
- 状态：见"验证结果"节

## 编译步骤（配方实际做的事）

```bash
autoreconf -i                 # 发布树无 configure / aclocal.m4 / Makefile.in / config.guess
# 就地放宽生成 configure 内的 2 处 `umask 077` → `umask 022`（见问题 #2）
unset CONFIG_SHELL; export CFLAGS="${CFLAGS:-} -fcommon"
../configure --prefix=/ --bindir='${prefix}/bin' ... --with-udev=no
make -j1                      # HMDFS jobserver FIFO 不可靠
make install DESTDIR=<pkg>
```

`conanfile.py` 的 `build()` 手工调用 `configure`（`Autotools.configure()` 无法干预子进程 env），
参数取自 `AutotoolsToolchain.configure_args`（含 conan 自己的 `--prefix/--bindir` 等），
**不手写 prefix**（R49：不注入 `/usr/local`）。

## 遇到的问题与解决方案

| # | 问题 | 根因（一手读数） | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: working directory cannot be determined`（伴随 `shell-init: error retrieving current directory: getcwd: cannot access parent directories`） | profile `[buildenv]` 的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 触发 autoconf 的 `exec $CONFIG_SHELL` 重执行；hnp bash 5.3 在 conan 构建目录内 `pwd` 失败（`bash -c 'pwd'` → rc=1），**同一目录** `/bin/sh -c 'pwd'` → rc=0。`e_machine` 无关，纯 shell 启动 getcwd | `build()` 内对该子进程 **POSIX unset** `CONFIG_SHELL`（不是赋空值——空值下 `SHELL=${CONFIG_SHELL-/bin/sh}` 不回退，空 `SHELL` 进 `@SHELL@` ⇒ `make: -c: No such file or directory`，该反例已由 DRAFT-autoconf269 存证）。命中 DRAFT-autoconf269 推荐方案 |
| 2 | `./config.status[746]: can't create ./conf7hX5od/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery` | `config.status` 用 `(umask 077 && mktemp -d ./confXXXXXX)` 建临时目录；同一构建目录实测：`umask 077` → `drwx--S---` 且随后重定向写入 EACCES；`umask 022` → `drwxr-s--x` 写入 rc=0。⇒ **本机 mktemp 的目录模式跟随 umask**（对 DRAFT-6507 的"mktemp 恒 0700、umask 无效"是一条**否证**，差异**不在实现**、在 hmdfs 对 mode 位的改写 [W4R1/P2-4a]（W4 r1 复算 + 本棒在 `~/tmp/uc2/z32-light-fix1/mt` 干净复跑矩阵：GNU coreutils 9.10（`~/usr/local/bin/mktemp`）与 toybox 0.8.12（`/system/bin/mktemp`）**逐臂读数逐字相同** —— `umask 077`→`2700` 且目录内写入 `Permission denied`；`umask 022`→`2751` 可写；`umask 000`→`2771` 可写。同一父目录下 `mkdir -m 0700` 实测被改写成 `2771`（**显式 mode 亦不可信**）⇒ 边界只能写成「hmdfs 会改写 mode 位；`0700` 目录对本进程 effective uid（`/proc/self/status` 的 `Uid` = **20020084**；注意 `$HOME` 的属主是另一个 uid `20001006`，两者不同，别把后者当 euid）不可写」，不得写成两支 mktemp 的实现差异；也不得沿用 DRAFT-6507 的「mktemp 恒 0700、umask 无效」定性（本机两支实现都跟随 umask，该草稿的放宽 umask 处方仍然可用；其本体由主窗另计，本 PR 不改））） | 在 `build()` 里把自举出的 `configure`（含内嵌 config.status）的 `umask 077` 全量替换为 `umask 022`（实测命中 2 处，命中数为 0 时抛错防静默失效）。生成件由本配方自己产出、不入仓 ⇒ 不违反 R6；不改上游源码、不注平台宏（R8/PF5）。**外层 `umask 022` 前缀单独使用无效**（create5 实证：脚本内部自带 `umask 077` 覆盖） |
| 3 | `ld.lld: error: duplicate symbol: light_loglevel`（main.c / helpers.c / light.c / impl/sysfs.c 各在 `.bss` 落一份） | 上游 `helpers.h` 里 `int light_loglevel;` 是 tentative definition；clang ≥ 11 默认 `-fno-common` ⇒ 每个 TU 生成实定义；GCC < 10 的 `-fcommon`（合并 common 符号）才是上游发布所依赖的语义 | 给 `configure` 子进程 `export CFLAGS="${CFLAGS:-} -fcommon"`，走 conan 已验证生效的 env 通道（`config.log` 内 `CFLAGS='-O3'` ⇒ 环境 CFLAGS 原样进 `@CFLAGS@`）。备注：先试 `tc.cflags.append("-fcommon")` 未落到编译行（create7 仍 duplicate symbol），故改走 env 通道 |
| 4 | 无 `install(1)` / `automake` 缺失 | `command -v automake` → `~/usr/local/bin/automake` 存在但执行报 `No such file or directory`（断链）；`/data/service/hnp/bin` 只有 autoconf 家族 | `tool_requires("automake/1.18")`（`abiword-plugin-*` 先例），`VirtualBuildEnv` 注入 PATH；W0 复跑确认"已发布: automake/1.18" |

## 能力面一手探针（§4①，三臂 + 正对照）

探针：`~/tmp/uc2/z32-light/probe.c`，与目标产物同一编译器（`/data/service/hnp/bin/clang -O0`）本机编译、
`/usr/bin/timeout 60` 包裹实跑，`probe rc=0`。上一棒引用的 `~/tmp/uc2/z32-light/probe.txt` **盘上不存在**（同目录只有 `probe.c`/`probe`/`proberun.sh`，`proberun.sh` 把输出打到 stdout 未落盘）⇒ 该指针作废，改引本棒重跑的带时间戳一手输出件（下一段）。
**一手输出件（W4 r1 整改重跑，本棒亲跑）**：`~/tmp/uc2/z32-light-fix1/probe-out.txt`（**89 行**）—— 复用上一棒的 `~/tmp/uc2/z32-light/probe.c`（4535 B）原件，用**同一编译器** `/data/service/hnp/bin/clang`（输出件第 4 行回显 `clang version 15.0.4`）`-O0` 重新编译（`probe-compile.err` 是空件 ⇒ 无告警无报错）、`/usr/bin/timeout 60` 包裹、逐臂打 errno 与数值；起止时间戳见第 1 行与第 81 行（`Fri Sep 25 05:28:31 CST 2026`，同时坐实本棒读数的本机时区与本地日期）。下表读数的**行号锚点**（同一实验、同一进程）[W4R1/P2-1b]：`/sys` 6-10、`/sys/devices` 11-15、`/sys/class` 16-20、`/sys/class/net`（**正对照臂：应可读却同拒**）21-25、`/sys/class/backlight` 26-30、`/sys/class/leds` 31-35、`/sys/bus/hid/drivers/razerkbd` 36-40、`/sys/power` 41-45、`/etc/udev` 46-50、`/run/udev` 51-55、brightness 写臂 SKIPPED 56、`libudev` 四臂 **57-61**（三个 SONAME `dlopen` 全 FAIL + `dlsym(RTLD_DEFAULT,"udev_new")` NOT-FOUND + `libudev : NOT LOADABLE`；W4 审计件 `not_covered` 明写这四臂它未复算 ⇒ 本件把它补上）、`open /sys/class O_DIRECTORY : fd=-1 errno=EACCES(13)` 62、`PROBE_RC=0` 64（⇒ 无 `ENOSYS`、未被信号杀）、`/proc/mounts` 的 sysfs 行 67、进程安全上下文 69、已知节点直读臂 71-75、上游 URL 复核臂 77-80、身份与非 sysfs 目录对照臂（SECTION-4）82-89。
读数口径：**errno 级**，且 `stat` 与 `opendir` 分开报（`Permission denied ≠ 不存在`）。

| 路径（臂） | `stat` | `opendir` | `access(R_OK)` |
|---|---|---|---|
| `/sys`（一般面） | OK `mode=40555` isdir | **EACCES(13)** | EACCES |
| `/sys/devices`（正对照） | OK `mode=40555` isdir | **EACCES(13)** | EACCES |
| `/sys/class`（正对照） | OK `mode=40555` isdir | **EACCES(13)** | EACCES |
| `/sys/class/net`（**应成功的对照臂**） | OK `mode=40755` isdir | **EACCES(13)** | EACCES |
| `/sys/class/backlight`（目标） | OK `mode=40755` isdir | **EACCES(13)** | EACCES |
| `/sys/class/leds`（目标） | OK `mode=40755` isdir（输出件第 33 行原文；上一版此处省写作 `0755`，前导 `4` 是 `S_IFDIR` 目录位、非笔误，本棒按输出件回填）| **EACCES(13)** | EACCES |
| `/sys/power` | OK `mode=40755` isdir | EACCES | EACCES |
| `/sys/bus/hid/drivers/razerkbd` | **ENOENT(2)** | ENOENT(2) | ENOENT |
| `/etc/udev`、`/run/udev` | **ENOENT(2)** | ENOENT(2) | ENOENT |

分层归因（四件事分开）：

- **ENOENT（子树确实不存在）**：`/sys/bus/hid/drivers/razerkbd`、`/etc/udev`、`/run/udev` —— `stat` 就 ENOENT。
- **EACCES（存在但不给看，权限/策略面）**：`/sys` **整树**，含 mode 已是 `0755` world-readable 的
  `/sys/class/net`、`/sys/class/backlight` ⇒ 拒点在 Unix mode 位之外（MAC/挂载策略层），
  **不是 backlight 子系统缺失**。一手佐证（同输出件、本棒自跑，非引用上一棒）：第 67 行 `/proc/mounts` 载 `sysfs /sys sysfs rw,relatime,hmmac=genfs,seclabel`（挂载是 `rw` ⇒ 排除「只读挂载」假说；`hmmac=genfs` + `seclabel` 指向 MAC 层），第 69 行本进程安全上下文 `u:r:hishell_hap:s0`，第 71-75 行**直读已知节点** `/sys/class/net/lo/ifindex` 的 `ls`/`stat`/`head` 三式全部 `Permission denied`⇒ 拒面比「仅 readdir 被拒」更宽，**不得假设枚举被拒而节点可读**；第 82-89 行为身份臂（`/proc/self/status` 的 `Uid`=`Gid`=`20020084`）与 `/proc`、`/dev`、`/etc` 的 `ls` 对照臂 [W4R1/P3-3]。补充读数：`open("/sys/class", O_RDONLY|O_DIRECTORY)` → `fd=-1 errno=EACCES(13)`。
- **ENOSYS / SIGSYS（内核未提供 syscall）**：**本轮未见**——`stat`/`opendir`/`read` 均返回正常 errno 而非 `ENOSYS`，
  进程未被信号杀死（`probe rc=0`）。⇒ 不得把本包受阻归类为 syscall 缺失。
- **工具自行降级**：`light` 的 `src/impl/sysfs.c:60` 在 `opendir("/sys/class/backlight")` 返回 NULL 时
  走 `LIGHT_ERR("failed to open backlight controller directory for reading")` 并使 `light_initialize` 失败 ⇒
  属"能力面受阻后工具自己报错退出"，非崩溃。**事实级纠偏（本棒一手实测，推翻原文「报错退出」）**：`B=$HOME/tmp/ch/home-light/p/b/lightf21c778bcc668/p/bin/light`（47488 B，mtime 2026-09-25 04:13）→ `/usr/bin/timeout 30 $B -L` **退出码 = 0**（`LIGHT_L_RC=0`），输出里 `/sys/class/` 命中 **0** 行，首行打印诊断 `No backlight controller was found, so we could not decide an automatic target…`（原始输出落 `~/tmp/uc2/z32-light-fix1/light-L.txt`）⇒ 真实口径是「**枚举结果为空 + 打印无控制器诊断，但退出码仍为 0**」，不是「报错退出」；草稿 `rec_description`/`rec_command` 已同步改成本口径 [W4R1/P2-3a]。
- **libudev 面（装载与枚举分开报）**：`dlopen("libudev.so"/".so.1"/".so.0")` **三个 soname 全失败**，
  `dlsym(RTLD_DEFAULT,"udev_new")` → NOT-FOUND ⇒ 装载臂即断，`udev_new`/`udev_enumerate_*` 调用臂**未执行**。
- **未执行、缺证据的臂（如实记录，不写成结论）**：
  ① `/sys/class/backlight/*/brightness` 的 `open(O_WRONLY)`/`write` errno —— 因父目录 `opendir` 被 EACCES 拒，
  枚举不到设备名，探针输出 `backlight dir unopenable errno=EACCES -> brightness write arm SKIPPED`；
  ② 以 root/特权身份重探（无法区分 MAC 策略与 uid 策略）；
  ③ `--with-udev` 分支下 `make install` 往 `${prefix}/lib/udev/rules.d` 落规则文件的运行期效果
  （本平台无 udev 守护，`/etc/udev` ENOENT）。⇒ **本文任何句子都不主张"OHOS 不能调背光"**，
  只主张"sysfs 枚举面在本机对本进程被 EACCES 拒，工具按自身逻辑自行降级（实测 `light -L` rc=0，见上一小节）"。

## 测试账（§4③，rule4 三条同源）

上游测试清点（跑在**未打补丁的 pristine 解包树** `~/tmp/uc2/z32-light/pristine`，六形自数）：

```bash
tar tzf light.tar.gz | grep -ciE "test|spec|check"        # → 0
find pristine | grep -ciE "test|spec|check"               # → 0
grep -cE "^(check|installcheck|test|check-am|check-TESTS):" src/Makefile.in
                                                          # → 文件不存在（发布树无生成件，见下）
grep -nE "TESTS|check_PROGRAMS|AM_INIT_AUTOMAKE" src/Makefile.am   # → 0 命中（只有 bin_PROGRAMS + install-exec-hook）
grep -nE "AM_INIT_AUTOMAKE|AC_INIT|TESTS" configure.ac    # → AC_INIT([light],[1.2],…) / AM_INIT_AUTOMAKE([1.11 foreign subdir-objects])，无 TESTS
ls pristine/tests                                         # → ls: .../pristine/tests: No such file or directory
```

⇒ **上游原生用例 0 条**。`Makefile.in` 在 Debian `.orig` 里根本不存在（autogen 形态发布树），
该臂记为"不适用 + 文件缺失证据"，不记为 0 命中即通过。

适配后：`test_package/test.sh` 6 条消费者断言，全部真实执行已安装二进制，每条外部调用套
`/usr/bin/timeout`（实测 `/usr/bin/timeout` 存在且可用：`/usr/bin/timeout 2 echo ok` → `ok`，rc=0），
`rc=124` 一律 FAIL。断言面：产物可解析、ELF magic + `e_machine=0xb7`(aarch64) 字节回读、
`-V` 版本出口、`-h` 选项文案面（`bright*` 与 `-L`）、无参数错误路径（**退出码口径以终稿 PASS 行为准**：`reports/w3-local-ci.log:344` 与 `reports/conan-create.log` 的 `PASS 5: bare light invocation returns 0 with usage/diagnostics and no signal death` ⇒ 退出码 0 + 有 usage/诊断 + 不被信号杀死；本文旧写法「非 0」与终稿不符，已纠 [W4R1/P2-3c]）、
`-L` 在能力缺失时的诚实降级（两分支：rc=0 必须有非空枚举，rc≠0 必须有诊断文案；静默成功/信号死亡/零诊断一律 FAIL）。

三条同源：`test_package/MANIFEST.yml` 的 `assertion_count: 6` == `test.sh` 的 `PASS` 行数（6）
== 终稿执行件 `~/tmp/uc2/z32-light/create10.log`（116 行，`grep -c "^PASS "` = **6**，`ls -l` mtime 2026-09-25 04:57）== 提交态 `archives/l/light/1.2.2/reports/conan-create.log`（112 行，同式 = **6**）== `reports/w3-local-ci.log` 的 `PASS 1..6`（第 **340-345** 行）四处一致；另 `test_package/MANIFEST.yml:24` `assertion_count: 6`。旧件 `create8.log`（277 行）属更早一轮、其 PASS 文案早于 `c9b4da7fb6`/`d6b5118037` 两次改写，只留作历史臂、不再当同源指针 [W4R1/P2-5a]。

> 选项面纠偏：上游 **只有短选项**（`src/light.c:182` 的 `_light_print_usage()`：`-H/-h`、`-V`、`-L`、`-S`、`-G`…），
> 全树 `grep '"--[a-z]'` 0 命中 ⇒ 无 `--version`/`--help`。仓内 `test_package-executable` 模板默认先试
> `--version` 再退 `--help`，对本包两臂皆不存在 ⇒ 若 L2 冒烟只试双横线（已知框架行为），
> 该臂应判 `skip` 而非"功能不可用"；真实可执行性证据以本 `test_package` 的 6 条断言为准。

## 上游 URL 与 PF7（§5.8 口径）

- 采用：`https://deb.debian.org/debian/pool/main/l/light/light_1.2.2.orig.tar.gz`
  （实测 33009 字节、`sha256=62e889ee9be80fe808a972ef4981acc39e83a20f9a84a66a82cd1f623c868d9c`，
  与主窗从 Debian 索引读到的 `Checksums-Sha256` 逐字一致）
- 官方 https 通道探测（B 机一手读数，`runall.sh`）：
  `https://api.github.com/repos/haikarainen/light/tags` → **404**
  `https://api.github.com/repos/haikarainen/light/releases` → **404**
  `https://github.com/haikarainen/light/archive/refs/tags/v1.2.2.tar.gz` → **404**
  `https://codeload.github.com/haikarainen/light/tar.gz/refs/tags/v1.2.2` → **404**
  （两个域都试了，可达性一致；下载体 9 字节 = `Not Found` 文本。⇒ 这是"该仓库在 GitHub 侧不可解析到"的网络/存在性事实，
  不是"上游不存在 tar"的推断——本包 tar 的真实来源就是 Debian pool。）
- ⇒ 拿不到可核对的官方 https 同源包，**维持 Debian `.orig`**（上游原样发布树，非重打包 diff 混入）并在此如实披露。
  **未**改 sha256、**未**塞镜像代理域、**未**用 `file://`、**未**用 `--no-preflight`。同形先例：`proda/1.0`（PR #12545）。
- 已知框架存量：`scripts/ohc/preflight.py` 把 `deb.debian.org` 判为下游重打包源且无 pristine 豁免 ⇒
  PF7 若判红属**规则与本包事实的冲突**，只披露不规避。仓内 `archives/a/a52dec`、`aalib`、`abook`、`abr2gbr`、`abx`
  等大量既有配方的 `conandata.yml` 同样指向 `deb.debian.org`（属存量面）。

## B 判定四范围同批查重（§4④）

命令原文与命中数（同一批、worktree `~/qzy/主理-32-light-1.2.2`）：

| 范围 | 命令 | 命中数 |
|---|---|---|
| `knowledge/graph/*.kv` | `grep -ril backlight` / `grep -ril udev` / `grep -ril sys/class` | **0 / 2 / 0**（udev → `E107.kv`、`E237.kv`） |
| `knowledge/graph/index.tsv` | `grep -iE "backlight\|udev\|sysfs"` | **1 行**（仅 `E287` 的 keywords 里出现 `sysfs`，语义是 fuzz/raw-socket 面）；`wc -l index.tsv` = 766 |
| `knowledge/drafts/*.kv` | `grep -ril udev` / `grep -ril backlight` / `grep -ril "sys/class"` | **8 / 0 / 2**（`sys/class` → `E547-draft-0114.kv`、`E701-draft-4725.kv`） |
| `archives/**/notes.md` **（W4 r1 扩列：本行原式属结构性漏查，见下方辨析段）** | 三档同批复算：① 原式 `grep -rlE "backlight\|/udev/"`；② 广式 `grep -rilE "backlight\|/udev/\|opendir\|EACCES\|sys/class\|sysfs"`；③ **判据档** = ② 的产物再逐份 `grep -qiE "opendir"` ∧ `grep -qiE "sys/class\|sysfs"` | ① **9 个包**（`eudev/3.2.14`、`fbida/2.15`、`libmm/1.24.2`、`libplayerone/3.1.0`、`lvm2/2.03.42`、`razercfg/0.44`、`stlink/1.8.0`、`systemd/261`、`upower/0.99.20`，均除自身）② 159 份 notes.md（除自身；其中 130 份的命中来自 `Permission denied` 一类**构建期噪声**⇒ ② 只能当召回面）③ **1 份 = `archives/n/nload/0.7.4/notes.md`** ⇒ 真同机制先例既不是原报的「无」，也不是 ② 的 130 [W4R1/P1-1a] |

主窗预扫纠偏：预扫记 `udev` drafts 8 处命中（**复核一致**）、`backlight` graph/drafts 0 命中（**复核一致**）、
`sys/class` 2 个文件（**复核一致**）；但 `notes.md` 面预扫列 5 包、实测 **9 包**（多出的 4 包已读原文：
`upower` 提到 udev 守护缺失、`razercfg`/`stlink`/`systemd` 属同类外设/系统面）。
另 `grep -rli backlight knowledge/` 全库仅命中 `DRAFT-ohos-syscall-capability-matrix-fork-probe.md`，
而该文件内 `backlight|sysfs|/sys/class|EACCES` 四词命中数为 **0** ⇒ 名字相关、内容不覆盖本机制。

**判 create 的机制**（唯一、且本包一手取证）：`sysfs 整树 readdir 对非特权进程 EACCES 而 stat 成功
⇒ 按 MAC/策略面归因，消费者断言只能主张"诚实降级"`。
四条件对照（对 `E701`/drafts/`E011` 逐一否证"命中"）：

- 同机制？否 —— E701 是 `AF_PACKET` raw socket / 真实网卡缺失；本条是 sysfs 目录 `opendir`/`O_DIRECTORY` 被拒。
- 同根因？否 —— E701 根因是内核能力（无接口 + raw 权限）；本条根因在 mode 位之外的 MAC/挂载策略
  （`0755` 仍 EACCES）。E011 / DRAFT-6507 是**构建期** HMDFS 目录权限与 uid 错位，与本条**运行期**面正交。⇒ 据此本草稿的 `error_signature` 已删去那条构建期签名（`can` + `t create .../subs1.awk` 一支，属 `E011`/DRAFT-6507 家族的几十包共有噪声，留着会把未来的构建失败误路由到这条运行期知识上）**[W4R1/P2-2]**。
- 同处置面？否 —— E701 用上游 `SKIP_ETHERNET` 跳过用例；本条的处置是改写断言口径（两分支 + 必须带诊断）
  并做正对照探针。
- 同作用域？否 —— E701 作用域是测试套件；本条作用域是"任何以 sysfs 为唯一功能面的包"的能力定性。
**漏查补正与两条辨析（W4 r1 唯一 P1；本棒一手复算）**：原第 4 范围只用 `backlight|/udev/` 这一**主题词**组合，结构性地扫不到「同一机制、不同主题词」的先例 ⇒ 这是**查重关键词写窄了的漏查**（不是「未列全」这类措辞问题，是取证面不成立）。按机制特征词扩列重跑三档（命令与计数见上表第 4 行）后，真同机制先例浮出 1 例；另有第 3 范围自己浮出的 `E547-draft-0114` 此前未做四条件辨析，两条一并补：
- 先例 1 `archives/n/nload/0.7.4`（**同机制 ✔ / 同根因 ✔ / 处置面 ✘ / 作用域 ✘**）：`notes.md:60` 与 `notes.md:106` 记的是同一道墙 —— `DevReaderLinuxSys::isAvailable()` 只用 `stat()` 探 `/sys/class/net`、`opendir()` 因 `Permission denied` 失败 ⇒ 误判 sysfs 可用、跳过 `/proc/net/dev` 回退、设备数为 0 → TUI SIGSEGV（与「`stat` OK 而 `opendir` EACCES」逐字同机制同根因）。但它的处置面是**改上游源码 + 落到既有的 `/proc` 替代后端**：`archives/n/nload/0.7.4/patches/0003-src-devreader-linux-sys.cpp.patch:19` 新增 `DIR* testDir = opendir("/sys/class/net")`（`:10` 是 `isAvailable()` 上下文、`:31` 是原有 `sysDir` 行，补丁共 34 行），而 light 上游**没有任何替代后端**（`src/impl/sysfs.c:60` 是唯一枚举面、且本包 `--with-udev=no`），本条处置是**零源码补丁 + 改写消费者断言口径**；作用域也不同 —— nload 是「单包这一个 TUI 的可用性」，本条是「一切以 sysfs 为唯一功能面的包的定性口径」。⇒ 处置面与作用域两条不满足 ⇒ 不构成同机制重复、本条仍 `create`、不撤草稿（但必须像这样把它列出来）**[W4R1/P1-1b]**。
- 先例 2 `knowledge/drafts/E547-draft-0114.kv`（id `E547`；**同机制 ✘ / 同根因 ✘ / 处置面 ✘ / 作用域仅同大类 ✔**）：它的 `phase`（该件第 9 行）是 `configuration|compilation|linking|runtime`、`root_cause`（第 19 行）是「OHOS 不提供 libudev ⇒ configure/cmake 报 `libudev.h` 缺失、链接期 `undefined reference to udev_new`」这类**依赖缺失**，处置面（第 26 行 `rec_description`）是**新增 stub 头 + 改 CMakeLists 关依赖**；本条是**运行期枚举被策略拒 + 零补丁**。两面的分界本棒一手实测：装载期 —— `libudev` 三个 SONAME `dlopen` 全 FAIL、`dlsym udev_new` NOT-FOUND（输出件 57-61 行）；运行期 —— `/sys/class/*` 的 `opendir` EACCES（6-45 行）。且 E547 设想的回退面（`/dev/hidraw` 直连、绕开 sysfs 枚举）在本机同样落在同一堵墙外（直读已知节点 `/sys/class/net/lo/ifindex` 连 `stat` 都 `Permission denied`，输出件 71-75 行）⇒ 三个条件不满足，不判重、也不互相替代 **[W4R1/P1-1c]**。
⇒ 判 **create**，落 `DRAFT-light-1.2.2-sysfs-readdir-eacces-honest-degradation.kv` + 同名 `.md`（一 PR 一知识；
构建期 getcwd/mktemp/common 三条只写进本 notes，不另开草稿，属 hit）。

**hit 条目**（构建期三条，四条件全对照后按 hit 处理并点名）：
`DRAFT-autoconf269-config-shell-unset-not-empty`（同机制：`exec $CONFIG_SHELL` 重执行 + hnp bash getcwd；
同根因；同处置面：`unset CONFIG_SHELL` 后手工 configure；同作用域：conan autotools 配方 ⇒ **hit**）；
`DRAFT-6507-cln-mktemp-0700-hmdfs` + `E011` 家族（同机制：config.status 临时目录 0700 不可写；
同处置面：放宽 umask；**差异**：该草稿主张 mktemp 恒 0700、umask 无效须换 `mkdir -m 0777`，
本机实测 mktemp 跟随 umask、`umask 022` 即可 ⇒ 按 hit 取处方、把否证写进本 notes，不另开草稿；**W4 r1 收紧**：该否证的成立面是「两支 mktemp 实现读数逐字相同 + hmdfs 改写 mode 位」，不是「实现有差异」，详见上「遇到的问题」表第 2 行末 **[W4R1/P2-4b]**）；
`E386`（同大类：HMDFS/noexec 下 shell 能力须实测、不可只信退出码；处置面部分重叠 ⇒ 参照）。

## 验证结果

```bash
# W0（依赖发布态，conanfile 生成后复跑）
bash ci/scripts/preflight_check.sh light/1.2.2
  → [OK] 已发布: automake/1.18
  → [OK] 版本号未被占用: light/1.2.2
  → [OK] 所有依赖均已发布到制品仓，可以安全开始适配 light/1.2.2
# 首次（未生成配方时）→ [OK] 预检通过（无依赖需要检查）

python3 scripts/ohc-run.py recipe-search light   # → ⚠ 无相似配方（语料 6173 条）——首稿走 conan-init 模板
conan create archives/l/light/1.2.2 -pr:h=… -pr:b=… --build=missing --user=ohpcd --channel=stable
  → CREATE_RC=0；**终稿证据件（W4 r1 改指）**：`~/tmp/uc2/z32-light/create10.log`（116 行，`^PASS ` = 6）与提交态 `archives/l/light/1.2.2/reports/conan-create.log`（112 行，`^PASS ` = 6）；`create8.log`（277 行）作废为历史臂（措辞早于终稿，见上「测试账」节）[W4R1/P2-5b]
```

## 交付物

| 文件 | 说明 |
|------|------|
| `1.2.2/conanfile.py` | 配方（autoreconf 自举 + configure env 修正 + `-fcommon`） |
| `1.2.2/conandata.yml` | 源码 URL + sha256（PF7 披露见上） |
| `1.2.2/test_package/{conanfile.py,test.sh,MANIFEST.yml}` | 6 条消费者断言 |
| `1.2.2/manifest.yaml`、`README.md`、`commands.json` | 版本级/软件级三件套（R38/L0k：CLI 包必须声明 commands.json） |

## 注意事项 / 风险

1. **构建可得 ≠ 功能可得**：本包在 OHOS 上能构建、能安装、能执行、能报出正确的架构与文案面，
   但背光/LED 枚举面受 sysfs 策略限制；PR 与测试断言都不得宣称"背光调节可用"。
2. `--with-udev` 分支未启用：本平台无 udev 守护（`/etc/udev`、`/run/udev` ENOENT），
   规则文件 `90-backlight.rules` 内容是 `chgrp video` + `chmod g+w`，落到 OHOS 也没有承载它的事件通道。
3. CLASSIC 分支的 `install-exec-hook` 会 `chmod 6755 <pkg>/bin/light`（SUID）。HMDFS 上 chmod 语义受限
   （E046），该 SUID 位是否真的生效**未取证**；不把"以 SUID 身份可调背光"写进任何结论。
4. 本 notes 里 `_relax_config_status_umask` 会在 `configure` 未含 `umask 077` 时**主动抛错**，
   以便 autoconf 版本变动时暴露而非静默退化。

## 门禁与自检读数（W4 r1 补披露；只披露、**未改任何判据**）

`~/tmp/uc2/z32-light/finish4.log`（129 行）与提交态产物里以下条目**未转绿**，逐项带行号列此（本棒 `grep -n` 复算）：

| 读数 | 出处（文件:行） | 处置 |
|---|---|---|
| `失败步骤: step5b, step8` | `finish4.log:113` | 只披露（step5b = 知识/规则自检存量臂，step8 = packaging 缺失，均非本包判据） |
| `目录缺失: packaging` | `finish4.log:71` | 只披露 |
| `❌ packaging/ — 需创建` | `finish4.log:108` | 只披露 |
| `状态不一致: notes=error: could not setup config files machinery…` vs `manifest=built` | `finish4.log:75` | 只披露。成因：`finalize-archive` 从本 notes「遇到的问题」表格用正则抓状态字段，命中了第 2 行原文里的 `config.status: error:` ⇒ 属抓取面误命中，不是构建状态为 error |
| `finalize-archive 有警告 (RC=2)` 与同文件 `EXIT_CODE: 0 (知识整理已完成)` 并存 | `finish4.log:78` 与 `finish4.log:127` | 只披露（外层 RC=2 是告警码、内层 EXIT_CODE=0 是知识整理完成码，不同层，不得互相顶替） |
| `.handoff.json` 同时记 `exit_code: 0` / `exit_reason: finish_success` 与 `step_failed: Step6` | `archives/l/light/1.2.2/.handoff.json` | 只披露 |
| `.handoff.json` 记 `knowledge_hit: none`，而本 PR 主张 1 条 `create` | 同上 | 只披露：该字段是 finish 步骤对**构建期**知识的判定，与运行期路径 B 主张不同面，未据此改判据 |
| preflight `PF_RC=1`（PF9×1 + PF7×2） | `~/tmp/uc2/z32-light/pf2.log` 内**无** `PF_RC=` 行（该件只回显条目，rc 由外层捕获），数值出自 W4 判决件 P3 第 5 条复算 | 只披露，属框架两闸互斥（R38 要求软件级三件套位于版本目录之外 vs PF9 要求变更全在版本目录内）；本包**不删件凑绿、不加 `--no-preflight`** |

**勘误（W4 r1 推翻上一棒结论；本棒一手复算）[W4R1/勘误]**：上一棒那句「本仓 finish 日志没有 `[step]` 行 ⇒ W3 marker 计数为 0」只对 `~/tmp/uc2/z32-light/finish4.log` 成立（该件是缩进 ✅ 格式，本棒实测 `grep -c "^\[step\]"` = **0**、`grep -c "^RESULT="` = **0**），**对 W3 判真面不成立** —— 本棒实测 `archives/l/light/1.2.2/reports/w3-local-ci.log` 的 `^[step]` = **48** 行、`RESULT=` 标记 = **8** 行（⚠ 这些 `RESULT=` 行带缩进，写成锚定的 `^RESULT=` 计数会得 0 而误判成缺证据，必须用非锚定式），`PASS 1..6` 在第 340-345 行；`✅ W3 本地 CI 模拟通过` 一句的出处 = `finish4.log:66`（同文件命中区间 60/61/66）。⇒ W3 证据链成立，本棒**未**重跑 `conan create`/`finish`（重跑会作废这份真跑证据并白触发第三轮审计）。

**W3 与最后两枚提交的时序（P3 披露，未为此重跑门禁）[W4R1/P3-2]**：`reports/w3-local-ci.log` 的判级时刻 = `.ci-result.json` 的 `timestamp` `2026-09-25T04:58:34.106955`（`exit_code: 0`、`step: W3_local_ci`、`integrity_hash 072f963e9cd44d15`、`log_sha256 5f759280…`），它**早于**其后的两枚提交 `d6b5118037`（改 `.kv` 键值折行 + `test.sh` 文案）与 `1f9a30d4ec`（只改 notes）。⇒ 那次的 `KC_RESULT=pass`（同批 `junk2.log:23` `JC_RESULT=pass`）**未覆盖终稿 `.kv`**；本棒改完 `.kv` 后另行 `python3 -c "import yaml;yaml.safe_load(...)"` 复核 = **44 键可解析**（结果见本目录 CHECKPOINTS.md），并核对 `reports/conan-create.log` 与 `create10.log` 的 PASS 6 文案已是 HEAD 终稿措辞 ⇒ 只有知识件面属"判级后改写"，构建面判据不受影响。

**日期同源（P3）[W4R1/P3-1]**：两级 `manifest.yaml` 的 `build_date` 原为 `2026-09-24`（conan 侧用 UTC 日；本棒一手可读的同刻证据：`.handoff.json` 的 `timestamp` = `2026-09-24T20:58:38.084721+00:00`，而同一台机子的探针输出件第 1 行回显本机时区为 `CST` 并把同一天记为 `Fri Sep 25 …`），与本 notes 其余读数（本地日 `2026-09-25`）不一致 ⇒ 本棒统一为**本地日 `2026-09-25`**，两处改动：`archives/l/light/1.2.2/manifest.yaml:4`、`archives/l/light/manifest.yaml:20`；UTC 原值在此留痕，**不改任何日志与时间戳**。

**上游不存在面的加强披露（P3，本棒一手复算）[W4R1/P3-4]**：除原列 4 条归档 URL 404 外，`https://api.github.com/repos/haikarainen/light` → **404**、`https://github.com/haikarainen/light` → **404**、`https://api.github.com/users/haikarainen` → **404**，而 `https://api.github.com/` → **200**（输出件 77-80 行）⇒ **仓库与用户本体都不存在**，不是「tag 名猜错」：任何 tag 名都不可能拿到官方 https 归档；根域 200 同时排除「网络不可达」这一解释。结论不变（维持 Debian `.orig` + 如实披露）。
---

**编译结束**: 2026-09-25 04:57
**最终状态**: built
