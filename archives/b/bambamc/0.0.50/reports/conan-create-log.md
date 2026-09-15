# conan-create.log — 逐字留档

> 归档口径：`.gitcode/review-memory.md` §19 禁止 PR 携带 `*.log`，而 workflow §6.1 要求
> 「被 PR 正文引用的证据必须对评审端可见」。本文件即按 §6.1 的**逐字 `.md` 留档**口径生成：
> 原始日志内容原封不动放在下方围栏内（仅此一处转义），原始 `*.log` 不入库。

| 项 | 值 |
| --- | --- |
| 原文件 | `reports/conan-create.log`（未入库） |
| 内容 | conan-verify 的 G2 干净轮 `conan create` 完整日志 |
| 生成命令 | `conan create archives/b/bambamc/0.0.50 --user=ohpcd --channel=stable -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<repo>/ci/conan/profiles/ohos-aarch64` |
| 产出者 | 由 `python3 scripts/ohc-run.py conan-verify bambamc 0.0.50` 写出（G2 段） |
| 原始字节数 | 74161 |
| 原始行数 | 586 |
| 原文件 sha256 | `6f2ffd869a9d1d0de0745a27695129a518fdbfe2e9f2cb018b91bb1d9fc0b69f` |

复核方式（原始日志已不入库，如需重建）：按上表命令在**同一 SHA 的干净工作树**上重跑，
再用 `sha256sum` 与上表比对；注意日志内嵌导出时间戳与每轮重建的缓存分片目录名，
跨轮只有在「构建输入 diff 为空 + 干净轮标志（`RUN: make`/`Calling build()`/`Apply patch`）齐备」
时才算同一采信轮（workflow §6.1 末段口径）。

## 原始日志（逐字）

