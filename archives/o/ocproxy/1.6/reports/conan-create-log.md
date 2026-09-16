# ocproxy 1.6 conan create 逐字日志（采信轮）

`ohc-run.py` 生成的运行期日志，属本轮真实运行。仓库把 `*.log` 明列为禁止入库文件
（`.gitcode/review-memory.md` §19），故逐字转写为 `.md`。

- 原始文件：`reports/conan-create.log`（由工具生成，未入库）
- 原始字节数：130089
- 原始行数：1499
- 原始 sha256：`f3d1611bd390ef771574e807046297655f51f81dee6d985009dd6af7615a21e7`
- 转写时间：2026-09-12T18:15:20Z
- 生成命令：`ohc-run.py conan-verify ocproxy 1.6 --profile ohos-aarch64 --user ohpcd --channel stable`
  （内部等价于 `conan create archives/o/ocproxy/1.6 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`）
- 对应工具日志：`reports/conan-verify-report.md`（Verdict: PASS）
- **唯一加工**：把逐轮重建的缓存分片目录名 `/storage/Users/currentUser/.conan2/p/b/ocpro<hash>`
  替换为 `<PKG_DIR>`，共 410 处（每轮清缓存重建都会换名，写死会让证据在下一轮不可复核）。

## 字节账（按实测填写）

```text
原始日志字节数                      : 130089
原始日志行数                        : 1499
归一化后的逐字正文（不含末尾换行）    : 110407
归一化后的逐字正文（含末尾换行）      : 110408
原始 − 归一化正文（不含末尾换行）     : 19682
替换处数                            : 410
平均每处净减少                       : 48.00 字符
```

## 结论行

```text
TOTAL=17 PASS=17 FAIL=0
```

## 逐字日志（已归一化分片目录名）

