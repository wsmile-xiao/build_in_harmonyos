# ocproxy 1.6 W3 本地 CI 模拟逐字日志（采信轮）

`ohc-run.py` 生成的运行期日志，属本轮真实运行。仓库把 `*.log` 明列为禁止入库文件
（`.gitcode/review-memory.md` §19），故逐字转写为 `.md`。

- 原始文件：`reports/w3-local-ci.log`（由工具生成，未入库）
- 原始字节数：134345
- 原始行数：1618
- 原始 sha256：`3dccee86116a467129d0cdcbb1326e350369496140d2a848cf86a912c191ed36`
- 转写时间：2026-09-12T18:15:20Z
- 生成命令：`python3 scripts/ohc-run.py finish ocproxy 1.6 built --project-dir <worktree>`
- **唯一加工**：把逐轮重建的缓存分片目录名 `/storage/Users/currentUser/.conan2/p/b/ocpro<hash>`
  替换为 `<PKG_DIR>`，共 410 处（每轮清缓存重建都会换名，写死会让证据在下一轮不可复核）。

## 字节账（按实测填写）

```text
原始日志字节数                      : 134345
原始日志行数                        : 1618
归一化后的逐字正文（不含末尾换行）    : 114664
归一化后的逐字正文（含末尾换行）      : 114665
原始 − 归一化正文（不含末尾换行）     : 19681
替换处数                            : 410
平均每处净减少                       : 48.00 字符
```

## 结论行

```text
TOTAL=17 PASS=17 FAIL=0
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: ocproxy version/help failed, vpnns failed
L4_RESULT=warn: dangerous functions in patches
L5_RESULT=pass: bin/ has content
```

## 逐字日志（已归一化分片目录名）