```text

======== Exporting recipe to the cache ========
bambamc/0.0.50@ohpcd/stable: Exporting package recipe: /storage/Users/currentUser/ws/wt-bambamc-0.0.50/archives/b/bambamc/0.0.50/conanfile.py
bambamc/0.0.50@ohpcd/stable: exports: File 'conandata.yml' found. Exporting it...
bambamc/0.0.50@ohpcd/stable: Calling export_sources()
bambamc/0.0.50@ohpcd/stable: Copied 1 '.yml' file: conandata.yml
bambamc/0.0.50@ohpcd/stable: Copied 1 '.py' file: conanfile.py
bambamc/0.0.50@ohpcd/stable: Copied 1 '.m4' file: m4-pkg.m4
bambamc/0.0.50@ohpcd/stable: Copied 2 '.patch' files: 0001-config-guess-harmonyos.patch, 0002-config-sub-harmonyos.patch
bambamc/0.0.50@ohpcd/stable: Exported to cache folder: /storage/Users/currentUser/.conan2/p/bamba37cc4b536df8c/e
bambamc/0.0.50@ohpcd/stable: Exported: bambamc/0.0.50@ohpcd/stable#eaaa0c5e3b8cc5e19ab9c7e6508b0c93 (2026-09-11 04:49:49 UTC)

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
automake/1.18: WARN: automake/1.18: package_type 'application' is defined, but 'shared' and/or 'header_only' options are present. The package_type will have precedence over the options regardless of their value.
libtool/2.5.4: WARN: libtool/2.5.4: package_type 'application' is defined, but 'shared' and/or 'header_only' options are present. The package_type will have precedence over the options regardless of their value.
Graph root
    cli
Requirements
    bambamc/0.0.50@ohpcd/stable#eaaa0c5e3b8cc5e19ab9c7e6508b0c93 - Cache
    zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9 - Cache
Build requirements
    automake/1.18#65a7ba60030d238eb8bb32266391cfc5 - Cache
    libtool/2.5.4#fe9f8e735ad45469571cf4de3ce552f4 - Cache

======== Computing necessary packages ========
Connecting to remote 'ohpcd' anonymously
bambamc/0.0.50@ohpcd/stable: Main binary package '7ed998dad2cd7b6fe73eee7bc365fa0677f5cb72' missing
bambamc/0.0.50@ohpcd/stable: Checking 11 compatible configurations
bambamc/0.0.50@ohpcd/stable: Compatible configurations not found in cache, checking servers
bambamc/0.0.50@ohpcd/stable: '0673f98dfb9c198a783c5c13c488b16e28f175d5': compiler.cppstd=98
bambamc/0.0.50@ohpcd/stable: 'c67530513469fbd1bf3c2cb0d87b4de9f1bdc097': compiler.cppstd=gnu98
bambamc/0.0.50@ohpcd/stable: 'a9cc41486cc943a28ba5380777f468b842cec8f3': compiler.cppstd=11
bambamc/0.0.50@ohpcd/stable: '07e2a7ccc1de582950ea81c6e87d78c5130bf852': compiler.cppstd=gnu11
bambamc/0.0.50@ohpcd/stable: '6eea3edc98ec5d112af7ddcfa256dcd73263df62': compiler.cppstd=14
bambamc/0.0.50@ohpcd/stable: 'f3c312b6ea9f88861a156775d2025ed86042673a': compiler.cppstd=gnu14
bambamc/0.0.50@ohpcd/stable: '09171cf7c05cbd104cd97319d81e9f00cf4e6f6b': compiler.cppstd=gnu17
bambamc/0.0.50@ohpcd/stable: '90adfe63e82736befb666207844765399606ed24': compiler.cppstd=20
bambamc/0.0.50@ohpcd/stable: '7fb23431f3177b1f1b756c52980630913a43338c': compiler.cppstd=gnu20
bambamc/0.0.50@ohpcd/stable: '2f2097d0d9387ee0b7d38c327f36e3d7f6a73928': compiler.cppstd=23
bambamc/0.0.50@ohpcd/stable: 'c5a8f8244f851b34d7135d66ba551caa684d7a29': compiler.cppstd=gnu23
bambamc/0.0.50@ohpcd/stable: No compatible configuration found

A new experimental approach for binary compatibility detection is available.
    Enable it by setting the core.graph:compatibility_mode=optimized conf
    and get improved performance when querying multiple compatible binaries in remotes.

Requirements
    bambamc/0.0.50@ohpcd/stable#eaaa0c5e3b8cc5e19ab9c7e6508b0c93:7ed998dad2cd7b6fe73eee7bc365fa0677f5cb72 - Build
    zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9:6b129b068851896169fae42d399fa922d239ce8a#b27d5a8c4c5eafd64d3a7f1e7a12dceb - Cache
Build requirements
    automake/1.18#65a7ba60030d238eb8bb32266391cfc5:01d92cf349a0dd98ff915f4bd99a04430171517f#74f532f1a4c52e1f559249f2d9bc44a4 - Cache
    libtool/2.5.4#fe9f8e735ad45469571cf4de3ce552f4:01d92cf349a0dd98ff915f4bd99a04430171517f#0ae9090203073e9b023dc4a5f951dd79 - Cache

======== Installing packages ========
automake/1.18: Already installed! (1 of 4)
libtool/2.5.4: Already installed! (2 of 4)
zlib/1.3.1.1: Already installed! (3 of 4)
bambamc/0.0.50@ohpcd/stable: Calling source() in /storage/Users/currentUser/.conan2/p/bamba37cc4b536df8c/s
bambamc/0.0.50@ohpcd/stable: Sources correctly downloaded from https://ghfast.top/https://github.com/gt1/bambamc/archive/refs/tags/bambamc_0_0_50.tar.gz
bambamc/0.0.50@ohpcd/stable: Uncompressing bambamc_0_0_50.tar.gz to .

-------- Installing package bambamc/0.0.50@ohpcd/stable (4 of 4) --------
bambamc/0.0.50@ohpcd/stable: Building from source
bambamc/0.0.50@ohpcd/stable: Package bambamc/0.0.50@ohpcd/stable:7ed998dad2cd7b6fe73eee7bc365fa0677f5cb72
bambamc/0.0.50@ohpcd/stable: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
bambamc/0.0.50@ohpcd/stable: options: fPIC=True shared=False
bambamc/0.0.50@ohpcd/stable: requires: zlib/1.3.Z
bambamc/0.0.50@ohpcd/stable: Copying sources to build folder
bambamc/0.0.50@ohpcd/stable: Building your package in /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b
bambamc/0.0.50@ohpcd/stable: Calling generate()
bambamc/0.0.50@ohpcd/stable: Generators folder: /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/conan
bambamc/0.0.50@ohpcd/stable: Generating aggregated env files
bambamc/0.0.50@ohpcd/stable: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
bambamc/0.0.50@ohpcd/stable: Calling build()
bambamc/0.0.50@ohpcd/stable: RUN: autoreconf --force --install
autoreconf: warning: autoconf input should be named 'configure.ac', not 'configure.in'
.aclocal-real: warning: autoconf input should be named 'configure.ac', not 'configure.in'
libtoolize: putting auxiliary files in '.'.
libtoolize: copying file './ltmain.sh'
libtoolize: putting macros in AC_CONFIG_MACRO_DIRS, 'm4'.
libtoolize: copying file 'm4/libtool.m4'
libtoolize: copying file 'm4/ltoptions.m4'
libtoolize: copying file 'm4/ltsugar.m4'
libtoolize: copying file 'm4/ltversion.m4'
libtoolize: copying file 'm4/lt~obsolete.m4'
.aclocal-real: warning: autoconf input should be named 'configure.ac', not 'configure.in'
configure.in:3: warning: The macro 'AC_CANONICAL_SYSTEM' is obsolete.
configure.in:3: You should run autoupdate.
./lib/autoconf/general.m4:2081: AC_CANONICAL_SYSTEM is expanded from...
configure.in:3: the top level
configure.in:4: warning: The macro 'AC_PROG_LIBTOOL' is obsolete.
configure.in:4: You should run autoupdate.
m4/libtool.m4:100: AC_PROG_LIBTOOL is expanded from...
configure.in:4: the top level
configure.in:6: warning: 'AM_CONFIG_HEADER': this macro is obsolete.
configure.in:6: You should use the 'AC_CONFIG_HEADERS' macro instead.
aclocal.m4:708: AM_CONFIG_HEADER is expanded from...
configure.in:6: the top level
configure.in:15: warning: The macro 'AC_PROG_CC_C99' is obsolete.
configure.in:15: You should run autoupdate.
./lib/autoconf/c.m4:1662: AC_PROG_CC_C99 is expanded from...
configure.in:15: the top level
configure.in:27: warning: The macro 'AC_HEADER_STDC' is obsolete.
configure.in:27: You should run autoupdate.
./lib/autoconf/headers.m4:663: AC_HEADER_STDC is expanded from...
configure.in:27: the top level
configure.in:40: warning: The macro 'AC_TRY_LINK' is obsolete.
configure.in:40: You should run autoupdate.
./lib/autoconf/general.m4:2918: AC_TRY_LINK is expanded from...
configure.in:40: the top level
configure.in:68: warning: The macro 'AC_TRY_LINK' is obsolete.
configure.in:68: You should run autoupdate.
./lib/autoconf/general.m4:2918: AC_TRY_LINK is expanded from...
configure.in:68: the top level
configure.in:144: warning: The macro 'AC_TRY_LINK' is obsolete.
configure.in:144: You should run autoupdate.
./lib/autoconf/general.m4:2918: AC_TRY_LINK is expanded from...
configure.in:144: the top level
configure.in:165: warning: AC_OUTPUT should be used without arguments.
configure.in:165: You should run autoupdate.
autoheader: warning: autoconf input should be named 'configure.ac', not 'configure.in'
.automake-real: warning: autoconf input should be named 'configure.ac', not 'configure.in'
configure.in:4: installing './compile'
configure.in:3: installing './config.guess'
configure.in:3: installing './config.sub'
configure.in:7: installing './install-sh'
configure.in:7: installing './missing'
.automake-real: warning: autoconf input should be named 'configure.ac', not 'configure.in'
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BamCollationHash.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
.automake-real: warning: possible forward-incompatibility.
.automake-real: At least one source file is in a subdirectory, but the 'subdir-objects'
.automake-real: automake option hasn't been enabled.  For now, the corresponding output
.automake-real: object file(s) will be placed in the top-level directory.  However, this
.automake-real: behavior may change in a future Automake major version, with object
.automake-real: files being placed in the same subdirectory as the corresponding sources.
.automake-real: You are advised to start using 'subdir-objects' option throughout your
.automake-real: project, to avoid future incompatibility.
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BamCollatorInterface.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_FormatAlignment.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BamCollationHashEntry.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_FormatNumber.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BamCollationOutputVector.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BamHeaderInfo.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_Hash.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BamCollationTempFileGenerator.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BamWriter.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_List.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BamCollationVector.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_CharBuffer.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_ListNode.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BamCollator.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_Chromosome.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_GzipReader.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_LineParsing.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BamFileHeader.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BamAlignmentPut.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BamSingleAlignment.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BamFileDecoder.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_GzipWriter.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_GzipFileDecoder.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_BgzfCompressor.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_LineBuffer.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_SamInfo.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_SamFileDecoder.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_SamBamFileDecoder.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:6: warning: source file 'bambamc/BamBam_StrDup.c' is in a subdirectory,
src/Makefile.am:6: but option 'subdir-objects' is disabled
src/Makefile.am:40: warning: source file 'test/bamreadertest.c' is in a subdirectory,
src/Makefile.am:40: but option 'subdir-objects' is disabled
src/Makefile.am:44: warning: source file 'test/bamwritertest.c' is in a subdirectory,
src/Makefile.am:44: but option 'subdir-objects' is disabled
src/Makefile.am: installing './depcomp'

bambamc/0.0.50@ohpcd/stable: Apply patch (portability): config.guess 增加 HarmonyOS 系统识别分支 输出 aarch64-unknown-linux-ohos
bambamc/0.0.50@ohpcd/stable: Apply patch (portability): config.sub 接受 ohos-linux 基本系统名 使 linux-ohos 三元组合法
bambamc/0.0.50@ohpcd/stable:   [ok] configure: config.status temp dir umask normalised to 022
bambamc/0.0.50@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/configure" --disable-shared --enable-static --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' --enable-static --disable-shared 
checking build system type... aarch64-unknown-linux-ohos
checking host system type... aarch64-unknown-linux-ohos
checking target system type... aarch64-unknown-linux-ohos
checking how to print strings... printf
checking for gcc... /data/service/hnp/bin/clang
checking whether the C compiler works... yes
checking for C compiler default output file name... a.out
checking for suffix of executables... 
checking whether we are cross compiling... no
checking for suffix of object files... o
checking whether the compiler supports GNU C... yes
checking whether /data/service/hnp/bin/clang accepts -g... yes
checking for /data/service/hnp/bin/clang option to enable C11 features... none needed
checking whether /data/service/hnp/bin/clang understands -c and -o together... yes
checking for a sed that does not truncate output... /usr/bin/sed
checking for grep that handles long lines and -e... /data/service/hnp/bin/grep
checking for egrep... /data/service/hnp/bin/grep -E
checking for fgrep... /data/service/hnp/bin/grep -F
checking for ld used by /data/service/hnp/bin/clang... /data/service/hnp/bin/ld
checking if the linker (/data/service/hnp/bin/ld) is GNU ld... yes
checking for BSD- or MS-compatible name lister (nm)... /data/service/hnp/bin/nm -B
checking the name lister (/data/service/hnp/bin/nm -B) interface... BSD nm
checking whether ln -s works... yes
checking the maximum length of command line arguments... 98304
checking how to convert aarch64-unknown-linux-ohos file names to aarch64-unknown-linux-ohos format... func_convert_file_noop
checking how to convert aarch64-unknown-linux-ohos file names to toolchain format... func_convert_file_noop
checking for /data/service/hnp/bin/ld option to reload object files... -r
checking for file... file
checking for objdump... objdump
checking how to recognize dependent libraries... pass_all
checking for dlltool... no
checking how to associate runtime and link libraries... printf %s\n
checking for ranlib... ranlib
checking for ar... ar
checking for archiver @FILE support... @
checking for strip... strip
checking for gawk... gawk
checking command to parse /data/service/hnp/bin/nm -B output from /data/service/hnp/bin/clang object... ok
checking for sysroot... no
checking for a working dd... /storage/Users/currentUser/usr/local/bin/dd
checking how to truncate binary pipes... /storage/Users/currentUser/usr/local/bin/dd bs=4096 count=1
checking for mt... no
checking if : is a manifest tool... no
checking for stdio.h... yes
checking for stdlib.h... yes
checking for string.h... yes
checking for inttypes.h... yes
checking for stdint.h... yes
checking for strings.h... yes
checking for sys/stat.h... yes
checking for sys/types.h... yes
checking for unistd.h... yes
checking for dlfcn.h... yes
checking for objdir... .libs
checking if /data/service/hnp/bin/clang supports -fno-rtti -fno-exceptions... yes
checking for /data/service/hnp/bin/clang option to produce PIC... -fPIC -DPIC
checking if /data/service/hnp/bin/clang PIC flag -fPIC -DPIC works... yes
checking if /data/service/hnp/bin/clang static flag -static works... yes
checking if /data/service/hnp/bin/clang supports -c -o file.o... yes
checking if /data/service/hnp/bin/clang supports -c -o file.o... (cached) yes
checking whether the /data/service/hnp/bin/clang linker (/data/service/hnp/bin/ld) supports shared libraries... yes
checking dynamic linker characteristics... GNU/Linux ld.so
checking how to hardcode library paths into programs... immediate
checking whether stripping libraries is possible... yes
checking if libtool supports shared libraries... yes
checking whether to build shared libraries... no
checking whether to build static libraries... yes
checking for a BSD-compatible install... /storage/Users/currentUser/usr/local/bin/ginstall -c
checking whether sleep supports fractional seconds... yes
checking filesystem timestamp resolution... 0.01
checking whether build environment is sane... yes
checking for a race-free mkdir -p... /storage/Users/currentUser/usr/local/bin/mkdir -p
checking whether make sets $(MAKE)... yes
checking whether make supports the include directive... yes (GNU style)
checking whether make supports nested variables... yes
checking xargs -n works... yes
checking whether UID '20020084' is supported by ustar format... no
checking whether GID '20020084' is supported by ustar format... no
checking how to create a ustar tar archive... none
checking dependency style of /data/service/hnp/bin/clang... gcc3
checking for egrep... (cached) /data/service/hnp/bin/grep -E
checking for pkg-config... /data/service/hnp/bin/pkg-config
checking pkg-config is at least version 0.9.0... yes
checking for zlib >= 0... yes
checking for zlib >= 0... yes
checking whether we can compile a zlib program... yes
checking for _mkdir... no
checking for direct.h... no
checking that generated files are newer than configure... done
configure: creating ./config.status
config.status: creating Makefile
config.status: creating src/Makefile
config.status: creating ubuntu.sh
config.status: creating bambamc.pc
config.status: creating src/bambamc/BamBam_Config.h
config.status: creating config.h
config.status: executing libtool commands
config.status: executing depfiles commands

bambamc/0.0.50@ohpcd/stable: RUN: make -j1
make  all-recursive
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release'
Making all in src
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/src'
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT bamreadertest-bamreadertest.o -MD -MP -MF .deps/bamreadertest-bamreadertest.Tpo -c -o bamreadertest-bamreadertest.o `test -f 'test/bamreadertest.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`test/bamreadertest.c
mv -f .deps/bamreadertest-bamreadertest.Tpo .deps/bamreadertest-bamreadertest.Po
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BamCollationHash.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollationHash.Tpo -c -o libbambamc_la-BamBam_BamCollationHash.lo `test -f 'bambamc/BamBam_BamCollationHash.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BamCollationHash.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BamCollationHash.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollationHash.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollationHash.c -o libbambamc_la-BamBam_BamCollationHash.o
mv -f .deps/libbambamc_la-BamBam_BamCollationHash.Tpo .deps/libbambamc_la-BamBam_BamCollationHash.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BamCollatorInterface.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollatorInterface.Tpo -c -o libbambamc_la-BamBam_BamCollatorInterface.lo `test -f 'bambamc/BamBam_BamCollatorInterface.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BamCollatorInterface.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BamCollatorInterface.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollatorInterface.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollatorInterface.c -o libbambamc_la-BamBam_BamCollatorInterface.o
mv -f .deps/libbambamc_la-BamBam_BamCollatorInterface.Tpo .deps/libbambamc_la-BamBam_BamCollatorInterface.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_FormatAlignment.lo -MD -MP -MF .deps/libbambamc_la-BamBam_FormatAlignment.Tpo -c -o libbambamc_la-BamBam_FormatAlignment.lo `test -f 'bambamc/BamBam_FormatAlignment.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_FormatAlignment.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_FormatAlignment.lo -MD -MP -MF .deps/libbambamc_la-BamBam_FormatAlignment.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_FormatAlignment.c -o libbambamc_la-BamBam_FormatAlignment.o
/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_FormatAlignment.c:47:41: warning: too many arguments in call to 'BamBam_GetFastqPlusLineLength'
                BamBam_GetFastqPlusLineLength(qnamelen) +
                ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~         ^
/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_FormatAlignment.c:47:32: warning: passing arguments to 'BamBam_GetFastqPlusLineLength' without a prototype is deprecated in all versions of C and is not supported in C2x [-Wdeprecated-non-prototype]
                BamBam_GetFastqPlusLineLength(qnamelen) +
                                             ^
2 warnings generated.
mv -f .deps/libbambamc_la-BamBam_FormatAlignment.Tpo .deps/libbambamc_la-BamBam_FormatAlignment.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BamCollationHashEntry.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollationHashEntry.Tpo -c -o libbambamc_la-BamBam_BamCollationHashEntry.lo `test -f 'bambamc/BamBam_BamCollationHashEntry.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BamCollationHashEntry.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BamCollationHashEntry.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollationHashEntry.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollationHashEntry.c -o libbambamc_la-BamBam_BamCollationHashEntry.o
mv -f .deps/libbambamc_la-BamBam_BamCollationHashEntry.Tpo .deps/libbambamc_la-BamBam_BamCollationHashEntry.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_FormatNumber.lo -MD -MP -MF .deps/libbambamc_la-BamBam_FormatNumber.Tpo -c -o libbambamc_la-BamBam_FormatNumber.lo `test -f 'bambamc/BamBam_FormatNumber.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_FormatNumber.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_FormatNumber.lo -MD -MP -MF .deps/libbambamc_la-BamBam_FormatNumber.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_FormatNumber.c -o libbambamc_la-BamBam_FormatNumber.o
mv -f .deps/libbambamc_la-BamBam_FormatNumber.Tpo .deps/libbambamc_la-BamBam_FormatNumber.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BamCollationOutputVector.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollationOutputVector.Tpo -c -o libbambamc_la-BamBam_BamCollationOutputVector.lo `test -f 'bambamc/BamBam_BamCollationOutputVector.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BamCollationOutputVector.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BamCollationOutputVector.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollationOutputVector.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollationOutputVector.c -o libbambamc_la-BamBam_BamCollationOutputVector.o
mv -f .deps/libbambamc_la-BamBam_BamCollationOutputVector.Tpo .deps/libbambamc_la-BamBam_BamCollationOutputVector.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BamHeaderInfo.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamHeaderInfo.Tpo -c -o libbambamc_la-BamBam_BamHeaderInfo.lo `test -f 'bambamc/BamBam_BamHeaderInfo.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BamHeaderInfo.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BamHeaderInfo.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamHeaderInfo.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamHeaderInfo.c -o libbambamc_la-BamBam_BamHeaderInfo.o
mv -f .deps/libbambamc_la-BamBam_BamHeaderInfo.Tpo .deps/libbambamc_la-BamBam_BamHeaderInfo.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_Hash.lo -MD -MP -MF .deps/libbambamc_la-BamBam_Hash.Tpo -c -o libbambamc_la-BamBam_Hash.lo `test -f 'bambamc/BamBam_Hash.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_Hash.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_Hash.lo -MD -MP -MF .deps/libbambamc_la-BamBam_Hash.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_Hash.c -o libbambamc_la-BamBam_Hash.o
mv -f .deps/libbambamc_la-BamBam_Hash.Tpo .deps/libbambamc_la-BamBam_Hash.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BamCollationTempFileGenerator.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollationTempFileGenerator.Tpo -c -o libbambamc_la-BamBam_BamCollationTempFileGenerator.lo `test -f 'bambamc/BamBam_BamCollationTempFileGenerator.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BamCollationTempFileGenerator.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BamCollationTempFileGenerator.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollationTempFileGenerator.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollationTempFileGenerator.c -o libbambamc_la-BamBam_BamCollationTempFileGenerator.o
mv -f .deps/libbambamc_la-BamBam_BamCollationTempFileGenerator.Tpo .deps/libbambamc_la-BamBam_BamCollationTempFileGenerator.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BamWriter.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamWriter.Tpo -c -o libbambamc_la-BamBam_BamWriter.lo `test -f 'bambamc/BamBam_BamWriter.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BamWriter.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BamWriter.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamWriter.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamWriter.c -o libbambamc_la-BamBam_BamWriter.o
mv -f .deps/libbambamc_la-BamBam_BamWriter.Tpo .deps/libbambamc_la-BamBam_BamWriter.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_List.lo -MD -MP -MF .deps/libbambamc_la-BamBam_List.Tpo -c -o libbambamc_la-BamBam_List.lo `test -f 'bambamc/BamBam_List.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_List.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_List.lo -MD -MP -MF .deps/libbambamc_la-BamBam_List.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_List.c -o libbambamc_la-BamBam_List.o
mv -f .deps/libbambamc_la-BamBam_List.Tpo .deps/libbambamc_la-BamBam_List.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BamCollationVector.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollationVector.Tpo -c -o libbambamc_la-BamBam_BamCollationVector.lo `test -f 'bambamc/BamBam_BamCollationVector.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BamCollationVector.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BamCollationVector.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollationVector.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollationVector.c -o libbambamc_la-BamBam_BamCollationVector.o
mv -f .deps/libbambamc_la-BamBam_BamCollationVector.Tpo .deps/libbambamc_la-BamBam_BamCollationVector.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_CharBuffer.lo -MD -MP -MF .deps/libbambamc_la-BamBam_CharBuffer.Tpo -c -o libbambamc_la-BamBam_CharBuffer.lo `test -f 'bambamc/BamBam_CharBuffer.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_CharBuffer.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_CharBuffer.lo -MD -MP -MF .deps/libbambamc_la-BamBam_CharBuffer.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_CharBuffer.c -o libbambamc_la-BamBam_CharBuffer.o
mv -f .deps/libbambamc_la-BamBam_CharBuffer.Tpo .deps/libbambamc_la-BamBam_CharBuffer.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_ListNode.lo -MD -MP -MF .deps/libbambamc_la-BamBam_ListNode.Tpo -c -o libbambamc_la-BamBam_ListNode.lo `test -f 'bambamc/BamBam_ListNode.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_ListNode.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_ListNode.lo -MD -MP -MF .deps/libbambamc_la-BamBam_ListNode.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_ListNode.c -o libbambamc_la-BamBam_ListNode.o
mv -f .deps/libbambamc_la-BamBam_ListNode.Tpo .deps/libbambamc_la-BamBam_ListNode.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BamCollator.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollator.Tpo -c -o libbambamc_la-BamBam_BamCollator.lo `test -f 'bambamc/BamBam_BamCollator.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BamCollator.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BamCollator.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamCollator.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollator.c -o libbambamc_la-BamBam_BamCollator.o
mv -f .deps/libbambamc_la-BamBam_BamCollator.Tpo .deps/libbambamc_la-BamBam_BamCollator.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_Chromosome.lo -MD -MP -MF .deps/libbambamc_la-BamBam_Chromosome.Tpo -c -o libbambamc_la-BamBam_Chromosome.lo `test -f 'bambamc/BamBam_Chromosome.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_Chromosome.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_Chromosome.lo -MD -MP -MF .deps/libbambamc_la-BamBam_Chromosome.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_Chromosome.c -o libbambamc_la-BamBam_Chromosome.o
mv -f .deps/libbambamc_la-BamBam_Chromosome.Tpo .deps/libbambamc_la-BamBam_Chromosome.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_GzipReader.lo -MD -MP -MF .deps/libbambamc_la-BamBam_GzipReader.Tpo -c -o libbambamc_la-BamBam_GzipReader.lo `test -f 'bambamc/BamBam_GzipReader.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_GzipReader.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_GzipReader.lo -MD -MP -MF .deps/libbambamc_la-BamBam_GzipReader.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_GzipReader.c -o libbambamc_la-BamBam_GzipReader.o
mv -f .deps/libbambamc_la-BamBam_GzipReader.Tpo .deps/libbambamc_la-BamBam_GzipReader.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_LineParsing.lo -MD -MP -MF .deps/libbambamc_la-BamBam_LineParsing.Tpo -c -o libbambamc_la-BamBam_LineParsing.lo `test -f 'bambamc/BamBam_LineParsing.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_LineParsing.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_LineParsing.lo -MD -MP -MF .deps/libbambamc_la-BamBam_LineParsing.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_LineParsing.c -o libbambamc_la-BamBam_LineParsing.o
mv -f .deps/libbambamc_la-BamBam_LineParsing.Tpo .deps/libbambamc_la-BamBam_LineParsing.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BamFileHeader.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamFileHeader.Tpo -c -o libbambamc_la-BamBam_BamFileHeader.lo `test -f 'bambamc/BamBam_BamFileHeader.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BamFileHeader.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BamFileHeader.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamFileHeader.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamFileHeader.c -o libbambamc_la-BamBam_BamFileHeader.o
mv -f .deps/libbambamc_la-BamBam_BamFileHeader.Tpo .deps/libbambamc_la-BamBam_BamFileHeader.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BamAlignmentPut.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamAlignmentPut.Tpo -c -o libbambamc_la-BamBam_BamAlignmentPut.lo `test -f 'bambamc/BamBam_BamAlignmentPut.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BamAlignmentPut.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BamAlignmentPut.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamAlignmentPut.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamAlignmentPut.c -o libbambamc_la-BamBam_BamAlignmentPut.o
mv -f .deps/libbambamc_la-BamBam_BamAlignmentPut.Tpo .deps/libbambamc_la-BamBam_BamAlignmentPut.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BamSingleAlignment.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamSingleAlignment.Tpo -c -o libbambamc_la-BamBam_BamSingleAlignment.lo `test -f 'bambamc/BamBam_BamSingleAlignment.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BamSingleAlignment.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BamSingleAlignment.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamSingleAlignment.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamSingleAlignment.c -o libbambamc_la-BamBam_BamSingleAlignment.o
mv -f .deps/libbambamc_la-BamBam_BamSingleAlignment.Tpo .deps/libbambamc_la-BamBam_BamSingleAlignment.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BamFileDecoder.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamFileDecoder.Tpo -c -o libbambamc_la-BamBam_BamFileDecoder.lo `test -f 'bambamc/BamBam_BamFileDecoder.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BamFileDecoder.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BamFileDecoder.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BamFileDecoder.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamFileDecoder.c -o libbambamc_la-BamBam_BamFileDecoder.o
mv -f .deps/libbambamc_la-BamBam_BamFileDecoder.Tpo .deps/libbambamc_la-BamBam_BamFileDecoder.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_GzipWriter.lo -MD -MP -MF .deps/libbambamc_la-BamBam_GzipWriter.Tpo -c -o libbambamc_la-BamBam_GzipWriter.lo `test -f 'bambamc/BamBam_GzipWriter.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_GzipWriter.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_GzipWriter.lo -MD -MP -MF .deps/libbambamc_la-BamBam_GzipWriter.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_GzipWriter.c -o libbambamc_la-BamBam_GzipWriter.o
mv -f .deps/libbambamc_la-BamBam_GzipWriter.Tpo .deps/libbambamc_la-BamBam_GzipWriter.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_GzipFileDecoder.lo -MD -MP -MF .deps/libbambamc_la-BamBam_GzipFileDecoder.Tpo -c -o libbambamc_la-BamBam_GzipFileDecoder.lo `test -f 'bambamc/BamBam_GzipFileDecoder.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_GzipFileDecoder.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_GzipFileDecoder.lo -MD -MP -MF .deps/libbambamc_la-BamBam_GzipFileDecoder.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_GzipFileDecoder.c -o libbambamc_la-BamBam_GzipFileDecoder.o
mv -f .deps/libbambamc_la-BamBam_GzipFileDecoder.Tpo .deps/libbambamc_la-BamBam_GzipFileDecoder.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_BgzfCompressor.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BgzfCompressor.Tpo -c -o libbambamc_la-BamBam_BgzfCompressor.lo `test -f 'bambamc/BamBam_BgzfCompressor.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_BgzfCompressor.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_BgzfCompressor.lo -MD -MP -MF .deps/libbambamc_la-BamBam_BgzfCompressor.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BgzfCompressor.c -o libbambamc_la-BamBam_BgzfCompressor.o
mv -f .deps/libbambamc_la-BamBam_BgzfCompressor.Tpo .deps/libbambamc_la-BamBam_BgzfCompressor.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_LineBuffer.lo -MD -MP -MF .deps/libbambamc_la-BamBam_LineBuffer.Tpo -c -o libbambamc_la-BamBam_LineBuffer.lo `test -f 'bambamc/BamBam_LineBuffer.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_LineBuffer.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_LineBuffer.lo -MD -MP -MF .deps/libbambamc_la-BamBam_LineBuffer.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_LineBuffer.c -o libbambamc_la-BamBam_LineBuffer.o
mv -f .deps/libbambamc_la-BamBam_LineBuffer.Tpo .deps/libbambamc_la-BamBam_LineBuffer.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_SamInfo.lo -MD -MP -MF .deps/libbambamc_la-BamBam_SamInfo.Tpo -c -o libbambamc_la-BamBam_SamInfo.lo `test -f 'bambamc/BamBam_SamInfo.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_SamInfo.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_SamInfo.lo -MD -MP -MF .deps/libbambamc_la-BamBam_SamInfo.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_SamInfo.c -o libbambamc_la-BamBam_SamInfo.o
mv -f .deps/libbambamc_la-BamBam_SamInfo.Tpo .deps/libbambamc_la-BamBam_SamInfo.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_SamFileDecoder.lo -MD -MP -MF .deps/libbambamc_la-BamBam_SamFileDecoder.Tpo -c -o libbambamc_la-BamBam_SamFileDecoder.lo `test -f 'bambamc/BamBam_SamFileDecoder.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_SamFileDecoder.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_SamFileDecoder.lo -MD -MP -MF .deps/libbambamc_la-BamBam_SamFileDecoder.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_SamFileDecoder.c -o libbambamc_la-BamBam_SamFileDecoder.o
mv -f .deps/libbambamc_la-BamBam_SamFileDecoder.Tpo .deps/libbambamc_la-BamBam_SamFileDecoder.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_SamBamFileDecoder.lo -MD -MP -MF .deps/libbambamc_la-BamBam_SamBamFileDecoder.Tpo -c -o libbambamc_la-BamBam_SamBamFileDecoder.lo `test -f 'bambamc/BamBam_SamBamFileDecoder.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_SamBamFileDecoder.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_SamBamFileDecoder.lo -MD -MP -MF .deps/libbambamc_la-BamBam_SamBamFileDecoder.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_SamBamFileDecoder.c -o libbambamc_la-BamBam_SamBamFileDecoder.o
mv -f .deps/libbambamc_la-BamBam_SamBamFileDecoder.Tpo .deps/libbambamc_la-BamBam_SamBamFileDecoder.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=compile /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT libbambamc_la-BamBam_StrDup.lo -MD -MP -MF .deps/libbambamc_la-BamBam_StrDup.Tpo -c -o libbambamc_la-BamBam_StrDup.lo `test -f 'bambamc/BamBam_StrDup.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`bambamc/BamBam_StrDup.c
libtool: compile:  /data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I.. -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include -fPIC -O3 -MT libbambamc_la-BamBam_StrDup.lo -MD -MP -MF .deps/libbambamc_la-BamBam_StrDup.Tpo -c /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_StrDup.c -o libbambamc_la-BamBam_StrDup.o
mv -f .deps/libbambamc_la-BamBam_StrDup.Tpo .deps/libbambamc_la-BamBam_StrDup.Plo
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=link /data/service/hnp/bin/clang  -fPIC -O3  -version-info 0:50:0 -L/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/lib -o libbambamc.la -rpath //lib libbambamc_la-BamBam_BamCollationHash.lo libbambamc_la-BamBam_BamCollatorInterface.lo libbambamc_la-BamBam_FormatAlignment.lo libbambamc_la-BamBam_BamCollationHashEntry.lo libbambamc_la-BamBam_FormatNumber.lo libbambamc_la-BamBam_BamCollationOutputVector.lo libbambamc_la-BamBam_BamHeaderInfo.lo libbambamc_la-BamBam_Hash.lo libbambamc_la-BamBam_BamCollationTempFileGenerator.lo libbambamc_la-BamBam_BamWriter.lo libbambamc_la-BamBam_List.lo libbambamc_la-BamBam_BamCollationVector.lo libbambamc_la-BamBam_CharBuffer.lo libbambamc_la-BamBam_ListNode.lo libbambamc_la-BamBam_BamCollator.lo libbambamc_la-BamBam_Chromosome.lo libbambamc_la-BamBam_GzipReader.lo libbambamc_la-BamBam_LineParsing.lo libbambamc_la-BamBam_BamFileHeader.lo libbambamc_la-BamBam_BamAlignmentPut.lo libbambamc_la-BamBam_BamSingleAlignment.lo libbambamc_la-BamBam_BamFileDecoder.lo libbambamc_la-BamBam_GzipWriter.lo libbambamc_la-BamBam_GzipFileDecoder.lo libbambamc_la-BamBam_BgzfCompressor.lo libbambamc_la-BamBam_LineBuffer.lo libbambamc_la-BamBam_SamInfo.lo libbambamc_la-BamBam_SamFileDecoder.lo libbambamc_la-BamBam_SamBamFileDecoder.lo libbambamc_la-BamBam_StrDup.lo -L/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/lib -lz -lz
libtool: link: ar cr .libs/libbambamc.a  libbambamc_la-BamBam_BamCollationHash.o libbambamc_la-BamBam_BamCollatorInterface.o libbambamc_la-BamBam_FormatAlignment.o libbambamc_la-BamBam_BamCollationHashEntry.o libbambamc_la-BamBam_FormatNumber.o libbambamc_la-BamBam_BamCollationOutputVector.o libbambamc_la-BamBam_BamHeaderInfo.o libbambamc_la-BamBam_Hash.o libbambamc_la-BamBam_BamCollationTempFileGenerator.o libbambamc_la-BamBam_BamWriter.o libbambamc_la-BamBam_List.o libbambamc_la-BamBam_BamCollationVector.o libbambamc_la-BamBam_CharBuffer.o libbambamc_la-BamBam_ListNode.o libbambamc_la-BamBam_BamCollator.o libbambamc_la-BamBam_Chromosome.o libbambamc_la-BamBam_GzipReader.o libbambamc_la-BamBam_LineParsing.o libbambamc_la-BamBam_BamFileHeader.o libbambamc_la-BamBam_BamAlignmentPut.o libbambamc_la-BamBam_BamSingleAlignment.o libbambamc_la-BamBam_BamFileDecoder.o libbambamc_la-BamBam_GzipWriter.o libbambamc_la-BamBam_GzipFileDecoder.o libbambamc_la-BamBam_BgzfCompressor.o libbambamc_la-BamBam_LineBuffer.o libbambamc_la-BamBam_SamInfo.o libbambamc_la-BamBam_SamFileDecoder.o libbambamc_la-BamBam_SamBamFileDecoder.o libbambamc_la-BamBam_StrDup.o
libtool: link: ranlib .libs/libbambamc.a
libtool: link: ( cd ".libs" && rm -f "libbambamc.la" && ln -s "../libbambamc.la" "libbambamc.la" )
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=link /data/service/hnp/bin/clang  -fPIC -O3  -L/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/lib -o bamreadertest bamreadertest-bamreadertest.o libbambamc.la -L/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/lib -lz -lz
libtool: link: /data/service/hnp/bin/clang -fPIC -O3 -o bamreadertest bamreadertest-bamreadertest.o  -L/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/lib ./.libs/libbambamc.a -lz
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src -I..   -I/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/include  -fPIC -O3 -MT bamwritertest-bamwritertest.o -MD -MP -MF .deps/bamwritertest-bamwritertest.Tpo -c -o bamwritertest-bamwritertest.o `test -f 'test/bamwritertest.c' || echo '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/'`test/bamwritertest.c
mv -f .deps/bamwritertest-bamwritertest.Tpo .deps/bamwritertest-bamwritertest.Po
/data/service/hnp/bin/bash ../libtool  --tag=CC   --mode=link /data/service/hnp/bin/clang  -fPIC -O3  -L/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/lib -o bamwritertest bamwritertest-bamwritertest.o libbambamc.la -L/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/lib -lz -lz
libtool: link: /data/service/hnp/bin/clang -fPIC -O3 -o bamwritertest bamwritertest-bamwritertest.o  -L/storage/Users/currentUser/.conan2/p/zlibef5df15a693be/p/lib ./.libs/libbambamc.a -lz
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/src'
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release'

