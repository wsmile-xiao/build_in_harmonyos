# w3-local-ci-log — 原始日志逐字留档（W3 本地 CI 模拟（setup.sh + build_and_test.sh））

> 本文件按 workflow 第 6.1 节「证据文件入库口径」生成：**原始 `*.log` 不随 PR 提交**
> （`.gitcode/review-memory.md` 第 19 条明列 PR 禁止 `*.log`），改为把原始日志内容
> **fenced 逐字复制**成本文件，同时满足该条与「评审端可见」。

| 项 | 值 |
| --- | --- |
| 原始文件 | `reports/w3-local-ci.log`（本地产出，按上述口径不入库） |
| 字节数 | 49803 |
| 行数 | 733 |
| sha256 | `dcdaa830ec9bcc3c8aaa6d1b541fc39f784faf70684893b68d973162b8c31f99` |
| 生成命令 | `cd <worktree> && PYTHONPATH=scripts python3 -c "from ohc.workflow_checks import run_local_ci; run_local_ci('debfoster', '2.8', '.')"` |

该文件由 scripts/ohc/workflow_checks.py 的 run_local_ci() 写出。

**判读提示**：本文件内容为逐字复制，未经改写；下列 fenced 块即原始日志全文。

```text
$ setup.sh (RC=0)
[step] Conan environment setup...
[step] Conan version: Conan version 2.29.1
[step] Disabling conancenter (private CI, not needed)
conancenter: https://center2.conan.io [Verify SSL: True, Enabled: False]
[step] remote 已就绪: ohpcd
[step] Importing profile from /storage/Users/currentUser/ws/wt-debfoster-2.8/ci/conan/profiles/ohos-aarch64
[step] Profile file available at: /storage/Users/currentUser/ws/wt-debfoster-2.8/ci/conan/profiles/ohos-aarch64
[step] Conan environment ready ✅
[step]   remote: ohpcd
[step]   profile: ohos-aarch64
[step]   conan: Conan version 2.29.1


$ build_and_test.sh archives/d/debfoster/2.8 (RC=0)
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
[step] CI_PACKAGES received: archives/d/debfoster/2.8
[step] Found 1 package(s) to build

━━━ Building: debfoster/2.8 ━━━
[step] L0: Quality gate checks...
[step] L0i: Checking dependency availability in registry (R36)...
        [ok] dependency in registry: gc/8.2.12
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
  检查模式: prdiff (29 个文件)

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
  [try 1/1.1/3] debfoster_2.8.orig.tar.xz ← https://deb.debian.org/debian/pool/main/d/debfoster/debfoster_2.8.orig.tar.xz...
  [ok] debfoster_2.8.orig.tar.xz (139KB) via mirror 1
  [done] Pre-downloaded 1 files, conandata.yml updated to file:// URLs
[step] Running conan create (output logged to /storage/Users/currentUser/ws/wt-debfoster-2.8/.ci_logs/conan_build_debfoster_2.8.log)...

======== Exporting recipe to the cache ========
debfoster/2.8: Exporting package recipe: /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/conanfile.py
debfoster/2.8: exports: File 'conandata.yml' found. Exporting it...
debfoster/2.8: Calling export_sources()
debfoster/2.8: Copied 1 '.yml' file: conandata.yml
debfoster/2.8: Copied 1 '.py' file: conanfile.py
debfoster/2.8: Copied 3 '.patch' files: 0001-configure-umask-hmdfs.patch, 0002-keepers-include-fcntl.patch, 0003-etc-makefile-install-d.patch
debfoster/2.8: Copied 1 '.guess' file: config.guess
debfoster/2.8: Copied 1 '.sub' file: config.sub
debfoster/2.8: Copied 3 files: install-sh, missing, depcomp
debfoster/2.8: Copied 1 '.m4' file: aclocal.m4
debfoster/2.8: Exported to cache folder: /storage/Users/currentUser/.conan2/p/debfo1c30c4915b19f/e
debfoster/2.8: Exported: debfoster/2.8#122450db94d28002bf26df223cbfc9ac (2026-09-11 02:05:45 UTC)

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
    debfoster/2.8#122450db94d28002bf26df223cbfc9ac - Cache
    gc/8.2.12#66bd5b05e364da6f7a7343b943cb186f - Cache

======== Computing necessary packages ========
debfoster/2.8: Forced build from source
Requirements
    debfoster/2.8#122450db94d28002bf26df223cbfc9ac:e402a17462529d13f1018a9751df0cb4c8656f19 - Build
    gc/8.2.12#66bd5b05e364da6f7a7343b943cb186f:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa#834af36b852b0ba4f1a0ed9c904b1f95 - Cache

======== Installing packages ========
gc/8.2.12: Already installed! (1 of 2)
debfoster/2.8: Calling source() in /storage/Users/currentUser/.conan2/p/debfo1c30c4915b19f/s
debfoster/2.8: Sources correctly downloaded from file:///storage/Users/currentUser/ws/wt-debfoster-2.8/.build-cache/predl_cache/86b8c49b_debfoster_2.8.orig.tar.xz
debfoster/2.8: Uncompressing 86b8c49b_debfoster_2.8.orig.tar.xz to .

-------- Installing package debfoster/2.8 (2 of 2) --------
debfoster/2.8: Building from source
debfoster/2.8: Package debfoster/2.8:e402a17462529d13f1018a9751df0cb4c8656f19
debfoster/2.8: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
debfoster/2.8: requires: gc/8.2.12#66bd5b05e364da6f7a7343b943cb186f:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa
debfoster/2.8: Copying sources to build folder
debfoster/2.8: Building your package in /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b
debfoster/2.8: Calling generate()
debfoster/2.8: Generators folder: /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/conan
debfoster/2.8: Generating aggregated env files
debfoster/2.8: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
debfoster/2.8: Calling build()
debfoster/2.8: Apply patch (portability): configure 内嵌的 config.status 以 umask 077 建立 ./confXXXXXX 临时目录；该目录在 hmdfs 上落盘为 2700 且属主不是本进程 uid，随后写 subs1.awk 报 Permission denied 使 configure 失败。改为 umask 022
debfoster/2.8: Apply patch (portability): src/keepers.c 调用 open() 并使用 O_RDONLY/O_RDWR/O_CREAT 但只包含 sys/file.h；glibc 经由 sys/file.h 间接引入 fcntl.h 而 OHOS 的 musl 不引入。显式包含 fcntl.h
debfoster/2.8: Apply patch (portability): etc/Makefile.am 的 install-data-local 硬编码 coreutils 的 install -d；OHOS 无 install 命令导致 make install 报 exit 127。改用 autoconf 提供的 MKDIR_P 变量并同步更新无法再生的 etc/Makefile.in
debfoster/2.8: RUN: "/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/configure" --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' 
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
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/configure: line 4638: AX_CFLAGS_WARN_ALL: command not found
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

debfoster/2.8: RUN: make -j1
Making all in src
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/src'
make  all-am
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/src'
depbase=`echo AVLTree.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT AVLTree.o -MD -MP -MF $depbase.Tpo -c -o AVLTree.o /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/AVLTree.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo asktty.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT asktty.o -MD -MP -MF $depbase.Tpo -c -o asktty.o /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/asktty.c &&\
mv -f $depbase.Tpo $depbase.Po
In file included from /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/asktty.c:10:
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/sys/fcntl.h:1:2: warning: redirecting incorrect #include <sys/fcntl.h> to <fcntl.h> [-W#warnings]
#warning redirecting incorrect #include <sys/fcntl.h> to <fcntl.h>
 ^
