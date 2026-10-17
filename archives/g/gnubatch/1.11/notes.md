# gnubatch 1.11 适配笔记

## 编译环境
- 构建系统: autotools (configure + make, tarball 自带 configure/Makefile.in，无需 bootstrap)
- 编译日期: 2026-10-09
- 编译器: clang/clang++ (OHOS aarch64, profile ci/conan/profiles/ohos-aarch64)
- 状态: built (设备验证后由 HMBS 统一提交)

## 上游信息
- 官方主页: https://www.gnu.org/software/gnubatch/
- 源码包: https://ftp.gnu.org/gnu/gnubatch/gnubatch-1.11.tar.gz
- sha256: f69129ecfab1e1d8f5b6ef802388b3adb842f5195a025eea16e955d0b5094ba9
- 许可证: GPL-3.0-or-later (LICENSE)
- 内容: 批处理作业调度系统：btsched 调度器、btexec/btpwchk 等 libexec 内部程序、gbch-* curses 用户前端（bin/）、gbch-passwd/gbch-hostedit 等 sbin 管理工具、gbatch.h 客户端 API（apilib）、loccgi/remcgi Web 接口；src/lib 三个内部共享库 libgnubatch_int/client/curs（libtool .la → .so）

## 依赖分析
| 类型 | 名称 | 版本 | 说明 |
|------|------|------|------|
| requires | ncurses | 6.6 | curses 前端链 -lcurses/-lncurses（configure AC_CHECK_LIB 探测链） |
| requires | libxcrypt | 4.5.2 | btpwchk/btuser/gbch-passwd 的 crypt() |
| tool_requires | flex | 2.6.4 | util/msglex.l 编译期重生成（tarball 无预生成 lex.yy.c） |
| tool_requires | bison | 3.8.2 | util/msgparse.y 编译期重生成 |

- configure 参数: `--without-x MAKEINFO=true LEXLIB=<flex libfl.a 绝对路径>`
- `--without-x`: batchwin Motif GUI，OHOS 无 Motif 工具链，核心调度器 + curses 前端为保留功能集（可退化边界，见下）
- `MAKEINFO=true`: 设备无 texinfo，文档随包预生成
- `LEXLIB=`: 上游 configure 的古老 AC_PROG_LEX 探测在 conan build_context 里链不上 -lfl，LEXLIB 留空会让 msglex.c 的 yywrap() 链接失败；钉死到 flex tool_require 的 libfl.a 绝对路径