bambamc/0.0.50@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/src/bamwritertest" > "/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/bamwritertest.bam" 2> "/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/bamwritertest.err"

bambamc/0.0.50@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/src/bamreadertest" < "/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/bamwritertest.bam" > "/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/bamreadertest.fastq" 2> "/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/bamreadertest.err"

bambamc/0.0.50@ohpcd/stable:   [ok] upstream tests: bamwritertest 186 bytes BGZF/BAM, bamreadertest rc=0
bambamc/0.0.50@ohpcd/stable: Package '7ed998dad2cd7b6fe73eee7bc365fa0677f5cb72' built
bambamc/0.0.50@ohpcd/stable: Build folder /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release
bambamc/0.0.50@ohpcd/stable: Generating the package
bambamc/0.0.50@ohpcd/stable: Packaging in folder /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/p
bambamc/0.0.50@ohpcd/stable: Calling package()
bambamc/0.0.50@ohpcd/stable: RUN: make install DESTDIR=/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/p -j20
make: jobserver mkfifo: /storage/Users/currentUser/GMfifo28913: Operation not permitted
Making install in src
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/src'
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/src'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/p//lib'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/p//include/bambamc'
 /data/service/hnp/bin/bash ../libtool   --mode=install /storage/Users/currentUser/usr/local/bin/ginstall -c   libbambamc.la '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/p//lib'
 /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamAlignmentPut.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamFlagBase.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_FormatAlignment.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollationHashEntry.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_FormatNumber.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollationHash.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamHeaderInfo.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_GzipReader.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollationOutputVector.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamSingleAlignment.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_Hash.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollationTempFileGenerator.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_LineParsing.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollationVector.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamWriter.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_List.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollator.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_CharBuffer.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_ListNode.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamCollatorInterface.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_Chromosome.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_MergeHeapEntry.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamFileDecoder.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_CollatorState.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_Unused.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BamFileHeader.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_FastQRead.h bambamc/BamBam_Config.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_GzipWriter.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_GzipFileDecoder.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_BgzfCompressor.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_LineBuffer.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_SamInfo.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_SamFileDecoder.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_SamBamFileDecoder.h /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/src/bambamc/BamBam_StrDup.h '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/p//include/bambamc'
