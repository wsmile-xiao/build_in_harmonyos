# bti 034 采信轮 conan create 逐字日志

采信轮（第 3 轮清缓存 `conan-verify`）的 `conan create` 逐字日志。产出者是 `conan-verify`
（W3 另把 create 输出写到 `.ci_logs/`，两者不是同一对象）。该轮判为 **clean**：

- `Calling build()` 出现 1 次、`Apply patch (portability)` 出现 3 次（三个补丁全部真实应用）、
  `RUN: make -j1` 出现 1 次（另有 1 次 `RUN: make install DESTDIR=… -j20`，属安装阶段）——
  缓存轮不含这些行；
- 日志尾部含 `test_package` 的真实执行结果行 `RESULT: 4/4 checks passed`；
- 采信轮对应的 Git SHA：`7e93f24bdfac47c068b05bc5970c4fd90e4952e0`（同一 SHA 连续两轮独立清缓存构建，产物比对见 reports/conan-verify-supplement.md 的 L5 段）。

计数命令（在 worktree 根目录执行）：

````text
L=archives/b/bti/034/reports/conan-create.log
grep -c 'Calling build()'      "$L"   # 1
grep -c 'Apply patch'          "$L"   # 3
grep -c 'RUN: make -j1'        "$L"   # 1
grep -c 'RUN: make'            "$L"   # 2（另 1 次为 make install）
````

## 逐字证据

- 原始文件：`/storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/reports/conan-create.log`
- 原始字节数：31220
- 原始行数：445（`wc -l`，即换行符个数）
- sha256（原始文件逐字节）：`4ed780cbdd02acb99a2e5d8a1e730754daeaadd17ee3af8a2a06806c2d948a89`
- 抽取命令（块内含末尾换行，不额外剥除）：

````text
sed -n '/^```text$/,/^```$/p' conan-create-log.md | sed '1d;$d' > conan-create.log
````

