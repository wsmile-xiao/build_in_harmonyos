# yasr 0.6.9 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带预生成 configure，GNU Autoconf 2.61 / automake 1.10；本流程不跑 autoreconf）
- 编译日期: 2026-09-26
- 编译器: clang（OHOS SDK，profile 经 `tools.build:compiler_executables` 注入）
- 构建主机: B 机（HarmonyOS aarch64，HongMeng Kernel 1.12.0，`uname -s = HarmonyOS`）
- 状态: built（conan create/verify 通过、制品未上传，故不标 published）

## 上游身份（定源一手证据）

| 判据 | 读数 |
|---|---|
| Debian `.dsc`（yasr_0.6.9-12，Format: 3.0 quilt） | `Homepage: https://yasr.sourceforge.net/`、`Maintainer: Debian Accessibility Team`、`Vcs-Git: salsa.debian.org/a11y-team/yasr.git`、`Build-Depends: debhelper-compat (= 13), quilt` |
| `.dsc` Checksums-Sha256 | `41f17cfab8e88824a8dc1476602a0944b9030a8f8da2538a7a6549e3534e3bdf 235768 yasr_0.6.9.orig.tar.gz` |
| 官方直链 | `https://downloads.sourceforge.net/yasr/yasr-0.6.9.tar.gz` → 302 → `master.dl.sourceforge.net/project/yasr/yasr/0.6.9/yasr-0.6.9.tar.gz?viasf=1`，HTTP 200、content-length 235768 |
| 逐字节比对 | 官方址下载件与 Debian `.orig` 双件 `cmp` 无差异、sha256 同为 `41f17cf…4e3bdf` ⇒ **取源阶梯第 1 级成立：conandata 写官方址、哈希一字未改**（不吃 `deb.debian.org` 池址，PF7 天然避开） |
| 同名 GitHub 仓 | `mgorse/yasr`、`tbsaunde/yasr` 的 `/tags` 均为空 ⇒ 无 0.6.9 tag，不是发布源；`github.com/yasr/yasr` = 404 |
| Savannah | `download.savannah.nongnu.org/releases/yasr/` = 404（存在另一个同名项目，勿混） |
| 源码自证 | `configure.in` 的 `AC_INIT(yasr, 0.6.9, mgorse@alum.wpi.edu)`、`yasr.h` 头注 `Web Page: http://yasr.sf.net` + 维护者 `mgorse@users.sourceforge.net` |
| 许可证 | `COPYING` = FSF **Library** General Public License Version 2 (June 1991)，正文含 3 处 "any later version" 授权 ⇒ `LGPL-2.0-or-later` |
| 非 Debian-native | 池内存在 `yasr_0.6.9.orig.tar.gz`（88 条目录项，含 `configure`/`AUTHORS`/`ChangeLog`）⇒ 有 pristine upstream，无需造 tarball |

语言口径：`scripts/ohc-run.py lang-preflight yasr 0.6.9` 实测 `task=cpp, detected=c` 判**匹配通过**（rc=0，"c↔cpp 兼容族不迁移"，R47），证据三项 = 构建系统 autotools / `configure.ac`(configure.in)+Makefile.am / 源文件 14 个（c:14, bash:1，主体占比 100%，cpp:0）。

## 编译步骤

```bash
# 探索期（模式 B）在 .work 副本上做源码级改动，再用 refresh-patch --auto 出补丁
sh $HOME/tmp/uc2/z64-yasr/run-build-probe2.sh          # log: log-buildprobe-04.txt
#   patch(.work) -> fresh probe tree -> ./configure --prefix=... -> 产物断言 -> make -j1 -> make install DESTDIR
python3 scripts/ohc-run.py refresh-patch --auto yasr 0.6.9   # 4 个补丁（编辑追踪器精准模式）
python3 scripts/ohc-run.py conan-verify yasr 0.6.9           # 见「验证结果」
```

`configure` 只带 `--prefix`（R1 参数最少化）；**不使用 `--build/--host/--target`**（E007/E122 forbid_1）。

## 遇到的问题与解决方案

| # | 症状 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type`，尾随 `can't create .../cgiXXXXXX/dummy.c: Permission denied`；`configure: error: cannot guess build type; you must specify one` | 捆绑 config.guess 是 2007-07-22 版，主 switch 无 `*:HarmonyOS:*:*` 分支，且该年代**没有 `GUESS=` 累积机制**（新式脚本才在末尾统一 `echo "$GUESS"`），所以脚本落入 "unable to guess" 尾部并去编译 dummy.c | 补丁 0001：在主 switch 前部插 HarmonyOS 分支，按 `UNAME_MACHINE` 映射 MACHINE 后 **`echo ${MACHINE}-unknown-linux-ohos` + `exit 0`**（不能用 `GUESS=` 赋值形态） |
| 2 | `config.sub: Invalid configuration 'aarch64-unknown-linux-ohos': machine 'aarch64-unknown-linux' not recognized`（但同一脚本接受 `aarch64-unknown-linux-gnu`） | 2007-06-28 版 config.sub 的 KERNEL-OS 拆分列表（约 123 行）没有 `linux-ohos*` ⇒ 三元组被从最后一个 `-` 切开，machine 落到 `aarch64-unknown-linux`；即便切对，OS 白名单（约 1239 行）也缺 `-linux-ohos*`，会先命中通用 `-linux*)` 分支被 `sed 's\|linux\|linux-gnu\|'` 改写成 `-linux-gnu-ohos`（静默假身份） | 补丁 0002：两处白名单各补一项，**且 OS 白名单新增项必须排在通用 `-linux*)` 之前**。验收：`sh config.sub aarch64-unknown-linux-ohos` 原样回显同一三元组（实测 rc=0） |
| 3 | 仓内官方处方 `scripts/patch-autotools-ohos.pl`（E007/E072 推荐）对 config.sub **一处都没改**：`Score 1/5`、rc=1、三处 `[warn] Could not find …` | 该 perl 脚本的锚点全部取自 2016+ 新式 GNU config：①`#if defined(__ANDROID__)`（2007 无）②`android-linux)` 三行块（`grep -c android config.sub` = **0**）③`linux-uclibc* )` 收尾括号（该版行尾是 `\` 续行，正则不匹配）。只有 NetBSD case 锚命中，而它生成的正是症状 1 里那种无效的 `GUESS=` 赋值 | 保留②的 config.guess 插入（改成 echo/exit），config.sub 依 E072 三处白名单语义手工落点 ⇒ 补丁 0001/0002 |
| 4 | `configure` **退出码 0 却没有产出**：日志里 `sed: ./confXXXXXX/subs-1.sed: Permission denied`、`can't create ./confXXXXXX/out`，随后 `sed: Makefile: No such file or directory`，`make` 才暴露 `No targets specified and no makefile found` | autoconf 的 `AS_TMPDIR` 用 `(umask 077 && mktemp -d "./confXXXXXX")`。本机 euid **20020084** 与构建树 owner **20001006/group file_manager** 不同 uid ⇒ 写权限只能来自 group 位；toybox `mktemp -d` **跟随 umask**（对照实验见下），`chmod` 又改不动模式 ⇒ 0700 私有临时目录对本 euid 不可写 | 补丁 0003：取 **E011** 的 `umask 077 → umask 022`（本包 configure 内 2 处，含 config.status 生成段）。已合入同型先例：`archives/a/a52dec/0.7.4/patches/0002-configure-umask-022.patch`，另有 aide 0.19.3 / xz 5.6.2 / tar 1.35 / wget 1.19.1 / ivykis 0.43.2 |
| 5 | `./yasr.h:312:12: error: conflicting types for 'openpty'`（`forkpty` 同）；note 指向 sysroot `usr/include/pty.h` | 上游在 `yasr.h` 自带**非 const** 的 `openpty()/forkpty()` 原型，与 musl `<pty.h>` 的 `const struct termios */const struct winsize *` 原型不符。而 `config.h` 有 `HAVE_OPENPTY/HAVE_FORKPTY/HAVE_PTY_H/HAVE_LOGIN_TTY/HAVE_CFMAKERAW/HAVE_LIBUTIL = 1` 且生成的 `yasr/Makefile` 里 `LIBOBJS =`（空）⇒ 自带的 `openpty.c/forkpty.c` 替代实现**根本没参与编译**，那两条原型纯属死重量 | 补丁 0004：用 `#ifndef HAVE_OPENPTY` / `#ifndef HAVE_FORKPTY` 守卫这两条原型（configure 探测宏，**不含平台宏**，PF5/R8 干净），不改签名、不动 `.c` |
| 6 | `make -j2` 报 `make: jobserver mkfifo: /storage/Users/currentUser/tmp/GMfifo25087: Operation not permitted` | 本机文件系统不允许在该位置创建 FIFO，GNU make 4.4.1 的 jobserver 建不起来 | 配方 `autotools.make(args=["-j1"])`（与 aide/vamps 等既有配方的 `-j1` 口径一致） |