1 warning generated.
depbase=`echo conffile.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT conffile.o -MD -MP -MF $depbase.Tpo -c -o conffile.o /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/conffile.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo debfoster.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT debfoster.o -MD -MP -MF $depbase.Tpo -c -o debfoster.o /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c &&\
mv -f $depbase.Tpo $depbase.Po
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:176:12: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                        Vprintf(_("Package was removed: %s\n"), (symbol_t)c->item);
                                ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:75:19: note: passing argument to parameter 'fmt' here
int Vprintf(char *fmt, ...) {
                  ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:391:29: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                show_set(&pkg->providers, _("Dependency %s is met by:"), name);
                                          ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:415:25: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
        if(!show_set(&visited, _("Package %s depends on:"), name))
                               ^~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:442:29: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
        if (!show_set(&dependents, _("The following %d packages on the keeper list rely on %s:"), count, name))
                                   ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:504:25: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
        if(!show_set(&related, _("The following %d packages are brought in by %s:"), count, name))
                               ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:695:25: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                if(!show_set(keepers, _("The following packages are on the keeper list:")))
                                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:697:23: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                show_set(nokeepers, _("The following packages are marked as non-keepers:"));
                                    ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:724:13: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                Vprintf(_("Installing package: %s\n"), (symbol_t)c->item);
                                        ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:75:19: note: passing argument to parameter 'fmt' here
int Vprintf(char *fmt, ...) {
                  ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:853:13: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                Vprintf(_("Keeping package: %s\n"), pkg->name);
                                        ^~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:75:19: note: passing argument to parameter 'fmt' here
int Vprintf(char *fmt, ...) {
                  ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:864:22: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                        show_set(related, _("\n%s is keeping the following %d packages installed:"), pkg->name, related_count);
                                          ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:867:25: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                switch((i = tty_ask(_("ynpshiuqx?"), _("Keep %s? [Ynpsiuqx?], [H]elp: "), pkg->name))) {
                                                    ^~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/asktty.h:4:26: note: passing argument to parameter here
extern int tty_ask(char *,char *, ...);
                         ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:867:42: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                switch((i = tty_ask(_("ynpshiuqx?"), _("Keep %s? [Ynpsiuqx?], [H]elp: "), pkg->name))) {
                                                                     ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/asktty.h:4:33: note: passing argument to parameter here
extern int tty_ask(char *,char *, ...);
                                ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:891:9: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                                                _("This is a task containing the following installed packages:"));
                                                                ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:927:45: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                        switch((i = tty_ask(_("ny"), _("Exit without saving? [yN?]: ")))) {
                                            ^~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/asktty.h:4:26: note: passing argument to parameter here
extern int tty_ask(char *,char *, ...);
                         ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:927:54: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                        switch((i = tty_ask(_("ny"), _("Exit without saving? [yN?]: ")))) {
                                                     ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/asktty.h:4:33: note: passing argument to parameter here
extern int tty_ask(char *,char *, ...);
                                ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:953:27: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                        if(!show_set(postpone, _("The following packages have been orphaned:")))
                                               ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:91:34: note: passing argument to parameter 'fmt' here
int show_set(AVLTree *set, char *fmt, ...) {
                                 ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:974:15: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                                Vprintf(_("Package is not installed: %s\n"), (symbol_t)c->item);
                                                        ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:75:19: note: passing argument to parameter 'fmt' here
int Vprintf(char *fmt, ...) {
                  ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:977:14: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                        Vprintf(_("Package is a dependency: %s\n"), pkg->name);
                                                ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:75:19: note: passing argument to parameter 'fmt' here
int Vprintf(char *fmt, ...) {
                  ^
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:980:14: warning: passing 'const char *' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
                                        Vprintf(_("Removing package: %s\n"), pkg->name);
                                                ^~~~~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:79:18: note: expanded from macro '_'
#define _(Msgid) gettext(Msgid)
                 ^~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/intl.h:55:25: note: expanded from macro 'gettext'
# define gettext(Msgid) ((const char *) (Msgid))
                        ^~~~~~~~~~~~~~~~~~~~~~~~
/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/debfoster.c:75:19: note: passing argument to parameter 'fmt' here
int Vprintf(char *fmt, ...) {
                  ^
19 warnings generated.
depbase=`echo error.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT error.o -MD -MP -MF $depbase.Tpo -c -o error.o /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/error.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo keepers.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT keepers.o -MD -MP -MF $depbase.Tpo -c -o keepers.o /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/keepers.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo status.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT status.o -MD -MP -MF $depbase.Tpo -c -o status.o /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/status.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo symbol.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT symbol.o -MD -MP -MF $depbase.Tpo -c -o symbol.o /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/symbol.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo vercmp.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT vercmp.o -MD -MP -MF $depbase.Tpo -c -o vercmp.o /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/vercmp.c &&\
mv -f $depbase.Tpo $depbase.Po
depbase=`echo xargs.o | sed 's|[^/]*$|.deps/&|;s|\.o$||'`;\
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT xargs.o -MD -MP -MF $depbase.Tpo -c -o xargs.o /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/src/xargs.c &&\
mv -f $depbase.Tpo $depbase.Po
/data/service/hnp/bin/clang -Wall -O3  -L/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/lib -o debfoster AVLTree.o asktty.o conffile.o debfoster.o error.o keepers.o status.o symbol.o vercmp.o xargs.o  -lgc -lgc -lcord
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/src'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/src'
Making all in etc
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/etc'
make[1]: Nothing to be done for 'all'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/etc'
Making all in doc
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/doc'
make[1]: Nothing to be done for 'all'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/doc'
Making all in po
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/po'
make[1]: Nothing to be done for 'all'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/po'
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release'
make[1]: Nothing to be done for 'all-am'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release'