```text

======== Exporting recipe to the cache ========
bti/034@ohpcd/stable: Exporting package recipe: /storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/conanfile.py
bti/034@ohpcd/stable: exports: File 'conandata.yml' found. Exporting it...
bti/034@ohpcd/stable: Calling export_sources()
bti/034@ohpcd/stable: Copied 1 '.yml' file: conandata.yml
bti/034@ohpcd/stable: Copied 1 '.py' file: conanfile.py
bti/034@ohpcd/stable: Copied 3 '.patch' files: 0001-bti-shrink-urls.patch, 0002-bti.c.patch, 0003-configure.patch
bti/034@ohpcd/stable: Exported to cache folder: /storage/Users/currentUser/.conan2/p/bti02b43406f3292/e
bti/034@ohpcd/stable: Exported: bti/034@ohpcd/stable#2272e41c8d6131b279f7f03c13f00e31 (2026-09-13 11:14:04 UTC)

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
    bti/034@ohpcd/stable#2272e41c8d6131b279f7f03c13f00e31 - Cache
    curl/8.15.0#4ae5a3c702753d2fc507808204655813 - Cache
    json-c/0.17#3c6e9ba2b444f1618c7f6c9c74742382 - Cache
    liboauth/1.0.3#8a3f827872cc9e4a146766615d81bd06 - Cache
    libxml2/2.15.3#6645e3b3d878fd252da369bed05e2cd5 - Cache
    openssl/3.5.6.1#d871951ad035e2c4eecb6112af441801 - Cache
    pcre/8.45#d37e7bcdd1483105496deb82632f1b44 - Cache
    zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9 - Cache
Build requirements
    automake/1.18#65a7ba60030d238eb8bb32266391cfc5 - Cache
    libtool/2.5.4#fe9f8e735ad45469571cf4de3ce552f4 - Cache
Overrides
    openssl/1.1.1w: ['openssl/3.5.6.1']
    openssl/3.5.6.1: ['openssl/3.5.6.1']

======== Computing necessary packages ========
Connecting to remote 'ohpcd' anonymously
bti/034@ohpcd/stable: Main binary package '893f4238a37e85b38a718fa7e2ba2a4231eb710a' missing
bti/034@ohpcd/stable: Checking 11 compatible configurations
bti/034@ohpcd/stable: Compatible configurations not found in cache, checking servers
bti/034@ohpcd/stable: '9573b607a18e644c1ecf4e869faf9b4c7633178b': compiler.cppstd=98
bti/034@ohpcd/stable: '539efbe47d0ec1fb05051f7e8bffa41f2b6d1fad': compiler.cppstd=gnu98
bti/034@ohpcd/stable: 'c43c6571b5e91b6457a1660ef16f51961a02d2b4': compiler.cppstd=11
bti/034@ohpcd/stable: '58a64709dc63b5fafb04fdff4b2748d7436d253a': compiler.cppstd=gnu11
bti/034@ohpcd/stable: 'f486f432cf16da7d6db46a3c52491682bf808b6d': compiler.cppstd=14
bti/034@ohpcd/stable: 'b1330ec53e5c862a205f8c2d9d04b38dd360cffb': compiler.cppstd=gnu14
bti/034@ohpcd/stable: '095cae31628ffe865a3bd7c425cd30eb082e6aec': compiler.cppstd=gnu17
bti/034@ohpcd/stable: 'cabd554fbe2d0d4ed979324dd2c17eee8b23c63b': compiler.cppstd=20
bti/034@ohpcd/stable: '7e6e52a3789132ca45c82445a036ba2892ff650a': compiler.cppstd=gnu20
bti/034@ohpcd/stable: '3e5a7f0e0c0e31a835453bc2e489898c8e34f9c9': compiler.cppstd=23
bti/034@ohpcd/stable: '4618747615cb680167dea332ad06a1359ce4aaa1': compiler.cppstd=gnu23
bti/034@ohpcd/stable: No compatible configuration found

A new experimental approach for binary compatibility detection is available.
    Enable it by setting the core.graph:compatibility_mode=optimized conf
    and get improved performance when querying multiple compatible binaries in remotes.

Requirements
    bti/034@ohpcd/stable#2272e41c8d6131b279f7f03c13f00e31:893f4238a37e85b38a718fa7e2ba2a4231eb710a - Build
    curl/8.15.0#4ae5a3c702753d2fc507808204655813:df2856b724fa5aed00dc7f60cec6755df39cf2b6#4a65670fdad2419ab77c3e47b23ed2eb - Cache
    json-c/0.17#3c6e9ba2b444f1618c7f6c9c74742382:01d92cf349a0dd98ff915f4bd99a04430171517f#fd10f04507655c87ed79a0e3d964e407 - Cache
    liboauth/1.0.3#8a3f827872cc9e4a146766615d81bd06:0f43cddf8f0746f39df42f9f026ecaab38cf98d1#f9373a9fcfee998d98b9507acdb46770 - Cache
    libxml2/2.15.3#6645e3b3d878fd252da369bed05e2cd5:01d92cf349a0dd98ff915f4bd99a04430171517f#164721fa4fa2b219536e9bc6e7fd9563 - Cache
    openssl/3.5.6.1#d871951ad035e2c4eecb6112af441801:f23d5a9b1d537641c03c7814478a2fadb727650a#d336cecc28c8a815f710217319108717 - Cache
    pcre/8.45#d37e7bcdd1483105496deb82632f1b44:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa#761258106077c36f1a5e0c436e87801e - Cache
Build requirements
Skipped binaries
    zlib/1.3.1.1, automake/1.18, libtool/2.5.4

======== Installing packages ========
json-c/0.17: Already installed! (1 of 7)
libxml2/2.15.3: Already installed! (2 of 7)
openssl/3.5.6.1: Already installed! (3 of 7)
pcre/8.45: Already installed! (4 of 7)
curl/8.15.0: Already installed! (5 of 7)
liboauth/1.0.3: Already installed! (6 of 7)
bti/034@ohpcd/stable: Calling source() in /storage/Users/currentUser/.conan2/p/bti02b43406f3292/s
bti/034@ohpcd/stable: Sources correctly downloaded from https://www.kernel.org/pub/software/web/bti/bti-034.tar.gz
bti/034@ohpcd/stable: Uncompressing bti-034.tar.gz to .

-------- Installing package bti/034@ohpcd/stable (7 of 7) --------
bti/034@ohpcd/stable: Building from source
bti/034@ohpcd/stable: Package bti/034@ohpcd/stable:893f4238a37e85b38a718fa7e2ba2a4231eb710a
bti/034@ohpcd/stable: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
bti/034@ohpcd/stable: requires: liboauth/1.0.3#8a3f827872cc9e4a146766615d81bd06:0f43cddf8f0746f39df42f9f026ecaab38cf98d1 curl/8.15.Z openssl/3.5.6.1#d871951ad035e2c4eecb6112af441801:f23d5a9b1d537641c03c7814478a2fadb727650a libxml2/2.15.Z json-c/0.17.Z pcre/8.45#d37e7bcdd1483105496deb82632f1b44:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa
bti/034@ohpcd/stable: Copying sources to build folder
bti/034@ohpcd/stable: Building your package in /storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b
bti/034@ohpcd/stable: Calling generate()
bti/034@ohpcd/stable: Generators folder: /storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/build-release/conan
bti/034@ohpcd/stable: Generating aggregated env files
bti/034@ohpcd/stable: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
bti/034@ohpcd/stable: Calling build()
bti/034@ohpcd/stable: Apply patch (portability): OHOS 没有 /bin/bash，bin_SCRIPTS 安装的 bti-shrink-urls 直接执行报 "bad interpreter: No such file or directory"（rc=126）。改为 #!/bin/sh； 该脚本在 OHOS 的 /bin/sh 下 `sh -n` 语法检查与 `--help` 运行均通过。

bti/034@ohpcd/stable: Apply patch (portability): json-c 0.13 起移除了 is_error 宏，上游 2014 年的 bti.c 仍使用该宏， 链接期报 undefined symbol: is_error。将 3 处调用改为显式 NULL 比较 （与 Debian bti 034-6 的 replace_removed_is_error.patch 同口径）。

bti/034@ohpcd/stable: Apply patch (portability): HMDFS 语义：config.status 用 umask 077 创建临时目录，落盘为 0700 目录， 在 setgid hmdfs 挂载上对构建用户不可写，configure 报 "can't create ./confXXXXXX/subs1.awk: Permission denied"。发布 tarball 只提供预生成 configure（无法 autoreconf），故就地放宽为 umask 022。

bti/034@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/configure" --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' PKG_CONFIG_PATH=/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/build-release/conan 
checking for a BSD-compatible install... /storage/Users/currentUser/usr/local/bin/ginstall -c
checking whether build environment is sane... yes
checking for a thread-safe mkdir -p... /storage/Users/currentUser/usr/local/bin/mkdir -p
checking for gawk... gawk
checking whether make sets $(MAKE)... yes
checking whether make supports nested variables... yes
checking whether make supports nested variables... (cached) yes
checking for gcc... /data/service/hnp/bin/clang
checking whether the C compiler works... yes
checking for C compiler default output file name... a.out
checking for suffix of executables... 
checking whether we are cross compiling... no
checking for suffix of object files... o
checking whether we are using the GNU C compiler... yes
checking whether /data/service/hnp/bin/clang accepts -g... yes
checking for /data/service/hnp/bin/clang option to accept ISO C89... none needed
checking whether /data/service/hnp/bin/clang understands -c and -o together... yes
checking for style of include used by make... GNU
checking dependency style of /data/service/hnp/bin/clang... gcc3
checking for xsltproc... /data/service/hnp/bin/xsltproc
checking for pkg-config... /data/service/hnp/bin/pkg-config
checking pkg-config is at least version 0.9.0... yes
checking for LIBOAUTH... yes
checking for LIBPCRE... yes
checking for LIBCURL... yes
checking for XML... yes
checking for JSON... yes
checking for library containing dlopen... none required
checking that generated files are newer than configure... done
configure: creating ./config.status
config.status: creating Makefile
config.status: executing depfiles commands

	bti 034
	=======

	prefix:                 /
	datarootdir:            ${prefix}/share
	mandir:                 ${datarootdir}/man

	compiler:               /data/service/hnp/bin/clang
	cflags:                 -O3
	ldflags:                

	xsltproc:               /data/service/hnp/bin/xsltproc


bti/034@ohpcd/stable: RUN: make -j1
  CC       bti-config.o
  CC       bti-bti.o
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:808:10: warning: 'oauth_http_get' is deprecated [-Wdeprecated-declarations]
        reply = oauth_http_get(request_url, post_params);
                ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:572:53: note: 'oauth_http_get' has been explicitly marked deprecated here
char *oauth_http_get (const char *u, const char *q) attribute_deprecated;
                                                    ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:51:49: note: expanded from macro 'attribute_deprecated'
#    define attribute_deprecated __attribute__((deprecated))
                                                ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:844:10: warning: 'oauth_http_get' is deprecated [-Wdeprecated-declarations]
        reply = oauth_http_get(request_url, post_params);
                ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:572:53: note: 'oauth_http_get' has been explicitly marked deprecated here
char *oauth_http_get (const char *u, const char *q) attribute_deprecated;
                                                    ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:51:49: note: expanded from macro 'attribute_deprecated'
#    define attribute_deprecated __attribute__((deprecated))
                                                ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:909:4: warning: 'curl_formadd' is deprecated: since 7.56.0. Use curl_mime_init() [-Wdeprecated-declarations]
                        curl_formadd(&formpost, &lastptr,
                        ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2624:26: note: 'curl_formadd' has been explicitly marked deprecated here
CURL_EXTERN CURLFORMcode CURL_DEPRECATED(7.56.0, "Use curl_mime_init()")
                         ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:910:10: warning: 'CURLFORM_COPYNAME' is deprecated: since 7.56.0. Use curl_mime_name() [-Wdeprecated-declarations]
                                     CURLFORM_COPYNAME, "status",
                                     ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2550:28: note: 'CURLFORM_COPYNAME' has been explicitly marked deprecated here
  CURLFORM_COPYNAME        CURL_DEPRECATED(7.56.0, "Use curl_mime_name()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:911:10: warning: 'CURLFORM_COPYCONTENTS' is deprecated: since 7.56.0. Use curl_mime_data() [-Wdeprecated-declarations]
                                     CURLFORM_COPYCONTENTS, session->tweet,
                                     ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2553:28: note: 'CURLFORM_COPYCONTENTS' has been explicitly marked deprecated here
  CURLFORM_COPYCONTENTS    CURL_DEPRECATED(7.56.0, "Use curl_mime_data()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:914:4: warning: 'curl_formadd' is deprecated: since 7.56.0. Use curl_mime_init() [-Wdeprecated-declarations]
                        curl_formadd(&formpost, &lastptr,
                        ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2624:26: note: 'curl_formadd' has been explicitly marked deprecated here
CURL_EXTERN CURLFORMcode CURL_DEPRECATED(7.56.0, "Use curl_mime_init()")
                         ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:915:10: warning: 'CURLFORM_COPYNAME' is deprecated: since 7.56.0. Use curl_mime_name() [-Wdeprecated-declarations]
                                     CURLFORM_COPYNAME, "source",
                                     ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2550:28: note: 'CURLFORM_COPYNAME' has been explicitly marked deprecated here
  CURLFORM_COPYNAME        CURL_DEPRECATED(7.56.0, "Use curl_mime_name()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:916:10: warning: 'CURLFORM_COPYCONTENTS' is deprecated: since 7.56.0. Use curl_mime_data() [-Wdeprecated-declarations]
                                     CURLFORM_COPYCONTENTS, "bti",
                                     ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2553:28: note: 'CURLFORM_COPYCONTENTS' has been explicitly marked deprecated here
  CURLFORM_COPYCONTENTS    CURL_DEPRECATED(7.56.0, "Use curl_mime_data()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:920:5: warning: 'curl_formadd' is deprecated: since 7.56.0. Use curl_mime_init() [-Wdeprecated-declarations]
                                curl_formadd(&formpost, &lastptr,
                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2624:26: note: 'curl_formadd' has been explicitly marked deprecated here
CURL_EXTERN CURLFORMcode CURL_DEPRECATED(7.56.0, "Use curl_mime_init()")
                         ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:921:11: warning: 'CURLFORM_COPYNAME' is deprecated: since 7.56.0. Use curl_mime_name() [-Wdeprecated-declarations]
                                             CURLFORM_COPYNAME,
                                             ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2550:28: note: 'CURLFORM_COPYNAME' has been explicitly marked deprecated here
  CURLFORM_COPYNAME        CURL_DEPRECATED(7.56.0, "Use curl_mime_name()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:923:11: warning: 'CURLFORM_COPYCONTENTS' is deprecated: since 7.56.0. Use curl_mime_data() [-Wdeprecated-declarations]
                                             CURLFORM_COPYCONTENTS,
                                             ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2553:28: note: 'CURLFORM_COPYCONTENTS' has been explicitly marked deprecated here
  CURLFORM_COPYCONTENTS    CURL_DEPRECATED(7.56.0, "Use curl_mime_data()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:927:27: warning: 'CURLOPT_HTTPPOST' is deprecated: since 7.56.0. Use CURLOPT_MIMEPOST [-Wdeprecated-declarations]
                        curl_easy_setopt(curl, CURLOPT_HTTPPOST, formpost);
                                               ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:1225:3: note: 'CURLOPT_HTTPPOST' has been explicitly marked deprecated here
  CURLOPTDEPRECATED(CURLOPT_HTTPPOST, CURLOPTTYPE_OBJECTPOINT, 24,
  ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:1111:43: note: expanded from macro 'CURLOPTDEPRECATED'
#define CURLOPTDEPRECATED(na,t,nu,v,m) na CURL_DEPRECATED(v,m) = t + nu
                                          ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:1006:7: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                                                curl_formfree(formpost);
                                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:1018:7: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                                                curl_formfree(formpost);
                                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:1029:7: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                                                curl_formfree(formpost);
                                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:1039:7: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                                                curl_formfree(formpost);
                                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:1050:4: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                        curl_formfree(formpost);
                        ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:1121:13: warning: 'oauth_http_post' is deprecated [-Wdeprecated-declarations]
                                reply = oauth_http_post(req_url, postarg);
                                        ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:629:54: note: 'oauth_http_post' has been explicitly marked deprecated here
char *oauth_http_post (const char *u, const char *p) attribute_deprecated;
                                                     ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:51:49: note: expanded from macro 'attribute_deprecated'
#    define attribute_deprecated __attribute__((deprecated))
                                                ^
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.c:1128:13: warning: 'oauth_http_get' is deprecated [-Wdeprecated-declarations]
                                reply = oauth_http_get(req_url, postarg);
                                        ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:572:53: note: 'oauth_http_get' has been explicitly marked deprecated here
char *oauth_http_get (const char *u, const char *q) attribute_deprecated;
                                                    ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:51:49: note: expanded from macro 'attribute_deprecated'
#    define attribute_deprecated __attribute__((deprecated))
                                                ^
19 warnings generated.
  CCLD     bti

bti/034@ohpcd/stable: Package '893f4238a37e85b38a718fa7e2ba2a4231eb710a' built
bti/034@ohpcd/stable: Build folder /storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/build-release
bti/034@ohpcd/stable: Generating the package
bti/034@ohpcd/stable: Packaging in folder /storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p
bti/034@ohpcd/stable: Calling package()
bti/034@ohpcd/stable: RUN: make install DESTDIR=/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p -j20
make: jobserver mkfifo: /storage/Users/currentUser/GMfifo7327: Operation not permitted
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/build-release'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p//bin'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p//bin'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p//share/man/man1'
  /storage/Users/currentUser/usr/local/bin/ginstall -c bti '/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p//bin'
 /storage/Users/currentUser/usr/local/bin/ginstall -c /storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti-shrink-urls '/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p//bin'
 /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 /storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti.1 /storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/bti-shrink-urls.1 '/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p//share/man/man1'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/b/build-release'

bti/034@ohpcd/stable: package(): Packaged 2 files: bti, bti-shrink-urls
bti/034@ohpcd/stable: package(): Packaged 2 '.1' files: bti.1, bti-shrink-urls.1
bti/034@ohpcd/stable: Created package revision 17ef361727b114fb4c87e55932c0eb2d
bti/034@ohpcd/stable: Package '893f4238a37e85b38a718fa7e2ba2a4231eb710a' created
bti/034@ohpcd/stable: Full package reference: bti/034@ohpcd/stable#2272e41c8d6131b279f7f03c13f00e31:893f4238a37e85b38a718fa7e2ba2a4231eb710a#17ef361727b114fb4c87e55932c0eb2d
bti/034@ohpcd/stable: Package folder /storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p

======== Launching test_package ========

======== Computing dependency graph ========
automake/1.18: WARN: automake/1.18: package_type 'application' is defined, but 'shared' and/or 'header_only' options are present. The package_type will have precedence over the options regardless of their value.
libtool/2.5.4: WARN: libtool/2.5.4: package_type 'application' is defined, but 'shared' and/or 'header_only' options are present. The package_type will have precedence over the options regardless of their value.
Graph root
    bti/034@ohpcd/stable (test package): /storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/test_package/conanfile.py
Requirements
    bti/034@ohpcd/stable#2272e41c8d6131b279f7f03c13f00e31 - Cache
    curl/8.15.0#4ae5a3c702753d2fc507808204655813 - Cache
    json-c/0.17#3c6e9ba2b444f1618c7f6c9c74742382 - Cache
    liboauth/1.0.3#8a3f827872cc9e4a146766615d81bd06 - Cache
    libxml2/2.15.3#6645e3b3d878fd252da369bed05e2cd5 - Cache
    openssl/3.5.6.1#d871951ad035e2c4eecb6112af441801 - Cache
    pcre/8.45#d37e7bcdd1483105496deb82632f1b44 - Cache
    zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9 - Cache
Build requirements
    automake/1.18#65a7ba60030d238eb8bb32266391cfc5 - Cache
    libtool/2.5.4#fe9f8e735ad45469571cf4de3ce552f4 - Cache
Overrides
    openssl/3.5.6.1: ['openssl/3.5.6.1']
    openssl/1.1.1w: ['openssl/3.5.6.1']

======== Computing necessary packages ========
Requirements
    bti/034@ohpcd/stable#2272e41c8d6131b279f7f03c13f00e31:893f4238a37e85b38a718fa7e2ba2a4231eb710a#17ef361727b114fb4c87e55932c0eb2d - Cache
    curl/8.15.0#4ae5a3c702753d2fc507808204655813:df2856b724fa5aed00dc7f60cec6755df39cf2b6#4a65670fdad2419ab77c3e47b23ed2eb - Cache
    json-c/0.17#3c6e9ba2b444f1618c7f6c9c74742382:01d92cf349a0dd98ff915f4bd99a04430171517f#fd10f04507655c87ed79a0e3d964e407 - Cache
    libxml2/2.15.3#6645e3b3d878fd252da369bed05e2cd5:01d92cf349a0dd98ff915f4bd99a04430171517f#164721fa4fa2b219536e9bc6e7fd9563 - Cache
Build requirements
Skipped binaries
    liboauth/1.0.3, openssl/3.5.6.1, pcre/8.45, zlib/1.3.1.1, automake/1.18, libtool/2.5.4

======== Installing packages ========
json-c/0.17: Already installed! (1 of 4)
libxml2/2.15.3: Already installed! (2 of 4)
curl/8.15.0: Already installed! (3 of 4)
bti/034@ohpcd/stable: Already installed! (4 of 4)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/test_package/build-release
bti/034@ohpcd/stable (test package): Test package build: build-release
bti/034@ohpcd/stable (test package): Test package build folder: /storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/test_package/build-release
bti/034@ohpcd/stable (test package): Writing generators to /storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/test_package/build-release/conan
bti/034@ohpcd/stable (test package): Generator 'VirtualRunEnv' calling 'generate()'
bti/034@ohpcd/stable (test package): Generating aggregated env files
bti/034@ohpcd/stable (test package): Generated aggregated env files: ['conanrun.sh', 'conanbuild.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
bti/034@ohpcd/stable (test package): Running test()
bti/034@ohpcd/stable (test package): RUN: /bin/sh "/storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/test_package/test.sh" "/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p/bin/bti"
[PASS] T1 --version => bti - version 034
[PASS] T2 --help => Version/Usage/--dry-run 齐全
[PASS] T3 缺失配置文件 => 可诊断错误
[PASS] T4 离线 dry-run => 请求构造产出 status="hello bti"
RESULT: 4/4 checks passed

```