libtool: install: /storage/Users/currentUser/usr/local/bin/ginstall -c .libs/libbambamc.lai /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/p//lib/libbambamc.la
libtool: install: /storage/Users/currentUser/usr/local/bin/ginstall -c .libs/libbambamc.a /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/p//lib/libbambamc.a
libtool: install: chmod 644 /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/p//lib/libbambamc.a
libtool: install: ranlib /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/p//lib/libbambamc.a
libtool: warning: remember to run 'libtool --finish //lib'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/src'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release/src'
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release'
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release'
make[2]: Nothing to be done for 'install-exec-am'.
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/p//lib/pkgconfig'
 /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 bambamc.pc '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/p//lib/pkgconfig'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/b/build-release'

bambamc/0.0.50@ohpcd/stable: package(): Packaged 1 '.a' file: libbambamc.a
bambamc/0.0.50@ohpcd/stable: package(): Packaged 1 '.pc' file: bambamc.pc
bambamc/0.0.50@ohpcd/stable: package(): Packaged 36 '.h' files
bambamc/0.0.50@ohpcd/stable: package(): Packaged 2 files: GPLv3, COPYING
bambamc/0.0.50@ohpcd/stable: Created package revision 7741c2216c609a72318971b109a36920
bambamc/0.0.50@ohpcd/stable: Package '7ed998dad2cd7b6fe73eee7bc365fa0677f5cb72' created
bambamc/0.0.50@ohpcd/stable: Full package reference: bambamc/0.0.50@ohpcd/stable#eaaa0c5e3b8cc5e19ab9c7e6508b0c93:7ed998dad2cd7b6fe73eee7bc365fa0677f5cb72#7741c2216c609a72318971b109a36920
bambamc/0.0.50@ohpcd/stable: Package folder /storage/Users/currentUser/.conan2/p/b/bambae3915d1bd7ded/p