debfoster/2.8: RUN: make check -j1
Making check in src
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/src'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/src'
Making check in etc
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/etc'
make[1]: Nothing to be done for 'check'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/etc'
Making check in doc
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/doc'
make[1]: Nothing to be done for 'check'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/doc'
Making check in po
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/po'
make[1]: Nothing to be done for 'check'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/po'
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release'
make[1]: Nothing to be done for 'check-am'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release'

debfoster/2.8: Package 'e402a17462529d13f1018a9751df0cb4c8656f19' built
debfoster/2.8: Build folder /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release
debfoster/2.8: Generating the package
debfoster/2.8: Packaging in folder /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/p
debfoster/2.8: Calling package()
debfoster/2.8: RUN: make install DESTDIR=/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/p -j20
make: jobserver mkfifo: /storage/Users/currentUser/GMfifo33290: Operation not permitted
Making install in src
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/src'
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/src'
make[2]: Nothing to be done for 'install-data-am'.
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/p//bin'
  /storage/Users/currentUser/usr/local/bin/ginstall -c debfoster '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/p//bin'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/src'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/src'
Making install in etc
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/etc'
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/etc'
/storage/Users/currentUser/usr/local/bin/mkdir -p /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/p//var/lib/debfoster
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/p//etc'
 /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/etc/debfoster.conf '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/p//etc'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/etc'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/etc'