## 最小复现（症状 1–4 三条判别实验，均可逐字重跑）

在 `$HOME/tmp/uc2/z64-yasr/probe-src`（pristine + 补丁前的树）内：

```sh
sh config.guess                          # 期望复现：unable to guess system type（rc=1）
sh config.sub aarch64-unknown-linux-ohos # 期望复现：machine 'aarch64-unknown-linux' not recognized（rc=1）
sh config.sub aarch64-unknown-linux-gnu  # 正对照：同一脚本却接受（rc=0）⇒ 症结在 OS/kernel 白名单不在 machine 表

# 症状 4 的判别式（euid≠owner + umask 决定 mktemp 结果可用性）
python3 -c "import os,stat; print('euid',os.getuid(),'egid',os.getgid()); s=os.stat('.'); print(oct(stat.S_IMODE(s.st_mode)), s.st_uid)"
(umask 077; v=$(mktemp -d ./confV.XXXXXX); ls -ld $v; touch $v/f)   # 复现：drwx--S--- -> Permission denied
(umask 022; u=$(mktemp -d ./confU.XXXXXX); ls -ld $u; touch $u/f)   # 正对照：drwxr-s--x -> 可写
rm -rf confB; mkdir confB; touch confB/f                            # 正对照：普通 mkdir 归一成 drwxrws--x，可写
(umask 077; mkdir confC; touch confC/f)                             # 正对照：连 umask 077 的 mkdir 也可写 ⇒ 病灶只在 mktemp 造的 0700
chmod 755 confV.*; ls -ld confV.*                                   # 复现：模式不变（E046 chmod 不生效）
```

实测读数：`euid 20020084 egid 20020084`、树 owner `0o2751 / uid 20001006`；`umask 022` 下 mktemp 目录 `drwxr-s--x` 可写，`umask 077` 下 `drwx--S---` 不可写；普通 `mkdir`（含 `umask 077`）得 `drwxrws--x` 可写；`chmod 755` 无效。

现场日志（绝对路径）：
- `/storage/Users/currentUser/tmp/uc2/z64-yasr/log-fsprobe-01.txt`（mount 表 + 实验 A–E）
- `/storage/Users/currentUser/tmp/uc2/z64-yasr/log-buildprobe-01.txt`（补丁前 config.guess/sub 基线 + `cannot guess build type` 首错）
- `/storage/Users/currentUser/tmp/uc2/z64-yasr/log-buildprobe-02.txt`（config.sub 两处编辑生效后：SUB_RC=0，仍卡 config.guess）
- `/storage/Users/currentUser/tmp/uc2/z64-yasr/log-buildprobe-03.txt`（echo/exit 修复后：CONFIGURE_RC=0 但 `sed: ./confXXXXXX/... Permission denied`、6 个产物全 MISS、MAKE_RC=2）
- `/storage/Users/currentUser/tmp/uc2/z64-yasr/log-buildprobe-04.txt`（E011 生效后：6 个产物全 OK、MAKE_RC=0、INSTALL_RC=0）
- `/storage/Users/currentUser/tmp/uc2/z64-yasr/log-configure-plain.txt`、`log-configure-ohos.txt`、`log-make.txt`、`log-install.txt`
- `/storage/Users/currentUser/tmp/uc2/z64-yasr/log-yasr-A.txt`、`log-yasr-B.txt`、`log-yasr-C.txt`（yasr 运行行为三路）

## 已试过的失败方案

