# conan-create-log — 原始日志逐字留档（conan-verify 的 G2 采信轮（先按 workflow 第 7.2 节四步真清缓存））

> 本文件按 workflow 第 6.1 节「证据文件入库口径」生成：**原始 `*.log` 不随 PR 提交**
> （`.gitcode/review-memory.md` 第 19 条明列 PR 禁止 `*.log`），改为把原始日志内容
> **fenced 逐字复制**成本文件，同时满足该条与「评审端可见」。

| 项 | 值 |
| --- | --- |
| 原始文件 | `reports/conan-create.log`（本地产出，按上述口径不入库） |
| 字节数 | 46472 |
| 行数 | 623 |
| sha256 | `ef35ef54f139228d7a36ae7da3f84be931dd4bc26e0fa75004c452233dbfbb7a` |
| 生成命令 | `conan-verify debfoster 2.8 --project-dir <worktree>` |

reports/conan-create.log 由 conan-verify 自身写出（scripts/ohc/conan_verify.py 固定写该路径）。

**判读提示**：本文件内容为逐字复制，未经改写；下列 fenced 块即原始日志全文。

```text

======== Exporting recipe to the cache ========
debfoster/2.8@ohpcd/stable: Exporting package recipe: /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/conanfile.py
debfoster/2.8@ohpcd/stable: exports: File 'conandata.yml' found. Exporting it...
debfoster/2.8@ohpcd/stable: Calling export_sources()
debfoster/2.8@ohpcd/stable: Copied 1 '.yml' file: conandata.yml
debfoster/2.8@ohpcd/stable: Copied 1 '.py' file: conanfile.py
debfoster/2.8@ohpcd/stable: Copied 3 '.patch' files: 0001-configure-umask-hmdfs.patch, 0002-keepers-include-fcntl.patch, 0003-etc-makefile-install-d.patch
debfoster/2.8@ohpcd/stable: Copied 1 '.guess' file: config.guess
debfoster/2.8@ohpcd/stable: Copied 1 '.sub' file: config.sub
debfoster/2.8@ohpcd/stable: Copied 3 files: install-sh, missing, depcomp
debfoster/2.8@ohpcd/stable: Copied 1 '.m4' file: aclocal.m4
debfoster/2.8@ohpcd/stable: Exported to cache folder: /storage/Users/currentUser/.conan2/p/debfo8777d8096a790/e
debfoster/2.8@ohpcd/stable: Exported: debfoster/2.8@ohpcd/stable#4687874699f15616ae67331175e4c4b8 (2026-09-11 02:01:38 UTC)

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
    debfoster/2.8@ohpcd/stable#4687874699f15616ae67331175e4c4b8 - Cache
    gc/8.2.12#66bd5b05e364da6f7a7343b943cb186f - Cache

======== Computing necessary packages ========
Connecting to remote 'ohpcd' anonymously
debfoster/2.8@ohpcd/stable: Main binary package 'e402a17462529d13f1018a9751df0cb4c8656f19' missing
debfoster/2.8@ohpcd/stable: Checking 11 compatible configurations
debfoster/2.8@ohpcd/stable: Compatible configurations not found in cache, checking servers
debfoster/2.8@ohpcd/stable: 'db33a2b51455444afda9ee52552e8b177e799a82': compiler.cppstd=98
debfoster/2.8@ohpcd/stable: '355a3a9e600e9cdfa59f3f4a73e6a5558781c353': compiler.cppstd=gnu98
debfoster/2.8@ohpcd/stable: '053f929c79d526da20622c8a82eaa875cc56731c': compiler.cppstd=11
debfoster/2.8@ohpcd/stable: '4845a990f27e08f6f69f25fcb360032109f440e0': compiler.cppstd=gnu11
debfoster/2.8@ohpcd/stable: '597f9e2885a9975827aa936248728892e789b5a3': compiler.cppstd=14
debfoster/2.8@ohpcd/stable: 'c6f9a79db85db392a0bb6d156a81f9ccf3b73d4d': compiler.cppstd=gnu14
debfoster/2.8@ohpcd/stable: '53cdd9dc15318a6c23cce5f03c6d2e3b249e4839': compiler.cppstd=gnu17
debfoster/2.8@ohpcd/stable: 'ec7b93a86a7a5b07ec4f989433e4306aaa561ec1': compiler.cppstd=20
debfoster/2.8@ohpcd/stable: '653813c2d51f61fa6fadd14deaa69dc3d34d6e02': compiler.cppstd=gnu20
debfoster/2.8@ohpcd/stable: '9159ee9b6c4a4a5acf755df6e22eb4ef1b902f04': compiler.cppstd=23
debfoster/2.8@ohpcd/stable: 'f7c5b667589564e88ac60ec89d05e612a4daaccd': compiler.cppstd=gnu23
debfoster/2.8@ohpcd/stable: No compatible configuration found

A new experimental approach for binary compatibility detection is available.
    Enable it by setting the core.graph:compatibility_mode=optimized conf
    and get improved performance when querying multiple compatible binaries in remotes.

Requirements
    debfoster/2.8@ohpcd/stable#4687874699f15616ae67331175e4c4b8:e402a17462529d13f1018a9751df0cb4c8656f19 - Build
    gc/8.2.12#66bd5b05e364da6f7a7343b943cb186f:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa#834af36b852b0ba4f1a0ed9c904b1f95 - Cache

======== Installing packages ========
gc/8.2.12: Already installed! (1 of 2)
debfoster/2.8@ohpcd/stable: Calling source() in /storage/Users/currentUser/.conan2/p/debfo8777d8096a790/s
debfoster/2.8@ohpcd/stable: Sources correctly downloaded from https://deb.debian.org/debian/pool/main/d/debfoster/debfoster_2.8.orig.tar.xz
debfoster/2.8@ohpcd/stable: Uncompressing debfoster_2.8.orig.tar.xz to .

-------- Installing package debfoster/2.8@ohpcd/stable (2 of 2) --------
debfoster/2.8@ohpcd/stable: Building from source
debfoster/2.8@ohpcd/stable: Package debfoster/2.8@ohpcd/stable:e402a17462529d13f1018a9751df0cb4c8656f19
debfoster/2.8@ohpcd/stable: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
debfoster/2.8@ohpcd/stable: requires: gc/8.2.12#66bd5b05e364da6f7a7343b943cb186f:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa
debfoster/2.8@ohpcd/stable: Copying sources to build folder
debfoster/2.8@ohpcd/stable: Building your package in /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b
debfoster/2.8@ohpcd/stable: Calling generate()
debfoster/2.8@ohpcd/stable: Generators folder: /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/conan
debfoster/2.8@ohpcd/stable: Generating aggregated env files
debfoster/2.8@ohpcd/stable: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
debfoster/2.8@ohpcd/stable: Calling build()
debfoster/2.8@ohpcd/stable: Apply patch (portability): configure 内嵌的 config.status 以 umask 077 建立 ./confXXXXXX 临时目录；该目录在 hmdfs 上落盘为 2700 且属主不是本进程 uid，随后写 subs1.awk 报 Permission denied 使 configure 失败。改为 umask 022
debfoster/2.8@ohpcd/stable: Apply patch (portability): src/keepers.c 调用 open() 并使用 O_RDONLY/O_RDWR/O_CREAT 但只包含 sys/file.h；glibc 经由 sys/file.h 间接引入 fcntl.h 而 OHOS 的 musl 不引入。显式包含 fcntl.h
debfoster/2.8@ohpcd/stable: Apply patch (portability): etc/Makefile.am 的 install-data-local 硬编码 coreutils 的 install -d；OHOS 无 install 命令导致 make install 报 exit 127。改用 autoconf 提供的 MKDIR_P 变量并同步更新无法再生的 etc/Makefile.in
debfoster/2.8@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/configure" --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' 
checking build system type... aarch64-unknown-linux-ohos
checking host system type... aarch64-unknown-linux-ohos
checking target system type... aarch64-unknown-linux-ohos
checking for a BSD-compatible install... /storage/Users/currentUser/usr/local/bin/ginstall -c
checking whether build environment is sane... yes
checking for a race-free mkdir -p... /storage/Users/currentUser/usr/local/bin/mkdir -p
checking for gawk... gawk
checking whether make sets $(MAKE)... yes
checking whether make supports nested variables... yes
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
checking whether make supports the include directive... yes (GNU style)
checking dependency style of /data/service/hnp/bin/clang... gcc3
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/configure: line 4638: AX_CFLAGS_WARN_ALL: command not found
checking for a sed that does not truncate output... /usr/bin/sed
checking whether NLS is requested... yes
checking for msgfmt... /data/service/hnp/bin/msgfmt
checking for gmsgfmt... /data/service/hnp/bin/msgfmt
checking for xgettext... /data/service/hnp/bin/xgettext
checking for msgmerge... no
checking for ld used by /data/service/hnp/bin/clang... /data/service/hnp/bin/ld
checking if the linker (/data/service/hnp/bin/ld) is GNU ld... yes
checking for shared library run path origin... done
checking 32-bit host C ABI... no
checking how to run the C preprocessor... /data/service/hnp/bin/clang -E
checking for egrep -e... /data/service/hnp/bin/grep -E
checking for ELF binary format... yes
checking for the common suffixes of directories in the library search path... lib,lib,lib
checking for CFPreferencesCopyAppValue... no
checking for CFLocaleCopyPreferredLanguages... no
checking for GNU gettext in libc... no
checking for iconv... yes
checking for working iconv... yes
checking for GNU gettext in libintl... no
checking whether to use NLS... no
checking for stdio.h... yes
checking for stdlib.h... yes
checking for string.h... yes
checking for inttypes.h... yes
checking for stdint.h... yes
checking for strings.h... yes
checking for sys/stat.h... yes
checking for sys/types.h... yes
checking for unistd.h... yes
checking for unistd.h... (cached) yes
checking for size_t... yes
checking for working alloca.h... yes
checking for alloca... yes
checking for GC_malloc in -lgc... yes
checking that generated files are newer than configure... done
configure: creating ./config.status
config.status: creating Makefile
config.status: creating src/Makefile
config.status: creating etc/Makefile
config.status: creating doc/Makefile
config.status: creating po/Makefile.in
config.status: creating src/config.h
config.status: executing depfiles commands
config.status: executing po-directories commands
config.status: creating po/POTFILES
config.status: creating po/Makefile

debfoster/2.8@ohpcd/stable: RUN: make -j1
Making all in src
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/src'
make  all-am
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/src'
depbase=`echo AVLTree.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT AVLTree.o -MD -MP -MF $depbase.Tpo -c -o AVLTree.o /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/AVLTree.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo asktty.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT asktty.o -MD -MP -MF $depbase.Tpo -c -o asktty.o /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/asktty.c &&\
mv -f $depbase.Tpo $depbase.Po
In file included from /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/asktty.c:10:
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/sys/fcntl.h:1:2: warning: redirecting incorrect #include <sys/fcntl.h> to <fcntl.h> [-W#warnings]
#warning redirecting incorrect #include <sys/fcntl.h> to <fcntl.h>
 ^
