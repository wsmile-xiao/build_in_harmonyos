# bti 034 W3 本地 CI 模拟逐字日志

`finish` Step 5/10 内嵌的 W3 本地 CI 模拟（`ci/conan/build_and_test.sh`）在本任务
最终 SHA 上的逐字日志，退出为 `L0_RESULT=pass / L1_RESULT=pass / L2_RESULT=pass /
L4_RESULT=pass / L5_RESULT=pass`，其中：

- `test_package` 真实执行：`RESULT: 4/4 checks passed`（见日志中 `Executing test` 段）；
- `L1e` 破坏性反向验证通过（把 `bin/` 移走后测试确实失败），证明测试真的依赖被测产物；
- `L2` 的 `bti --version/--help` 打印非阻塞 `[warn]`：该冒烟检查不带 conanrun 环境，
  而 bti 的 `DT_NEEDED` 为 `libcurl.so`/`libxml2.so.16`/`libjson-c.so.5`（无 RUNPATH），
  缺 `LD_LIBRARY_PATH` 即加载失败；同一轮的 `bti-shrink-urls --help` 为 `[ok]`。
  真实消费路径由 `test_package`（`env="conanrun"`）覆盖，人工 L2 补测见
  `reports/conan-verify-supplement.md`。

## 逐字证据

- 原始文件：`/storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/reports/w3-local-ci.log`
- 原始字节数：35078
- 原始行数：562（`wc -l`，即换行符个数）
- sha256（原始文件逐字节）：`2355b571c52a6b0a8c56acb3e2f9434dad29ab1bc7d92a0b877117377f7f7610`
- 抽取命令（块内含末尾换行，不额外剥除）：

````text
sed -n '/^```text$/,/^```$/p' w3-local-ci-log.md | sed '1d;$d' > w3-local-ci.log
````