1. **E060 的 `use-tmpfs-workaround`（把源码复制到 tmpfs 如 `$HOME/tmp` 再 configure）— 未被执行；本条撤回第 1 棒的「否证」，改判「证据不足」**。第 1 棒那句「探索树本来就在 `$HOME/tmp/uc2/...`（＝tmpfs）下仍失败 ⇒ 处方已被现场满足而无效」**事实为假**：`/proc/mounts:71` = `/data/service/el2/100/hmdfs/account /storage/Users/currentUser hmdfs rw,nodev,relatime,hmmac=genfs` ⇒ `$HOME` 本身的 fs 类型就是 **hmdfs**；父级 `tmpfs on /storage/Users` 为真，但按最长前缀规则被其子挂载 `currentUser` 覆盖。第 2 棒按最长前缀实算三条构建树（`$HOME/tmp/uc2/z64-yasr/probe-src`、`$HOME/tmp/builds/yasr-0.6.9.work`、`$HOME/qzy/主理-64-yasr-0.6.9`）**全部 dev=`/data/service/el2/100/hmdfs/account`、type=`hmdfs`** ⇒ **E060 的 tmpfs 处方从未被真正执行过**，因此不可能否证 E060。⛔ 不得写作「OHOS 不支持 tmpfs」「E060 处方无效」，也不得据此改动 E060 的 HMDFS 归因（池内兄弟条目 `E011.kv:22`、`E206.kv:9`、`E136.kv:5` 与之同归因，连坐风险）。缺的那一环＝「把同一份补丁前基线放到一个**可写的真 tmpfs** 上跑 configure/config.status，并与 hmdfs 侧成对」；本机非特权 uid（`/proc/self/status` 的 `Uid:` 四栏实算 **20020084**）下**不存在可写的真 tmpfs**：`/dev/shm` 是真 tmpfs（`drwxrwxrwt root root`）但 `mkdir` 报 `Permission denied`、`/storage/hmdfs`（tmpfs）报 `Operation not permitted`、`/mnt/hmdfs/100`（tmpfs）报 `Permission denied`、`/data/local/tmp`（hmfs）对本 uid 不可写、`/tmp` 是只读 erofs ⇒ 该配对在本机做不出来（需 root／换挂载策略才能取证）。⇒ 口径：**E060 的 tmpfs 处方未被执行，既未证实也未否证（证据不足）**；本包真正生效的解法是 **E011/E206 的 `umask 077→022`**（补丁 0003），与落在哪种文件系统无关。取证：`~/tmp/uc2/z64-yasr/log-e060probe-w2-r1.txt`（§1 mount 全表／§3 逐路径 fs 类型／§4 可写性配对／§5 落点归属）；`log-e060pair2-r1.txt` 那轮两侧都没跑到目标机理（hmdfs 侧首条真实错误是 `no acceptable C compiler found in $PATH`、tmpfs 侧 `cp` 被 EACCES 挡住）⇒ **不构成任何一方的证据**。
   - 附（E060 条目自身两处可披露缺陷，属观察、不是新机制主张）：`knowledge/graph/E060.kv:21` 与 `:27-30` 把 tmpfs 的例子写成 `$HOME/tmp`，而本机 `$HOME` 自身即 hmdfs（`/proc/mounts:71`）⇒ **照字面抄等于原地不动**；`:16` 与 `:25` 的 `mount | grep hmdfs` 实测命中 9 行、其中 **3 行根本不是 hmdfs**（`tmpfs on /storage/hmdfs`、`tmpfs on /mnt/hmdfs/100`、`/dev/fuse on /data/storage/el2/media/Photo` 只因 selinux context 串含 `hmdfs` 才命中）⇒ 该检测式会假阳性、且不告诉你是哪个路径在 hmdfs。是否入条目由主理／框架窗走独立 KB PR，**本 PR 不主张条目更正**。
2. **`scripts/patch-autotools-ohos.pl` 单用 — 失败**（config.sub 改动数 0、Score 1/5、rc=1，且它给 config.guess 写的 `GUESS=` 块在旧式脚本上无效）。
3. **`--build/--host` 三元组绕过 — 未采用**：E007/E122 的 `forbid_1_pattern` 明令禁止（会让 AC_RUN_IFELSE 类运行时探测整体跳过、config.h 与实际平台不符）。⚠ 注意 `经验文档/手册/07-技术速查.md:18` 对 `cannot guess build type` 给的恰是这条被禁参数，与本包实测路径相反 ⇒ 留给主理/框架窗判断（本包不依它即绿）。⚠ **仓外引用**：`经验文档/手册/07-技术速查.md` 属规则工作区、不在本仓、**不随本 PR 出仓** ⇒ 评审者按该路径取不到原件；该页第 18 行的处方原文在此完整抄录为 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`（同页另提醒「两边都写 OHOS 会误判」）（本 notes 下文的 M2 节引用同一行时写作省略号形式 `--build=… --host=aarch64-unknown-linux-ohos`），**判据以本 notes 本节为唯一载体**。
4. **`autoreconf -fvi` 重生成 configure（E175 处方）— 不可行**：B 机 `/storage/Users/currentUser/usr/local/bin/automake` 不存在（`check_env.py` 因此在 `str(e)` 未绑定处抛 NameError、init-build 假红 rc=1），且 `configure.in` 用 autoconf 2.13 世代的 `AM_CONFIG_HEADER` + `AC_OUTPUT([m4/Makefile ...])` 位置参数形态，用 autoconf 2.72 重生成本身就要踩宏淘汰坑。tarball 既然自带预生成 configure，就走 §3.6 优先级②改生成件。
5. **`--disable-nls` 之类关开关 — 未采用**：`AM_GNU_GETTEXT(external)` 在本机自然通过（`INTLLIBS =` 空、`/data/service/hnp/bin/msgfmt` 可用），无需收缩特性面。

## 依赖（W0）

零 Conan 依赖。`configure.in` 只探测 libc/libutil/gettext 与 `AC_PROG_*`，全部由 OHOS musl sysroot 满足。一手证据：`config.h` 内 `HAVE_CFMAKERAW/HAVE_FORKPTY/HAVE_LIBUTIL/HAVE_LOGIN_TTY/HAVE_OPENPTY/HAVE_PTY_H/HAVE_SYS_IOCTL_H = 1`（`HAVE_LIBUTIL_H`、`HAVE_UTIL_H` 为 `#undef`），生成的 `yasr/Makefile` 中 `LIBOBJS =`、`INTLLIBS =`、`LTLIBOBJS =` 全为空 ⇒ 无替代对象、无 `-lintl`。日志：`/storage/Users/currentUser/tmp/uc2/z64-yasr/log-configure-ohos.txt`、`/storage/Users/currentUser/tmp/uc2/z64-yasr/probe-src/config.h`。

## 测试口径（R51 / rule4 五维账本）