```text

======== Exporting recipe to the cache ========
ocproxy/1.6@ohpcd/stable: Exporting package recipe: /storage/Users/currentUser/ws/worktrees/ocproxy-1.6/archives/o/ocproxy/1.6/conanfile.py
ocproxy/1.6@ohpcd/stable: exports: File 'conandata.yml' found. Exporting it...
ocproxy/1.6@ohpcd/stable: Calling export_sources()
ocproxy/1.6@ohpcd/stable: Copied 1 '.yml' file: conandata.yml
ocproxy/1.6@ohpcd/stable: Copied 1 '.py' file: conanfile.py
ocproxy/1.6@ohpcd/stable: Copied 2 '.patch' files: 0001-src-ocproxy.c.patch, 0002-src-vpnns.c.patch
ocproxy/1.6@ohpcd/stable: Exported to cache folder: /storage/Users/currentUser/.conan2/p/ocprof679957b1f0ca/e
ocproxy/1.6@ohpcd/stable: Exported: ocproxy/1.6@ohpcd/stable#bf437c7df4642717f72c865da569c739 (2026-09-12 18:13:04 UTC)

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
    ocproxy/1.6@ohpcd/stable#bf437c7df4642717f72c865da569c739 - Cache
Test requirements
    zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9 - Cache
Build requirements
    automake/1.18#65a7ba60030d238eb8bb32266391cfc5 - Cache

======== Computing necessary packages ========
Connecting to remote 'ohpcd' anonymously
ocproxy/1.6@ohpcd/stable: Main binary package '6c61b811dee32ee923502180c65131bd5a2ee7df' missing
ocproxy/1.6@ohpcd/stable: Checking 11 compatible configurations
ocproxy/1.6@ohpcd/stable: Compatible configurations not found in cache, checking servers
ocproxy/1.6@ohpcd/stable: '5e01c11d056010f0c08428e7b63b1f36b7bcb577': compiler.cppstd=98
ocproxy/1.6@ohpcd/stable: '0a02420c573ba7d4f03aee3a507c13d91d8e64c8': compiler.cppstd=gnu98
ocproxy/1.6@ohpcd/stable: '09f01763f0c23d6dfe52f07470ea2bf663b5bfd3': compiler.cppstd=11
ocproxy/1.6@ohpcd/stable: '532c4381287f85395d24f1a4c970344937063599': compiler.cppstd=gnu11
ocproxy/1.6@ohpcd/stable: '588e64129909341c2eece5f48be66c9fe103c743': compiler.cppstd=14
ocproxy/1.6@ohpcd/stable: 'e9f0cb474f5ae5a2b20a3b99888ba8d2ec7fdc8b': compiler.cppstd=gnu14
ocproxy/1.6@ohpcd/stable: '7ad845c565ae73e273fe75226b112bc6b324cb43': compiler.cppstd=gnu17
ocproxy/1.6@ohpcd/stable: '927704ff3d543b8f9319e5ce78928667c9931e57': compiler.cppstd=20
ocproxy/1.6@ohpcd/stable: '7fb9eecd668dace1d134f16def15d29f98ffc5e0': compiler.cppstd=gnu20
ocproxy/1.6@ohpcd/stable: 'd94afcbd7b0450910969daecb210773f390e2032': compiler.cppstd=23
ocproxy/1.6@ohpcd/stable: '7579dfd864e05c1e1b826544f2186e5ed02b733f': compiler.cppstd=gnu23
ocproxy/1.6@ohpcd/stable: No compatible configuration found

A new experimental approach for binary compatibility detection is available.
    Enable it by setting the core.graph:compatibility_mode=optimized conf
    and get improved performance when querying multiple compatible binaries in remotes.

Requirements
    libevent/2.1.13#01073c17d132a8cb6e7e1d19d25c1b22:01d92cf349a0dd98ff915f4bd99a04430171517f#048429a7b3e6320eed34ce0c15f1613e - Cache
    ocproxy/1.6@ohpcd/stable#bf437c7df4642717f72c865da569c739:6c61b811dee32ee923502180c65131bd5a2ee7df - Build
Test requirements
Build requirements
    automake/1.18#65a7ba60030d238eb8bb32266391cfc5:01d92cf349a0dd98ff915f4bd99a04430171517f#74f532f1a4c52e1f559249f2d9bc44a4 - Cache
Skipped binaries
    zlib/1.3.1.1

======== Installing packages ========
automake/1.18: Already installed! (1 of 3)
libevent/2.1.13: Already installed! (2 of 3)
ocproxy/1.6@ohpcd/stable: Calling source() in /storage/Users/currentUser/.conan2/p/ocprof679957b1f0ca/s
ocproxy/1.6@ohpcd/stable: Sources correctly downloaded from https://ghfast.top/https://github.com/cernekee/ocproxy/archive/refs/tags/v1.60.tar.gz
ocproxy/1.6@ohpcd/stable: Uncompressing v1.60.tar.gz to .

-------- Installing package ocproxy/1.6@ohpcd/stable (3 of 3) --------
ocproxy/1.6@ohpcd/stable: Building from source
ocproxy/1.6@ohpcd/stable: Package ocproxy/1.6@ohpcd/stable:6c61b811dee32ee923502180c65131bd5a2ee7df
ocproxy/1.6@ohpcd/stable: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
ocproxy/1.6@ohpcd/stable: requires: libevent/2.1.Z
ocproxy/1.6@ohpcd/stable: Copying sources to build folder
ocproxy/1.6@ohpcd/stable: Building your package in <PKG_DIR>/b
ocproxy/1.6@ohpcd/stable: Calling generate()
ocproxy/1.6@ohpcd/stable: Generators folder: <PKG_DIR>/b/build-release/conan
ocproxy/1.6@ohpcd/stable: Generating aggregated env files
ocproxy/1.6@ohpcd/stable: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
ocproxy/1.6@ohpcd/stable: Calling build()
ocproxy/1.6@ohpcd/stable: Apply patch (portability): Add -V/--version and -h/--help to ocproxy so packaging and CI smoke checks can identify the binary without a tunnel (matches the option style upstream added in 1.60 for vpnns); includes <config.h> for PACKAGE_VERSION and pre-scans argv so the informational switches work before the VPNFD check
ocproxy/1.6@ohpcd/stable: Apply patch (portability): Port vpnns to the OHOS libc: replace the GNU-only get_current_dir_name() with the POSIX getcwd(NULL, 0); BEHAVIOUR CHANGE: a vpnns invocation without a command now prints usage and exits 1 instead of launching $SHELL through the namespace setup path (which dereferenced the missing command and crashed on kernels that refuse the namespace setup)
ocproxy/1.6@ohpcd/stable: RUN: autoreconf --force --install --verbose
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

ocproxy/1.6@ohpcd/stable: RUN: "<PKG_DIR>/b/configure" --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' --build=aarch64-linux-ohos --host=aarch64-linux-ohos
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

ocproxy/1.6@ohpcd/stable: RUN: make -j1
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

ocproxy/1.6@ohpcd/stable: Package '6c61b811dee32ee923502180c65131bd5a2ee7df' built
ocproxy/1.6@ohpcd/stable: Build folder <PKG_DIR>/b/build-release
ocproxy/1.6@ohpcd/stable: Generating the package
ocproxy/1.6@ohpcd/stable: Packaging in folder <PKG_DIR>/p
ocproxy/1.6@ohpcd/stable: Calling package()
ocproxy/1.6@ohpcd/stable: RUN: make install DESTDIR=<PKG_DIR>/p -j1
make[1]: Entering directory '<PKG_DIR>/b/build-release'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '<PKG_DIR>/p//bin'
  /storage/Users/currentUser/usr/local/bin/ginstall -c ocproxy vpnns '<PKG_DIR>/p//bin'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '<PKG_DIR>/p//share/doc/ocproxy'
 /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 <PKG_DIR>/b/README.md <PKG_DIR>/b/CHANGES '<PKG_DIR>/p//share/doc/ocproxy'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '<PKG_DIR>/p//share/man/man1'
 /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 <PKG_DIR>/b/ocproxy.1 <PKG_DIR>/b/vpnns.1 '<PKG_DIR>/p//share/man/man1'
make[1]: Leaving directory '<PKG_DIR>/b/build-release'

ocproxy/1.6@ohpcd/stable: package(): Packaged 4 files: ocproxy, vpnns, CHANGES, LICENSE
ocproxy/1.6@ohpcd/stable: package(): Packaged 1 '.md' file: README.md
ocproxy/1.6@ohpcd/stable: package(): Packaged 2 '.1' files: ocproxy.1, vpnns.1
ocproxy/1.6@ohpcd/stable: Created package revision 45365941e427890ca1c54c00f2c1ed29
ocproxy/1.6@ohpcd/stable: Package '6c61b811dee32ee923502180c65131bd5a2ee7df' created
ocproxy/1.6@ohpcd/stable: Full package reference: ocproxy/1.6@ohpcd/stable#bf437c7df4642717f72c865da569c739:6c61b811dee32ee923502180c65131bd5a2ee7df#45365941e427890ca1c54c00f2c1ed29
ocproxy/1.6@ohpcd/stable: Package folder <PKG_DIR>/p

======== Launching test_package ========

======== Computing dependency graph ========
automake/1.18: WARN: automake/1.18: package_type 'application' is defined, but 'shared' and/or 'header_only' options are present. The package_type will have precedence over the options regardless of their value.
Graph root
    ocproxy/1.6@ohpcd/stable (test package): /storage/Users/currentUser/ws/worktrees/ocproxy-1.6/archives/o/ocproxy/1.6/test_package/conanfile.py
Requirements
    libevent/2.1.13#01073c17d132a8cb6e7e1d19d25c1b22 - Cache
    ocproxy/1.6@ohpcd/stable#bf437c7df4642717f72c865da569c739 - Cache
Test requirements
    zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9 - Cache
Build requirements
    automake/1.18#65a7ba60030d238eb8bb32266391cfc5 - Cache

======== Computing necessary packages ========
Requirements
    libevent/2.1.13#01073c17d132a8cb6e7e1d19d25c1b22:01d92cf349a0dd98ff915f4bd99a04430171517f#048429a7b3e6320eed34ce0c15f1613e - Cache
    ocproxy/1.6@ohpcd/stable#bf437c7df4642717f72c865da569c739:6c61b811dee32ee923502180c65131bd5a2ee7df#45365941e427890ca1c54c00f2c1ed29 - Cache
Test requirements
Build requirements
Skipped binaries
    zlib/1.3.1.1, automake/1.18

======== Installing packages ========
libevent/2.1.13: Already installed! (1 of 2)
ocproxy/1.6@ohpcd/stable: Already installed! (2 of 2)

======== Testing the package ========
ocproxy/1.6@ohpcd/stable (test package): Test package build: 
ocproxy/1.6@ohpcd/stable (test package): Test package build folder: /storage/Users/currentUser/ws/worktrees/ocproxy-1.6/archives/o/ocproxy/1.6/test_package
ocproxy/1.6@ohpcd/stable (test package): Writing generators to /storage/Users/currentUser/ws/worktrees/ocproxy-1.6/archives/o/ocproxy/1.6/test_package
ocproxy/1.6@ohpcd/stable (test package): Generator 'VirtualRunEnv' calling 'generate()'
ocproxy/1.6@ohpcd/stable (test package): Generating aggregated env files
ocproxy/1.6@ohpcd/stable (test package): Generated aggregated env files: ['conanrun.sh', 'conanbuild.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
ocproxy/1.6@ohpcd/stable (test package): Running test()
ocproxy/1.6@ohpcd/stable (test package): RUN: "/data/service/hnp/bin/python3" "/storage/Users/currentUser/ws/worktrees/ocproxy-1.6/archives/o/ocproxy/1.6/test_package/run_test.py" "<PKG_DIR>/p/bin"
== package layout ==
  [PASS] ocproxy installed and executable :: <PKG_DIR>/p/bin/ocproxy
  [PASS] vpnns installed and executable :: <PKG_DIR>/p/bin/vpnns
== failure modes ==
  [PASS] missing VPNFD fails closed :: rc=1 out='VPNFD is not set, aborting'
  [PASS] non-numeric VPNFD fails closed :: rc=1 out="invalid integer: 'not-a-number'"
== live proxy behaviour ==
  [PASS] -D SOCKS5 listener accepts connections :: port=53553
  [PASS] -L port-forward listener accepts connections :: port=50493
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
```
