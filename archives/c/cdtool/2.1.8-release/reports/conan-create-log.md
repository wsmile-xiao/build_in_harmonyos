# conan create 逐字日志 — cdtool 2.1.8-release

> 本文件是运行日志的**逐字转写**（W§6.1：运行日志不入库，证据转逐字 `.md` 留档）。

- 原文件: `reports/conan-create.log`（已删除，不入库）
- 原文件字节数: 20525
- 原文件行数: 336
- 原文件 sha256: `2404b65116835b409b135b71631265950b11b1a9c31fcf0e75d4f3c7db421115`
- 生成命令（设备实测，2026-09-13）:
  ```bash
  conan create archives/c/cdtool/2.1.8-release \
    -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
  ```
- 说明: 该轮为清缓存后的干净构建（G2 采信轮），日志含 3 条 `Apply patch` 与 `test_package` 执行段。

```text

======== Exporting recipe to the cache ========
cdtool/2.1.8-release@ohpcd/stable: Exporting package recipe: /storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/archives/c/cdtool/2.1.8-release/conanfile.py
cdtool/2.1.8-release@ohpcd/stable: exports: File 'conandata.yml' found. Exporting it...
cdtool/2.1.8-release@ohpcd/stable: Calling export_sources()
cdtool/2.1.8-release@ohpcd/stable: Copied 1 '.yml' file: conandata.yml
cdtool/2.1.8-release@ohpcd/stable: Copied 1 '.py' file: conanfile.py
cdtool/2.1.8-release@ohpcd/stable: Copied 3 '.patch' files: 0001-configure-umask-000.patch, 0002-commands-include-fcntl.patch, 0003-cdown-getline-rename.patch
cdtool/2.1.8-release@ohpcd/stable: Exported to cache folder: /storage/Users/currentUser/.conan2/p/cdtooffea4b2184563/e
cdtool/2.1.8-release@ohpcd/stable: Exported: cdtool/2.1.8-release@ohpcd/stable#3ff64316d19bee10c1edeec46af2997d (2026-09-12 18:13:56 UTC)

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
    cdtool/2.1.8-release@ohpcd/stable#3ff64316d19bee10c1edeec46af2997d - Cache

======== Computing necessary packages ========
Connecting to remote 'ohpcd' anonymously
cdtool/2.1.8-release@ohpcd/stable: Main binary package '6b129b068851896169fae42d399fa922d239ce8a' missing
cdtool/2.1.8-release@ohpcd/stable: Checking 11 compatible configurations
cdtool/2.1.8-release@ohpcd/stable: Compatible configurations not found in cache, checking servers
cdtool/2.1.8-release@ohpcd/stable: '7a45daa5a53e1e1e2f88f46c8c5d42c55b8041f7': compiler.cppstd=98
cdtool/2.1.8-release@ohpcd/stable: '82803953774dd8ef49af18e200a16f3642cfae9d': compiler.cppstd=gnu98
cdtool/2.1.8-release@ohpcd/stable: '8ac2a79ad39b36194df9085b36c9d86fa5599f02': compiler.cppstd=11
cdtool/2.1.8-release@ohpcd/stable: '7f9f31995579bd0e1e9a725bfd253c9c7553a331': compiler.cppstd=gnu11
cdtool/2.1.8-release@ohpcd/stable: '20ce5ca62dba04ef245a37652eafaea893be3909': compiler.cppstd=14
cdtool/2.1.8-release@ohpcd/stable: '1c21bc3ded24ff47b1a195f6cb801f864247735c': compiler.cppstd=gnu14
cdtool/2.1.8-release@ohpcd/stable: 'eda5abb401cbed7c3f6f2ad04bfecec451641886': compiler.cppstd=gnu17
cdtool/2.1.8-release@ohpcd/stable: '69cb9bbff6b978dbd5b9122e0a14671a692c43e9': compiler.cppstd=20
cdtool/2.1.8-release@ohpcd/stable: '57551ed2580a3a49716d342ade5714c03470032d': compiler.cppstd=gnu20
cdtool/2.1.8-release@ohpcd/stable: 'da04b77fe39bcbcfe9926450ff73c2349d9b48b8': compiler.cppstd=23
cdtool/2.1.8-release@ohpcd/stable: '1c92d4b02dd3fd6c66325064d993005ded38ba97': compiler.cppstd=gnu23
cdtool/2.1.8-release@ohpcd/stable: No compatible configuration found

A new experimental approach for binary compatibility detection is available.
    Enable it by setting the core.graph:compatibility_mode=optimized conf
    and get improved performance when querying multiple compatible binaries in remotes.

Requirements
    cdtool/2.1.8-release@ohpcd/stable#3ff64316d19bee10c1edeec46af2997d:6b129b068851896169fae42d399fa922d239ce8a - Build

======== Installing packages ========
cdtool/2.1.8-release@ohpcd/stable: Calling source() in /storage/Users/currentUser/.conan2/p/cdtooffea4b2184563/s
cdtool/2.1.8-release@ohpcd/stable: Sources correctly downloaded from https://hinterhof.net/cdtool/dist/cdtool-2.1.8.tar.gz
cdtool/2.1.8-release@ohpcd/stable: Uncompressing cdtool-2.1.8.tar.gz to .

-------- Installing package cdtool/2.1.8-release@ohpcd/stable (1 of 1) --------
cdtool/2.1.8-release@ohpcd/stable: Building from source
cdtool/2.1.8-release@ohpcd/stable: Package cdtool/2.1.8-release@ohpcd/stable:6b129b068851896169fae42d399fa922d239ce8a
cdtool/2.1.8-release@ohpcd/stable: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
cdtool/2.1.8-release@ohpcd/stable: Copying sources to build folder
cdtool/2.1.8-release@ohpcd/stable: Building your package in /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/b
cdtool/2.1.8-release@ohpcd/stable: Calling generate()
cdtool/2.1.8-release@ohpcd/stable: Generators folder: /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/b/build-release/conan
cdtool/2.1.8-release@ohpcd/stable: Generating aggregated env files
cdtool/2.1.8-release@ohpcd/stable: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
cdtool/2.1.8-release@ohpcd/stable: Calling build()
cdtool/2.1.8-release@ohpcd/stable: Apply patch (portability): autoconf 生成的 configure 用 umask 077 建立 config.status 的临时目录 confstatXXXXXX；OHOS 文件系统上 0700 目录对构建进程不可写，config.status 的重定向全部报 Permission denied，config.h/Makefile 未生成，而 configure 自身仍返回 0（静默失败），错误推迟到 make 才以 No targets specified and no makefile found 暴露。改为 umask 000。

cdtool/2.1.8-release@ohpcd/stable: Apply patch (portability): commands.c 使用 open(O_RDONLY | O_NONBLOCK) 但未包含 fcntl.h，其已包含的 sys/file.h 在 OHOS musl 上不引入 fcntl.h，clang 15 报 use of undeclared identifier 'O_RDONLY' / 'O_NONBLOCK'。补 fcntl.h。

cdtool/2.1.8-release@ohpcd/stable: Apply patch (portability): cdown.c 自定义 char *getline(void)（CDDB 文本行读取）与 OHOS musl stdio.h 声明的 POSIX.1-2008 ssize_t getline(char**, size_t*, FILE*) 冲突，clang 15 报 conflicting types for 'getline' 及全部调用点 too few arguments。将自定义函数 及其调用点、注释统一改名为 cdtool_getline。

cdtool/2.1.8-release@ohpcd/stable: RUN: TMPDIR=/storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/b/build-release ./configure --prefix=/ --bindir=/bin --mandir=/share/man
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

cdtool/2.1.8-release@ohpcd/stable: RUN: TMPDIR=/storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/b/build-release make -j1
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

cdtool/2.1.8-release@ohpcd/stable: Package '6b129b068851896169fae42d399fa922d239ce8a' built
cdtool/2.1.8-release@ohpcd/stable: Build folder /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/b/build-release
cdtool/2.1.8-release@ohpcd/stable: Generating the package
cdtool/2.1.8-release@ohpcd/stable: Packaging in folder /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p
cdtool/2.1.8-release@ohpcd/stable: Calling package()
cdtool/2.1.8-release@ohpcd/stable: RUN: TMPDIR=/storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/b/build-release make install DESTDIR=/storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p -j1
mkdir -p /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/bin
/storage/Users/currentUser/usr/local/bin/ginstall -c cdctrl /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/bin -o root
/storage/Users/currentUser/usr/local/bin/ginstall -c cdloop /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/bin -o root
/storage/Users/currentUser/usr/local/bin/ginstall -c cdadd /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/bin -o root
/storage/Users/currentUser/usr/local/bin/ginstall -c cdown /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/bin -o root
/storage/Users/currentUser/usr/local/bin/ginstall -c cdtool2cddb /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/bin -o root
mkdir -p /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/share/man/man1
/storage/Users/currentUser/usr/local/bin/ginstall -c cdctrl.1 /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/share/man/man1
/storage/Users/currentUser/usr/local/bin/ginstall -c cdloop.1 /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/share/man/man1
/storage/Users/currentUser/usr/local/bin/ginstall -c cdadd.1 /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/share/man/man1
/storage/Users/currentUser/usr/local/bin/ginstall -c cdown.1 /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/share/man/man1
/storage/Users/currentUser/usr/local/bin/ginstall -c cdtool.1 /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/share/man/man1
/storage/Users/currentUser/usr/local/bin/ginstall -c cdtool2cddb.1 /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/share/man/man1
mkdir -p /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p//lib/cdtool
/storage/Users/currentUser/usr/local/bin/ginstall -c cdtool /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p//lib/cdtool -o root
for command in cdplay cdpause cdstop cdclose cdeject cdir cdinfo cdreset cdvolume cdshuffle; do \
  if ! test -h /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/bin/$command; then \
    echo installing $command; \
    rm -f /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/bin/$command; \
    ln -s ../lib/cdtool/cdtool /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/bin/$command; \
  fi; \
  if ! test -h /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/share/man/man1/$command.1; then \
    echo installing $command.1; \
    rm -f /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/share/man/man1/$command.1; \
    ln -s cdtool.1 /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p/share/man/man1/$command.1; \
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

cdtool/2.1.8-release@ohpcd/stable: package(): Packaged 16 files
cdtool/2.1.8-release@ohpcd/stable: package(): Packaged 16 '.1' files
cdtool/2.1.8-release@ohpcd/stable: Created package revision f603de1b9c22a7c458c8c05386191cd5
cdtool/2.1.8-release@ohpcd/stable: Package '6b129b068851896169fae42d399fa922d239ce8a' created
cdtool/2.1.8-release@ohpcd/stable: Full package reference: cdtool/2.1.8-release@ohpcd/stable#3ff64316d19bee10c1edeec46af2997d:6b129b068851896169fae42d399fa922d239ce8a#f603de1b9c22a7c458c8c05386191cd5
cdtool/2.1.8-release@ohpcd/stable: Package folder /storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p
cdtool/2.1.8-release@ohpcd/stable: cdtool 2.1.8-release: lib/cdtool/cdtool + bin/ 15 项（5 独立产物 + 10 别名符号链接）

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    cdtool/2.1.8-release@ohpcd/stable (test package): /storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/archives/c/cdtool/2.1.8-release/test_package/conanfile.py
Requirements
    cdtool/2.1.8-release@ohpcd/stable#3ff64316d19bee10c1edeec46af2997d - Cache

======== Computing necessary packages ========
Requirements
    cdtool/2.1.8-release@ohpcd/stable#3ff64316d19bee10c1edeec46af2997d:6b129b068851896169fae42d399fa922d239ce8a#f603de1b9c22a7c458c8c05386191cd5 - Cache

======== Installing packages ========
cdtool/2.1.8-release@ohpcd/stable: Already installed! (1 of 1)
cdtool/2.1.8-release@ohpcd/stable: cdtool 2.1.8-release: lib/cdtool/cdtool + bin/ 15 项（5 独立产物 + 10 别名符号链接）

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/archives/c/cdtool/2.1.8-release/test_package/build-release
cdtool/2.1.8-release@ohpcd/stable (test package): Test package build: build-release
cdtool/2.1.8-release@ohpcd/stable (test package): Test package build folder: /storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/archives/c/cdtool/2.1.8-release/test_package/build-release
cdtool/2.1.8-release@ohpcd/stable (test package): Generating aggregated env files
cdtool/2.1.8-release@ohpcd/stable (test package): Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
cdtool/2.1.8-release@ohpcd/stable (test package): Running test()
cdtool/2.1.8-release@ohpcd/stable (test package): RUN: python3 "/storage/Users/currentUser/ws/worktrees/cdtool-2.1.8-release/archives/c/cdtool/2.1.8-release/test_package/test_cdtool.py" "/storage/Users/currentUser/.conan2/p/b/cdtoo96472d0ac765e/p"
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

```