| 维度 | 数值 | 依据 |
|---|---|---|
| 上游测试静态总数 | **0** | `grep -rn "^TESTS\|^check_PROGRAMS\|^noinst_PROGRAMS" Makefile.am yasr/Makefile.am acclogin/Makefile.am m4/Makefile.am po/Makefile.in.in` → 唯一命中 `yasr/Makefile.am:4: noinst_PROGRAMS = keytest`（交互式按键诊断程序，不安装、`make check` 也不跑它）；无 test/tests 目录、无 gtest/criterion/check 绑定 |
| 上游可执行测试数 | **0** | automake 只给隐式 `check: check-am`，其依赖集为空；`make -n check` 在 configure 未产出 Makefile 时报 `No rule to make target 'check'`（见 `log-buildprobe-01.txt` 第 7 节） |
| 实测通过数（上游） | **0** | 无测试可跑；未使用任何 `--disable-*` 开关，分母未被缩减 |
| 跳过数（上游） | **0** | 同上（0 分母 ⇒ 无 skip 可言，非"跳过了测试"） |
| 失败数（上游） | **0** | 同上 |
| 新增鸿蒙消费者冒烟用例 | **5 设计 / 5 实测通过 / 0 失败 / 0 跳过** | `test_package/test.sh` 逐条实测：①`ok: bin/yasr is a regular executable file`；②`ok: share/yasr/yasr.conf installed and non-empty`；③`ok: share/man/man1/yasr.1 installed`；④`ok: yasr -C <missing> -> rc=1 and printed the config search list`；⑤`ok: yasr -C <packaged yasr.conf> -> rc=0, config accepted, pty session ended cleanly`。机器标记 `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":5,"passedCount":5}`，上游标记 `HMBS_UPSTREAM_TEST_RESULT={…"discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}`。取证日志：`/storage/Users/currentUser/tmp/uc2/z64-yasr/log-create-r1.txt` 第 103–119 行（`CREATE_RC=0` 见第 122 行）——**该轮 conan create 复用了指向同一 recipe revision 的已构建包（日志内 `Already installed!`），重跑的是 test_package 阶段**，故 5/5 是测试实跑数；构建实跑证据**只取 W3 自己那一轮**：`reports/w3-local-ci.log` 同一件内 `:178` = `Calling build()`、首条编译行起于 `:295`、`:407` = `yasr/0.6.9: Created package revision 5d93e898b92ac005425699893b42e2b1`，且该轮自带 5/5 冒烟（区间 `:443`–`:459`；逐条 `ok:` 在 `:445`/`:448`/`:451`/`:453`/`:456`，`[test] summary: pass=5 fail=0 (of 5)` 在 `:458`）⇒ 构建实跑与测试实跑同锚一件，不需要借用第 1 棒的 create 日志。⚠ **另起一句说明：W3 这一轮与第 1 棒那一轮不是同一枚 package**（两轮各为独立的一轮，本行不作任何同一性主张，**上一版此处的「两次独立…构建」括注属不实表述、已撤回**——第 1 棒那轮是缓存复用轮、只重跑 `test_package`（两条 `Already installed!` 见 `log-create-r1.txt:70`、`:85`，另见本行末「另据一手件」句），这两轮中含 `Calling build()` 与 `Created package revision` 的是本轮 W3，即本行前句已引的 `reports/w3-local-ci.log:178`、`:407`）——第 1 棒 `log-create-r1.txt:17` 导出的 recipe revision 是 `dac327c95693ff4de967cd733ea0ef72`、引用带 `@ohpcd/stable` 作用域、测试期包目录 `yasr4dc3a3777d7fa`（该件 `:99`）；W3 轮是 `yasr/0.6.9#7b21e7ba0bca1e0d4873d54d8fc9aa31:6b129b068851896169fae42d399fa922d239ce8a#5d93e898b92ac005425699893b42e2b1`（`reports/w3-local-ci.log:409`，`Requirements` 段同值见 `:422`）、包目录 `yasr3e3aae545ad33`（`:410`）⇒ recipe revision / 引用形态 / 缓存包目录**三项全不同**。（两轮字面都出现 package id `6b129b06…` 与 package revision `5d93e898…`——`log-create-r1.txt:67`、`:82` 两条 `Requirements` 行逐字含这两串——但 Conan 的包身份含 recipe revision，同名字面值不等于同一枚 package：既不得据此合并叙述两轮，也不得拿「字面值相同」去否认上列 recipe revision / 引用形态 / 缓存包目录三项确实不同。）另据一手件：`log-create-r1.txt` 全文无 `Calling build()`、无 `Created package revision`，只有两条 `Already installed!`（`:70`、`:85`）⇒ 第 1 棒那轮本就只承载 test_package 重跑，这正与「该轮 5/5 是测试实跑数」的读法一致。⚠ 原指针 `reports/conan-create.log` 已被第 2 棒 `ohc-run.py finish` 重写覆盖（61206B → 6126B，现只剩两条 `Already installed! (1 of 1)`，无编译行、无 `Created package revision`）⇒ 该文件不再承载构建实跑证据；本行五维数字不变。测试期包目录**按轮分列**（不混写）：第 1 棒那轮 `/storage/Users/currentUser/tmp/ch/home-yasr-64/p/b/yasr4dc3a3777d7fa/p`（`log-create-r1.txt:99`，`bindir entry: yasr link=False exec=True` 见该件 `:100`）；W3 那轮 `/storage/Users/currentUser/tmp/ch/home-yasr-64/p/b/yasr3e3aae545ad33/p`（`reports/w3-local-ci.log:410`，同名 `bindir entry` 行见 `:440`） |

上游确无测试的清点证据 = 上面第一条 grep 的完整命中集（对 88 条 tar 目录项逐一核过），同时登记在本表与 `test_package/MANIFEST.yml` 的 `upstream_test_audit` 字段。

yasr 自身 CLI 面（决定冒烟形态）：`yasr.1` SYNOPSIS = `yasr [-C config file] [-c] [-s synthesizer] [-p synthesizer port] [program arg1 …]`；**无 `--version`/`--help`**（实测 `unrecognized option`）。运行行为实测：`-C <缺失>` → rc=1 + `yasr: unable to find … or ~/.yasr.conf or <pkgdatadir>/yasr.conf.`（printf 到 **stdout**）；`-C <随包 conf>` 且 stdin=/dev/null → rc=0 静默。日志 `/storage/Users/currentUser/tmp/uc2/z64-yasr/log-yasr-{A,B,C}.txt`。

## 验证结果

`python3 scripts/ohc-run.py conan-verify yasr 0.6.9`（经 `gate.sh` GATE_PASS +
`build-slot.sh --kind short --mem 2500` 抢槽执行）——**判绿三一致全部成立**：

| 判据 | 实测 |
|---|---|
| 文字 PASS | `G1: PASS`、`G0: PASS`、`G2: PASS`、`G3: PASS`、末行 `✅ 配方验证通过: yasr 0.6.9` |
| `**Verdict**` 行 | `/storage/Users/currentUser/qzy/主理-64-yasr-0.6.9/archives/y/yasr/0.6.9/reports/conan-verify-report.md`：**Verdict**: PASS（该件原被 `.gitignore` 的 `reports/` 规则忽略，2026-09-26 由主理 `git add -f` 随本 PR 入库、未改一个字节 ⇒ 读者可直接打开；其 `:33` 指向的 `conan-create.log` 指针早于本轮 `finish` 的覆盖⇒ 已失效，见下方 G4/L2/L4/L5 段的披露） |
| 退出码 | `VERIFY_RC=0`（日志 `/storage/Users/currentUser/tmp/uc2/z64-yasr/log-verify-r1.txt`） |