Making install in doc
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/doc'
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/doc'
make[2]: Nothing to be done for 'install-exec-am'.
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/p//share/man/man8'
 /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/doc/debfoster.8 '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/p//share/man/man8'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/doc'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/doc'
Making install in po
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/po'
if test "debfoster" = "gettext-tools"; then \
  /storage/Users/currentUser/usr/local/bin/mkdir -p /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/p//share/gettext/po; \
  for file in Makefile.in.in remove-potcdate.sin quot.sed boldquot.sed en@quot.header en@boldquot.header insert-header.sin Rules-quot   Makevars.template; do \
    /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/po/$file \
		    /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/p//share/gettext/po/$file; \
  done; \
  for file in Makevars; do \
    rm -f /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/p//share/gettext/po/$file; \
  done; \
else \
  : ; \
fi
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release/po'
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release'
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release'
make[2]: Nothing to be done for 'install-exec-am'.
make[2]: Nothing to be done for 'install-data-am'.
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/b/build-release'

debfoster/2.8: package(): Packaged 2 files: debfoster, COPYING
debfoster/2.8: package(): Packaged 1 '.conf' file: debfoster.conf
debfoster/2.8: package(): Packaged 1 '.8' file: debfoster.8
debfoster/2.8: package(): Packaged 1 '.debfoster' file: LICENSE.debfoster
debfoster/2.8: package(): Packaged 1 '.AVLTree' file: LICENSE.AVLTree
debfoster/2.8: package(): Packaged 1 '.symbol' file: LICENSE.symbol
debfoster/2.8: Created package revision 3b26741a6c16f104f3a99d80f151271a
debfoster/2.8: Package 'e402a17462529d13f1018a9751df0cb4c8656f19' created
debfoster/2.8: Full package reference: debfoster/2.8#122450db94d28002bf26df223cbfc9ac:e402a17462529d13f1018a9751df0cb4c8656f19#3b26741a6c16f104f3a99d80f151271a
debfoster/2.8: Package folder /storage/Users/currentUser/.conan2/p/b/debfoa67fa32ac0e26/p

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    debfoster/2.8 (test package): /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/test_package/conanfile.py
Requirements
    debfoster/2.8#122450db94d28002bf26df223cbfc9ac - Cache
    gc/8.2.12#66bd5b05e364da6f7a7343b943cb186f - Cache

======== Computing necessary packages ========
Requirements
    debfoster/2.8#122450db94d28002bf26df223cbfc9ac:e402a17462529d13f1018a9751df0cb4c8656f19#3b26741a6c16f104f3a99d80f151271a - Cache
Skipped binaries
    gc/8.2.12

======== Installing packages ========
debfoster/2.8: Already installed! (1 of 1)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/test_package/build-release
debfoster/2.8 (test package): Test package build: build-release
debfoster/2.8 (test package): Test package build folder: /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/test_package/build-release
debfoster/2.8 (test package): Writing generators to /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/test_package/build-release/conan
debfoster/2.8 (test package): Generator 'VirtualRunEnv' calling 'generate()'
debfoster/2.8 (test package): Generating aggregated env files
debfoster/2.8 (test package): Generated aggregated env files: ['conanrun.sh', 'conanbuild.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
debfoster/2.8 (test package): Running test()
debfoster/2.8 (test package): RUN: /data/service/hnp/bin/bash /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/test_package/test.sh
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

[ok] debfoster/2.8 — conan create passed
[step] L1: Verifying test execution from conan create log...
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[ok] L1c: Upstream official tests (make check/ctest) executed in build phase
[step] L4: Scanning patches for dangerous functions...
[step] L5: Baseline artifact check...
[ok] L5: bin/ has content
[step] L1e: Destructive negative test (R34)...
        [sabotage] bin/ moved away
        [sabotage] lib/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on debfoster
[step] L2: Smoke test (version/help check)...
[ok] L2: debfoster --version OK

L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: debfoster --version OK
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