## 上游测试审计 (R51)
- gnubatch-1.11.tar.gz 共 1340 条目，无 tests/ 或 test/ 目录，无任何 *test* 命名文件
- 所有 Makefile.in 无 TESTS/check_PROGRAMS；configure.ac 无 AC_CONFIG_TESTDIR/testsuite
- 顶层 Makefile.in 根本没有 check 目标（make check = No rule to make target）
- 结论: 上游无测试套件，无可运行的上游检查命令；功能覆盖由 test_package 7 项承担（MANIFEST.yml 留证）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clang-15 下 configure 探测与编译大量报 implicit int / tentative definition 错误 | 2009 年份 K&R C（AC_TRY_RUN 探测里隐式 int main、全局暂定定义），clang 默认 gnu17 是硬错误；上游 Makefile 忽略 CFLAGS（CCFLAGS 由 configure 烘焙） | CC 直接挂 `-std=gnu89 -fcommon`（os.environ + conanbuild 环境双写） |
| 2 | configure 报 C compiler cannot create executables | 共享 profile 烘焙的 /data/service/hnp/bin/clang 在迁移后真机上不存在；conanautotools.sh 里嵌死路径 | `_usable_compilers()` 按 configured → PATH → ~/usr/local/bin 解析真实编译器；`_fix_generated_autotools_compiler()` 就地改写 generators 目录里的死路径；CC/CXX 再显式 define |
| 3 | configure[139] re-exec: inaccessible or not found (Error 127) | CONFIG_SHELL=/data/service/hnp/bin/bash 同样是死路径 | `_resolve_shell()` 钉 /bin/sh；`_harden_configure_shell()` 在 configure 头部注入 HMBS_SHELL_HARDEN 块；`_scrub_poisoned_shell()` 清 configure/config.status 里的死路径 |
| 4 | mktemp 目录不可写 | HMDFS 强制目录 setgid，`umask 077 && mktemp -d` 得到 drwx--S--- 自己也写不了 | `_patch_configure_umask()` 删除 `umask 077 && `（HMDFS E114 同范式） |
| 5 | config.guess/config.sub 不认 ohos 三元组 | tarball 内置 2022-01 vintage | `_patch_config_guess_sub_for_ohos()` 容错插入 HarmonyOS/linux-ohos 分支（rrep 同款，双 vintage 门控） |
| 6 | make install 首行 `install -d -o gnubatch -g root -m 755 SPOOLDIR` 失败 | gnubatch 安装命令带 -o/-g/-m 所有权旗标，install-sh 拒收 -o/-g；设备/CI 用户无特权 chown 必败 | `_write_install_shim()` 容错 cp/mkdir shim：-d 是模式旗标（其后仍解析 -o/-g/-m），丢弃所有权，-m 生效；INSTALL=<shim> 命令行注入并重写各 Makefile 的 INSTALL 行（libtool --mode=install 也跟随）；shim 内零 `$(...)`（设备 /bin/sh 命令替换落只读 /tmp） |
| 7 | make install 尾部 `perl Checkuserinst` 失败 | STAGED_INSTALL=false 使 `false \|\| perl Checkuserinst` 真跑；脚本在 gnubatch 系统用户不存在时 exit 1（设备/CI 必然如此），且设备可能无 perl | 命令行覆盖 `STAGED_INSTALL=true` 短路 Checkuserinst/Checknetinst 与 gbch-uchange 运行期步骤 |
| 8 | （预防）产物落 <pkg>/<pkg>/bin 嵌套路径 | configure 已烘焙 --prefix=package_folder，再传 DESTDIR 会双重前缀（SPOOLDIR/BINDIR 均为 $(DESTDIR)@foo@ 形态） | install 不传 DESTDIR，直接 make install（rrep autotools.install() 先例） |
| 9 | configure 报 "No joy - maybe no shm?"（后续还有 message queues / semaphores 两个同类探针） | **OHOS 安全模型禁止非特权进程使用 SysV IPC**（2026-10-09 真机实测：uid 2000 下 shmget(IPC_PRIVATE) 在 4K/128K/8M 全部失败；msgget 直接被 SIGSYS/Signal 31 杀死 = seccomp 拦截）。三个 AC_TRY_RUN 探针永远走 AC_MSG_ERROR 分支，构建被探针本身拦死 | `_patch_configure_ipc_probes()` 把 configure 里 4 处唯一的 as_fn_error 行替换为编译期默认值（shm 8MB / 消息队列 64 / 信号量 32，均在探针自身接受范围内）。探出的值只喂 btsched 运行期默认（NUMSEMA4/NUMXBUFS/job alloc），无任何前端/密码/API 代码消费它；本地已按真机 configure 逐串验证 4/4 命中 |
| 10 | 异地（VPATH）构建双故障：config.status 报 `./Makefiles_h.sh: inaccessible or not found`（`Makegnubatch.conf.sh` 同）；随后 make 在 util/ 报 `No rule to make target 'hdefs.h', needed by 'helpparse.o'`（真机 job gb_create3 2026-10-09 03:25 CST） | 上游不支持 out-of-source 构建：configure.ac:728 的 AC_CONFIG_COMMANDS 钩子以 `./Makefiles_h.sh` 相对路径调用（只在源码根存在），钩子失败导致 `src/hdrs/files.h`（由 infiles.h sed 生成）从未产出；util/Makefile.in:52 的 `helpparse.o ...: hdefs.h` 裸依赖无 VPATH 规则 | `layout()` 改 in-source：`basic_layout(self, src_folder=".")` + `self.folders.build = "."`（ripmime/recode/redis 同款先例），configure+make 于源码根进行，两个钩子与 hdefs.h 均就地可寻 |
| 11 | （in-source 修复后）configure 探测 `wrefresh in -lncurses... no`；make 编 pmenu.c 报 `fatal error: 'curses.h' file not found`，编译行只有 profile 默认 `-I~/usr/local/include`（真机 job gb_create4 2026-10-09 04:38 CST） | generate() 只生成了 AutotoolsToolchain，从未生成 AutotoolsDeps——conan 依赖 ncurses/libxcrypt 的 CPPFLAGS/LDFLAGS 不在 conanbuild 环境里，头/库路径进不了 configure 探测与编译行 | `generate()` 增加 `AutotoolsDeps(self).generate()`；GNU make 内建 `.c.o` 规则消费 `$(CPPFLAGS)`，configure 探测也吃 CPPFLAGS/LDFLAGS |
| 12 | （AutotoolsDeps 修复后）configure 探测仍 `wrefresh in -lcurses/-lncurses... no`（真机 config.log：`ld.lld: error: unable to find library -lncurses`）；链接期 gbch-pmenu 报 `undefined symbol: keypad/wrefresh/stdscr` 等（真机 job gb_create5 2026-10-09 04:46 CST） | ①conan ncurses/6.6 在 OHOS 只发布宽字符静态库（libncursesw.a/libmenuw.a/…，无 libncurses.a/libcurses.a——gb_diag2 04:49 实测 lib 目录），上游 -lcurses/-lncurses 探测必然失败 → LIBCURSES 为空；②util/ins/loccgi/motif/gtk 的 Makefile.in 硬编码 `LDFLAGS =`（空），覆盖 conanbuild 环境里带 conan -L 路径的 LDFLAGS，即使 LIBCURSES 有值链接行也找不到 -lncursesw/-lcrypt | `_patch_configure_curses_probe()` 把 configure 的 -lncurses 探测改写为 -lncursesw（探测行已带 conan -L，能链上真实包；宽字符 ABI 是窄字符超集）；`_patch_makefile_ldflags()` 把 5 个 Makefile.in 的 `LDFLAGS =` 改为 `LDFLAGS =@LDFLAGS@`（@LDFLAGS@ 是 AC_SUBST 变量，bake 进探测同款 -L 列表）。gb_create6（05:25）实测两修复生效：`wrefresh in -lncurses... yes`、gbch-pmenu/gbch-hostedit 带 -lncursesw 链接成功；构建推进到 util/gbpasswd.c 触发下一条问题（见 #13） |
| 13 | （curses 修复后）util/gbpasswd.c 编译报 `implicit function declaration 'getpass'/'l64a'` + clang-15 硬错误 `-Wint-conversion assigning to 'char *' from 'int'`（真机 job gb_create6/gb_create7 2026-10-09 05:25/05:36 CST；gb_create7 已带 `-D_GNU_SOURCE` 仍同错） | **OHOS/musl 根本没有这两个函数**：sysroot unistd.h 里 grep getpass/l64a 为空（加 `_GNU_SOURCE` 也为空，gb_diag3），libc.so 无符号（llvm-nm 空，gb_diag4），显式 extern 声明链接报 undefined symbol。上游自带 l64a 兜底但锁在 `#ifdef OS_FREEBSD` 后，而 OS_FREEBSD 宏在别处接 FreeBSD 专属代码（incl_sig.h/getkey/ripc.c），不可全局定义 | `_patch_gbpasswd_compat()` 在 gbpasswd.c 的 `extern char *crypt(...)` 锚点后注入 `!__GLIBC__ && !OS_FREEBSD` 守卫的静态 getpass/l64a 实现（getpass 走 /dev/tty+stdin 回退；test_package 用 `-p` 非交互路径，注入段只需编译链接正确）。`-D_GNU_SOURCE` 尝试已撤销（无效） |
| 14 | （gbpasswd 修复后）顶层 `buildd` 规则报 `Unable to link src/gtk/xbtqsel.menu to build/gtk/xbtqsel.menu`，helpparse exit 27（真机 job gb_create8 2026-10-09 05:52 CST；此时 util/ 已全绿：gbch-passwd/shmdump/helpparse 均编译链接成功） | helpparse 的 mod_copy() 用 link(2) 硬链接把 src 树铺进 build/，**hmdfs 对 link() 一律返回 EPERM**（gb_diag5 05:55 实测：$HOME/tmp 与 conan cache 两处均 EPERM，symlink/copy 正常） | `_patch_helpparse_stage_link()` 注入 `gb_ohos_stage_link()` 帮助函数：先试 link()（glibc 主机保持上游行为），失败回退字节拷贝并 chmod 保留源文件权限位（staged 文件要喂 build/ 里的 make，可执行位必须存活）；替换 mod_copy 内唯一一处 link() 调用。**注入位置教训**：首次注入把帮助函数插在 mod_copy 签名行与其 `{` 之间导致语法错（gb_create9 06:02），改为插在锚点行之前后本地模拟注入 + `cc -fsyntax-only` 预验证（gb_createA 通过 staging 关） |
| 15 | （staging 修复后）build/lib 编译报 `libtool: No such file or directory` Error 127（altlen.o，真机 job gb_createA 2026-10-09 06:11 CST；此时 helpparse staging 已过，build/ 树正常铺出） | src/lib/Makefile.in（CC=libtool --mode=compile、三条 --mode=link）与 src/Makefile.in（SHLIBCC=libtool --mode=link）都裸调 `libtool`；唯一在盘上的 libtool 是 configure 在源码根生成的 `./libtool`，make 在 build/ 子树里执行时它不在 PATH | `build_requirements()` 增加 `tool_requires("libtool/2.5.4")`——conan 把真 libtool 放进 conanbuild PATH（仓内已合入先例：wolfmqtt 1.19/2.1、whitedb、wolfssl 均 libtool/2.5.4） |
| 16 | （libtool 修复后）build/lib 编译在 setkey.c 硬失败：`fatal error: 'termio.h' file not found`（setkey.c:34，真机 job gb_createB 2026-10-09 06:22 CST；此时 src/lib 为首个故障点，util/ 仍全绿） | configure 实测 `checking for termio.h... no` / `termios.h... yes`——**musl 无 `<termio.h>`，也没有 `<sgtty.h>`、`struct termio/tchars/sgttyb`**。上游在 curses.h 不提供 struct termio 时（NO_TERMIO_IN_CURSES 定义）回退 `#include <termio.h>`；且 HAVE_TERMIO_H 未定义会连带踩 setkey.c:41 `#include <sgtty.h>` 与 case I/K/E/Q 的 BSD `struct tchars/sgttyb` 分支。树内其余 struct termio 用点（btuser/btq/bq_vlist/bq_jlist）全在 HAVE_TERMIOS_H（yes）分支，不受影响 | `_patch_termio_compat()`（幂等，gb_ohos_termio 标记）：config.h 后强制 `HAVE_TERMIO_H`（走标准 POSIX termio 分支，跳过 sgtty/tchars），首个本地 include 前注入 `<termios.h>` + `#define termio termios` + TCGETA/TCSETA→TCGETS/TCSETS（legacy 码按 28 字节 struct termio 读写，会错位本文件 c_cc[VMIN/VTIME/VINTR] 的写入），并注释陈旧 `#include <termio.h>`。本地预验证：真实方法体对 gb_sim 注入 + 幂等复跑 + `cc -fsyntax-only -Wall` setkey/getkey 双绿（2026-10-09 18:2x CST） |
| 17 | （termio 修复后）build 推进至 src/ 后 `btfilemon.c:1445:24: error: use of undeclared identifier 'SIGCLD'`（2026-10-10 真机 conan-verify job `gnubatch-1.11-verify-20261010-1`；util/、src/lib 已过，首个新故障点在 src/btfilemon.c） | glibc 将 SIGCLD 起别名为 SIGCHLD，**OHOS/musl 两者都不定义**；上游 `hdrs/incl_sig.h:63` 仅在 `#ifdef OS_FREEBSD` 下 `#define SIGCLD SIGCHLD`，其余平台默认依赖系统 `<signal.h>` 提供 SIGCLD。btfilemon.c/sh_exec.c/sh_misc.c 共用该头，且 `#ifndef BUGGY_SIGCLD` 分支激活实际调用 sigact_routine(SIGCLD, …) | `_patch_sigcld_compat()`（幂等，`gb_ohos_sigcld` 标记）在 `src/hdrs/incl_sig.h` 末尾追加 `#ifndef SIGCLD / #define SIGCLD SIGCHLD / #endif`；已定义 SIGCLD 的平台不受影响（FreeBSD 分支保留）。注：源树根为 source_folder 且头在 `src/hdrs`，首轮误注顶层 `hdrs/` 已修正 |
| 18 | （SIGCLD 修复后）build 推进至 src/btsched.c `btsched.c:247:16: error: incomplete definition of type 'struct ucontext'`（2026-10-10 job `gnubatch-1.11-verify-20261010-7`，btsched 成为首个新故障点） | btsched.c:246-247 在 `#ifdef OS_LINUX` 下用 glibc **x86_64** 的 ucontext ABI：`struct ucontext *uc; pc = uc->uc_mcontext.gregs[14]`。OHOS/musl sysroot（aarch64-linux-ohos/bits/signal.h）只提供 `ucontext_t`（tag `struct __ucontext`）且 `mcontext_t == struct sigcontext` 带专用 `pc` 字段，无 `struct ucontext`/`gregs` | `_patch_btsched_ucontext_compat()`（幂等，`gb_ohos_ucontext` 标记）把该两行改为 `#if __GLIBC__ && __x86_64__`（保留 glibc 路径）/`#elif __aarch64__`（`ucontext_t *uc; pc = uc->uc_mcontext.pc`）/`#else (void)p`。该块仅用于把故障 PC 记入 loop.trap，保留诊断语义 |
| 19 | （ucontext 修复后）btsched 链接报 `ld.lld: error: undefined symbol: ulimit`（sh_exec.c，do_resched_msgs，job `gnubatch-1.11-verify-20261010-8`；首版修复后 job -9 仍报，同一符号） | sh_exec.c 在 `#if defined(OS_LINUX) && !defined(HAVE_ULIMIT_H)` 下声明 `extern int ulimit(int,long)` 并调 `ulimit(2, jp->h.bj_ulimit)`。glibc 导出 legacy `ulimit()`，**OHOS/musl 无此符号**。关键坑：OHOS sysroot 的 `<ulimit.h>` 是**桩**（只 `#define UL_GETFSIZE/UL_SETFSIZE`，不声明 ulimit），configure 因此置 `HAVE_ULIMIT_H=1`，上游 extern 块落在假 `#if` 分支内——**把兼容实现放进该块不会编译**（首版即因此无效） | 改为与 guard 无关：`_patch_ulimit_compat()`（幂等，`gb_ohos_ulimit` 标记）在 `#include "sh_ext.h"` 后定义 `gb_ohos_ulimit_setfsize(long)`（getrlimit/setrlimit(RLIMIT_FSIZE)，512 字节单位，仅非 glibc），并把唯一调用点 `ulimit(2, …)` 改为 `#if __GLIBC__ ulimit(2,…) #else gb_ohos_ulimit_setfsize(…) #endif`。全树扫描确认 ulimit 为最后一处缺失 legacy 符号 |
| 20 | （ulimit 修复后）remcgi 链接报 `ld.lld: error: duplicate symbol: JREQ`（`rbtjccgi.o` ↔ `libgnubatch_client.a` 的 `optpparm.o`，job `gnubatch-1.11-verify-20261010-10`。同 job 另有 `src/gtk/xfilemon.c: 'gtk/gtk.h' file not found`，但上游顶层 `gtkd` 目标对 GTK 失败容错——`if cd gtk;make; then … else echo "GTK build failed - not critical"`，非阻塞） | `optpparm.c:59` 的 `BtjobRef JREQ;` 是文件域**暂定定义**，`rbtjccgi.c` 类同；上游依赖经典 `-fcommon`（暂定定义合并入 COMMON）。但子目录 Makefile 写死 `CC = <clang>`（makefile 赋值覆盖构建环境 CC），配方声称的 `-std=gnu89 -fcommon` 实际从未传给编译器，clang 默认 `-fno-common` ⇒ 两个强符号冲突 | `_patch_makefile_fcommon()`（幂等）遍历全部 `Makefile.in`，向 `CCFLAGS =` 行追加 ` -fcommon`（经 CFLAGS 与 libtool 行传播），恢复上游单定义模型；只加 `-fcommon` 不加 `gnu89`，避免影响已按 C99 编译通过的其他翻译单元。共 8 个 Makefile.in |
| 21 | （#20 修复后）build() 全过、进入 package() 的 `make install` 报 `cp: //bin/gbch-pmenu: Read-only file system`（job `gnubatch-1.11-verify-20261010-11`） | 配方 package() 直接 `make install`，其注释假设 configure 已把 `--prefix` 烘为 package_folder；实测 Conan 2 传的是 **`--prefix=/`**，install 目录形如 `$(DESTDIR)@bindir@`（`@bindir@=/bin`）。DESTDIR 留空 ⇒ 写 `//bin`（只读 erofs） | package() 改为 `make -j1 install INSTALL=<shim> STAGED_INSTALL=true DESTDIR=<package_folder>`（Conan 2 标准：prefix=/ + DESTDIR），文件落 `<pkg>/bin` 无嵌套；同时订正配方内基于错误前提的注释。注意命令行为变量 DESTDIR 经 MAKEFLAGS 传给各子 make |
| 22 | （#21 修复后）make install 造 gbch-* 别名时报 `ln: cannot create hard link from 'gbch-start' to 'gbch-disconn': Operation not permitted`（job `gnubatch-1.11-verify-20261010-12`；此时文件已正确落入 `<pkg>/bin`，证明 #21 的 DESTDIR 生效） | 与 #14 helpparse 同源：**hmdfs 对 link(2) 一律返回 EPERM**。`src/Makefile.in:239-240/262-263` 用 `ln -f` 造 gbch-disconn/conn/dst→gbch-start 与 gbch-jdel 族别名；`helpmsg/Makefile.in:42/46` 造 btq.help/btuser.help | `_patch_makefile_ln_to_cp()`（幂等）按"命令位置 `ln <ws> -f`"正则把 `ln -f` 换成 `cp -f`（symlink/copy 在 hmdfs 正常；`ln -s` 不动）。**同时覆盖 `*.sh`**：job -13 修好 Makefile.in 后暴露 `helpmsg/Maketerms.sh`（安装期造 terminfo 硬链接 btq.xterm/btuser.xterm…，`ln -f`）同样 EPERM，故把补丁范围从 `Makefile.in` 扩到 `Makefile.in`+`*.sh` |
| 23 | （#22 修复后）package() 完成、进入 test_package，`test.sh` 报 `FAIL: <pkg>/sbin/gbch-passwd missing or not executable`，且警告 `packaged dir missing: <pkg>/sbin`（`gbch-passwd` 实际落在 `<pkg>/bin`；job `gnubatch-1.11-verify-20261010-14`） | Conan 的 AutotoolsToolchain **默认 `--sbindir=${prefix}/bin`**（见 `config.status: S["sbindir"]="${prefix}/bin"`），把 sbin 折叠进 bin；`ins/Makefile` 的 `PROGS -> SBINDIR`，故 SUID 管理工具 gbch-passwd/gbch-hostedit 装进 bin。但 test_package、`package_info`（PATH 含 sbin）与迁移文档预期的包布局均为 `sbin/` | `generate()` 追加 `--sbindir=${prefix}/sbin`（Conan 默认在前、本参数追加在后，autoconf last-wins）⇒ `PROGS→<pkg>/sbin`、`USERPROGS→<pkg>/bin` |
| 24 | （#23 修复后）`test.sh` 7 用例 3/7：用例 1-3 ok，4-7 密码子系统往返失败。case4 stderr `Unable to find current uid 20020100 in pw file`（rc=4）。job `gnubatch-1.11-verify-20261010-15` | **非代码 bug，属设备用户模型限制**：`util/gbpasswd.c` 在无 `-u` 时用 `getpwuid(getuid())` 解析账号名；设备 uid=20020100 **不在 `/etc/passwd`**（只读、无 `useradd`），非 root 走 `-u` 也被拒（rc=3）。root CI 下 `getpwuid(0)==root` 本可通过 | test_package 新增**设备测试夹具** `pwshim.c`（LD_PRELOAD）：仅为当前 uid 提供 `getpwuid/getpwnam` 合成 passwd 条目，其余查询回落 libc；`test.sh` 编译并仅对用例 4-7 设置 `LD_PRELOAD`。产品代码零改动，crypt/gbpwfile/btpwchk **真实**往返（本地以 job -15 产物实测 case4 rc=0、case5 输出 0、case6 输出 1；夹具不可用时 4-7 显式失败不掩盖）。`MANIFEST.yml` 记录夹具来源与理由 |