```
G0 预构建评估      PASS（命中 E490，见下方评估）
G1 配方完整性      PASS（name/version/source/build/package/package_info/export_sources/
                      apply_conandata_patches/conandata/test_package/test_package MANIFEST 全绿；
                      R26 提示"未检测到静态链接配置（非系统同名库无需静态）"）
G2 conan create    PASS（当时日志 archives/y/yasr/0.6.9/reports/conan-create.log，该件已被后续
                      finish 覆盖为 6126B、不含构建实跑行 ⇒ 构建实跑证据现读同目录
                      reports/w3-local-ci.log:407（Created package revision 5d93e898…）；
                      执行期框架临时注入 ghfast.top 镜像后已回写原 conandata，
                      复核 `grep -c "ghfast\|gh-proxy\|mirrors\|cnb.cool" conandata.yml` = 0）
G3 系统同名库隔离  PASS（"无 lib/ 目录（纯可执行包）"、"无系统同名库冲突（R26 通过）"）
G4/L2/L4/L5        报告【有】单列，但四枚都是「跳过形」的 ✅；本棒不据其主张任何通过，逐字抄录如下——
                     conan-verify-report.md（该件已由主理 git add -f 随本 PR 入库、未改一个字节 ⇒ 下面四组是其逐字转写，括号内 :39/:40/:42/:43/:45/:46/:48/:49 均可直接对照该件行号复核；⚠ 该件 :33 的日志指针 archives/y/yasr/0.6.9/reports/conan-create.log 早于本轮 finish 的覆盖，现该文件只剩两条 Already installed!（该件 :63、:78，共 6126B，无编译行、无 Created package revision）⇒ 该指针已失效，本轮构建实跑的真证据见 reports/w3-local-ci.log:407）：
                       :39  ## G4: ✅ PASS  ，子行 :40  ⚠️ 无法找到程序包 ID
                       :42  ## L2: ✅ PASS ／ :45  ## L4: ✅ PASS ／ :48  ## L5: ✅ PASS
                       三者的子行 :43 ／ :46 ／ :49 全是「⏭️ 跳过（无 cache 路径）」（顶栏图标与子行语义相反）
                     W3 同层实测读数 = reports/w3-local-ci.log:478-482：L0=pass、L1=pass、L2=skip、
                       L4=warn（L4_RESULT=warn: dangerous functions in patches —— warn 不是 pass，不得写成过）
                       L5=pass
                     口径：L2_RESULT=skip 既不是失败，也【不能】当产物可执行证据——该步按绝对路径起进程
                       （ci/conan/build_and_test.sh:1685 / :1693），判据是 --version/--help 返回 0，
                       而 yasr 这两个选项都没有（见「测试口径」小节 CLI 面一段：实测 unrecognized option）；
                       ⇒ 它同样【不是】「产物不可执行」的证据：同日志 :440 bindir entry: yasr link=False exec=True、
                       :453（rc=1 真跑）与 :456（rc=0 真跑）才是产物可 exec 的一手证据。
```

**G0 命中的 E490 评估＝不适用，未据此改配方**。E490 建议 `chmod +x configure
config.guess config.sub install-sh missing`，前提是"打包路径丢掉了脚本执行位"；
本包两条一手证据都不成立：①`get()` 解 tar 保留原模式，探索树里
`-rwxrwx--- ./configure`、`-rwxrwx--- config.guess`、`-rwxrwx--- config.sub`
执行位齐备，`./configure` 直接可跑；②本机文件系统 `chmod` 不生效（E046，本次判别实验
`chmod 755 confV.*` 后模式仍是 `drwx--S---` 已复验），照抄该处方只会写进一个
起不了作用的命令。故仅记录评估，不加 `chmod`，G2 亦在不动它们的前提下通过。

状态口径：工具提示"可标记 status: published"，但本棒范围只到
build + conan-verify 绿，`finish`/W3 与 W4 独立审计不在本棒 ⇒ 版本级
manifest 如实保留 `status: built`（R29 口径，同 aide/vamps 先例），由主理在
`finish` 后决定是否升级。

## 补丁清单

| 补丁 | 文件 | 增删 | 性质 |
|---|---|---|---|
| 0001-config.guess.patch | config.guess | +12/-0 | 三元组识别（旧式 echo/exit 形态） |
| 0002-config.sub.patch | config.sub | +2/-2 | KERNEL-OS 拆分表 + OS 白名单双补 |
| 0003-configure.patch | configure | +2/-2 | E011 umask 077→022（config.status 临时目录可写） |
| 0004-yasr-yasr.h.patch | yasr/yasr.h | +6/-2 | HAVE_* 守卫陈旧 pty 原型 |

生成方式：`ohc-run.py refresh-patch --auto`（编辑追踪器精准模式）。哈希取**提交态所依据的那一轮**，并与版本级 `manifest.yaml:71`–`:72` 统一为一手可核值：orig `ad045dff3da595ac` / work `2b82354341219ce4`（一手日志 `/storage/Users/currentUser/tmp/uc2/z64-yasr/log-finish-w2r1.txt:33`、`:34`，即第 2 棒 `finish` 的 Step1 重跑 refresh-patch；版本级 `manifest.yaml:73` 的 `generated_at: 2026-09-26T03:23:18` 属同一轮）。⚠ 本行此前写的 work `44c2b9e0b3865318` 是**第 1 棒那轮**的读数（该轮 manifest 见提交 `dbfc976791` 内 `generated_at: 2026-09-26T02:44:58`），但盘上已无该轮的一手 refresh-patch 日志可核（`~/tmp/uc2/z64-yasr/` 全目录 grep `44c2b9e0` 只命中本 notes 与审计件对本 notes 的抄录），且该轮之后补丁被 `finish` 重生成过 ⇒ 不再作为提交态依据；两处（本行与 manifest）现取同一枚可核值，不留互斥读数。

## 已知限制（一手证据，交主理裁定，本棒未自行绕过）

**打包后的 `yasr` 在不带 `-C` 且用户没有 `~/.yasr.conf` 时找不到随包默认配置。**

证据链（原引 G2 自写的 `reports/conan-create.log`；该文件已被第 2 棒 `finish` 覆盖为 6126B、不再含下列行 ⇒ 现改锚同目录 `reports/w3-local-ci.log`，同为构建机件）：

- `/storage/Users/currentUser/qzy/主理-64-yasr-0.6.9/archives/y/yasr/0.6.9/reports/w3-local-ci.log` 第 183 行（原 create.log 第 103 行随覆盖失效）：
  `yasr/0.6.9@ohpcd/stable: RUN: ".../b/configure" --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include'`
  ⇒ Conan 的 AutotoolsToolchain 按"可重定位打包"约定把 `--prefix` 定为 `/`。
- 同日志第 295 行（首条编译命令；原 create.log 第 417 行同批失效）：
  `clang -DPACKAGE_DATA_DIR=\"//share/yasr\" -DLOCALEDIR=\"//share/locale\" ... -c -o config.o .../yasr/config.c`
  ⇒ `yasr/Makefile.am` 的 `DEFS = -DPACKAGE_DATA_DIR=\"$(pkgdatadir)\" ...` 是**编译期常量**，`${prefix}` 为空 ⇒ 烙进二进制的值是 `//share/yasr`。