1 warning generated.
depbase=`echo conffile.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT conffile.o -MD -MP -MF $depbase.Tpo -c -o conffile.o /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/conffile.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo debfoster.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT debfoster.o -MD -MP -MF $depbase.Tpo -c -o debfoster.o /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c &&\
mv -f $depbase.Tpo $depbase.Po
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:176:12: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                        Vprintf(_("Package was removed: %s\n"), (symbol_t)c->item);
                                ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:75:19: note: passing argument to parameter 'fmt' here
int Vprintf(char *fmt, ...) {
                  ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:391:29: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                show_set(&pkg->providers, _("Dependency %s is met by:"), name);
                                          ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:415:25: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
        if(!show_set(&visited, _("Package %s depends on:"), name))
                               ^~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:442:29: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
        if (!show_set(&dependents, _("The following %d packages on the keeper list rely on %s:"), count, name))
                                   ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:504:25: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
        if(!show_set(&related, _("The following %d packages are brought in by %s:"), count, name))
                               ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:695:25: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                if(!show_set(keepers, _("The following packages are on the keeper list:")))
                                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:697:23: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                show_set(nokeepers, _("The following packages are marked as non-keepers:"));
                                    ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:724:13: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                Vprintf(_("Installing package: %s\n"), (symbol_t)c->item);
                                        ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:75:19: note: passing argument to parameter 'fmt' here
int Vprintf(char *fmt, ...) {
                  ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:853:13: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                Vprintf(_("Keeping package: %s\n"), pkg->name);
                                        ^~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:75:19: note: passing argument to parameter 'fmt' here
int Vprintf(char *fmt, ...) {
                  ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:864:22: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                        show_set(related, _("\n%s is keeping the following %d packages installed:"), pkg->name, related_count);
                                          ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:867:25: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                switch((i = tty_ask(_("ynpshiuqx?"), _("Keep %s? [Ynpsiuqx?], [H]elp: "), pkg->name))) {
                                                    ^~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/asktty.h:4:26: note: passing argument to parameter here
extern int tty_ask(char *,char *, ...);
                         ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:867:42: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                switch((i = tty_ask(_("ynpshiuqx?"), _("Keep %s? [Ynpsiuqx?], [H]elp: "), pkg->name))) {
                                                                     ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/asktty.h:4:33: note: passing argument to parameter here
extern int tty_ask(char *,char *, ...);
                                ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:891:9: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                                                _("This is a task containing the following installed packages:"));
                                                                ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:927:45: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                        switch((i = tty_ask(_("ny"), _("Exit without saving? [yN?]: ")))) {
                                            ^~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/asktty.h:4:26: note: passing argument to parameter here
extern int tty_ask(char *,char *, ...);
                         ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:927:54: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                        switch((i = tty_ask(_("ny"), _("Exit without saving? [yN?]: ")))) {
                                                     ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/asktty.h:4:33: note: passing argument to parameter here
extern int tty_ask(char *,char *, ...);
                                ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:953:27: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                        if(!show_set(postpone, _("The following packages have been orphaned:")))
                                               ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:974:15: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                                Vprintf(_("Package is not installed: %s\n"), (symbol_t)c->item);
                                                        ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:75:19: note: passing argument to parameter 'fmt' here
int Vprintf(char *fmt, ...) {
                  ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:977:14: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                        Vprintf(_("Package is a dependency: %s\n"), pkg->name);
                                                ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:75:19: note: passing argument to parameter 'fmt' here
int Vprintf(char *fmt, ...) {
                  ^
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:980:14: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                        Vprintf(_("Removing package: %s\n"), pkg->name);
                                                ^~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/debfoster.c:75:19: note: passing argument to parameter 'fmt' here
int Vprintf(char *fmt, ...) {
                  ^
19 warnings generated.
depbase=`echo error.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT error.o -MD -MP -MF $depbase.Tpo -c -o error.o /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/error.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo keepers.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT keepers.o -MD -MP -MF $depbase.Tpo -c -o keepers.o /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/keepers.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo status.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT status.o -MD -MP -MF $depbase.Tpo -c -o status.o /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/status.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo symbol.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT symbol.o -MD -MP -MF $depbase.Tpo -c -o symbol.o /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/symbol.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo vercmp.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT vercmp.o -MD -MP -MF $depbase.Tpo -c -o vercmp.o /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/vercmp.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo xargs.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT xargs.o -MD -MP -MF $depbase.Tpo -c -o xargs.o /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/xargs.c &&\
mv -f $depbase.Tpo $depbase.Po
/data/service/hnp/bin/clang -Wall -O3  -L/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/lib -o debfoster AVLTree.o asktty.o conffile.o debfoster.o error.o keepers.o status.o symbol.o vercmp.o xargs.o  -lgc -lgc -lcord
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/src'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/src'
Making all in etc
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/etc'
make[1]: Nothing to be done for 'all'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/etc'
Making all in doc
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/doc'
make[1]: Nothing to be done for 'all'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/doc'
Making all in po
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/po'
make[1]: Nothing to be done for 'all'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/po'
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release'
make[1]: Nothing to be done for 'all-am'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release'

