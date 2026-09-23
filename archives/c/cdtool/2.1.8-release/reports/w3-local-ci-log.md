# W3 本地 CI 模拟 逐字日志 — cdtool 2.1.8-release

> 运行日志的**逐字转写**（W§6.1：运行日志不入库，证据转逐字 `.md` 留档）。

- 原文件: `reports/w3-local-ci.log`（已删除，不入库）
- 原文件字节数: 24886
- 原文件行数: 458
- 原文件 sha256: `6ce39f822782ac7db64a42ae96e78b97dbdf95e4a77432bebe6d5f272084af8c`
- 生成命令: `conan-verify`/finish 内嵌的 W3 本地 CI 模拟（2026-09-13）

```text
$ setup.sh (RC=0)
[step] Conan environment setup...
[step] Conan version: Conan version 2.29.1
[step] Disabling conancenter (private CI, not needed)
conancenter: https://center2.conan.io [Verify SSL: True, Enabled: False]
[step] remote 已就绪: ohpcd
[step] Importing profile from /storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/ci/conan/profiles/ohos-aarch64
[step] Profile file available at: /storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/ci/conan/profiles/ohos-aarch64
[step] Conan environment ready ✅
[step]   remote: ohpcd
[step]   profile: ohos-aarch64
[step]   conan: Conan version 2.29.1


$ build_and_test.sh archives/c/cdtool/2.1.8-release (RC=0)
[step] Conan build + test pipeline (CI, no AI)
[step]   scan_root: archives
[step]   profile: ohos-aarch64
[step]   channel: (no channel — plain name/version)
[step] Validating package build timeout overrides...
[step] G0: Knowledge graph integrity check...
        [ok] G0: Knowledge graph integrity check passed (540 entries)
G0_RESULT=pass
[step] G0e: Root directory whitelist check...
        [ok] G0e: Root directory whitelist passed
[step] CI_PACKAGES received: archives/c/cdtool/2.1.8-release
[step] Found 1 package(s) to build

━━━ Building: cdtool/2.1.8-release ━━━
[step] L0: Quality gate checks...
[step] L0j: Checking version collision with registry (R37)...
        [ok] version not in registry yet (first publish)
[step] L0k: Checking commands.json for CLI tools (R38)...
        [ok] commands.json valid (type=tool)
[step] L0m: Checking directory structure (R39/L0m-4/L0m-5)...
        [ok] L0m: directory structure valid
[ok] L0: All quality gate checks passed

[step] KC: Knowledge graph quality check...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  知识库质量门禁 (knowledge_check)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  .kv 文件数: 540

[step] KC1: 草稿泄漏检测...
[OK] KC1: 草稿泄漏检测通过

[step] KC2: 模板占位符残留检测...
[OK] KC2: 模板占位符残留检测通过

[step] KC3: rec_auto_fix 格式校验...
[OK] KC3: rec_auto_fix 格式校验通过

[step] KC4: 非标准字段检测...
[OK] KC4: 非标准字段检测通过

[step] KC5: index.tsv 行数一致性...
[OK] KC5: index.tsv 一致 (540 = 540)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Errors: 0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KC_RESULT=pass
KC_ERRORS=0
        [ok] KC: knowledge check passed

[step] JC: Junk file check...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  杂项文件拦截 (junk_check)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  检查模式: prdiff (16 个文件)

[step] JC1: 运行时状态文件检测...

[step] JC2: 二进制产物检测...

[step] JC3: 源码 tarball / 打包产物检测...

[step] JC4: 临时构建产物检测...

[step] JC5: archives 隐藏文件白名单检测...

[step] JC6: PR 单软件原子性检测...
  涉及软件数: 1（合规）

[OK] 未发现杂项文件
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Junk Files: 0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JC_RESULT=pass
JC_ERRORS=0
        [ok] JC: no junk files detected
[step] Pre-download: extracting source URLs from conandata.yml...
  found 1 source URL(s)
  [try 1/1.1/3] cdtool-2.1.8.tar.gz ← https://hinterhof.net/cdtool/dist/cdtool-2.1.8.tar.gz...
  [ok] cdtool-2.1.8.tar.gz (114KB) via mirror 1
  [done] Pre-downloaded 1 files, conandata.yml updated to file:// URLs
[step] Running conan create (output logged to /storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/.ci_logs/conan_build_cdtool_2.1.8-release.log)...

======== Exporting recipe to the cache ========
cdtool/2.1.8-release: Exporting package recipe: /storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/archives/c/cdtool/2.1.8-release/conanfile.py
cdtool/2.1.8-release: exports: File 'conandata.yml' found. Exporting it...
cdtool/2.1.8-release: Calling export_sources()
cdtool/2.1.8-release: Copied 1 '.yml' file: conandata.yml
cdtool/2.1.8-release: Copied 1 '.py' file: conanfile.py
cdtool/2.1.8-release: Copied 3 '.patch' files: 0001-configure-umask-000.patch, 0002-commands-include-fcntl.patch, 0003-cdown-getline-rename.patch
cdtool/2.1.8-release: Exported to cache folder: /storage/Users/currentUser/.conan2/p/cdtoo8d33f60104f02/e
cdtool/2.1.8-release: Exported: cdtool/2.1.8-release#59c7a5a1b075e77d40ee50e39ad80509 (2026-09-12 18:25:10 UTC)

======== Input profiles ========
Profile host:
[settings]
arch=armv8
build_type=Release
compiler=clang
compiler.cppstd=17
compiler.libcxx=libc++
compiler.version=15
os=OHOS
os.version=6.0
[conf]
tools.build:compiler_executables={'c': '/data/service/hnp/bin/clang', 'cpp': '/data/service/hnp/bin/clang++'}
[buildenv]
CONFIG_SHELL=/data/service/hnp/bin/bash
SHELL=/data/service/hnp/bin/bash
PATH=+(path)/storage/Users/currentUser/usr/local/bin
PATH=+(path)/data/service/hnp/bin
LD_LIBRARY_PATH=+(path)/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib

Profile build:
[settings]
arch=armv8
build_type=Release
compiler=clang
compiler.cppstd=17
compiler.libcxx=libc++
compiler.version=15
os=OHOS
os.version=6.0
[conf]
tools.build:compiler_executables={'c': '/data/service/hnp/bin/clang', 'cpp': '/data/service/hnp/bin/clang++'}
[buildenv]
CONFIG_SHELL=/data/service/hnp/bin/bash
SHELL=/data/service/hnp/bin/bash
PATH=+(path)/storage/Users/currentUser/usr/local/bin
PATH=+(path)/data/service/hnp/bin
LD_LIBRARY_PATH=+(path)/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib


======== Computing dependency graph ========
Graph root
    cli
Requirements
    cdtool/2.1.8-release#59c7a5a1b075e77d40ee50e39ad80509 - Cache

======== Computing necessary packages ========
cdtool/2.1.8-release: Forced build from source
Requirements
    cdtool/2.1.8-release#59c7a5a1b075e77d40ee50e39ad80509:6b129b068851896169fae42d399fa922d239ce8a - Build

======== Installing packages ========
cdtool/2.1.8-release: Calling source() in /storage/Users/currentUser/.conan2/p/cdtoo8d33f60104f02/s
cdtool/2.1.8-release: Sources correctly downloaded from file:///storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/.build-cache/predl_cache/77c1b295_cdtool-2.1.8.tar.gz
cdtool/2.1.8-release: Uncompressing 77c1b295_cdtool-2.1.8.tar.gz to .

-------- Installing package cdtool/2.1.8-release (1 of 1) --------
cdtool/2.1.8-release: Building from source
cdtool/2.1.8-release: Package cdtool/2.1.8-release:6b129b068851896169fae42d399fa922d239ce8a
cdtool/2.1.8-release: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
cdtool/2.1.8-release: Copying sources to build folder
cdtool/2.1.8-release: Building your package in /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/b
cdtool/2.1.8-release: Calling generate()
cdtool/2.1.8-release: Generators folder: /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/b/build-release/conan
cdtool/2.1.8-release: Generating aggregated env files
cdtool/2.1.8-release: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
cdtool/2.1.8-release: Calling build()
cdtool/2.1.8-release: Apply patch (portability): autoconf 生成的 configure 用 umask 077 建立 config.status 的临时目录 confstatXXXXXX；OHOS 文件系统上 0700 目录对构建进程不可写，config.status 的重定向全部报 Permission denied，config.h/Makefile 未生成，而 configure 自身仍返回 0（静默失败），错误推迟到 make 才以 No targets specified and no makefile found 暴露。改为 umask 000。

cdtool/2.1.8-release: Apply patch (portability): commands.c 使用 open(O_RDONLY | O_NONBLOCK) 但未包含 fcntl.h，其已包含的 sys/file.h 在 OHOS musl 上不引入 fcntl.h，clang 15 报 use of undeclared identifier 'O_RDONLY' / 'O_NONBLOCK'。补 fcntl.h。

cdtool/2.1.8-release: Apply patch (portability): cdown.c 自定义 char *getline(void)（CDDB 文本行读取）与 OHOS musl stdio.h 声明的 POSIX.1-2008 ssize_t getline(char**, size_t*, FILE*) 冲突，clang 15 报 conflicting types for 'getline' 及全部调用点 too few arguments。将自定义函数 及其调用点、注释统一改名为 cdtool_getline。

cdtool/2.1.8-release: RUN: TMPDIR=/storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/b/build-release ./configure --prefix=/ --bindir=/bin --mandir=/share/man
checking for gcc... /data/service/hnp/bin/clang
checking for C compiler default output file name... a.out
checking whether the C compiler works... yes
checking whether we are cross compiling... no
checking for suffix of executables... 
checking for suffix of object files... o
checking whether we are using the GNU C compiler... yes
checking whether /data/service/hnp/bin/clang accepts -g... yes
checking for /data/service/hnp/bin/clang option to accept ANSI C... none needed
checking how to run the C preprocessor... /data/service/hnp/bin/clang -E
checking for egrep... grep -E
checking whether /data/service/hnp/bin/clang needs -traditional... no
checking for a BSD-compatible install... /storage/Users/currentUser/usr/local/bin/ginstall -c
checking whether ln -s works... yes
checking for strip... strip
checking for connect in -lsocket... no
checking for ANSI C header files... yes
checking whether time.h and sys/time.h may both be included... yes
checking for sys/wait.h that is POSIX.1 compatible... yes
checking for sys/types.h... yes
checking for sys/stat.h... yes
checking for stdlib.h... yes
checking for string.h... yes
checking for memory.h... yes
checking for strings.h... yes
checking for inttypes.h... yes
checking for stdint.h... yes
checking for unistd.h... yes
checking getopt.h usability... yes
checking getopt.h presence... yes
checking for getopt.h... yes
checking mntent.h usability... yes
checking mntent.h presence... yes
checking for mntent.h... yes
checking sys/mnttab.h usability... no
checking sys/mnttab.h presence... no
checking for sys/mnttab.h... no
checking ioctl.h usability... no
checking ioctl.h presence... no
checking for ioctl.h... no
checking sys/ioctl.h usability... yes
checking sys/ioctl.h presence... yes
checking for sys/ioctl.h... yes
checking fcntl.h usability... yes
checking fcntl.h presence... yes
checking for fcntl.h... yes
checking sys/cdio.h usability... no
checking sys/cdio.h presence... no
checking for sys/cdio.h... no
checking linux/cdrom.h usability... yes
checking linux/cdrom.h presence... yes
checking for linux/cdrom.h... yes
checking for ioctl CDROMRESET... yes
checking for ioctl CDROMCLOSETRAY... yes
checking for uid_t in sys/types.h... yes
checking for pid_t... yes
checking for size_t... yes
checking return type of signal handlers... void
checking for an ANSI C-conforming const... yes
checking type of array argument to getgroups... gid_t
checking for getgroups... yes
checking for working getgroups... yes
checking for getmntent in -lsun... no
checking for getmntent in -lseq... no
checking for getmntent in -lgen... no
checking for getmntent... yes
checking for strsep... yes
checking for memmove... yes
checking for memset... yes
checking for socket... yes
checking for gethostbyname... yes
checking for library containing gethostbyname... none required
checking whether to disable SCSI code... no
configure: creating ./config.status
config.status: creating Makefile
config.status: creating config.h

cdtool/2.1.8-release: RUN: TMPDIR=/storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/b/build-release make -j1
/data/service/hnp/bin/clang -O3 -Wall -DNDEBUG  -c -o commands.o commands.c
/data/service/hnp/bin/clang -O3 -Wall -DNDEBUG  -c -o hardware.o hardware.c
/data/service/hnp/bin/clang -O3 -Wall -DNDEBUG  -c -o database.o database.c
/data/service/hnp/bin/clang -O3 -Wall -DNDEBUG  -c -o info.o info.c
/data/service/hnp/bin/clang -O3 -Wall -DNDEBUG  -c -o shuffle.o shuffle.c
shuffle.c:239:7: warning: variable 'status' set but not used [-Wunused-but-set-variable]
  int status;
      ^
1 warning generated.
/data/service/hnp/bin/clang -O3 -Wall -DNDEBUG  -c -o util.o util.c
/data/service/hnp/bin/clang -O3 -Wall -DNDEBUG  -c -o cdown.o cdown.c
cdown.c:265:57: warning: format specifies type 'int' but the argument has type 'size_t' (aka 'unsigned long') [-Wformat]
        "truncated message" : "empty message or error", len);
                                                        ^~~
cdown.c:655:22: warning: a function declaration without a prototype is deprecated in all versions of C and is treated as a zero-parameter prototype in C2x, conflicting with a previous declaration [-Wdeprecated-non-prototype]
  extern int    optind, getopt();
                        ^
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/unistd.h:122:5: note: conflicting prototype is here
int getopt(int, char * const [], const char *);
    ^
2 warnings generated.
/data/service/hnp/bin/clang -o cdown  commands.o hardware.o database.o info.o shuffle.o util.o cdown.o 
/data/service/hnp/bin/clang -O3 -Wall -DNDEBUG  -c -o cdtool.o cdtool.c
cdtool.c:71:22: warning: a function declaration without a prototype is deprecated in all versions of C and is treated as a zero-parameter prototype in C2x, conflicting with a previous declaration [-Wdeprecated-non-prototype]
  extern int    optind, getopt();
                        ^
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/unistd.h:122:5: note: conflicting prototype is here
int getopt(int, char * const [], const char *);
    ^
1 warning generated.
/data/service/hnp/bin/clang -o cdtool  commands.o hardware.o database.o info.o shuffle.o util.o cdtool.o 
/data/service/hnp/bin/clang -O3 -Wall -DNDEBUG  -c -o cdctrl.o cdctrl.c
cdctrl.c:252:24: warning: a function declaration without a prototype is deprecated in all versions of C and is treated as a zero-parameter prototype in C2x, conflicting with a previous declaration [-Wdeprecated-non-prototype]
    extern int optind, getopt();
                       ^
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/unistd.h:122:5: note: conflicting prototype is here
int getopt(int, char * const [], const char *);
    ^
1 warning generated.
/data/service/hnp/bin/clang -o cdctrl  commands.o hardware.o database.o info.o shuffle.o util.o cdctrl.o 
/data/service/hnp/bin/clang -O3 -Wall -DNDEBUG  -c -o cdtool2cddb.o cdtool2cddb.c
/data/service/hnp/bin/clang -o cdtool2cddb   cdtool2cddb.o

cdtool/2.1.8-release: Package '6b129b068851896169fae42d399fa922d239ce8a' built
cdtool/2.1.8-release: Build folder /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/b/build-release
cdtool/2.1.8-release: Generating the package
cdtool/2.1.8-release: Packaging in folder /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p
cdtool/2.1.8-release: Calling package()
cdtool/2.1.8-release: RUN: TMPDIR=/storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/b/build-release make install DESTDIR=/storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p -j1
mkdir -p /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/bin
/storage/Users/currentUser/usr/local/bin/ginstall -c cdctrl /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/bin -o root
/storage/Users/currentUser/usr/local/bin/ginstall -c cdloop /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/bin -o root
/storage/Users/currentUser/usr/local/bin/ginstall -c cdadd /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/bin -o root
/storage/Users/currentUser/usr/local/bin/ginstall -c cdown /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/bin -o root
/storage/Users/currentUser/usr/local/bin/ginstall -c cdtool2cddb /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/bin -o root
mkdir -p /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/share/man/man1
/storage/Users/currentUser/usr/local/bin/ginstall -c cdctrl.1 /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/share/man/man1
/storage/Users/currentUser/usr/local/bin/ginstall -c cdloop.1 /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/share/man/man1
/storage/Users/currentUser/usr/local/bin/ginstall -c cdadd.1 /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/share/man/man1
/storage/Users/currentUser/usr/local/bin/ginstall -c cdown.1 /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/share/man/man1
/storage/Users/currentUser/usr/local/bin/ginstall -c cdtool.1 /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/share/man/man1
/storage/Users/currentUser/usr/local/bin/ginstall -c cdtool2cddb.1 /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/share/man/man1
mkdir -p /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p//lib/cdtool
/storage/Users/currentUser/usr/local/bin/ginstall -c cdtool /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p//lib/cdtool -o root
for command in cdplay cdpause cdstop cdclose cdeject cdir cdinfo cdreset cdvolume cdshuffle; do \
  if ! test -h /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/bin/$command; then \
    echo installing $command; \
    rm -f /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/bin/$command; \
    ln -s ../lib/cdtool/cdtool /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/bin/$command; \
  fi; \
  if ! test -h /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/share/man/man1/$command.1; then \
    echo installing $command.1; \
    rm -f /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/share/man/man1/$command.1; \
    ln -s cdtool.1 /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p/share/man/man1/$command.1; \
  fi; \
done
installing cdplay
installing cdplay.1
installing cdpause
installing cdpause.1
installing cdstop
installing cdstop.1
installing cdclose
installing cdclose.1
installing cdeject
installing cdeject.1
installing cdir
installing cdir.1
installing cdinfo
installing cdinfo.1
installing cdreset
installing cdreset.1
installing cdvolume
installing cdvolume.1
installing cdshuffle
installing cdshuffle.1

cdtool/2.1.8-release: package(): Packaged 16 files
cdtool/2.1.8-release: package(): Packaged 16 '.1' files
cdtool/2.1.8-release: Created package revision 798e8658a0e8d646f30fbe3b3367a642
cdtool/2.1.8-release: Package '6b129b068851896169fae42d399fa922d239ce8a' created
cdtool/2.1.8-release: Full package reference: cdtool/2.1.8-release#59c7a5a1b075e77d40ee50e39ad80509:6b129b068851896169fae42d399fa922d239ce8a#798e8658a0e8d646f30fbe3b3367a642
cdtool/2.1.8-release: Package folder /storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p
cdtool/2.1.8-release: cdtool 2.1.8-release: lib/cdtool/cdtool + bin/ 15 项（5 独立产物 + 10 别名符号链接）

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    cdtool/2.1.8-release (test package): /storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/archives/c/cdtool/2.1.8-release/test_package/conanfile.py
Requirements
    cdtool/2.1.8-release#59c7a5a1b075e77d40ee50e39ad80509 - Cache

======== Computing necessary packages ========
Requirements
    cdtool/2.1.8-release#59c7a5a1b075e77d40ee50e39ad80509:6b129b068851896169fae42d399fa922d239ce8a#798e8658a0e8d646f30fbe3b3367a642 - Cache

======== Installing packages ========
cdtool/2.1.8-release: Already installed! (1 of 1)
cdtool/2.1.8-release: cdtool 2.1.8-release: lib/cdtool/cdtool + bin/ 15 项（5 独立产物 + 10 别名符号链接）

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/archives/c/cdtool/2.1.8-release/test_package/build-release
cdtool/2.1.8-release (test package): Test package build: build-release
cdtool/2.1.8-release (test package): Test package build folder: /storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/archives/c/cdtool/2.1.8-release/test_package/build-release
cdtool/2.1.8-release (test package): Generating aggregated env files
cdtool/2.1.8-release (test package): Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
cdtool/2.1.8-release (test package): Running test()
cdtool/2.1.8-release (test package): RUN: python3 "/storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/archives/c/cdtool/2.1.8-release/test_package/test_cdtool.py" "/storage/Users/currentUser/.conan2/p/b/cdtoo445d869223c1b/p"
PASS: lib/cdtool/cdtool 存在且为常规文件（非符号链接）
PASS: lib/cdtool/cdtool 可执行且非空（55744 B）
PASS: ELF 为 64 位小端（ELFCLASS64 + ELFDATA2LSB）
PASS: ELF 目标架构为 AArch64（e_machine=0xB7）
PASS: ELF 类型为 DYN（位置无关可执行 PIE，e_type=3）
PASS: 产物内嵌 OHOS musl 加载器路径 /lib/ld-musl-aarch64.so.1
PASS: 产物不引用 glibc 的 libc.so.6
PASS: bin/ 下 10 个别名符号链接均指向 ../lib/cdtool/cdtool 且可解析
PASS: bin/ 下 5 个独立产物存在且可执行（cdctrl/cdown/cdadd/cdloop/cdtool2cddb）
PASS: share/man/man1 下 16 份手册页且含 cdtool.1
PASS: 10 个别名手册页均为指向 cdtool.1 的符号链接
PASS: 真实运行 cdplay -V rc=0 且输出含 'CDTOOL'
PASS: 真实运行 cdtool -V rc=0 且输出含 'CDTOOL'
PASS: 真实运行 cdctrl -h rc=0 且输出含 'cdctrl'
PASS: 真实运行 cdown -V rc=0 且输出含 'cdown'
PASS: 真实运行 cdtool2cddb -h rc=0 且输出含 'Usage'
NOTE: bin/ 下无 cdtool 入口属上游设计：主程序在 lib/cdtool/cdtool，bin/ 的 10 个别名指向它
NOTE: 上游无自动化测试套件（无 tests/、无 check 目标），TOTAL=0 如实声明；本消费测试为其功能性替代验证
ALL PASS

[ok] cdtool/2.1.8-release — conan create passed
[step] L1: Verifying test execution from conan create log...
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[step] L1c: No upstream make check/ctest in log (may be in test_package only)
[step] L4: Scanning patches for dangerous functions...
[step] L5: Baseline artifact check...
[ok] L5: bin/ has content
[step] L1e: Destructive negative test (R34)...
        [sabotage] bin/ moved away
        [sabotage] lib/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on cdtool
[step] L2: Smoke test (version/help check)...
[warn] L2: cdadd --version/--help failed (non-blocking)
[warn] L2: cdclose --version/--help failed (non-blocking)
[warn] L2: cdctrl --version/--help failed (non-blocking)
[warn] L2: cdeject --version/--help failed (non-blocking)
[warn] L2: cdinfo --version/--help failed (non-blocking)
[warn] L2: cdir --version/--help failed (non-blocking)
[warn] L2: cdloop --version/--help failed (non-blocking)
[warn] L2: cdown --version/--help failed (non-blocking)
[warn] L2: cdpause --version/--help failed (non-blocking)
[warn] L2: cdplay --version/--help failed (non-blocking)
[warn] L2: cdreset --version/--help failed (non-blocking)
[warn] L2: cdshuffle --version/--help failed (non-blocking)
[warn] L2: cdstop --version/--help failed (non-blocking)
[warn] L2: cdtool2cddb --version/--help failed (non-blocking)
[warn] L2: cdvolume --version/--help failed (non-blocking)

L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: cdadd version/help failed, cdclose failed, cdctrl failed, cdeject failed, cdinfo failed, cdir failed, cdloop failed, cdown failed, cdpause failed, cdplay failed, cdreset failed, cdshuffle failed, cdstop failed, cdtool2cddb failed, cdvolume failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
[step] Generating ci-metadata.json...
[ok] ci-metadata.json written

━━━ Build Summary ━━━
  Total:   1
  Success: 1
  Failed:  0
  Pass rate: 100.0% (1/1)
[step] All packages built and tested successfully ✅
[step] Pre-download: conandata.yml 已还原为官方 URL
```