- 运行期复现（`/storage/Users/currentUser/tmp/uc2/z64-yasr/log-create-r1.txt` 第 114 行）：
  `yasr: unable to find /storage/.../tmp/no-such-yasr.conf or ~/.yasr.conf or //share/yasr/yasr.conf.`

影响面与既有缓解：`config.c` 的配置搜索是三级 `-C 指定 → $HOME/.yasr.conf → PACKAGE_DATA_DIR/yasr.conf`；前两级与 prefix 无关，`yasr.conf` 也确实随包安装到 `share/yasr/yasr.conf`（测试用例②已断言非空），所以**只要用户按上游文档有 `~/.yasr.conf` 或用 `-C` 指定，功能完整**。本包 5 个冒烟用例走的正是这两条可用路径（用例⑤用 `-C`）；"仅靠随包默认配置"这一路**未被覆盖，也确证不可用**——不要把它记成"已验证可用"。

可选处置（本棒不擅自选，因为每条都有代价）：

1. 保持现状 + 在 PR 正文与 README 的「运行环境」里披露（本棒已按此执行）。零构建风险，符合 Conan 的可重定位约定。
2. 在 `generate()` 里把 `--prefix` 改指 `self.package_folder`：能让 `PACKAGE_DATA_DIR` 落在真包里，但会把**含 hash 的 cache 绝对路径烙进二进制**，换机器/换 CONAN_HOME/CI 与本地路径不同即失效——风险高于收益，且属"为过测试而硬编码路径"。
3. 给 `yasr.conf` 安装位置加运行期兜底（例如包装脚本设 `YASRCONF`/复制模板到 `$HOME`）：改变上游行为面，属产品决策，应由主理或用户点头。

## 适用边界

- 补丁 0001/0002 只适用于**捆绑 2016 年前旧式 GNU config 脚本**的 autotools 包（判别式：`grep -c '^GUESS=' config.guess` 返回 0；`grep -c android config.sub` 返回 0）。新式脚本仍应先用 `patch-autotools-ohos.pl` 并按 E007/E072/E122 落点。
- 补丁 0003 的前提是**构建 euid 与树 owner 不同 uid**（本机 20020084 vs 20001006）且该位置 `mktemp -d` 跟随 umask、`chmod` 无效；若某环境 euid==owner，则 0700 临时目录本就可用，此补丁为无害冗余。
- 补丁 0004 属"上游自带函数原型与 sysroot 原型 const 不符"一类，**判据是先看 `config.h` 的 `HAVE_<FUNC>` 与 Makefile 的 `LIBOBJS` 是否为空**：空 ⇒ 替代实现未编译，守卫原型即可（首选）；非空 ⇒ 必须连 `*.c` 定义一起对齐 const，不能只删声明。
- 本包无第三方 Conan 依赖，故不涉及 R49 私有 prefix 注入；也不涉 R26 系统同名库（不产出 `.so`）。

## B 候选机制台账（四范围查重计数，B 终判归主理）

四范围 = `knowledge/graph/`、`knowledge/drafts/`、`经验文档/B草稿库/`、`经验文档/手册/07-技术速查.md`。

⚠ **仓外引用总说明（适用本台账全部三条 M1/M2/M3）**：四范围中的 `knowledge/graph/` 与 `knowledge/drafts/` 是**仓内件**，评审者可直接打开核对；而 `经验文档/B草稿库/`、`经验文档/手册/07-技术速查.md` 以及 M3 里引用的 `OHOS行为探针清单.md` 都属**规则工作区、不在本仓、不随本 PR 出仓** ⇒ 评审者按这些路径取不到原件。本台账只把它们用作**查重范围与计数依据**，凡需要对外成立的判据一律以本 notes 本节抄录的读数（命中条目名、行号、机制句、处方原文）为**唯一载体**，不留悬空外部引用；下文各处引用这些仓外件时另附短提示。

### M1 `config.status` 私有临时目录：euid≠owner + `umask 077` + toybox mktemp 跟随 umask ⇒ configure 退 0 而产物静默缺失
- knowledge/graph：`umask 077` 命中 **E011 / E136 / E206 / E223 / E533**（+ index/pre-scan-rules）；`umask 022` 命中 E011/E129/E136/E206；`mktemp`/`confXXXXXX` 命中 E011/E052/E060/E114/E118/E136；`owner` 命中 E011/E040/E101/E114/E223/E224…；数字 uid `20020084` 命中 **0**（但 E206 写的是 `20020101`，同类不同机）。
- knowledge/drafts：`umask`/`mktemp` 命中 DRAFT-001、DRAFT-10686-…、DRAFT-11301-ohos-compile-fail-suite、DRAFT-11103-teseq-mdate-…
- 经验文档/B草稿库：命中 `DRAFT-PKG-VER-hmdfs-umask-007-660-not-executable.md`（README 第 34 行已标"⚠ 待复核・不建议派发，症状与 E087 重叠、Issue #3158 以不存在的 E543 名义发布"）与 `DRAFT-PKG-VER-host-os-linux-substring-match-enables-werror.md`。
- 手册/07：**第 16 行**已有该机制条目并直接指向 E011/E114 处方。
- **层次对齐结论：能对齐到行号** ⇒ `knowledge/graph/E206.kv` 第 9 行（owner uid 20001006 / 非 owner 无法写入 0700 临时目录）与第 6 行（`umask 077→022` 处方）、`knowledge/graph/E136.kv`（`umask 077 + SGID ⇒ drwx--S---` 模式串与本包实测逐字相同）、`经验文档/手册/07-技术速查.md:16`。本包新增部分只是"configure rc=0 与产物缺失的分离"这一条验收口径，属既有机制的应用现场 ⇒ **倾向 hit，终判归主理**。（⚠ **仓外件提示**：`经验文档/手册/07-技术速查.md:16` 不随本 PR 出仓、评审者取不到原件；该行判据在此原样抄出＝「`config.status` 报 `subs1.awk: Permission denied` 或 umask 077 临时目录不可写：HMDFS 权限组合问题，用 E011/E114 的受控方案移除 configure 中 umask 077 包裹（保留真实临时目录创建），不换环境掩盖」⇒ 判据以本 notes 本节为唯一载体）