debfoster/2.8@ohpcd/stable: RUN: make check -j1
Making check in src
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/src'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/src'
Making check in etc
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/etc'
make[1]: Nothing to be done for 'check'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/etc'
Making check in doc
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/doc'
make[1]: Nothing to be done for 'check'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/doc'
Making check in po
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/po'
make[1]: Nothing to be done for 'check'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/po'
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release'
make[1]: Nothing to be done for 'check-am'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release'

debfoster/2.8@ohpcd/stable: Package 'e402a17462529d13f1018a9751df0cb4c8656f19' built
debfoster/2.8@ohpcd/stable: Build folder /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release
debfoster/2.8@ohpcd/stable: Generating the package
debfoster/2.8@ohpcd/stable: Packaging in folder /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p
debfoster/2.8@ohpcd/stable: Calling package()
debfoster/2.8@ohpcd/stable: RUN: make install DESTDIR=/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p -j20
make: jobserver mkfifo: /storage/Users/currentUser/GMfifo27597: Operation not permitted
Making install in src
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/src'
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/src'
make[2]: Nothing to be done for 'install-data-am'.
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p//bin'
  /storage/Users/currentUser/usr/local/bin/ginstall -c debfoster '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p//bin'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/src'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/src'
Making install in etc
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/etc'
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/etc'
/storage/Users/currentUser/usr/local/bin/mkdir -p /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p//var/lib/debfoster
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p//etc'
 /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/etc/debfoster.conf '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p//etc'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/etc'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/etc'