======== Launching test_package ========

======== Computing dependency graph ========
automake/1.18: WARN: automake/1.18: package_type 'application' is defined, but 'shared' and/or 'header_only' options are present. The package_type will have precedence over the options regardless of their value.
libtool/2.5.4: WARN: libtool/2.5.4: package_type 'application' is defined, but 'shared' and/or 'header_only' options are present. The package_type will have precedence over the options regardless of their value.
Graph root
    bambamc/0.0.50@ohpcd/stable (test package): /storage/Users/currentUser/ws/wt-bambamc-0.0.50/archives/b/bambamc/0.0.50/test_package/conanfile.py
Requirements
    bambamc/0.0.50@ohpcd/stable#eaaa0c5e3b8cc5e19ab9c7e6508b0c93 - Cache
    zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9 - Cache
Build requirements
    automake/1.18#65a7ba60030d238eb8bb32266391cfc5 - Cache
    libtool/2.5.4#fe9f8e735ad45469571cf4de3ce552f4 - Cache

======== Computing necessary packages ========
Requirements
    bambamc/0.0.50@ohpcd/stable#eaaa0c5e3b8cc5e19ab9c7e6508b0c93:7ed998dad2cd7b6fe73eee7bc365fa0677f5cb72#7741c2216c609a72318971b109a36920 - Cache
    zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9:6b129b068851896169fae42d399fa922d239ce8a#b27d5a8c4c5eafd64d3a7f1e7a12dceb - Cache