```text
$ setup.sh (RC=0)
[step] Conan environment setup...
[step] Conan version: Conan version 2.29.1
[step] Disabling conancenter (private CI, not needed)
conancenter: https://center2.conan.io [Verify SSL: True, Enabled: False]
[step] remote 已就绪: ohpcd
[step] Importing profile from /storage/Users/currentUser/ws/worktrees/ocproxy-1.6/ci/conan/profiles/ohos-aarch64
[step] Profile file available at: /storage/Users/currentUser/ws/worktrees/ocproxy-1.6/ci/conan/profiles/ohos-aarch64
[step] Conan environment ready ✅
[step]   remote: ohpcd
[step]   profile: ohos-aarch64
[step]   conan: Conan version 2.29.1


$ build_and_test.sh archives/o/ocproxy/1.6 (RC=0)
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
[step] CI_PACKAGES received: archives/o/ocproxy/1.6
[step] Found 1 package(s) to build

━━━ Building: ocproxy/1.6 ━━━
[step] L0: Quality gate checks...
[step] L0i: Checking dependency availability in registry (R36)...
        [ok] dependency in registry: automake/1.18
        [ok] dependency in registry: libevent/2.1.13
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
[step] Mirror fallback: rewriting source URLs in conandata.yml...
        [ok] Source URLs rewritten with mirror fallback
[step] Pre-download: extracting source URLs from conandata.yml...
  found 2 source URL(s)
  [try 1/1.1/3] v1.60.tar.gz ← https://gh-proxy.com/https://github.com/cernekee/ocproxy/archive/refs/tags/v1.60...
  [ok] v1.60.tar.gz (951KB) via mirror 1
  [try 1/2.1/3] v1.60.tar.gz ← https://gh-proxy.com/https://github.com/cernekee/ocproxy/archive/refs/tags/v1.60...
  [ok] v1.60.tar.gz (951KB) via mirror 1
  [done] Pre-downloaded 2 files, conandata.yml updated to file:// URLs
[step] Running conan create (output logged to /storage/Users/currentUser/ws/worktrees/ocproxy-1.6/.ci_logs/conan_build_ocproxy_1.6.log)...

======== Exporting recipe to the cache ========
ocproxy/1.6: Exporting package recipe: /storage/Users/currentUser/ws/worktrees/ocproxy-1.6/archives/o/ocproxy/1.6/conanfile.py
ocproxy/1.6: exports: File 'conandata.yml' found. Exporting it...
ocproxy/1.6: Calling export_sources()
ocproxy/1.6: Copied 1 '.yml' file: conandata.yml
ocproxy/1.6: Copied 1 '.py' file: conanfile.py
ocproxy/1.6: Copied 2 '.patch' files: 0001-src-ocproxy.c.patch, 0002-src-vpnns.c.patch
ocproxy/1.6: Exported to cache folder: /storage/Users/currentUser/.conan2/p/ocpro63ded43059237/e
ocproxy/1.6: Exported: ocproxy/1.6#b5086f68885e0b2f3fc53fbca35fc3a0 (2026-09-12 18:10:58 UTC)

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
Graph root
    cli
Requirements
    libevent/2.1.13#01073c17d132a8cb6e7e1d19d25c1b22 - Cache
    ocproxy/1.6#b5086f68885e0b2f3fc53fbca35fc3a0 - Cache
Test requirements
    zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9 - Cache
Build requirements
    automake/1.18#65a7ba60030d238eb8bb32266391cfc5 - Cache

======== Computing necessary packages ========
ocproxy/1.6: Forced build from source
Requirements
    libevent/2.1.13#01073c17d132a8cb6e7e1d19d25c1b22:01d92cf349a0dd98ff915f4bd99a04430171517f#048429a7b3e6320eed34ce0c15f1613e - Cache
    ocproxy/1.6#b5086f68885e0b2f3fc53fbca35fc3a0:6c61b811dee32ee923502180c65131bd5a2ee7df - Build
Test requirements
Build requirements
    automake/1.18#65a7ba60030d238eb8bb32266391cfc5:01d92cf349a0dd98ff915f4bd99a04430171517f#74f532f1a4c52e1f559249f2d9bc44a4 - Cache
Skipped binaries
    zlib/1.3.1.1

======== Installing packages ========
automake/1.18: Already installed! (1 of 3)
libevent/2.1.13: Already installed! (2 of 3)
ocproxy/1.6: Calling source() in /storage/Users/currentUser/.conan2/p/ocpro63ded43059237/s
ocproxy/1.6: Sources correctly downloaded from file:///storage/Users/currentUser/ws/worktrees/ocproxy-1.6/.build-cache/predl_cache/125480b7_v1.60.tar.gz
ocproxy/1.6: Uncompressing 125480b7_v1.60.tar.gz to .

-------- Installing package ocproxy/1.6 (3 of 3) --------
ocproxy/1.6: Building from source
ocproxy/1.6: Package ocproxy/1.6:6c61b811dee32ee923502180c65131bd5a2ee7df
ocproxy/1.6: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
ocproxy/1.6: requires: libevent/2.1.Z
ocproxy/1.6: Copying sources to build folder
ocproxy/1.6: Building your package in <PKG_DIR>/b
ocproxy/1.6: Calling generate()
ocproxy/1.6: Generators folder: <PKG_DIR>/b/build-release/conan
ocproxy/1.6: Generating aggregated env files
ocproxy/1.6: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
ocproxy/1.6: Calling build()
ocproxy/1.6: Apply patch (portability): Add -V/--version and -h/--help to ocproxy so packaging and CI smoke checks can identify the binary without a tunnel (matches the option style upstream added in 1.60 for vpnns); includes <config.h> for PACKAGE_VERSION and pre-scans argv so the informational switches work before the VPNFD check
ocproxy/1.6: Apply patch (portability): Port vpnns to the OHOS libc: replace the GNU-only get_current_dir_name() with the POSIX getcwd(NULL, 0); BEHAVIOUR CHANGE: a vpnns invocation without a command now prints usage and exits 1 instead of launching $SHELL through the namespace setup path (which dereferenced the missing command and crashed on kernels that refuse the namespace setup)
ocproxy/1.6: RUN: autoreconf --force --install --verbose
autoreconf: export WARNINGS=
autoreconf: Entering directory '.'
autoreconf: configure.ac: not using Gettext
autoreconf: running: /storage/Users/currentUser/.conan2/p/autom3efab95d532f9/p/bin/aclocal --force 
.aclocal-real: warning: couldn't open directory 'm4': No such file or directory
autoreconf: configure.ac: tracing
autoreconf: configure.ac: not using Libtool
autoreconf: configure.ac: not using Intltool
autoreconf: configure.ac: not using Gtkdoc
autoreconf: running: /data/service/hnp/autoconf.org/autoconf_2.72/bin/autoconf --force
configure.ac:7: warning: The macro 'AC_GNU_SOURCE' is obsolete.
configure.ac:7: You should run autoupdate.
./lib/autoconf/specific.m4:489: AC_GNU_SOURCE is expanded from...
configure.ac:7: the top level
configure.ac:54: warning: The macro 'AC_TRY_COMPILE' is obsolete.
configure.ac:54: You should run autoupdate.
./lib/autoconf/general.m4:2845: AC_TRY_COMPILE is expanded from...
acinclude.m4:39: AS_COMPILER_FLAGS is expanded from...
configure.ac:54: the top level
autoreconf: running: /data/service/hnp/autoconf.org/autoconf_2.72/bin/autoheader --force
autoreconf: running: /storage/Users/currentUser/.conan2/p/autom3efab95d532f9/p/bin/automake --add-missing --copy --force-missing
configure.ac:6: installing './compile'
configure.ac:11: installing './config.guess'
configure.ac:11: installing './config.sub'
configure.ac:3: installing './install-sh'
configure.ac:3: installing './missing'
Makefile.am: installing './depcomp'
autoreconf: Leaving directory '.'

ocproxy/1.6: RUN: "<PKG_DIR>/b/configure" --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' --build=aarch64-linux-ohos --host=aarch64-linux-ohos
checking for a BSD-compatible install... /storage/Users/currentUser/usr/local/bin/ginstall -c
checking whether sleep supports fractional seconds... yes
checking filesystem timestamp resolution... 0.01
checking whether build environment is sane... yes
checking for a race-free mkdir -p... /storage/Users/currentUser/usr/local/bin/mkdir -p
checking for gawk... gawk
checking whether make sets $(MAKE)... yes
checking whether make supports nested variables... yes
checking xargs -n works... yes
checking whether UID '20020084' is supported by ustar format... no
checking whether GID '20020084' is supported by ustar format... no
checking how to create a ustar tar archive... none
checking whether make supports the include directive... yes (GNU style)
checking for aarch64-linux-ohos-gcc... /data/service/hnp/bin/clang
checking whether the C compiler works... yes
checking for C compiler default output file name... a.out
checking for suffix of executables... 
checking whether we are cross compiling... no
checking for suffix of object files... o
checking whether the compiler supports GNU C... yes
checking whether /data/service/hnp/bin/clang accepts -g... yes
checking for /data/service/hnp/bin/clang option to enable C11 features... none needed
checking whether /data/service/hnp/bin/clang understands -c and -o together... yes
checking dependency style of /data/service/hnp/bin/clang... gcc3
checking for stdio.h... yes
checking for stdlib.h... yes
checking for string.h... yes
checking for inttypes.h... yes
checking for stdint.h... yes
checking for strings.h... yes
checking for sys/stat.h... yes
checking for sys/types.h... yes
checking for unistd.h... yes
checking for wchar.h... yes
checking for minix/config.h... no
checking whether it is safe to define __EXTENSIONS__... yes
checking whether _XOPEN_SOURCE should be defined... no
checking for aarch64-linux-ohos-gcc... (cached) /data/service/hnp/bin/clang
checking whether the compiler supports GNU C... (cached) yes
checking whether /data/service/hnp/bin/clang accepts -g... (cached) yes
checking for /data/service/hnp/bin/clang option to enable C11 features... (cached) none needed
checking whether /data/service/hnp/bin/clang understands -c and -o together... (cached) yes
checking dependency style of /data/service/hnp/bin/clang... (cached) gcc3
checking build system type... aarch64-unknown-linux-ohos
checking host system type... aarch64-unknown-linux-ohos
checking for linux/if_tun.h... yes
checking for sched.h... yes
checking for supported compiler flags...  -Wall -Wextra -Wno-missing-field-initializers -Wno-sign-compare -Wno-pointer-sign -Wno-unused-parameter -Werror=pointer-to-int-cast -Wdeclaration-after-statement -Werror-implicit-function-declaration -Wformat-nonliteral -Wformat-security -Winit-self -Wno-missing-declarations -Wmissing-include-dirs -Wnested-externs -Wpointer-arith -Wwrite-strings
checking for library containing event_add... none required
checking for event2/event.h... yes
checking if compiler needs -Werror to reject unknown flags... yes
checking for the pthreads library -lpthreads... no
checking whether pthreads work without any flags... yes
checking for joinable pthread attribute... PTHREAD_CREATE_JOINABLE
checking if more special flags are required for pthreads... no
checking for PTHREAD_PRIO_INHERIT... yes
checking that generated files are newer than configure... done
configure: creating ./config.status
config.status: creating Makefile
config.status: creating config.h
config.status: executing depfiles commands

ocproxy/1.6: RUN: make -j1
make  all-am
make[1]: Entering directory '<PKG_DIR>/b/build-release'
  CC       lwip/src/core/def.o
  CC       lwip/src/core/dns.o
<PKG_DIR>/b/lwip/src/core/dns.c:472:38: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      ip_addr_debug_print(DNS_DEBUG, &(dns_table[i].ipaddr));
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/dns.c:472:38: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      ip_addr_debug_print(DNS_DEBUG, &(dns_table[i].ipaddr));
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/dns.c:472:38: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      ip_addr_debug_print(DNS_DEBUG, &(dns_table[i].ipaddr));
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/dns.c:472:38: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      ip_addr_debug_print(DNS_DEBUG, &(dns_table[i].ipaddr));
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/dns.c:816:44: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
            ip_addr_debug_print(DNS_DEBUG, (&(pEntry->ipaddr)));
            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/dns.c:816:44: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
            ip_addr_debug_print(DNS_DEBUG, (&(pEntry->ipaddr)));
            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/dns.c:816:44: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
            ip_addr_debug_print(DNS_DEBUG, (&(pEntry->ipaddr)));
            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/dns.c:816:44: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
            ip_addr_debug_print(DNS_DEBUG, (&(pEntry->ipaddr)));
            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
8 warnings generated.
  CC       lwip/src/core/inet_chksum.o
  CC       lwip/src/core/init.o
  CC       lwip/src/core/mem.o
  CC       lwip/src/core/memp.o
  CC       lwip/src/core/netif.o
<PKG_DIR>/b/lwip/src/core/netif.c:261:36: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(NETIF_DEBUG, ipaddr);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/netif.c:261:36: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(NETIF_DEBUG, ipaddr);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/netif.c:261:36: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(NETIF_DEBUG, ipaddr);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/netif.c:261:36: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(NETIF_DEBUG, ipaddr);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/netif.c:263:36: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(NETIF_DEBUG, netmask);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/netif.c:263:36: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(NETIF_DEBUG, netmask);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/netif.c:263:36: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(NETIF_DEBUG, netmask);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/netif.c:263:36: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(NETIF_DEBUG, netmask);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/netif.c:265:36: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(NETIF_DEBUG, gw);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/netif.c:265:36: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(NETIF_DEBUG, gw);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/netif.c:265:36: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(NETIF_DEBUG, gw);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/netif.c:265:36: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(NETIF_DEBUG, gw);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
12 warnings generated.
  CC       lwip/src/core/pbuf.o
  CC       lwip/src/core/stats.o
  CC       lwip/src/core/sys.o
  CC       lwip/src/core/tcp.o
<PKG_DIR>/b/lwip/src/core/tcp.c:681:29: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
         len, pcb->rcv_wnd, TCP_WND - pcb->rcv_wnd));
         ~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/src/lwipopts.h:178:33: note: expanded from macro 'TCP_WND'
#define TCP_WND                 65534 /* Avoid wrap. */
                                ^
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp.c:949:58: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
        ipX_addr_debug_print(PCB_ISIPV6(pcb), TCP_DEBUG, &pcb->remote_ip);
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp.c:949:58: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
        ipX_addr_debug_print(PCB_ISIPV6(pcb), TCP_DEBUG, &pcb->remote_ip);
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp.c:949:58: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
        ipX_addr_debug_print(PCB_ISIPV6(pcb), TCP_DEBUG, &pcb->remote_ip);
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp.c:949:58: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
        ipX_addr_debug_print(PCB_ISIPV6(pcb), TCP_DEBUG, &pcb->remote_ip);
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
5 warnings generated.
  CC       lwip/src/core/tcp_in.o
<PKG_DIR>/b/lwip/src/core/tcp_in.c:1199:38: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
                                  m, m * TCP_SLOW_INTERVAL));
                                  ~~~^~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp_in.c:1212:45: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
                                  pcb->rto, pcb->rto * TCP_SLOW_INTERVAL));
                                  ~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
2 warnings generated.
  CC       lwip/src/core/tcp_out.o
<PKG_DIR>/b/lwip/src/core/tcp_out.c:326:26: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      pcb->snd_queuelen, TCP_SND_QUEUELEN));
      ~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/src/lwipopts.h:170:33: note: expanded from macro 'TCP_SND_QUEUELEN'
#define TCP_SND_QUEUELEN        (4 * TCP_SND_BUF/TCP_MSS)
                                ^
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp_out.c:591:117: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      LWIP_DEBUGF(TCP_OUTPUT_DEBUG | 2, ("tcp_write: queue too long %"TCPWNDSIZE_F" (%"TCPWNDSIZE_F")\n", queuelen, TCP_SND_QUEUELEN));
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/src/lwipopts.h:170:33: note: expanded from macro 'TCP_SND_QUEUELEN'
#define TCP_SND_QUEUELEN        (4 * TCP_SND_BUF/TCP_MSS)
                                ^
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp_out.c:751:59: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
                                       pcb->snd_queuelen, TCP_SND_QUEUELEN));
                                       ~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/src/lwipopts.h:170:33: note: expanded from macro 'TCP_SND_QUEUELEN'
#define TCP_SND_QUEUELEN        (4 * TCP_SND_BUF/TCP_MSS)
                                ^
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp_out.c:1415:35: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
                   pcb->ssthresh, 2*pcb->mss));
                   ~~~~~~~~~~~~~~~^~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp_out.c:1442:52: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), TCP_DEBUG, &pcb->remote_ip);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp_out.c:1442:52: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), TCP_DEBUG, &pcb->remote_ip);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp_out.c:1442:52: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), TCP_DEBUG, &pcb->remote_ip);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp_out.c:1442:52: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), TCP_DEBUG, &pcb->remote_ip);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp_out.c:1496:52: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), TCP_DEBUG, &pcb->remote_ip);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp_out.c:1496:52: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), TCP_DEBUG, &pcb->remote_ip);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp_out.c:1496:52: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), TCP_DEBUG, &pcb->remote_ip);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/tcp_out.c:1496:52: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), TCP_DEBUG, &pcb->remote_ip);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
12 warnings generated.
  CC       lwip/src/core/timers.o
  CC       lwip/src/core/udp.o
<PKG_DIR>/b/lwip/src/core/udp.c:200:55: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(ip_current_is_v6(), UDP_DEBUG, ipX_current_dest_addr());
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip.h:198:35: note: expanded from macro 'ipX_current_dest_addr'
#define ipX_current_dest_addr()   (&ip_data.current_iphdr_dest)
                                  ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:200:55: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(ip_current_is_v6(), UDP_DEBUG, ipX_current_dest_addr());
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip.h:198:35: note: expanded from macro 'ipX_current_dest_addr'
#define ipX_current_dest_addr()   (&ip_data.current_iphdr_dest)
                                  ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:200:55: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(ip_current_is_v6(), UDP_DEBUG, ipX_current_dest_addr());
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip.h:198:35: note: expanded from macro 'ipX_current_dest_addr'
#define ipX_current_dest_addr()   (&ip_data.current_iphdr_dest)
                                  ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:200:55: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(ip_current_is_v6(), UDP_DEBUG, ipX_current_dest_addr());
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip.h:198:35: note: expanded from macro 'ipX_current_dest_addr'
#define ipX_current_dest_addr()   (&ip_data.current_iphdr_dest)
                                  ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:202:55: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(ip_current_is_v6(), UDP_DEBUG, ipX_current_src_addr());
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip.h:196:35: note: expanded from macro 'ipX_current_src_addr'
#define ipX_current_src_addr()    (&ip_data.current_iphdr_src)
                                  ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:202:55: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(ip_current_is_v6(), UDP_DEBUG, ipX_current_src_addr());
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip.h:196:35: note: expanded from macro 'ipX_current_src_addr'
#define ipX_current_src_addr()    (&ip_data.current_iphdr_src)
                                  ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:202:55: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(ip_current_is_v6(), UDP_DEBUG, ipX_current_src_addr());
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip.h:196:35: note: expanded from macro 'ipX_current_src_addr'
#define ipX_current_src_addr()    (&ip_data.current_iphdr_src)
                                  ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:202:55: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(ip_current_is_v6(), UDP_DEBUG, ipX_current_src_addr());
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip.h:196:35: note: expanded from macro 'ipX_current_src_addr'
#define ipX_current_src_addr()    (&ip_data.current_iphdr_src)
                                  ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:237:56: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG, &pcb->local_ip);
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:237:56: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG, &pcb->local_ip);
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:237:56: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG, &pcb->local_ip);
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:237:56: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG, &pcb->local_ip);
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:239:56: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG, &pcb->remote_ip);
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:239:56: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG, &pcb->remote_ip);
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:239:56: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG, &pcb->remote_ip);
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:239:56: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG, &pcb->remote_ip);
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:583:79: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
    ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG | LWIP_DBG_LEVEL_SERIOUS, ip_2_ipX(dst_ip));
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:110:26: note: expanded from macro 'ip_2_ipX'
#define ip_2_ipX(ipaddr) (ipaddr)
                         ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:583:79: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
    ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG | LWIP_DBG_LEVEL_SERIOUS, ip_2_ipX(dst_ip));
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:110:26: note: expanded from macro 'ip_2_ipX'
#define ip_2_ipX(ipaddr) (ipaddr)
                         ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:583:79: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
    ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG | LWIP_DBG_LEVEL_SERIOUS, ip_2_ipX(dst_ip));
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:110:26: note: expanded from macro 'ip_2_ipX'
#define ip_2_ipX(ipaddr) (ipaddr)
                         ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:583:79: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
    ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG | LWIP_DBG_LEVEL_SERIOUS, ip_2_ipX(dst_ip));
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:110:26: note: expanded from macro 'ip_2_ipX'
#define ip_2_ipX(ipaddr) (ipaddr)
                         ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:893:69: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG | LWIP_DBG_TRACE, ip_2_ipX(ipaddr));
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:110:26: note: expanded from macro 'ip_2_ipX'
#define ip_2_ipX(ipaddr) (ipaddr)
                         ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:893:69: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG | LWIP_DBG_TRACE, ip_2_ipX(ipaddr));
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:110:26: note: expanded from macro 'ip_2_ipX'
#define ip_2_ipX(ipaddr) (ipaddr)
                         ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:893:69: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG | LWIP_DBG_TRACE, ip_2_ipX(ipaddr));
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:110:26: note: expanded from macro 'ip_2_ipX'
#define ip_2_ipX(ipaddr) (ipaddr)
                         ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:893:69: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG | LWIP_DBG_TRACE, ip_2_ipX(ipaddr));
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:110:26: note: expanded from macro 'ip_2_ipX'
#define ip_2_ipX(ipaddr) (ipaddr)
                         ^
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:950:86: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG | LWIP_DBG_TRACE | LWIP_DBG_STATE, &pcb->local_ip);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:950:86: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG | LWIP_DBG_TRACE | LWIP_DBG_STATE, &pcb->local_ip);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:950:86: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG | LWIP_DBG_TRACE | LWIP_DBG_STATE, &pcb->local_ip);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:950:86: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ipX_addr_debug_print(PCB_ISIPV6(pcb), UDP_DEBUG | LWIP_DBG_TRACE | LWIP_DBG_STATE, &pcb->local_ip);
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:1014:24: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
                       &pcb->remote_ip);
                       ^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:1014:24: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
                       &pcb->remote_ip);
                       ^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:1014:24: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
                       &pcb->remote_ip);
                       ^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/udp.c:1014:24: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
                       &pcb->remote_ip);
                       ^~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/ip_addr.h:122:81: note: expanded from macro 'ipX_addr_debug_print'
#define ipX_addr_debug_print(is_ipv6, debug, ipaddr) ip_addr_debug_print(debug, ipaddr)
                                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
32 warnings generated.
  CC       lwip/src/core/ipv4/icmp.o
<PKG_DIR>/b/lwip/src/core/ipv4/icmp.c:312:35: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(ICMP_DEBUG, &(iphdr->src));
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/ipv4/icmp.c:312:35: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(ICMP_DEBUG, &(iphdr->src));
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/ipv4/icmp.c:312:35: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(ICMP_DEBUG, &(iphdr->src));
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/ipv4/icmp.c:312:35: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(ICMP_DEBUG, &(iphdr->src));
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/ipv4/icmp.c:314:35: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(ICMP_DEBUG, &(iphdr->dest));
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:214:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr1_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/ipv4/icmp.c:314:35: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(ICMP_DEBUG, &(iphdr->dest));
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:215:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr2_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/ipv4/icmp.c:314:35: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(ICMP_DEBUG, &(iphdr->dest));
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:216:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr3_16(ipaddr) : 0,       \
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/ipv4/icmp.c:314:35: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
  ip_addr_debug_print(ICMP_DEBUG, &(iphdr->dest));
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4_addr.h:217:23: note: expanded from macro 'ip_addr_debug_print'
                      ipaddr != NULL ? ip4_addr4_16(ipaddr) : 0))
                      ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
8 warnings generated.
  CC       lwip/src/core/ipv4/ip4.o
<PKG_DIR>/b/lwip/src/core/ipv4/ip4.c:314:111: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
    LWIP_DEBUGF(IP_DEBUG | LWIP_DBG_LEVEL_WARNING, ("IP packet dropped due to bad version number %"U16_F"\n", IPH_V(iphdr)));
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/ipv4/lwip/ip4.h:94:21: note: expanded from macro 'IPH_V'
#define IPH_V(hdr)  ((hdr)->_v_hl >> 4)
                    ^
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/ipv4/ip4.c:503:64: warning: format specifies type 'unsigned short' but the argument has type 'int' [-Wformat]
      ntohs(IPH_ID(iphdr)), p->tot_len, ntohs(IPH_LEN(iphdr)), !!(IPH_OFFSET(iphdr) & PP_HTONS(IP_MF)), (ntohs(IPH_OFFSET(iphdr)) & IP_OFFMASK)*8));
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
<PKG_DIR>/b/lwip/src/core/ipv4/ip4.c:503:105: warning: format specifies type 'unsigned short' but the argument has type 'unsigned int' [-Wformat]
      ntohs(IPH_ID(iphdr)), p->tot_len, ntohs(IPH_LEN(iphdr)), !!(IPH_OFFSET(iphdr) & PP_HTONS(IP_MF)), (ntohs(IPH_OFFSET(iphdr)) & IP_OFFMASK)*8));
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<PKG_DIR>/b/lwip/src/include/lwip/debug.h:87:53: note: expanded from macro 'LWIP_DEBUGF'
                                 LWIP_PLATFORM_DIAG(message); \
                                 ~~~~~~~~~~~~~~~~~~~^~~~~~~~
<PKG_DIR>/b/contrib/ports/unix/include/arch/cc.h:83:42: note: expanded from macro 'LWIP_PLATFORM_DIAG'
#define LWIP_PLATFORM_DIAG(x)   do {printf x;} while(0)
                                           ^
3 warnings generated.
  CC       lwip/src/core/ipv4/ip4_addr.o
  CC       lwip/src/core/ipv4/ip_frag.o
  CC       lwip/src/api/api_lib.o
  CC       lwip/src/api/api_msg.o
  CC       lwip/src/api/err.o
  CC       lwip/src/api/netdb.o
  CC       lwip/src/api/tcpip.o
  CC       contrib/ports/unix/lwip_chksum.o
  CC       contrib/ports/unix/perf.o
  CC       contrib/ports/unix/sys_arch.o
  CC       contrib/ports/unix/netif/list.o
  CC       contrib/ports/unix/netif/tcpdump.o
  CC       src/ocproxy.o
  CCLD     ocproxy
  CC       src/vpnns.o
In file included from <PKG_DIR>/b/src/vpnns.c:49:
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/sys/fcntl.h:1:2: warning: redirecting incorrect #include <sys/fcntl.h> to <fcntl.h> [-W#warnings]
#warning redirecting incorrect #include <sys/fcntl.h> to <fcntl.h>
 ^
<PKG_DIR>/b/src/vpnns.c:398:1: warning: non-void function does not return a value in all control paths [-Wreturn-type]
}
^
2 warnings generated.
  CCLD     vpnns
make[1]: Leaving directory '<PKG_DIR>/b/build-release'

ocproxy/1.6: Package '6c61b811dee32ee923502180c65131bd5a2ee7df' built
ocproxy/1.6: Build folder <PKG_DIR>/b/build-release
ocproxy/1.6: Generating the package
ocproxy/1.6: Packaging in folder <PKG_DIR>/p
ocproxy/1.6: Calling package()
ocproxy/1.6: RUN: make install DESTDIR=<PKG_DIR>/p -j1
make[1]: Entering directory '<PKG_DIR>/b/build-release'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '<PKG_DIR>/p//bin'
  /storage/Users/currentUser/usr/local/bin/ginstall -c ocproxy vpnns '<PKG_DIR>/p//bin'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '<PKG_DIR>/p//share/doc/ocproxy'
 /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 <PKG_DIR>/b/README.md <PKG_DIR>/b/CHANGES '<PKG_DIR>/p//share/doc/ocproxy'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '<PKG_DIR>/p//share/man/man1'
 /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 <PKG_DIR>/b/ocproxy.1 <PKG_DIR>/b/vpnns.1 '<PKG_DIR>/p//share/man/man1'
make[1]: Leaving directory '<PKG_DIR>/b/build-release'

ocproxy/1.6: package(): Packaged 4 files: ocproxy, vpnns, CHANGES, LICENSE
ocproxy/1.6: package(): Packaged 1 '.md' file: README.md
ocproxy/1.6: package(): Packaged 2 '.1' files: ocproxy.1, vpnns.1
ocproxy/1.6: Created package revision 755325dadae110c2336e3cde519bd7f4
ocproxy/1.6: Package '6c61b811dee32ee923502180c65131bd5a2ee7df' created
ocproxy/1.6: Full package reference: ocproxy/1.6#b5086f68885e0b2f3fc53fbca35fc3a0:6c61b811dee32ee923502180c65131bd5a2ee7df#755325dadae110c2336e3cde519bd7f4
ocproxy/1.6: Package folder <PKG_DIR>/p

======== Launching test_package ========

======== Computing dependency graph ========
automake/1.18: WARN: automake/1.18: package_type 'application' is defined, but 'shared' and/or 'header_only' options are present. The package_type will have precedence over the options regardless of their value.
Graph root
    ocproxy/1.6 (test package): /storage/Users/currentUser/ws/worktrees/ocproxy-1.6/archives/o/ocproxy/1.6/test_package/conanfile.py
Requirements
    libevent/2.1.13#01073c17d132a8cb6e7e1d19d25c1b22 - Cache
    ocproxy/1.6#b5086f68885e0b2f3fc53fbca35fc3a0 - Cache
Test requirements
    zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9 - Cache
Build requirements
    automake/1.18#65a7ba60030d238eb8bb32266391cfc5 - Cache

======== Computing necessary packages ========
Requirements
    libevent/2.1.13#01073c17d132a8cb6e7e1d19d25c1b22:01d92cf349a0dd98ff915f4bd99a04430171517f#048429a7b3e6320eed34ce0c15f1613e - Cache
    ocproxy/1.6#b5086f68885e0b2f3fc53fbca35fc3a0:6c61b811dee32ee923502180c65131bd5a2ee7df#755325dadae110c2336e3cde519bd7f4 - Cache
Test requirements
Build requirements
Skipped binaries
    zlib/1.3.1.1, automake/1.18

======== Installing packages ========
libevent/2.1.13: Already installed! (1 of 2)
ocproxy/1.6: Already installed! (2 of 2)

======== Testing the package ========
ocproxy/1.6 (test package): Test package build: 
ocproxy/1.6 (test package): Test package build folder: /storage/Users/currentUser/ws/worktrees/ocproxy-1.6/archives/o/ocproxy/1.6/test_package
ocproxy/1.6 (test package): Writing generators to /storage/Users/currentUser/ws/worktrees/ocproxy-1.6/archives/o/ocproxy/1.6/test_package
ocproxy/1.6 (test package): Generator 'VirtualRunEnv' calling 'generate()'
ocproxy/1.6 (test package): Generating aggregated env files
ocproxy/1.6 (test package): Generated aggregated env files: ['conanrun.sh', 'conanbuild.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
ocproxy/1.6 (test package): Running test()
ocproxy/1.6 (test package): RUN: "/data/service/hnp/bin/python3" "/storage/Users/currentUser/ws/worktrees/ocproxy-1.6/archives/o/ocproxy/1.6/test_package/run_test.py" "<PKG_DIR>/p/bin"
== package layout ==
  [PASS] ocproxy installed and executable :: <PKG_DIR>/p/bin/ocproxy
  [PASS] vpnns installed and executable :: <PKG_DIR>/p/bin/vpnns
== failure modes ==
  [PASS] missing VPNFD fails closed :: rc=1 out='VPNFD is not set, aborting'
  [PASS] non-numeric VPNFD fails closed :: rc=1 out="invalid integer: 'not-a-number'"
== live proxy behaviour ==
  [PASS] -D SOCKS5 listener accepts connections :: port=50419
  [PASS] -L port-forward listener accepts connections :: port=43855
  [PASS] SOCKS5 no-auth negotiation answered :: 0500
  [PASS] SOCKS5 CONNECT accepted for tunnel delivery :: proxy_rc=None reply=''
  [PASS] SOCKS5 request produced tunnel traffic :: bytes_read_from_tunnel=227
  [PASS] malformed -D fails closed :: rc=1 out="invalid integer: 'not-a-port'"
  [PASS] truncated -L fails closed :: rc=1 out="Invalid port forward specifier: '1234:onlyhost'"
== version and help switches ==
  [PASS] ocproxy --version works without a tunnel :: rc=0 out='ocproxy 1.60 - user-level SOCKS and port forwarding proxy\nCopyright (C) 2011-2017 David M. Miller and contributors\nThis program is free software; see the LICENS'
  [PASS] ocproxy -V short form works :: rc=0 out='ocproxy 1.60 - user-level SOCKS and port forwarding proxy\nCopyright (C) 2011-2017 David M. Miller and contributors\nThis program is free software; see the LICENS'
  [PASS] ocproxy --help lists the tunnel options :: rc=0 out='Usage: ocproxy [options]\n\n  -I <addr>            Tunnel interface IPv4 address (or INTERNAL_IP4_ADDRESS)\n  -M <mtu>             Tunnel interface MTU (or INTERNA'
== vpnns ==
  [PASS] vpnns -h prints usage and exits 1 :: rc=1 out='Create a new namespace and run COMMAND:\n  vpnns [ --name <name> ] -- <command> [args...]\n\nAttach to an existing namespace and bring up IP networking:\n  vpnns --'
  [PASS] vpnns -v prints version and exits 0 :: rc=0 out='vpnns - per-app VPN using Linux namespaces\nCopyright (C) 2016 Google Inc.\nThis program is part of the ocproxy 1.60 package.\n\nThis is free software with ABSOLUTE'
  [PASS] vpnns without a command fails closed :: rc=1 out='<PKG_DIR>/p/bin/vpnns: no command given\n\nCreate a new namespace and run COMMAND:\n  vpnns [ --name <name> ] -- <c'

TOTAL=17 PASS=17 FAIL=0

[ok] ocproxy/1.6 — conan create passed
[step] L1: Verifying test execution from conan create log...
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[step] L1c: No upstream make check/ctest in log (may be in test_package only)
[step] L4: Scanning patches for dangerous functions...
[warn] L4: Dangerous functions found in patches:
/storage/Users/currentUser/ws/worktrees/ocproxy-1.6/archives/o/ocproxy/1.6/patches/0002-src-vpnns.c.patch
/storage/Users/currentUser/ws/worktrees/ocproxy-1.6/archives/o/ocproxy/1.6/patches/.patch-backup-20260913014106/0002-src-vpnns.c.patch
/storage/Users/currentUser/ws/worktrees/ocproxy-1.6/archives/o/ocproxy/1.6/patches/.patch-backup-20260913020930/0002-src-vpnns.c.patch
[step] L5: Baseline artifact check...
[ok] L5: bin/ has content
[step] L1e: Destructive negative test (R34)...
        [sabotage] bin/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on ocproxy
[step] L2: Smoke test (version/help check)...
[warn] L2: ocproxy --version/--help failed (non-blocking)
[warn] L2: vpnns --version/--help failed (non-blocking)

L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: ocproxy version/help failed, vpnns failed
L4_RESULT=warn: dangerous functions in patches
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