Making install in doc
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/doc'
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/doc'
make[2]: Nothing to be done for 'install-exec-am'.
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p//share/man/man8'
 /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/doc/debfoster.8 '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p//share/man/man8'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/doc'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/doc'
Making install in po
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/po'
if test "debfoster" = "gettext-tools"; then \
  /storage/Users/currentUser/usr/local/bin/mkdir -p /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p//share/gettext/po; \
  for file in Makefile.in.in remove-potcdate.sin quot.sed boldquot.sed en@quot.header en@boldquot.header insert-header.sin Rules-quot   Makevars.template; do \
    /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/po/$file \
		    /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p//share/gettext/po/$file; \
  done; \
  for file in Makevars; do \
    rm -f /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p//share/gettext/po/$file; \
  done; \
else \
  : ; \
fi
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release/po'
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release'
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release'
make[2]: Nothing to be done for 'install-exec-am'.
make[2]: Nothing to be done for 'install-data-am'.
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release'

debfoster/2.8@ohpcd/stable: package(): Packaged 2 files: debfoster, COPYING
debfoster/2.8@ohpcd/stable: package(): Packaged 1 '.conf' file: debfoster.conf
debfoster/2.8@ohpcd/stable: package(): Packaged 1 '.8' file: debfoster.8
debfoster/2.8@ohpcd/stable: package(): Packaged 1 '.debfoster' file: LICENSE.debfoster
debfoster/2.8@ohpcd/stable: package(): Packaged 1 '.AVLTree' file: LICENSE.AVLTree
debfoster/2.8@ohpcd/stable: package(): Packaged 1 '.symbol' file: LICENSE.symbol
debfoster/2.8@ohpcd/stable: Created package revision 3b26741a6c16f104f3a99d80f151271a
debfoster/2.8@ohpcd/stable: Package 'e402a17462529d13f1018a9751df0cb4c8656f19' created
debfoster/2.8@ohpcd/stable: Full package reference: debfoster/2.8@ohpcd/stable#4687874699f15616ae67331175e4c4b8:e402a17462529d13f1018a9751df0cb4c8656f19#3b26741a6c16f104f3a99d80f151271a
debfoster/2.8@ohpcd/stable: Package folder /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    debfoster/2.8@ohpcd/stable (test package): /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/test_package/conanfile.py
Requirements
    debfoster/2.8@ohpcd/stable#4687874699f15616ae67331175e4c4b8 - Cache
    gc/8.2.12#66bd5b05e364da6f7a7343b943cb186f - Cache