Build requirements
Skipped binaries
    automake/1.18, libtool/2.5.4

======== Installing packages ========
zlib/1.3.1.1: Already installed! (1 of 2)
bambamc/0.0.50@ohpcd/stable: Already installed! (2 of 2)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/wt-bambamc-0.0.50/archives/b/bambamc/0.0.50/test_package/build/clang-15-armv8-17-release
bambamc/0.0.50@ohpcd/stable (test package): Test package build: build/clang-15-armv8-17-release
bambamc/0.0.50@ohpcd/stable (test package): Test package build folder: /storage/Users/currentUser/ws/wt-bambamc-0.0.50/archives/b/bambamc/0.0.50/test_package/build/clang-15-armv8-17-release
bambamc/0.0.50@ohpcd/stable (test package): Writing generators to /storage/Users/currentUser/ws/wt-bambamc-0.0.50/archives/b/bambamc/0.0.50/test_package/build/clang-15-armv8-17-release/generators
bambamc/0.0.50@ohpcd/stable (test package): Generator 'CMakeDeps' calling 'generate()'
bambamc/0.0.50@ohpcd/stable (test package): CMakeDeps necessary find_package() and targets for your CMakeLists.txt
    find_package(bambamc)
    target_link_libraries(... bambamc::bambamc)