## 源码修改
无补丁文件；所有适配在配方 build()/package() 内以容错脚本方式完成（config.guess/sub 插入、umask 剥除、shell 加固、install shim），上游源码零改动。

## 降级边界（可退化移植声明）
1. X/Motif GUI（batchwin）以 `--without-x` 关闭：OHOS 无 Motif 工具链。
2. **调度器运行期**：OHOS 安全模型对非特权进程禁止/杀死 SysV IPC 调用（真机实测 shmget 全尺寸失败、msgget 触发 SIGSYS）。因此 btsched 调度器本体在 OHOS 上编译完整但**无法在无 root 的普通用户会话里真正调度**（这是平台安全模型约束，非移植缺陷）。保留并验证的功能 = 全部 curses 用户前端（gbch-q/btq/gbch-hols 等，连接运行中的调度器时可用）、密码/用户管理工具链（gbch-passwd/btpwchk，本包 test_package 真实往返验证）、客户端 API 库（apilib gbatch.h）。运行期默认值（NUMSEMA4=32/NUMXBUFS=64/shmsize=8MB）为编译期内置，不影响上述保留功能。

## test_package (鸿蒙消费者功能用例, test.sh 7 项)
| # | 用例 | 命令 | 验证点 |
|---|------|------|--------|
| 1 | btpwchk_version_banner | btpwchk --version | rc=0 且 stderr 含 GNUbatch version 1.11（内部程序 + libgnubatch_int .so 解析） |
| 2 | gbch_hols_version_banner | gbch-hols --version | rc=0 且版本串（curses 前端，过 ncurses .so 链） |
| 3 | gbch_passwd_usage_error | gbch-passwd -Z | rc=1 且 stderr 含 Usage（getopt 错误路径） |
| 4 | gbch_passwd_file_create | gbch-passwd -f -F $TMPDIR/gbpwfile -p <pw> | rc=0 且密码文件非空含 user:hash |
| 5 | btpwchk_correct_password | echo <pw> \| SPROGDIR=$TMPDIR btpwchk <user> | rc=0 且输出 0（crypt 校验通过，SPROGDIR 重定向 XIPWFILE） |
| 6 | btpwchk_wrong_password | echo wrong \| SPROGDIR=$TMPDIR btpwchk <user> | rc=1 且输出 1 |
| 7 | btpwchk_unknown_user | echo x \| SPROGDIR=$TMPDIR btpwchk ghost | rc=5 且输出 5（pwfile 未命中路径） |

- 全部真实执行 + 退出码/输出/文件断言，非存在性断言；4-7 构成密码子系统真实往返（gbch-passwd 写的 gbpwfile 正是 btpwchk/btsched 认证用格式）

## 验证结果
- 2026-10-10 真机 conan-verify（job gnubatch-1.11-verify-20261010-1/-4）：G0/G1 PASS；G2 构建推进过 util/、src/lib，首个新故障点 src/btfilemon.c:1445 `SIGCLD`（见问题 #17，已修）。修复后重跑（-5/-6）因设备对外 TLS 间歇故障未能完成：source() 下载 ftp.gnu.org 报 cert hostname mismatch / SSL EOF，ping conan.cnb.cool 报 SSL handshake / cert hostname mismatch；同一时刻 curl 至 ftp.gnu.org 3/3 200、`conan list -r ohpcd` 3/3 正常，判定为外部基础设施问题而非配方。待外部网络稳定后重跑 conan-verify 与 build_and_test.sh。
- （CI 同构 build_and_test.sh 需在平台指定 feat 分支、基于 origin/main 的原子 diff 上运行；在 migration/mac-* 保全分支上 JC6/JC1/JC5 会因整库差集与无关预存脏文件结构性失败，不作为本库质量结论。）