### M2 旧式（2007）config.guess/config.sub 让 `patch-autotools-ohos.pl` 三处锚点全落空；且 config.sub 两处白名单缺一不可、顺序敏感
- knowledge/graph：`patch-autotools-ohos` 命中 E007/E122/E205/E268；`android-linux` 命中 **E072**；`linux-ohos` 命中 E007/E016/E072/E099/E122/E268；`GUESS` 命中 **0**。
- knowledge/drafts：`android`/`GUESS` 命中 **DRAFT-E564-oldstyle-config-guess-ohos-reanchor.kv**、**DRAFT-autotools-config-sub-silent-ohos-triplet.kv**、DRAFT-config-guess-era-echo-exit.kv/.md。
- 经验文档/B草稿库 + 手册/07：`config.guess`/`config.sub` 命中 手册/07 第 16/18 行与 B草稿库的 host_os 子串条目；未见旧式锚点专题件。
- **层次对齐结论：能对齐到文件级、并对齐到条目内部具体判据**——`DRAFT-E564`（锚点①②③④⑤逐条失效清单 + `Score 1/5` + `cgiXXXXXX/dummy.c: Permission denied` 现场 + 旧式无 `echo "$GUESS"` ⇒ 须 echo/exit）、`DRAFT-autotools-config-sub-silent`（两处 hunk 分工 + `-linux*)` 分支 `sed 's|linux|linux-gnu|'` 造成静默 `-linux-gnu-ohos` + `sh config.sub "$(sh config.guess)"` 原样回显判据）。本包是这两条的**第三个现场**（年代更早：2007-06-28/2007-07-22，且 `grep -c android` = 0 的新否证读数）⇒ **倾向 hit（按文件名引用，不占知识位），终判归主理**。
- ⚠ 同时给主理一条与在池条目相反的现场读数供复核：`经验文档/手册/07-技术速查.md:18` 对 `cannot guess build type` 的处方是 `--build=… --host=aarch64-unknown-linux-ohos`，而 E007/E122 的 `forbid_1_pattern` 明令禁止该写法；本包在**完全不传** `--build/--host` 的前提下靠补丁转绿。（⚠ **仓外件提示**：`经验文档/手册/07-技术速查.md:18` 不随本 PR 出仓、评审者取不到原件；该行处方原文已在本 notes「已试过的失败方案」第 3 条完整抄出 ⇒ 判据以本 notes 为唯一载体）

### M3 `yasr.h` 自带非 const `openpty()/forkpty()` 原型与 musl `<pty.h>` 冲突；判据 = `HAVE_*` + `LIBOBJS` 是否为空决定"守卫声明"还是"对齐定义"
- knowledge/graph：`openpty` = **0**、`LIBOBJS` = **0**、`pty.h` 仅 E373（读原文后 E373 讲的是 Conan build-scope 环境传递，与本机制无关 ⇒ 属"grep 命中≠语义命中"的假阳性，不可当 hit 依据）、`conflicting types` 命中 E091/E119（两条都是 `sockaddr_storage` 的 `linux/socket.h` 重定义，与 const 原型冲突不同类，**层次对不上**）。
- knowledge/drafts：`forkpty`/`cfmakeraw`/`HAVE_OPENPTY` 命中 3 份：`DRAFT-openvi-7.9.33-nonautotools-argv0-mode-musl-pty-ncurses-override.kv`、`E563-draft-CBD3.{kv,md}`、`E551-draft-J669.md`。**本棒未逐份读完其判据**（时间盒），故只报计数，不下 hit/create 结论——需主理核这三条是否已覆盖"上游自带原型与 sysroot const 原型冲突 ⇒ 先用 `config.h` 的 `HAVE_<FUNC>` 与 Makefile 的 `LIBOBJS` 判定替代实现是否参与编译，再决定守卫 vs 改签名"这条判据。
- 经验文档/B草稿库 + 手册/07：`openpty`/`forkpty`/`LIBOBJS` 相关命中为 `OHOS行为探针清单.md:21`（pty/termios 探针条目，状态"⬜ 待探"），非同一判据；B草稿库与手册/07 内 **0 命中**。（⚠ **仓外件提示**：`OHOS行为探针清单.md:21` 属规则工作区、不随本 PR 出仓、评审者取不到原件；该行的实质读数已在此抄出＝一条状态仍为「⬜ 待探」的 pty/termios 探针项，探针对象是 `openpty`/`tcgetattr` 流控与 struct 布局、波特率枚举，与本机制的 const 原型冲突判据不是一回事 ⇒ 判据以本 notes 本节为唯一载体）
- ⇒ 若主理复核后三条 drafts 均不覆盖该判据，**M3 是本 PR 唯一可能升 create 的候选**；本棒不判、不建 Issue、不动 `knowledge/drafts`。

## 3+2 声明（B 终判归主理，本棒仅如实登记）

- **适配路径**：路径 A（配方适配）为主，B 候选机制 3 条已入上表台账，终判与是否建草稿/Issue 归主理。
- **使用知识库**（第 3 棒按**执行强度分级**登记；⛔ 不再笼统写「全部命中并按处方执行」）：**字面按处方执行**＝E011（`E011.kv:40 rec_approach: edit-umask-in-configure`、`:47 rec_command: sed -i ...umask 077/umask 022` ⇒ 本包补丁 0003 正是该动作，`conandata.yml:28-30` 描述点名 E011）；**等价执行**（在 configure 层改、`config.status` 随之正确）＝E206（`E206.kv:6/:13/:16`）；**rec_approach 已执行、字面工具未执行**＝E122（`:29/:33` 的 `linux-ohos*` 白名单以 0002 补丁落地而非 `sed -i`）、E007（`:34 patch-autotools-script` 已执行＝0001；`:40` 的 `perl scripts/patch-autotools-ohos.pl` **未采用**且实测失败，见「已试过的失败方案」第 2 条）、E072（`:13` 根因＝0002 所打处）；**仅根因命中、处方未采用 ⇒ 不计入「按处方执行」**＝E136（`E136.kv:5` 的 `umask 077 + SGID ⇒ drwx--S---` 模式串与本包实测逐字相同，但 `:8 rec_command` 走「把 mktemp 重定向到 `$TMPDIR/confXXXXXX`」这条**本包没有采用**的不同解法——本包用的是 E011/E206 的 umask 改法）。另执行：§3.6（优先级②改生成件）、R47（c↔cpp 兼容族）、R38/PF8（commands.json）、R39/PF7（SourceForge 官方源）。三条 `forbid_1` 均遵守，但**各按其原文判据**（此前把 E072 那条写成「禁 `--build=`/`--host=`」是错引）：`E007.kv:45` 与 `E122.kv:37` 的 `forbid_1_pattern` 确为 `--build=*|--host=*` ⇒ 本包未传三元组参数，遵守；`E072.kv:53` 的 `forbid_1_pattern` 实为「手动修改 configure.ac 中的 host_alias 绕过」（`:54` 的理由是 host_alias 只临时覆盖、不解决 config.sub 的验证问题），**与三元组参数无关** ⇒ 本包对它的遵守由「没碰 `configure.ac`」举证，而不是「没传 `--build/--host`」。两条独立举证：**①未碰 `configure.ac`**——四个补丁的目标文件只有 `config.guess`、`config.sub`、`configure`、`yasr/yasr.h`（各件第 1 行的 `--- a/…` 头：`patches/0001-config.guess.patch:1`、`patches/0002-config.sub.patch:1`、`patches/0003-configure.patch:1`、`patches/0004-yasr-yasr.h.patch:1`），无 `configure.ac`；**②未传 `--build`/`--host`/`--target`**——一手命令行 `reports/w3-local-ci.log:183` 的 `configure` 只带 `--prefix=/` 与 `bindir`/`sbindir`/`libdir`/`includedir`/`oldincludedir` 五项目录参数（合计 6 个），无三元组参数；配方侧 `generate()` 只有 `AutotoolsToolchain(self)`（`conanfile.py:87`）+ `tc.generate()`（`conanfile.py:92`），`conanfile.py:88`–`:91` 是记述该取舍的注释文字。
- **知识库扩展**：本 PR 未创建草稿、未建 Issue；第 1 棒在此处写的「对 E060 的归因与处方提出**否证证据**」**已撤回**——实况是 E060 的 tmpfs 处方在本机**从未被执行**（`$HOME` 自身即 hmdfs、且无可写的真 tmpfs）⇒ **既未证实也未否证（证据不足）**，详见「已试过的失败方案」第 1 条。本 PR **不主张任何条目更正**；E060 的两处可披露缺陷（`$HOME/tmp` 落点写错、`mount | grep hmdfs` 假阳性）留主理／框架窗走独立 KB PR。B 判定归主理。
- **关联 Issue**：无（本棒未建）。