bambamc/0.0.50@ohpcd/stable (test package): Generator 'CMakeToolchain' calling 'generate()'
bambamc/0.0.50@ohpcd/stable (test package): CMakeToolchain generated: conan_toolchain.cmake
bambamc/0.0.50@ohpcd/stable (test package): CMakeToolchain generated: /storage/Users/currentUser/ws/wt-bambamc-0.0.50/archives/b/bambamc/0.0.50/test_package/build/clang-15-armv8-17-release/generators/CMakePresets.json
bambamc/0.0.50@ohpcd/stable (test package): CMakeToolchain generated: /storage/Users/currentUser/ws/wt-bambamc-0.0.50/archives/b/bambamc/0.0.50/test_package/CMakeUserPresets.json
bambamc/0.0.50@ohpcd/stable (test package): Generating aggregated env files
bambamc/0.0.50@ohpcd/stable (test package): Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']

======== Testing the package: Building ========
bambamc/0.0.50@ohpcd/stable (test package): Calling build()
bambamc/0.0.50@ohpcd/stable (test package): Running CMake.configure()
bambamc/0.0.50@ohpcd/stable (test package): RUN: cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE="generators/conan_toolchain.cmake" -DCMAKE_INSTALL_PREFIX="/storage/Users/currentUser/ws/wt-bambamc-0.0.50/archives/b/bambamc/0.0.50/test_package" -DCMAKE_POLICY_DEFAULT_CMP0091="NEW" -DCMAKE_BUILD_TYPE="Release" "/storage/Users/currentUser/ws/wt-bambamc-0.0.50/archives/b/bambamc/0.0.50/test_package"
Problem parsing /proc/meminfo
-- Using Conan toolchain: /storage/Users/currentUser/ws/wt-bambamc-0.0.50/archives/b/bambamc/0.0.50/test_package/build/clang-15-armv8-17-release/generators/conan_toolchain.cmake
-- Conan toolchain: Defining libcxx as C++ flags: -stdlib=libc++
-- Conan toolchain: C++ Standard 17 with extensions OFF
-- The C compiler identification is Clang 15.0.4
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org so it can be added to cmake
-- Detecting C compiler ABI info
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org so it can be added to cmake
-- Detecting C compiler ABI info - done
-- Check for working C compiler: /data/service/hnp/bin/clang - skipped
-- Detecting C compile features
-- Detecting C compile features - done
-- Conan: Target declared 'bambamc::bambamc'
-- Conan: Target declared 'ZLIB::ZLIB'
-- Configuring done (0.7s)
-- Generating done (0.0s)
-- Build files have been written to: /storage/Users/currentUser/ws/wt-bambamc-0.0.50/archives/b/bambamc/0.0.50/test_package/build/clang-15-armv8-17-release

bambamc/0.0.50@ohpcd/stable (test package): Running CMake.build()
bambamc/0.0.50@ohpcd/stable (test package): RUN: cmake --build "/storage/Users/currentUser/ws/wt-bambamc-0.0.50/archives/b/bambamc/0.0.50/test_package/build/clang-15-armv8-17-release" -- -j20
make: jobserver mkfifo: /storage/Users/currentUser/GMfifo29088: Operation not permitted
[ 50%] Building C object CMakeFiles/test_bambamc.dir/test_bambamc.c.obj
[100%] Linking C executable test_bambamc
[100%] Built target test_bambamc


======== Testing the package: Executing test ========
bambamc/0.0.50@ohpcd/stable (test package): Running test()
bambamc/0.0.50@ohpcd/stable (test package): RUN: "./test_bambamc" "/storage/Users/currentUser/ws/wt-bambamc-0.0.50/archives/b/bambamc/0.0.50/test_package/build/clang-15-armv8-17-release/consumer_roundtrip.bam"
bambamc consumer round-trip: 28 checks, 0 failures

```