======== Computing necessary packages ========
Requirements
    debfoster/2.8@ohpcd/stable#4687874699f15616ae67331175e4c4b8:e402a17462529d13f1018a9751df0cb4c8656f19#3b26741a6c16f104f3a99d80f151271a - Cache
Skipped binaries
    gc/8.2.12

======== Installing packages ========
debfoster/2.8@ohpcd/stable: Already installed! (1 of 1)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/test_package/build-release
debfoster/2.8@ohpcd/stable (test package): Test package build: build-release
debfoster/2.8@ohpcd/stable (test package): Test package build folder: /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/test_package/build-release
debfoster/2.8@ohpcd/stable (test package): Writing generators to /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/test_package/build-release/conan
debfoster/2.8@ohpcd/stable (test package): Generator 'VirtualRunEnv' calling 'generate()'
debfoster/2.8@ohpcd/stable (test package): Generating aggregated env files
debfoster/2.8@ohpcd/stable (test package): Generated aggregated env files: ['conanrun.sh', 'conanbuild.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
debfoster/2.8@ohpcd/stable (test package): Running test()
debfoster/2.8@ohpcd/stable (test package): RUN: /data/service/hnp/bin/bash /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/test_package/test.sh
ok   debfoster --version reports 2.8
ok   -V is an alias of --version
ok   help prints a usage line
ok   help documents -k/--keeperfile
ok   help documents -s/--show-orphans
ok   help documents all six query modes
ok   unknown command line option exits 1
ok   unknown -o option exits 1
ok   -o argument without '=' exits 1
ok   unreadable dpkg status database exits 3
ok   -a on an empty keeper file says so
ok   -s lists exactly the two unrequested packages
ok   -d lists a package's dependencies
ok   -d reports an unknown package by name
ok   -p resolves a virtual dependency through Provides:
ok   -r reports the dependency that only appbar needs
ok   -e resolves the keeper package that relies on a dependency
ok   -a echoes the keeper file contents sorted
ok   -r reports nothing once the dependency is a keeper itself
ok   -e on an empty keeper list reports no dependents
ok   interactive keep answers exactly one question
ok   essential and dependency packages are never asked about
ok   answering y records the package in the keeper file
ok   the y answer is visible through -a
ok   answering n records the refusal with a leading dash
ok   a refused package disappears from -a
ok   a refused package is still reported as an orphan by -s
ok   the keeper file survives a repeated run
ok   -d lists both dependencies of toolv
ok   -s finds the two packages nothing depends on
ok   -r reports only the single-use dependency of toolv
ok   -r does not claim a dependency another package also needs
ok   -e on the versioned fixture reports no dependents
ok   the packaged default configuration file is installed
ok   the packaged configuration is accepted by -c and -o
ok   without -c the build-time prefix paths are used

HMBS_TEST_SUMMARY discovered=36 passed=36 failed=0 skipped=0

```