### 对话 #1（子代理 主理-64，第 1 棒）
- 完成：定源（三向同哈希，官方址 == Debian `.orig` 逐字节）→ recipe-search（6174 条无相似配方）→ 图谱检索（E007/E072/E122/E011/E060/E206/E136 命中）→ init-build 骨架（check_env 假红后补 `.build-context` 续做）→ lang-preflight 通过（c↔cpp 兼容族）→ 四处源码级修改 → `refresh-patch --auto` 出 4 补丁 → 探索构建 configure/make/install 全绿（产物断言 6/6）→ 交付件（conanfile / conandata / 两级 manifest / README / commands.json / test_package / notes）→ **conan-verify 判绿三一致（VERIFY_RC=0 + 报告 `**Verdict**: PASS` + G0–G3 文字 PASS）** → test_package 5/5 实测通过 → 提交并推送 `feat/yasr-0.6.9`。
- 未做（按本棒范围划界）：`finish`（W3，写 `.ci-result.json`）、W4 独立审计、建 PR、平台动作、登记表——**全部归主理**。
- 下一步唯一动作：主理在本 worktree（B 机 `/storage/Users/currentUser/qzy/主理-64-yasr-0.6.9`，分支 `feat/yasr-0.6.9`）执行
  `python3 scripts/ohc-run.py finish yasr 0.6.9 built`
  走 W2 结构 + R36 依赖 + W3 本地 CI，再派 W4 审计与建 PR；B 终判可依上节台账（M1/M2 有行号级同族条目，M3 需先核 3 份 drafts）。
- 已知待主理裁定的两处口径：①版本级 manifest 现为 `status: built`（工具提示可 published，但 W3 未跑）；②`经验文档/手册/07-技术速查.md:18` 对 `cannot guess build type` 给的是 `--build/--host` 处方，与 E007/E122 的 forbid_1 相反，本包在**不传**这两个参数的情况下已转绿（属文档冲突证据，非本包缺陷；⚠ 该引用件属仓外规则工作区、不随本 PR 出仓，处方原文已在本 notes「已试过的失败方案」第 3 条完整抄出 ⇒ 判据以本 notes 为唯一载体）。
- 断点与证据目录：`/storage/Users/currentUser/tmp/uc2/z64-yasr/STATE.md`（判决三值同记于该文件）。
---

**编译结束**: 2026-09-26 03:23
**最终状态**: built


## 附：W3 互锁读数的仓内载体（补第 4 轮审计唯一 P2；2026-09-26 由主理-64 补写）

`.ci-result.json` 依 `origin/main` 自带的 `.gitignore:238` **有意不随本 PR 出仓**（它同时是 JC1 运行时状态件与 JC5 点前缀隐藏件，随 PR 会把两道 CI 点判红）。为免「互锁读数无仓内载体」，把一手值逐字抄在这里，读者可直接对**跟踪件** `reports/w3-local-ci.log` 复核：

| 字段（取自 `.ci-result.json`） | 值 | 仓内可复核对象 |
|---|---|---|
| `exit_code` | `0` | — |
| `step` | `W3_local_ci` | — |
| `timestamp` | `2026-09-26T03:24:42.197707` | 晚于本包最后一枚构建输入提交 `dbfc976791`（02:58） |
| `log_sha256` | `4a163b555920cc585355d931cac8a17392ba7c51d9f4baac1216b64751c78622` | == 跟踪件 `reports/w3-local-ci.log` 的 `sha256sum` 实算值（本机复算同值 ⇒ 互锁成立，非只比 mtime） |
| 标记计数 | `[step]` = 46、`_RESULT=` = 10 | 同一跟踪件 `grep -c` 即得 |

另附 `finish` 整体 **rc=2** 的归因（⛔ 不得读成"本包构建失败"，也不得读成"finish 全绿"）：

- 失败步骤为 step5b、step8，另有 `STEP_FAILED: Step6`；同轮日志还印 `gen_summary 失败: 'str' object has no attribute 'append'` 与 `知识图谱完整性检查发现 1 类问题`——均属框架侧。
- Step3 的 `G0 干净构建验证` 报 `configure 失败 (exit 1)`，一手错误行原文是 `configure: error: expected an absolute directory name for --prefix:`，后跟一个**未被 harness 展开的模板占位字面量**（该词含 package_folder，为避开门禁的尖括号占位扫描此处不逐字粘贴；原文见 `~/tmp/ohc-verify-yasr-x0q7cpnu/g0-configure.log` 末行，属仓外件）。
- **正对照**：同一现象在本窗 wmcube / socklog / vcdimager 三包的 `finish` 日志里同样出现 ⇒ 判为框架通病，不是本包 configure 真的坏。本包真实构建证据取上表互锁的 W3 日志：`:407` 的 `Created package revision 5d93e898b92ac005425699893b42e2b1` 与 `:178` 的 `Calling build()`（该件随 PR，行号可按）。
- 因此本 PR 的「W3 本地 CI 模拟通过」专指 `ohc-run.py finish` 的 **W3 步骤**（`step=W3_local_ci`、`exit_code=0`），⛔ 不主张 `finish` 十步整体绿。