```text
$ setup.sh (RC=0)
[step] Conan environment setup...
[step] Conan version: Conan version 2.29.1
[step] Disabling conancenter (private CI, not needed)
conancenter: https://center2.conan.io [Verify SSL: True, Enabled: False]
[step] remote 已就绪: ohpcd
[step] Importing profile from /storage/Users/currentUser/ws/worktrees/bti-034/ci/conan/profiles/ohos-aarch64
[step] Profile file available at: /storage/Users/currentUser/ws/worktrees/bti-034/ci/conan/profiles/ohos-aarch64
[step] Conan environment ready ✅
[step]   remote: ohpcd
[step]   profile: ohos-aarch64
[step]   conan: Conan version 2.29.1


$ build_and_test.sh archives/b/bti/034 (RC=0)
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
[step] CI_PACKAGES received: archives/b/bti/034
[step] Found 1 package(s) to build

━━━ Building: bti/034 ━━━
[step] L0: Quality gate checks...
[step] L0i: Checking dependency availability in registry (R36)...
        [ok] dependency in registry: curl/8.15.0
        [ok] dependency in registry: json-c/0.17
        [ok] dependency in registry: liboauth/1.0.3
        [ok] dependency in registry: libxml2/2.15.3
        [ok] dependency in registry: openssl/3.5.6.1
        [ok] dependency in registry: pcre/8.45
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
  检查模式: prdiff (13 个文件)

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
  found 2 source URL(s)
  [try 1/1.1/3] source_6d2dc7d4 ← https://gregkh.github.io/bti/...
  [ok] source_6d2dc7d4 (2KB) via mirror 1
  [try 1/1.1/3] bti-034.tar.gz ← https://www.kernel.org/pub/software/web/bti/bti-034.tar.gz...
  [ok] bti-034.tar.gz (119KB) via mirror 1
  [done] Pre-downloaded 2 files, conandata.yml updated to file:// URLs
[step] Running conan create (output logged to /storage/Users/currentUser/ws/worktrees/bti-034/.ci_logs/conan_build_bti_034.log)...

======== Exporting recipe to the cache ========
bti/034: Exporting package recipe: /storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/conanfile.py
bti/034: exports: File 'conandata.yml' found. Exporting it...
bti/034: Calling export_sources()
bti/034: Copied 1 '.yml' file: conandata.yml
bti/034: Copied 1 '.py' file: conanfile.py
bti/034: Copied 3 '.patch' files: 0001-bti-shrink-urls.patch, 0002-bti.c.patch, 0003-configure.patch
bti/034: Exported to cache folder: /storage/Users/currentUser/.conan2/p/bti005b807b24e5e/e
bti/034: Exported: bti/034#2be2e8b07e021d5c814a217accfbf924 (2026-09-13 11:14:57 UTC)

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
    bti/034#2be2e8b07e021d5c814a217accfbf924 - Cache
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
bti/034: Forced build from source
Requirements
    bti/034#2be2e8b07e021d5c814a217accfbf924:893f4238a37e85b38a718fa7e2ba2a4231eb710a - Build
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
bti/034: Calling source() in /storage/Users/currentUser/.conan2/p/bti005b807b24e5e/s
bti/034: Sources correctly downloaded from file:///storage/Users/currentUser/ws/worktrees/bti-034/.build-cache/predl_cache/ee7314de_bti-034.tar.gz
bti/034: Uncompressing bti-034.tar.gz to .

-------- Installing package bti/034 (7 of 7) --------
bti/034: Building from source
bti/034: Package bti/034:893f4238a37e85b38a718fa7e2ba2a4231eb710a
bti/034: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
bti/034: requires: liboauth/1.0.3#8a3f827872cc9e4a146766615d81bd06:0f43cddf8f0746f39df42f9f026ecaab38cf98d1 curl/8.15.Z openssl/3.5.6.1#d871951ad035e2c4eecb6112af441801:f23d5a9b1d537641c03c7814478a2fadb727650a libxml2/2.15.Z json-c/0.17.Z pcre/8.45#d37e7bcdd1483105496deb82632f1b44:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa
bti/034: Copying sources to build folder
bti/034: Building your package in /storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b
bti/034: Calling generate()
bti/034: Generators folder: /storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/build-release/conan
bti/034: Generating aggregated env files
bti/034: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
bti/034: Calling build()
bti/034: Apply patch (portability): OHOS 没有 /bin/bash，bin_SCRIPTS 安装的 bti-shrink-urls 直接执行报 "bad interpreter: No such file or directory"（rc=126）。改为 #!/bin/sh； 该脚本在 OHOS 的 /bin/sh 下 `sh -n` 语法检查与 `--help` 运行均通过。

bti/034: Apply patch (portability): json-c 0.13 起移除了 is_error 宏，上游 2014 年的 bti.c 仍使用该宏， 链接期报 undefined symbol: is_error。将 3 处调用改为显式 NULL 比较 （与 Debian bti 034-6 的 replace_removed_is_error.patch 同口径）。

bti/034: Apply patch (portability): HMDFS 语义：config.status 用 umask 077 创建临时目录，落盘为 0700 目录， 在 setgid hmdfs 挂载上对构建用户不可写，configure 报 "can't create ./confXXXXXX/subs1.awk: Permission denied"。发布 tarball 只提供预生成 configure（无法 autoreconf），故就地放宽为 umask 022。

bti/034: RUN: "/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/configure" --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' PKG_CONFIG_PATH=/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/build-release/conan 
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


bti/034: RUN: make -j1
  CC       bti-config.o
  CC       bti-bti.o
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:808:10: warning: 'oauth_http_get' is deprecated [-Wdeprecated-declarations]
        reply = oauth_http_get(request_url, post_params);
                ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:572:53: note: 'oauth_http_get' has been explicitly marked deprecated here
char *oauth_http_get (const char *u, const char *q) attribute_deprecated;
                                                    ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:51:49: note: expanded from macro 'attribute_deprecated'
#    define attribute_deprecated __attribute__((deprecated))
                                                ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:844:10: warning: 'oauth_http_get' is deprecated [-Wdeprecated-declarations]
        reply = oauth_http_get(request_url, post_params);
                ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:572:53: note: 'oauth_http_get' has been explicitly marked deprecated here
char *oauth_http_get (const char *u, const char *q) attribute_deprecated;
                                                    ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:51:49: note: expanded from macro 'attribute_deprecated'
#    define attribute_deprecated __attribute__((deprecated))
                                                ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:909:4: warning: 'curl_formadd' is deprecated: since 7.56.0. Use curl_mime_init() [-Wdeprecated-declarations]
                        curl_formadd(&formpost, &lastptr,
                        ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2624:26: note: 'curl_formadd' has been explicitly marked deprecated here
CURL_EXTERN CURLFORMcode CURL_DEPRECATED(7.56.0, "Use curl_mime_init()")
                         ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:910:10: warning: 'CURLFORM_COPYNAME' is deprecated: since 7.56.0. Use curl_mime_name() [-Wdeprecated-declarations]
                                     CURLFORM_COPYNAME, "status",
                                     ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2550:28: note: 'CURLFORM_COPYNAME' has been explicitly marked deprecated here
  CURLFORM_COPYNAME        CURL_DEPRECATED(7.56.0, "Use curl_mime_name()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:911:10: warning: 'CURLFORM_COPYCONTENTS' is deprecated: since 7.56.0. Use curl_mime_data() [-Wdeprecated-declarations]
                                     CURLFORM_COPYCONTENTS, session->tweet,
                                     ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2553:28: note: 'CURLFORM_COPYCONTENTS' has been explicitly marked deprecated here
  CURLFORM_COPYCONTENTS    CURL_DEPRECATED(7.56.0, "Use curl_mime_data()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:914:4: warning: 'curl_formadd' is deprecated: since 7.56.0. Use curl_mime_init() [-Wdeprecated-declarations]
                        curl_formadd(&formpost, &lastptr,
                        ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2624:26: note: 'curl_formadd' has been explicitly marked deprecated here
CURL_EXTERN CURLFORMcode CURL_DEPRECATED(7.56.0, "Use curl_mime_init()")
                         ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:915:10: warning: 'CURLFORM_COPYNAME' is deprecated: since 7.56.0. Use curl_mime_name() [-Wdeprecated-declarations]
                                     CURLFORM_COPYNAME, "source",
                                     ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2550:28: note: 'CURLFORM_COPYNAME' has been explicitly marked deprecated here
  CURLFORM_COPYNAME        CURL_DEPRECATED(7.56.0, "Use curl_mime_name()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:916:10: warning: 'CURLFORM_COPYCONTENTS' is deprecated: since 7.56.0. Use curl_mime_data() [-Wdeprecated-declarations]
                                     CURLFORM_COPYCONTENTS, "bti",
                                     ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2553:28: note: 'CURLFORM_COPYCONTENTS' has been explicitly marked deprecated here
  CURLFORM_COPYCONTENTS    CURL_DEPRECATED(7.56.0, "Use curl_mime_data()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:920:5: warning: 'curl_formadd' is deprecated: since 7.56.0. Use curl_mime_init() [-Wdeprecated-declarations]
                                curl_formadd(&formpost, &lastptr,
                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2624:26: note: 'curl_formadd' has been explicitly marked deprecated here
CURL_EXTERN CURLFORMcode CURL_DEPRECATED(7.56.0, "Use curl_mime_init()")
                         ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:921:11: warning: 'CURLFORM_COPYNAME' is deprecated: since 7.56.0. Use curl_mime_name() [-Wdeprecated-declarations]
                                             CURLFORM_COPYNAME,
                                             ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2550:28: note: 'CURLFORM_COPYNAME' has been explicitly marked deprecated here
  CURLFORM_COPYNAME        CURL_DEPRECATED(7.56.0, "Use curl_mime_name()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:923:11: warning: 'CURLFORM_COPYCONTENTS' is deprecated: since 7.56.0. Use curl_mime_data() [-Wdeprecated-declarations]
                                             CURLFORM_COPYCONTENTS,
                                             ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2553:28: note: 'CURLFORM_COPYCONTENTS' has been explicitly marked deprecated here
  CURLFORM_COPYCONTENTS    CURL_DEPRECATED(7.56.0, "Use curl_mime_data()"),
                           ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:927:27: warning: 'CURLOPT_HTTPPOST' is deprecated: since 7.56.0. Use CURLOPT_MIMEPOST [-Wdeprecated-declarations]
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
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:1006:7: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                                                curl_formfree(formpost);
                                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:1018:7: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                                                curl_formfree(formpost);
                                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:1029:7: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                                                curl_formfree(formpost);
                                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:1039:7: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                                                curl_formfree(formpost);
                                                ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:1050:4: warning: 'curl_formfree' is deprecated: since 7.56.0. Use curl_mime_free() [-Wdeprecated-declarations]
                        curl_formfree(formpost);
                        ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:2660:18: note: 'curl_formfree' has been explicitly marked deprecated here
CURL_EXTERN void CURL_DEPRECATED(7.56.0, "Use curl_mime_free()")
                 ^
/storage/Users/currentUser/.conan2/p/curl3b1c48f2fda9f/p/include/curl/curl.h:44:18: note: expanded from macro 'CURL_DEPRECATED'
  __attribute__((deprecated("since " # version ". " message)))
                 ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:1121:13: warning: 'oauth_http_post' is deprecated [-Wdeprecated-declarations]
                                reply = oauth_http_post(req_url, postarg);
                                        ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:629:54: note: 'oauth_http_post' has been explicitly marked deprecated here
char *oauth_http_post (const char *u, const char *p) attribute_deprecated;
                                                     ^
/storage/Users/currentUser/.conan2/p/b/liboa4862fd7269437/p/include/oauth.h:51:49: note: expanded from macro 'attribute_deprecated'
#    define attribute_deprecated __attribute__((deprecated))
                                                ^
/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.c:1128:13: warning: 'oauth_http_get' is deprecated [-Wdeprecated-declarations]
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

bti/034: Package '893f4238a37e85b38a718fa7e2ba2a4231eb710a' built
bti/034: Build folder /storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/build-release
bti/034: Generating the package
bti/034: Packaging in folder /storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/p
bti/034: Calling package()
bti/034: RUN: make install DESTDIR=/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/p -j20
make: jobserver mkfifo: /storage/Users/currentUser/GMfifo8594: Operation not permitted
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/build-release'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/p//bin'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/p//bin'
 /storage/Users/currentUser/usr/local/bin/mkdir -p '/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/p//share/man/man1'
 /storage/Users/currentUser/usr/local/bin/ginstall -c /storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti-shrink-urls '/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/p//bin'
  /storage/Users/currentUser/usr/local/bin/ginstall -c bti '/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/p//bin'
 /storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 /storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti.1 /storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/bti-shrink-urls.1 '/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/p//share/man/man1'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/b/build-release'

bti/034: package(): Packaged 2 files: bti, bti-shrink-urls
bti/034: package(): Packaged 2 '.1' files: bti.1, bti-shrink-urls.1
bti/034: Created package revision 17ef361727b114fb4c87e55932c0eb2d
bti/034: Package '893f4238a37e85b38a718fa7e2ba2a4231eb710a' created
bti/034: Full package reference: bti/034#2be2e8b07e021d5c814a217accfbf924:893f4238a37e85b38a718fa7e2ba2a4231eb710a#17ef361727b114fb4c87e55932c0eb2d
bti/034: Package folder /storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/p

======== Launching test_package ========

======== Computing dependency graph ========
automake/1.18: WARN: automake/1.18: package_type 'application' is defined, but 'shared' and/or 'header_only' options are present. The package_type will have precedence over the options regardless of their value.
libtool/2.5.4: WARN: libtool/2.5.4: package_type 'application' is defined, but 'shared' and/or 'header_only' options are present. The package_type will have precedence over the options regardless of their value.
Graph root
    bti/034 (test package): /storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/test_package/conanfile.py
Requirements
    bti/034#2be2e8b07e021d5c814a217accfbf924 - Cache
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
    bti/034#2be2e8b07e021d5c814a217accfbf924:893f4238a37e85b38a718fa7e2ba2a4231eb710a#17ef361727b114fb4c87e55932c0eb2d - Cache
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
bti/034: Already installed! (4 of 4)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/test_package/build-release
bti/034 (test package): Test package build: build-release
bti/034 (test package): Test package build folder: /storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/test_package/build-release
bti/034 (test package): Writing generators to /storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/test_package/build-release/conan
bti/034 (test package): Generator 'VirtualRunEnv' calling 'generate()'
bti/034 (test package): Generating aggregated env files
bti/034 (test package): Generated aggregated env files: ['conanrun.sh', 'conanbuild.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
bti/034 (test package): Running test()
bti/034 (test package): RUN: /bin/sh "/storage/Users/currentUser/ws/worktrees/bti-034/archives/b/bti/034/test_package/test.sh" "/storage/Users/currentUser/.conan2/p/b/btie3ddf14ae32e7/p/bin/bti"
[PASS] T1 --version => bti - version 034
[PASS] T2 --help => Version/Usage/--dry-run 齐全
[PASS] T3 缺失配置文件 => 可诊断错误
[PASS] T4 离线 dry-run => 请求构造产出 status="hello bti"
RESULT: 4/4 checks passed

[ok] bti/034 — conan create passed
[step] L1: Verifying test execution from conan create log...
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[step] L1c: No upstream make check/ctest in log (may be in test_package only)
[step] L4: Scanning patches for dangerous functions...
[step] L5: Baseline artifact check...
[ok] L5: bin/ has content
[step] L1e: Destructive negative test (R34)...
        [sabotage] bin/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on bti
[step] L2: Smoke test (version/help check)...
[warn] L2: bti --version/--help failed (non-blocking)
[ok] L2: bti-shrink-urls --help OK

L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: bti version/help failed, bti-shrink-urls --help OK
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
