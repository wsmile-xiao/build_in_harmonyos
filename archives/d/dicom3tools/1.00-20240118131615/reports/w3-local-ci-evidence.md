# W3 本地 CI 模拟日志留档

> 逐字留档：下方标记之间的内容与原始日志**逐字节相同**（未加工）。
> review-memory §19 禁止 PR 入库 `*.log`，故运行日志以本形态留档（原文件不入库）。

| 属性 | 值 |
| --- | --- |
| 原始文件 | `w3-local-ci.log` |
| 字节数 | 679830 |
| 行数 | 5076 |
| sha256 | `ee010fab6aadf88e1cbd4365da288a6853764cd50daf10353a34894035e3a0aa` |
| 采集命令 | `python3 scripts/ohc-run.py finish dicom3tools 1.00-20240118131615 built（内嵌 Step 5/10 W3）` |
| 采集时间 | 2026-09-11（设备本地时间） |
| 采信轮提交 | `48813722e1ccb489db358f51e973a6376ced5c03` |

<!-- BEGIN VERBATIM LOG -->
$ setup.sh (RC=0)
[step] Conan environment setup...
[step] Conan version: Conan version 2.29.1
[step] Disabling conancenter (private CI, not needed)
conancenter: https://center2.conan.io [Verify SSL: True, Enabled: False]
[step] remote 已就绪: ohpcd
[step] Importing profile from /storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/ci/conan/profiles/ohos-aarch64
[step] Profile file available at: /storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/ci/conan/profiles/ohos-aarch64
[step] Conan environment ready ✅
[step]   remote: ohpcd
[step]   profile: ohos-aarch64
[step]   conan: Conan version 2.29.1


$ build_and_test.sh archives/d/dicom3tools/1.00-20240118131615 (RC=0)
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
[step] CI_PACKAGES received: archives/d/dicom3tools/1.00-20240118131615
[step] Found 1 package(s) to build

━━━ Building: dicom3tools/1.00-20240118131615 ━━━
[step] L0: Quality gate checks...
[step] L0i: Checking dependency availability in registry (R36)...
        [ok] dependency in registry: libx11/6.4.0
        [ok] dependency in registry: libxext/6.4.0
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
  检查模式: prdiff (31 个文件)

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
  [try 1/1.1/3] dicom3tools_1.00.snapshot.20240118131615.tar.bz2 ← https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_1.00.snapshot.202...
  [ok] dicom3tools_1.00.snapshot.20240118131615.tar.bz2 (1060KB) via mirror 1
  [try 1/1.1/3] imake.tar.gz ← https://www.dclunie.com/imake/imake.tar.gz...
  [ok] imake.tar.gz (152KB) via mirror 1
  [done] Pre-downloaded 2 files, conandata.yml updated to file:// URLs
[step] Running conan create (output logged to /storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/.ci_logs/conan_build_dicom3tools_1.00-20240118131615.log)...

======== Exporting recipe to the cache ========
dicom3tools/1.00-20240118131615: Exporting package recipe: /storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/archives/d/dicom3tools/1.00-20240118131615/conanfile.py
dicom3tools/1.00-20240118131615: exports: File 'conandata.yml' found. Exporting it...
dicom3tools/1.00-20240118131615: Calling export_sources()
dicom3tools/1.00-20240118131615: Copied 1 '.yml' file: conandata.yml
dicom3tools/1.00-20240118131615: Copied 1 '.py' file: conanfile.py
dicom3tools/1.00-20240118131615: Copied 6 '.patch' files
dicom3tools/1.00-20240118131615: Exported to cache folder: /storage/Users/currentUser/.conan2/p/dicom3c2289d24782d/e
dicom3tools/1.00-20240118131615: Exported: dicom3tools/1.00-20240118131615#dbc4912b37a88e0d156227705fe835f2 (2026-09-11 17:23:29 UTC)

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
    dicom3tools/1.00-20240118131615#dbc4912b37a88e0d156227705fe835f2 - Cache
    libx11/6.4.0#63e25e48c3af73db324ce61d0dba9cce - Cache
    libxau/1.0.11#e70832a1f31a85a0398300bf72179ad9 - Cache
    libxcb/1.16#eb6f913ae9cabe62e164fe5fb3ba9391 - Cache
    libxdmcp/1.1.5#8aaf268abc5f64d20cb46f0ec0c6fdb7 - Cache
    libxext/6.4.0#20942ab436730e84acb01dcf565fda68 - Cache
    xorgproto/2025.1#f5274e33759da898a6e8d87d7708d47c - Cache
    xtrans/1.6.0#664ea4b0b501c5f144fc094ab1a4dfc5 - Cache
Test requirements
    check/0.15.2#6d41c3078e77093b6b9dfe97b95e0f9c - Cache
Build requirements
    perl/5.42.2#13c4f5bde5668df0b7268c4d0c01073c - Cache
    xcb-proto/1.17.0#f985020ceb16e7e9ea7af4f2e57652b5 - Cache

======== Computing necessary packages ========
Connecting to remote 'ohpcd' anonymously
dicom3tools/1.00-20240118131615: Forced build from source
Requirements
    dicom3tools/1.00-20240118131615#dbc4912b37a88e0d156227705fe835f2:5eb970f88879b3d0c0e7ef18bb72a19b24bbb2cb - Build
    libx11/6.4.0#63e25e48c3af73db324ce61d0dba9cce:c042bc3ef1476cfe65d9b8d95c3088cf1ad1a5ab#0e5934cee0577987a9f173673f0cb4a2 - Cache
    libxau/1.0.11#e70832a1f31a85a0398300bf72179ad9:b33b73a64003feb619a47ac2da762d7e7521ab18#2875a48c0f9c6168a810db745fe96324 - Cache
    libxcb/1.16#eb6f913ae9cabe62e164fe5fb3ba9391:d9d8d69421c16a44ece624cdbba864af799b6b14#ac43d5ee9e4e48933f548d4dd8c72790 - Cache
    libxdmcp/1.1.5#8aaf268abc5f64d20cb46f0ec0c6fdb7:b33b73a64003feb619a47ac2da762d7e7521ab18#b9dab63027b7d0ce0f0c04f8ceef5197 - Cache
    libxext/6.4.0#20942ab436730e84acb01dcf565fda68:e647863c487673f3505fad09e4305079038bb22d#b056ec34282b1e4cef84cb5be71b6aab - Cache
    xorgproto/2025.1#f5274e33759da898a6e8d87d7708d47c:283a988d63e011a731408b6abe0950de49e6171d#b7dc443b533634631c412ae235a57198 - Cache
    xtrans/1.6.0#664ea4b0b501c5f144fc094ab1a4dfc5:283a988d63e011a731408b6abe0950de49e6171d#f07ea55c2b81548d01d94db631e0ac0e - Cache
Test requirements
Build requirements
Skipped binaries
    check/0.15.2, perl/5.42.2, xcb-proto/1.17.0

======== Installing packages ========
xorgproto/2025.1: Already installed! (1 of 8)
libxau/1.0.11: Already installed! (2 of 8)
libxdmcp/1.1.5: Already installed! (3 of 8)
xtrans/1.6.0: Already installed! (4 of 8)
libxcb/1.16: Already installed! (5 of 8)
libx11/6.4.0: Already installed! (6 of 8)
libxext/6.4.0: Already installed! (7 of 8)
dicom3tools/1.00-20240118131615: Calling source() in /storage/Users/currentUser/.conan2/p/dicom3c2289d24782d/s
dicom3tools/1.00-20240118131615: Sources correctly downloaded from file:///storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/.build-cache/predl_cache/fcd997c6_dicom3tools_1.00.snapshot.20240118131615.tar.bz2
dicom3tools/1.00-20240118131615: Uncompressing fcd997c6_dicom3tools_1.00.snapshot.20240118131615.tar.bz2 to dicom3tools
dicom3tools/1.00-20240118131615: Sources correctly downloaded from file:///storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/.build-cache/predl_cache/18136a74_imake.tar.gz
dicom3tools/1.00-20240118131615: Uncompressing 18136a74_imake.tar.gz to imake

-------- Installing package dicom3tools/1.00-20240118131615 (8 of 8) --------
dicom3tools/1.00-20240118131615: Building from source
dicom3tools/1.00-20240118131615: Package dicom3tools/1.00-20240118131615:5eb970f88879b3d0c0e7ef18bb72a19b24bbb2cb
dicom3tools/1.00-20240118131615: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
dicom3tools/1.00-20240118131615: requires: libxext/6.4.Z libx11/6.4.Z xtrans/1.6.0#664ea4b0b501c5f144fc094ab1a4dfc5:283a988d63e011a731408b6abe0950de49e6171d libxcb/1.16.Z xorgproto/2025.1#f5274e33759da898a6e8d87d7708d47c:283a988d63e011a731408b6abe0950de49e6171d
dicom3tools/1.00-20240118131615: Copying sources to build folder
dicom3tools/1.00-20240118131615: Building your package in /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b
dicom3tools/1.00-20240118131615: Generating aggregated env files
dicom3tools/1.00-20240118131615: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
dicom3tools/1.00-20240118131615: Calling build()
dicom3tools/1.00-20240118131615: Apply patch (portability): Configure probes the C and C++ compilers and the C library capabilities instead of parsing a gcc version number
dicom3tools/1.00-20240118131615: Apply patch (portability): Imakefile and appsrc/dconvert/signa/Imakefile: write commented-out recipe lines as XCOMM so that a C preprocessor does not reject them as invalid directives
dicom3tools/1.00-20240118131615: Apply patch (portability): libsrc/support/*.awk: send diagnostics to stderr; a failed redirect to /dev/tty is fatal to gawk and truncated generated headers
dicom3tools/1.00-20240118131615: Apply patch (portability): imake: build against musl and a modern C compiler (strerror instead of sys_errlist, no bare return in a non-void function)
dicom3tools/1.00-20240118131615: Apply patch (bugfix): makedepend: build on a modern C library (rename the private getline, explicit void returns) and fix the diagnostic helpers that truncate pointers on 64-bit targets
dicom3tools/1.00-20240118131615: Apply patch (portability): libsrc/docs, libsrc/standard and libsrc/standard/elmdict: use portable userland command syntax: replace the obsolescent sort keys (+N -M, which only GNU coreutils honours via _POSIX2_VERSION=199209) with the modern -k form, and xargs -L 1 with the POSIX xargs -n 1, because a toybox sort/xargs rejects both and the failing pipeline truncates the generated headers
dicom3tools/1.00-20240118131615: RUN: "/data/service/hnp/bin/clang" -std=gnu89 -w -DFIXUP_CPP_WHITESPACE -o "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake" -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/config" -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/include" -DCPP_PROGRAM='"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/cpp"' "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/config/imake.c"

dicom3tools/1.00-20240118131615: RUN: "/data/service/hnp/bin/clang" -w -c -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/util/makedepend" -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/include" -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/config" -DINCLUDEDIR='"/usr/include"' -o "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/makedepend-obj/include.o" "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/util/makedepend/include.c"

dicom3tools/1.00-20240118131615: RUN: "/data/service/hnp/bin/clang" -w -c -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/util/makedepend" -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/include" -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/config" -DINCLUDEDIR='"/usr/include"' -o "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/makedepend-obj/main.o" "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/util/makedepend/main.c"

dicom3tools/1.00-20240118131615: RUN: "/data/service/hnp/bin/clang" -w -c -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/util/makedepend" -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/include" -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/config" -DINCLUDEDIR='"/usr/include"' -o "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/makedepend-obj/parse.o" "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/util/makedepend/parse.c"

dicom3tools/1.00-20240118131615: RUN: "/data/service/hnp/bin/clang" -w -c -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/util/makedepend" -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/include" -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/config" -DINCLUDEDIR='"/usr/include"' -o "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/makedepend-obj/pr.o" "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/util/makedepend/pr.c"

dicom3tools/1.00-20240118131615: RUN: "/data/service/hnp/bin/clang" -w -c -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/util/makedepend" -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/include" -I"/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/config" -DINCLUDEDIR='"/usr/include"' -o "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/makedepend-obj/cppsetup.o" "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/imake/util/makedepend/cppsetup.c"

dicom3tools/1.00-20240118131615: RUN: "/data/service/hnp/bin/clang" -w -o "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend" "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/makedepend-obj/include.o" "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/makedepend-obj/main.o" "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/makedepend-obj/parse.o" "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/makedepend-obj/pr.o" "/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/makedepend-obj/cppsetup.o"

dicom3tools/1.00-20240118131615: Configure: writing config/generic.cf
dicom3tools/1.00-20240118131615: RUN: ./Configure
Configure: begin
Configure: we are on OS HarmonyOS
Configure: we are on instruction set architecture unknown
Configure: make install use platform specific directory harmonyos.hongmeng.kernel.1.unknown
Configure: using gawk
Configure: using flex flex version 2.6.4 usage statistics:
grep: (standard input): binary file matches
Configure: using bzip2 
Configure: will try to use gcc
Configure: gcc not available :(
Configure: probing C compiler clang
Configure: probing C++ compiler clang++
Configure: C++ headers are iostream and friends, in namespace std
Configure: math headers do not provide infinity() and quiet_nan(), using the dumb fallbacks
Configure: no gethostid() in the C library
egrep: warning: egrep is obsolescent; using grep -E

dicom3tools/1.00-20240118131615: RUN: /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I./config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext'
In file included from <stdin>:3:
In file included from ./config/Imake.tmpl:550:
./config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
./config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.

dicom3tools/1.00-20240118131615: RUN: make IMAKE_DEFINES="'-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext'" IMAKE="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake" DEPEND="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend" MKDIRHIER="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/mkdirhier" Makefiles
making Makefiles in ./appsrc...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work'
rm -rf appsrc/Makefile.bak
cd appsrc; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../. -DCURDIR=./appsrc -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from .././config/Imake.tmpl:550:
.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
making Makefiles in ./appsrc/acrnema...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
rm -rf acrnema/Makefile.bak
cd acrnema; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../. -DCURDIR=./appsrc/acrnema -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../.././config/Imake.tmpl:550:
../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/acrnema'
make[4]: Nothing to be done for 'Makefiles'.
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/acrnema'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
making Makefiles in ./appsrc/dcdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
rm -rf dcdisp/Makefile.bak
cd dcdisp; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../. -DCURDIR=./appsrc/dcdisp -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../.././config/Imake.tmpl:550:
../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcdisp'
make[4]: Nothing to be done for 'Makefiles'.
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcdisp'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
making Makefiles in ./appsrc/dcfile...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
rm -rf dcfile/Makefile.bak
cd dcfile; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../. -DCURDIR=./appsrc/dcfile -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../.././config/Imake.tmpl:550:
../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcfile'
make[4]: Nothing to be done for 'Makefiles'.
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcfile'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
making Makefiles in ./appsrc/dcintro...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
rm -rf dcintro/Makefile.bak
cd dcintro; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../. -DCURDIR=./appsrc/dcintro -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../.././config/Imake.tmpl:550:
../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcintro'
make[4]: Nothing to be done for 'Makefiles'.
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcintro'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
making Makefiles in ./appsrc/misc...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
rm -rf misc/Makefile.bak
cd misc; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../. -DCURDIR=./appsrc/misc -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../.././config/Imake.tmpl:550:
../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/misc'
make[4]: Nothing to be done for 'Makefiles'.
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/misc'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
making Makefiles in ./appsrc/simple...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
rm -rf simple/Makefile.bak
cd simple; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../. -DCURDIR=./appsrc/simple -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../.././config/Imake.tmpl:550:
../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
making Makefiles in ./appsrc/simple/ge9800...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
rm -rf ge9800/Makefile.bak
cd ge9800; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/simple/ge9800 -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/ge9800'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/ge9800'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
making Makefiles in ./appsrc/simple/genesis...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
rm -rf genesis/Makefile.bak
cd genesis; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/simple/genesis -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/genesis'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/genesis'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
making Makefiles in ./appsrc/simple/pace...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
rm -rf pace/Makefile.bak
cd pace; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/simple/pace -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/pace'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/pace'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
making Makefiles in ./appsrc/simple/signa...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
rm -rf signa/Makefile.bak
cd signa; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/simple/signa -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/signa'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/signa'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
making Makefiles in ./appsrc/simple/somatom...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
rm -rf somatom/Makefile.bak
cd somatom; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/simple/somatom -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/somatom'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/somatom'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
making Makefiles in ./appsrc/simple/sytec...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
rm -rf sytec/Makefile.bak
cd sytec; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/simple/sytec -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/sytec'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/sytec'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
making Makefiles in ./appsrc/simple/vision...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
rm -rf vision/Makefile.bak
cd vision; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/simple/vision -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/vision'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/vision'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
making Makefiles in ./appsrc/dconvert...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
rm -rf dconvert/Makefile.bak
cd dconvert; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../. -DCURDIR=./appsrc/dconvert -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../.././config/Imake.tmpl:550:
../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
making Makefiles in ./appsrc/dconvert/support...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
rm -rf support/Makefile.bak
cd support; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/dconvert/support -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/support'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/support'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
making Makefiles in ./appsrc/dconvert/xxxx...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
rm -rf xxxx/Makefile.bak
cd xxxx; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/dconvert/xxxx -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/xxxx'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/xxxx'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
making Makefiles in ./appsrc/dconvert/pace...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
rm -rf pace/Makefile.bak
cd pace; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/dconvert/pace -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pace'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pace'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
making Makefiles in ./appsrc/dconvert/imtn...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
rm -rf imtn/Makefile.bak
cd imtn; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/dconvert/imtn -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/imtn'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/imtn'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
making Makefiles in ./appsrc/dconvert/gen...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
rm -rf gen/Makefile.bak
cd gen; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/dconvert/gen -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gen'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gen'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
making Makefiles in ./appsrc/dconvert/gaw...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
rm -rf gaw/Makefile.bak
cd gaw; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/dconvert/gaw -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gaw'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gaw'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
making Makefiles in ./appsrc/dconvert/shim...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
rm -rf shim/Makefile.bak
cd shim; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/dconvert/shim -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/shim'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/shim'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
making Makefiles in ./appsrc/dconvert/somp...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
rm -rf somp/Makefile.bak
cd somp; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/dconvert/somp -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/somp'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/somp'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
making Makefiles in ./appsrc/dconvert/himr...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
rm -rf himr/Makefile.bak
cd himr; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/dconvert/himr -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/himr'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/himr'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
making Makefiles in ./appsrc/dconvert/pq...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
rm -rf pq/Makefile.bak
cd pq; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/dconvert/pq -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pq'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pq'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
making Makefiles in ./appsrc/dconvert/toshiba...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
rm -rf toshiba/Makefile.bak
cd toshiba; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/dconvert/toshiba -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/toshiba'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/toshiba'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
making Makefiles in ./appsrc/dconvert/signa...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
rm -rf signa/Makefile.bak
cd signa; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/dconvert/signa -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/signa'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/signa'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
making Makefiles in ./appsrc/dconvert/ge9800...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
rm -rf ge9800/Makefile.bak
cd ge9800; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./appsrc/dconvert/ge9800 -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/ge9800'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/ge9800'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work'
making Makefiles in ./config...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work'
rm -rf config/Makefile.bak
cd config; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../. -DCURDIR=./config -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ./Imake.tmpl:550:
./Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
./Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/config'
make[2]: Nothing to be done for 'Makefiles'.
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/config'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work'
making Makefiles in ./libsrc...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work'
rm -rf libsrc/Makefile.bak
cd libsrc; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../. -DCURDIR=./libsrc -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from .././config/Imake.tmpl:550:
.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
making Makefiles in ./libsrc/standard...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
rm -rf standard/Makefile.bak
cd standard; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../. -DCURDIR=./libsrc/standard -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../.././config/Imake.tmpl:550:
../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
making Makefiles in ./libsrc/standard/elmdict...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
rm -rf elmdict/Makefile.bak
cd elmdict; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/standard/elmdict -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/elmdict'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/elmdict'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
making Makefiles in ./libsrc/standard/module...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
rm -rf module/Makefile.bak
cd module; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/standard/module -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/module'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/module'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
making Makefiles in ./libsrc/standard/iodcomp...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
rm -rf iodcomp/Makefile.bak
cd iodcomp; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/standard/iodcomp -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/iodcomp'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/iodcomp'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
making Makefiles in ./libsrc/standard/strval...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
rm -rf strval/Makefile.bak
cd strval; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/standard/strval -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/strval'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/strval'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
making Makefiles in ./libsrc/include...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
rm -rf include/Makefile.bak
cd include; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../. -DCURDIR=./libsrc/include -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../.././config/Imake.tmpl:550:
../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
making Makefiles in ./libsrc/include/dcdisp...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
rm -rf dcdisp/Makefile.bak
cd dcdisp; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/include/dcdisp -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dcdisp'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dcdisp'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
making Makefiles in ./libsrc/include/dconvert...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
rm -rf dconvert/Makefile.bak
cd dconvert; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/include/dconvert -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dconvert'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dconvert'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
making Makefiles in ./libsrc/include/dctool...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
rm -rf dctool/Makefile.bak
cd dctool; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/include/dctool -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dctool'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dctool'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
making Makefiles in ./libsrc/include/generic...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
rm -rf generic/Makefile.bak
cd generic; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/include/generic -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/generic'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/generic'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
making Makefiles in ./libsrc/include/locale...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
rm -rf locale/Makefile.bak
cd locale; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/include/locale -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/locale'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/locale'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
making Makefiles in ./libsrc/include/ourdisp...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
rm -rf ourdisp/Makefile.bak
cd ourdisp; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/include/ourdisp -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/ourdisp'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/ourdisp'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
making Makefiles in ./libsrc/include/pixeldat...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
rm -rf pixeldat/Makefile.bak
cd pixeldat; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/include/pixeldat -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/pixeldat'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/pixeldat'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
making Makefiles in ./libsrc/lib...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
rm -rf lib/Makefile.bak
cd lib; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../. -DCURDIR=./libsrc/lib -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../.././config/Imake.tmpl:550:
../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/lib'
make[4]: Nothing to be done for 'Makefiles'.
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/lib'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
making Makefiles in ./libsrc/src...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
rm -rf src/Makefile.bak
cd src; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../. -DCURDIR=./libsrc/src -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../.././config/Imake.tmpl:550:
../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
making Makefiles in ./libsrc/src/dcdisp...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
rm -rf dcdisp/Makefile.bak
cd dcdisp; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/src/dcdisp -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dcdisp'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dcdisp'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
making Makefiles in ./libsrc/src/dctool...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
rm -rf dctool/Makefile.bak
cd dctool; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/src/dctool -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dctool'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dctool'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
making Makefiles in ./libsrc/src/generic...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
rm -rf generic/Makefile.bak
cd generic; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/src/generic -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/generic'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/generic'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
making Makefiles in ./libsrc/src/locale...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
rm -rf locale/Makefile.bak
cd locale; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/src/locale -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/locale'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/locale'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
making Makefiles in ./libsrc/src/ourdisp...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
rm -rf ourdisp/Makefile.bak
cd ourdisp; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/src/ourdisp -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/ourdisp'
make[6]: Nothing to be done for 'Makefiles'.
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/ourdisp'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
making Makefiles in ./libsrc/src/dconvert...
make[5]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
rm -rf dconvert/Makefile.bak
cd dconvert; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../. -DCURDIR=./libsrc/src/dconvert -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../.././config/Imake.tmpl:550:
../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[6]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
making Makefiles in ./libsrc/src/dconvert/support...
make[7]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
rm -rf support/Makefile.bak
cd support; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../../. -DCURDIR=./libsrc/src/dconvert/support -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../../.././config/Imake.tmpl:550:
../../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[8]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/support'
make[8]: Nothing to be done for 'Makefiles'.
make[8]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/support'
make[7]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
making Makefiles in ./libsrc/src/dconvert/pace...
make[7]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
rm -rf pace/Makefile.bak
cd pace; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../../. -DCURDIR=./libsrc/src/dconvert/pace -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../../.././config/Imake.tmpl:550:
../../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[8]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pace'
make[8]: Nothing to be done for 'Makefiles'.
make[8]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pace'
make[7]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
making Makefiles in ./libsrc/src/dconvert/xxxx...
make[7]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
rm -rf xxxx/Makefile.bak
cd xxxx; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../../. -DCURDIR=./libsrc/src/dconvert/xxxx -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../../.././config/Imake.tmpl:550:
../../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[8]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/xxxx'
make[8]: Nothing to be done for 'Makefiles'.
make[8]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/xxxx'
make[7]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
making Makefiles in ./libsrc/src/dconvert/imtn...
make[7]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
rm -rf imtn/Makefile.bak
cd imtn; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../../. -DCURDIR=./libsrc/src/dconvert/imtn -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../../.././config/Imake.tmpl:550:
../../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[8]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/imtn'
make[8]: Nothing to be done for 'Makefiles'.
make[8]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/imtn'
make[7]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
making Makefiles in ./libsrc/src/dconvert/gen...
make[7]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
rm -rf gen/Makefile.bak
cd gen; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../../. -DCURDIR=./libsrc/src/dconvert/gen -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../../.././config/Imake.tmpl:550:
../../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[8]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gen'
make[8]: Nothing to be done for 'Makefiles'.
make[8]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gen'
make[7]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
making Makefiles in ./libsrc/src/dconvert/gaw...
make[7]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
rm -rf gaw/Makefile.bak
cd gaw; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../../. -DCURDIR=./libsrc/src/dconvert/gaw -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../../.././config/Imake.tmpl:550:
../../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[8]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gaw'
make[8]: Nothing to be done for 'Makefiles'.
make[8]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gaw'
make[7]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
making Makefiles in ./libsrc/src/dconvert/shim...
make[7]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
rm -rf shim/Makefile.bak
cd shim; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../../. -DCURDIR=./libsrc/src/dconvert/shim -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../../.././config/Imake.tmpl:550:
../../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[8]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/shim'
make[8]: Nothing to be done for 'Makefiles'.
make[8]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/shim'
make[7]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
making Makefiles in ./libsrc/src/dconvert/somp...
make[7]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
rm -rf somp/Makefile.bak
cd somp; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../../. -DCURDIR=./libsrc/src/dconvert/somp -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../../.././config/Imake.tmpl:550:
../../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[8]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/somp'
make[8]: Nothing to be done for 'Makefiles'.
make[8]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/somp'
make[7]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
making Makefiles in ./libsrc/src/dconvert/himr...
make[7]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
rm -rf himr/Makefile.bak
cd himr; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../../. -DCURDIR=./libsrc/src/dconvert/himr -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../../.././config/Imake.tmpl:550:
../../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[8]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/himr'
make[8]: Nothing to be done for 'Makefiles'.
make[8]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/himr'
make[7]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
making Makefiles in ./libsrc/src/dconvert/pq...
make[7]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
rm -rf pq/Makefile.bak
cd pq; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../../. -DCURDIR=./libsrc/src/dconvert/pq -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../../.././config/Imake.tmpl:550:
../../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[8]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pq'
make[8]: Nothing to be done for 'Makefiles'.
make[8]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pq'
make[7]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
making Makefiles in ./libsrc/src/dconvert/signa...
make[7]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
rm -rf signa/Makefile.bak
cd signa; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../../. -DCURDIR=./libsrc/src/dconvert/signa -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../../.././config/Imake.tmpl:550:
../../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[8]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/signa'
make[8]: Nothing to be done for 'Makefiles'.
make[8]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/signa'
make[7]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
making Makefiles in ./libsrc/src/dconvert/ge9800...
make[7]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
rm -rf ge9800/Makefile.bak
cd ge9800; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../../../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../../../. -DCURDIR=./libsrc/src/dconvert/ge9800 -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../../../.././config/Imake.tmpl:550:
../../../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../../../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[8]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/ge9800'
make[8]: Nothing to be done for 'Makefiles'.
make[8]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/ge9800'
make[7]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
make[6]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
make[5]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
making Makefiles in ./libsrc/support...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
rm -rf support/Makefile.bak
cd support; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../. -DCURDIR=./libsrc/support -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../.././config/Imake.tmpl:550:
../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/support'
make[4]: Nothing to be done for 'Makefiles'.
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/support'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
making Makefiles in ./libsrc/docs...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
rm -rf docs/Makefile.bak
cd docs; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I../.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../../. -DCURDIR=./libsrc/docs -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from ../.././config/Imake.tmpl:550:
../.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
../.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/docs'
make[4]: Nothing to be done for 'Makefiles'.
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/docs'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work'
making Makefiles in ./support...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work'
rm -rf support/Makefile.bak
cd support; /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake -I.././config '-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext' -DTOPDIR=../. -DCURDIR=./support -DSystemIncludeOption=-I; \
make  Makefiles
In file included from <stdin>:3:
In file included from .././config/Imake.tmpl:550:
.././config/Project.p-tmpl:192:53: warning: missing terminating '"' character [-Winvalid-pp-token]
                      C_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
.././config/Project.p-tmpl:193:53: warning: missing terminating '"' character [-Winvalid-pp-token]
              CPLUSPLUS_DEFINES = -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"
                                                    ^
2 warnings generated.
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/support'
make[2]: Nothing to be done for 'Makefiles'.
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/support'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work'

dicom3tools/1.00-20240118131615: RUN: make IMAKE_DEFINES="'-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext'" IMAKE="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake" DEPEND="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend" MKDIRHIER="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/mkdirhier" depend
depending in ./libsrc...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
depending in ./libsrc/standard...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
depending in ./libsrc/standard/elmdict...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/elmdict'
make[3]: Nothing to be done for 'depend'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/elmdict'
depending in ./libsrc/standard/module...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/module'
make[3]: Nothing to be done for 'depend'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/module'
depending in ./libsrc/standard/iodcomp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/iodcomp'
make[3]: Nothing to be done for 'depend'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/iodcomp'
depending in ./libsrc/standard/strval...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/strval'
make[3]: Nothing to be done for 'depend'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/strval'
cat elmdict/dicom3.tpl elmdict/philips.tpl elmdict/siemens.tpl elmdict/gems.tpl elmdict/papyrus.tpl elmdict/toshiba.tpl elmdict/hitachi.tpl elmdict/isg.tpl elmdict/elscint.tpl elmdict/acuson.tpl elmdict/camtron.tpl elmdict/agfa.tpl elmdict/picker.tpl elmdict/spi.tpl elmdict/other.tpl elmdict/dicos.tpl elmdict/diconde.tpl elmdict/dicondep.tpl | sort -b -k1,1n -k5,5n >elmdict.tpl
cat module/base.tpl module/file.tpl module/pet.tpl module/rt.tpl module/acqctx.tpl module/specimen.tpl module/dx.tpl module/vl.tpl module/waveform.tpl module/sr.tpl module/softcopy.tpl module/mr.tpl module/ct.tpl module/xaxrf.tpl module/us.tpl >module.tpl
cat iodcomp/base.tpl iodcomp/file.tpl iodcomp/xaxrf.tpl iodcomp/pet.tpl iodcomp/rt.tpl iodcomp/dx.tpl iodcomp/vl.tpl iodcomp/waveform.tpl iodcomp/sr.tpl iodcomp/softcopy.tpl iodcomp/mr.tpl iodcomp/ct.tpl iodcomp/us.tpl >iodcomp.tpl
cat strval/base.tpl strval/charset.tpl strval/file.tpl strval/xaxrf.tpl strval/us.tpl strval/nm.tpl strval/pet.tpl strval/rt.tpl strval/dx.tpl strval/sdmdx.tpl strval/vl.tpl strval/waveform.tpl strval/sr.tpl strval/softcopy.tpl strval/mr.tpl strval/ct.tpl >strval.tpl
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
depending in ./libsrc/include...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
depending in ./libsrc/include/dcdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dcdisp'
make[3]: Nothing to be done for 'depend'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dcdisp'
depending in ./libsrc/include/dconvert...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dconvert'
make[3]: Nothing to be done for 'depend'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dconvert'
depending in ./libsrc/include/dctool...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dctool'
rm -rf transynu.h
gawk -f ../../.././libsrc/support/transyn.awk \
role=extern outname=transynu <../../.././libsrc/standard/transyn.tpl >transynu.h
rm -rf sopclu.h
gawk -f ../../.././libsrc/support/sopcl.awk \
role=extern outname=sopclu <../../.././libsrc/standard/sopcl.tpl >sopclu.h
rm -rf elmconst.h
gawk -f ../../.././libsrc/support/elmdict.awk \
role=constant outname=elmconst <../../.././libsrc/standard/elmdict.tpl >elmconst.h
rm -rf strvalc.h
gawk -f ../../.././libsrc/support/strval.awk \
role=declare outname=strvalc <../../.././libsrc/standard/strval.tpl >strvalc.h
rm -rf binvalc.h
gawk -f ../../.././libsrc/support/binval.awk \
role=declare outname=binvalc <../../.././libsrc/standard/binval.tpl >binvalc.h
rm -rf tagvalc.h
gawk -f ../../.././libsrc/support/tagval.awk \
role=declare outname=tagvalc <../../.././libsrc/standard/tagval.tpl >tagvalc.h
rm -rf condnc.h
gawk -f ../../.././libsrc/support/condn.awk \
role=declare outname=condnc <../../.././libsrc/standard/condn.tpl >condnc.h
rm -rf modulec.h
gawk -f ../../.././libsrc/support/module.awk \
role=declare outname=modulec <../../.././libsrc/standard/module.tpl >modulec.h
rm -rf iodcompc.h
gawk -f ../../.././libsrc/support/iodcomp.awk \
role=declare outname=iodcompc <../../.././libsrc/standard/iodcomp.tpl >iodcompc.h
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dctool'
depending in ./libsrc/include/generic...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/generic'
make[3]: Nothing to be done for 'depend'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/generic'
depending in ./libsrc/include/locale...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/locale'
make[3]: Nothing to be done for 'depend'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/locale'
depending in ./libsrc/include/ourdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/ourdisp'
make[3]: Nothing to be done for 'depend'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/ourdisp'
depending in ./libsrc/include/pixeldat...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/pixeldat'
make[3]: Nothing to be done for 'depend'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/pixeldat'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
depending in ./libsrc/lib...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/lib'
make[2]: Nothing to be done for 'depend'.
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/lib'
depending in ./libsrc/src...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
depending in ./libsrc/src/dcdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dcdisp'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- lutclass.cc lutextr.cc rdargb.cc rdcmyk.cc rdgray.cc rdhsv.cc rdimage.cc rdindex.cc rdrgb.cc usegray.cc useindex.cc usepal.cc usetrue.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dcdisp'
depending in ./libsrc/src/dctool...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dctool'
rm -rf transynt.h
gawk -f ../../.././libsrc/support/transyn.awk \
role=table outname=transynt <../../.././libsrc/standard/transyn.tpl >transynt.h
rm -rf transync.h
gawk -f ../../.././libsrc/support/transyn.awk \
role=constant outname=transync <../../.././libsrc/standard/transyn.tpl >transync.h
rm -rf sopclc.h
gawk -f ../../.././libsrc/support/sopcl.awk \
role=constant outname=sopclc <../../.././libsrc/standard/sopcl.tpl >sopclc.h
rm -rf sopclt.h
gawk -f ../../.././libsrc/support/sopcl.awk \
role=table outname=sopclt <../../.././libsrc/standard/sopcl.tpl >sopclt.h
rm -rf elmtable.h
gawk -f ../../.././libsrc/support/elmdict.awk \
role=table outname=elmtable <../../.././libsrc/standard/elmdict.tpl >elmtable.h
rm -rf strvald.h
gawk -f ../../.././libsrc/support/strval.awk \
role=define outname=strvald <../../.././libsrc/standard/strval.tpl >strvald.h
rm -rf binvald.h
gawk -f ../../.././libsrc/support/binval.awk \
role=define outname=binvald <../../.././libsrc/standard/binval.tpl >binvald.h
rm -rf tagvald.h
gawk -f ../../.././libsrc/support/tagval.awk \
role=define outname=tagvald <../../.././libsrc/standard/tagval.tpl >tagvald.h
rm -rf condnd.h
gawk -f ../../.././libsrc/support/condn.awk \
role=define outname=condnd <../../.././libsrc/standard/condn.tpl >condnd.h
rm -rf moduleb.h
gawk -f ../../.././libsrc/support/module.awk \
role=build outname=moduleb <../../.././libsrc/standard/module.tpl >moduleb.h
rm -rf modulev.h
gawk -f ../../.././libsrc/support/module.awk \
role=verify outname=modulev <../../.././libsrc/standard/module.tpl >modulev.h
rm -rf modulew.h
gawk -f ../../.././libsrc/support/module.awk \
role=write outname=modulew <../../.././libsrc/standard/module.tpl >modulew.h
rm -rf iodcompb.h
gawk -f ../../.././libsrc/support/iodcomp.awk \
role=build outname=iodcompb <../../.././libsrc/standard/iodcomp.tpl >iodcompb.h
rm -rf iodcompv.h
gawk -f ../../.././libsrc/support/iodcomp.awk \
role=verify outname=iodcompv <../../.././libsrc/standard/iodcomp.tpl >iodcompv.h
rm -rf iodcompw.h
gawk -f ../../.././libsrc/support/iodcomp.awk \
role=write outname=iodcompw <../../.././libsrc/standard/iodcomp.tpl >iodcompw.h
rm -rf iodcomps.h
gawk -f ../../.././libsrc/support/iodcomp.awk \
role=select outname=iodcomps <../../.././libsrc/standard/iodcomp.tpl >iodcomps.h
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- charset.cc transyn.cc transynd.cc transync.cc sopclc.cc sopcli.cc attr.cc attrtag.cc attrtypd.cc attrtyps.cc attrtypt.cc attrtypo.cc attrtypv.cc attrlist.cc attrlsln.cc attrothr.cc attrnew.cc attrseq.cc attrmxrd.cc attrmxvr.cc attrmxls.cc attrvrfy.cc elmdict.cc elmpriv.cc dcstream.cc uidgen.cc dcopti.cc dcopto.cc dcoptc.cc pixposn.cc strval.cc binval.cc tagval.cc condn.cc moduleb.cc modulev.cc modulew.cc iodcompb.cc iodcompv.cc iodcompw.cc iodcomps.cc dicomdir.cc ie.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dctool'
depending in ./libsrc/src/generic...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/generic'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- getoptns.cc datetype.cc bnopti.cc bnopto.cc ioopti.cc ioopto.cc txstream.cc version.cc platform.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/generic'
depending in ./libsrc/src/locale...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/locale'
gawk -f mesgtext.awk language=English < mesgtext.tpl >mesgttbl.h
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- mesgtext.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/locale'
depending in ./libsrc/src/ourdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/ourdisp'
../../.././support/xbmtocbm wlcursor.xbm wlcursor.cbm
../../.././support/xbmtocbm wlmask.xbm wlmask.cbm
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/ourdisp -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- ourdisp.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/ourdisp'
depending in ./libsrc/src/dconvert...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
depending in ./libsrc/src/dconvert/support...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/support'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- planea.cc plane.cc dateconv.cc
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/support'
depending in ./libsrc/src/dconvert/pace...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pace'
cp pace.h ../../../.././libsrc/include/dconvert/pace.h
rm -rf pacehdrp.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=PACE_ role=headerpart offsetwarning=off <pace.tpl >pacehdrp.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf pacehdrw.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=PACE_ role=wholeheader <pace.tpl >pacehdrw.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf pacehdrc.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=PACE_ role=constructheader <pace.tpl >pacehdrc.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf paceconv.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=PACE_ role=dicom <pace.tpl >paceconv.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf pacedmpf.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=PACE_ role=dump <pace.tpl >pacedmpf.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- pacedc.cc paceconv.cc pacempln.cc pacemmsc.cc pacemdt.cc pacedmp.cc pacedmpf.cc pacehdrc.cc pace.cc
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pace'
depending in ./libsrc/src/dconvert/xxxx...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/xxxx'
make[4]: Nothing to be done for 'depend'.
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/xxxx'
depending in ./libsrc/src/dconvert/imtn...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/imtn'
cp imtn.h ../../../.././libsrc/include/dconvert/imtn.h
rm -rf imtnhdrp.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=IMTN_ role=headerpart <imtn.tpl >imtnhdrp.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf imtnhdrw.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=IMTN_ role=wholeheader <imtn.tpl >imtnhdrw.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf imtnhdrc.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=IMTN_ role=constructheader <imtn.tpl >imtnhdrc.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf imtnconv.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=IMTN_ role=dicom <imtn.tpl >imtnconv.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf imtndmpf.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=IMTN_ role=dump <imtn.tpl >imtndmpf.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- imtndc.cc imtnconv.cc imtnmpln.cc imtnmmsc.cc imtnmdt.cc imtndmp.cc imtndmpf.cc imtnhdrc.cc imtn.cc
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/imtn'
depending in ./libsrc/src/dconvert/gen...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gen'
cp gen.h ../../../.././libsrc/include/dconvert/gen.h
cp geninfo.h ../../../.././libsrc/include/dconvert/geninfo.h
rm -rf genhdrp.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GEN_ role=headerpart offsetwarning=off <gen.tpl >genhdrp.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf genhdrw.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GEN_ role=wholeheader headerclassparameters=",GEN_FileStructureInformation &fileinfo" <gen.tpl >genhdrw.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf genhdrc.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GEN_ role=constructheader headerclassparameters=",GEN_FileStructureInformation &fileinfo" <gen.tpl >genhdrc.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf genconv.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GEN_ role=dicom <gen.tpl >genconv.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf gendmpf.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GEN_ role=dump <gen.tpl >gendmpf.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- gendc.cc genconv.cc genmpln.cc genmmsc.cc genmdt.cc gendmp.cc gendmpf.cc genhdrc.cc gen.cc
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gen'
depending in ./libsrc/src/dconvert/gaw...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gaw'
cp gaw.h ../../../.././libsrc/include/dconvert/gaw.h
cp gawinfo.h ../../../.././libsrc/include/dconvert/gawinfo.h
rm -rf gawhdrp.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GAW_ role=headerpart offsetwarning=off <gaw.tpl >gawhdrp.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf gawhdrw.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GAW_ role=wholeheader headerclassparameters=",GAW_FileStructureInformation &fileinfo" <gaw.tpl >gawhdrw.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf gawhdrc.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GAW_ role=constructheader headerclassparameters=",GAW_FileStructureInformation &fileinfo" <gaw.tpl >gawhdrc.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf gawconv.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GAW_ role=dicom <gaw.tpl >gawconv.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf gawdmpf.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GAW_ role=dump <gaw.tpl >gawdmpf.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- gawdc.cc gawconv.cc gawmpln.cc gawmmsc.cc gawmdt.cc gawdmp.cc gawdmpf.cc gawhdrc.cc gaw.cc
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gaw'
depending in ./libsrc/src/dconvert/shim...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/shim'
cp shim.h ../../../.././libsrc/include/dconvert/shim.h
rm -rf shimhdrp.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SHIM_ role=headerpart <shim.tpl >shimhdrp.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf shimhdrw.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SHIM_ role=wholeheader <shim.tpl >shimhdrw.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf shimhdrc.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SHIM_ role=constructheader <shim.tpl >shimhdrc.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf shimconv.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SHIM_ role=dicom <shim.tpl >shimconv.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf shimdmpf.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SHIM_ role=dump <shim.tpl >shimdmpf.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- shimdc.cc shimconv.cc shimmpln.cc shimmmsc.cc shimmdt.cc shimdmp.cc shimdmpf.cc shimhdrc.cc shim.cc
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/shim'
depending in ./libsrc/src/dconvert/somp...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/somp'
cp somp.h ../../../.././libsrc/include/dconvert/somp.h
rm -rf somphdrp.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SOMP_ role=headerpart <somp.tpl >somphdrp.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf somphdrw.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SOMP_ role=wholeheader <somp.tpl >somphdrw.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf somphdrc.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SOMP_ role=constructheader <somp.tpl >somphdrc.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf sompconv.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SOMP_ role=dicom <somp.tpl >sompconv.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf sompdmpf.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SOMP_ role=dump <somp.tpl >sompdmpf.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- sompdc.cc sompconv.cc sompmpln.cc sompmmsc.cc sompmdt.cc sompdmp.cc sompdmpf.cc somphdrc.cc somp.cc
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/somp'
depending in ./libsrc/src/dconvert/himr...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/himr'
cp himr.h ../../../.././libsrc/include/dconvert/himr.h
rm -rf himrhdrp.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=HIMR_ role=headerpart <himr.tpl >himrhdrp.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
Line 15: warning - offset 54 % size of type (4 bytes) not zero - possible alignment problem
Line 163: warning - offset 978 % size of type (4 bytes) not zero - possible alignment problem
rm -rf himrhdrw.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=HIMR_ role=wholeheader <himr.tpl >himrhdrw.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf himrhdrc.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=HIMR_ role=constructheader <himr.tpl >himrhdrc.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf himrconv.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=HIMR_ role=dicom <himr.tpl >himrconv.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf himrdmpf.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=HIMR_ role=dump <himr.tpl >himrdmpf.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- himrdc.cc himrconv.cc himrmpln.cc himrmmsc.cc himrmdt.cc himrdmp.cc himrdmpf.cc himrhdrc.cc himr.cc
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/himr'
depending in ./libsrc/src/dconvert/pq...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pq'
cp pq.h ../../../.././libsrc/include/dconvert/pq.h
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- pqdc.cc pqconv.cc pqmpln.cc pqmmsc.cc pqmdt.cc pqdmp.cc pqdmpf.cc pqhdrc.cc pq.cc
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pq'
depending in ./libsrc/src/dconvert/signa...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/signa'
cp signa.h ../../../.././libsrc/include/dconvert/signa.h
rm -rf sgnhdrp.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SGN_ role=headerpart offsetwarning=off <signa.tpl >sgnhdrp.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf sgnhdrw.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SGN_ role=wholeheader <signa.tpl >sgnhdrw.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf sgnhdrc.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SGN_ role=constructheader <signa.tpl >sgnhdrc.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf sgnconv.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SGN_ role=dicom <signa.tpl >sgnconv.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf sgndmpf.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=SGN_ role=dump <signa.tpl >sgndmpf.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- sgndc.cc sgnconv.cc sgnmpln.cc sgnmmsc.cc sgnmdt.cc sgndmp.cc sgndmpf.cc sgnhdrc.cc sgn.cc
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/signa'
depending in ./libsrc/src/dconvert/ge9800...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/ge9800'
cp ge9800.h ../../../.././libsrc/include/dconvert/ge9800.h
rm -rf ge9800hdrp.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GE9800_ role=headerpart <ge9800.tpl >ge9800hdrp.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
Line 168: warning - offset 234 % size of type (4 bytes) not zero - possible alignment problem
Line 169: warning - offset 238 % size of type (4 bytes) not zero - possible alignment problem
Line 178: warning - offset 254 % size of type (4 bytes) not zero - possible alignment problem
Line 179: warning - offset 258 % size of type (4 bytes) not zero - possible alignment problem
Line 201: warning - offset 286 % size of type (4 bytes) not zero - possible alignment problem
Line 202: warning - offset 290 % size of type (4 bytes) not zero - possible alignment problem
Line 203: warning - offset 294 % size of type (4 bytes) not zero - possible alignment problem
Line 204: warning - offset 298 % size of type (4 bytes) not zero - possible alignment problem
Line 205: warning - offset 302 % size of type (4 bytes) not zero - possible alignment problem
Line 232: warning - offset 430 % size of type (4 bytes) not zero - possible alignment problem
Line 319: warning - offset 142 % size of type (4 bytes) not zero - possible alignment problem
rm -rf ge9800hdrw.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GE9800_ role=wholeheader <ge9800.tpl >ge9800hdrw.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf ge9800hdrc.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GE9800_ role=constructheader <ge9800.tpl >ge9800hdrc.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf ge9800conv.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GE9800_ role=dicom <ge9800.tpl >ge9800conv.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
rm -rf ge9800dmpf.h
gawk -f ../../../.././libsrc/support/convert.awk \
prefix=GE9800_ role=dump <ge9800.tpl >ge9800dmpf.h
gawk: ../../../.././libsrc/support/convert.awk:517: warning: escape sequence `\'' treated as plain `''
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- ge9800dc.cc ge9800conv.cc ge9800mpln.cc ge9800mmsc.cc ge9800mdt.cc ge9800dmp.cc ge9800dmpf.cc ge9800hdrc.cc ge9800.cc
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/ge9800'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
depending in ./libsrc/support...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/support'
make[2]: Nothing to be done for 'depend'.
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/support'
depending in ./libsrc/docs...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/docs'
make[2]: Nothing to be done for 'depend'.
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/docs'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
depending in ./appsrc...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
depending in ./appsrc/acrnema...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/acrnema'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- ancreate.cc andump.cc ancp.cc
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/acrnema'
depending in ./appsrc/dcdisp...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcdisp'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dcdisp -I../.././libsrc/include/dctool -I../.././libsrc/include/ourdisp -I../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- dcdisp.cc
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcdisp'
depending in ./appsrc/dcfile...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcfile'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- dccreate.cc dcentvfy.cc dclutmix.cc dcuidchg.cc dcdtchg.cc dclutburn.cc dctopdf.cc pdftodc.cc pgxtodc.cc dcencap.cc dcburn.cc rawftodc.cc dccomb.cc dcuncat.cc dcsrmrg.cc dcostosr.cc dcrmmeta.cc dcsrdump.cc dccidump.cc dcdecmpr.cc dcsub.cc dcsort.cc dcproj.cc dcarith.cc dctopgm8.cc dctopgx.cc dcpost.cc dctable.cc dcmkpres.cc dcortho.cc antodc.cc dccp.cc dcdict.cc dcdirdmp.cc dcdump.cc dcfile.cc dchist.cc dckey.cc dcmerge.cc dcposn.cc dciodvfy.cc dcsmpte.cc dcbriggs.cc dcsqextr.cc dcstats.cc dctoraw.cc dctopnm.cc pbmtoovl.cc pnmtodc.cc rawtodc.cc dclutdmp.cc
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcfile'
depending in ./appsrc/dcintro...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcintro'
make[2]: Nothing to be done for 'depend'.
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcintro'
depending in ./appsrc/misc...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/misc'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- bmpdump.cc pgmtobmp.cc dumpwhat.cc binpatch.cc jpegdump.cc jpegsplit.cc pbmswbit.cc pnmpred.cc pnmtoraw.cc rawarith.cc rawdiff.cc rawmask.cc rawnjl.cc rawnjl2.cc dumptiff.cc
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/misc'
depending in ./appsrc/simple...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
depending in ./appsrc/simple/ge9800...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/ge9800'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- ge98topgm.cc ge98id.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/ge9800'
depending in ./appsrc/simple/genesis...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/genesis'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- gentopgm.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/genesis'
depending in ./appsrc/simple/pace...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/pace'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- pacetopgm.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/pace'
depending in ./appsrc/simple/signa...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/signa'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- sgntopgm.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/signa'
depending in ./appsrc/simple/somatom...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/somatom'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- somtopgm.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/somatom'
depending in ./appsrc/simple/sytec...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/sytec'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- syttopgm.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/sytec'
depending in ./appsrc/simple/vision...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/vision'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- vsntopgm.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/vision'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
depending in ./appsrc/dconvert...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
depending in ./appsrc/dconvert/support...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/support'
make[3]: Nothing to be done for 'depend'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/support'
depending in ./appsrc/dconvert/xxxx...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/xxxx'
make[3]: Nothing to be done for 'depend'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/xxxx'
depending in ./appsrc/dconvert/pace...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pace'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- pacedump.cc pacetodc.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pace'
depending in ./appsrc/dconvert/imtn...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/imtn'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- imtndump.cc imtntodc.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/imtn'
depending in ./appsrc/dconvert/gen...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gen'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- gendump.cc gentodc.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gen'
depending in ./appsrc/dconvert/gaw...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gaw'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- gawdump.cc gawtodc.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gaw'
depending in ./appsrc/dconvert/shim...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/shim'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- shimdump.cc shimtodc.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/shim'
depending in ./appsrc/dconvert/somp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/somp'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- sompdump.cc somptodc.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/somp'
depending in ./appsrc/dconvert/himr...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/himr'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- himrdump.cc himrtodc.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/himr'
depending in ./appsrc/dconvert/pq...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pq'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- pqdump.cc pqtodc.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pq'
depending in ./appsrc/dconvert/toshiba...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/toshiba'
make[3]: Nothing to be done for 'depend'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/toshiba'
depending in ./appsrc/dconvert/signa...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/signa'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- sgndump.cc sgntodc.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/signa'
depending in ./appsrc/dconvert/ge9800...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/ge9800'
/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos" "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include" -s "# DO NOT DELETE" --  -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   -- ge9800dump.cc ge9800todc.cc
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/ge9800'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
depending in ./support...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/support'
make[1]: Nothing to be done for 'depend'.
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/support'

dicom3tools/1.00-20240118131615: RUN: make -j8 IMAKE_DEFINES="'-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext'" IMAKE="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake" DEPEND="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend" MKDIRHIER="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/mkdirhier" INSTALL='/data/service/hnp/bin/busybox install' INSTPGMFLAGS=
make: jobserver mkfifo: /storage/Users/currentUser/GMfifo6040: Operation not permitted
making all in ./libsrc...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
make[1]: warning: -j8 forced in submake: resetting jobserver mode.
make[1]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6043: Operation not permitted
making all in ./libsrc/standard...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
make[2]: warning: -j8 forced in submake: resetting jobserver mode.
make[2]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6046: Operation not permitted
making all in ./libsrc/standard/elmdict...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/elmdict'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6049: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/elmdict'
making all in ./libsrc/standard/module...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/module'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6051: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/module'
making all in ./libsrc/standard/iodcomp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/iodcomp'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6053: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/iodcomp'
making all in ./libsrc/standard/strval...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/strval'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6056: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/strval'
rm -rf elmdict.xml
cat elmdict/dicom3.tpl elmdict/dicos.tpl elmdict/diconde.tpl | sort -b -k1,1n -k5,5n | gawk -f ../.././libsrc/support/elmtoxml.awk >elmdict.xml
gawk: ../.././libsrc/support/elmtoxml.awk:39: warning: escape sequence `\&' treated as plain `&'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
making all in ./libsrc/include...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
make[2]: warning: -j8 forced in submake: resetting jobserver mode.
make[2]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6068: Operation not permitted
making all in ./libsrc/include/dcdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dcdisp'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6071: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dcdisp'
making all in ./libsrc/include/dconvert...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dconvert'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6073: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dconvert'
making all in ./libsrc/include/dctool...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dctool'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6075: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dctool'
making all in ./libsrc/include/generic...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/generic'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6077: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/generic'
making all in ./libsrc/include/locale...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/locale'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6079: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/locale'
making all in ./libsrc/include/ourdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/ourdisp'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6081: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/ourdisp'
making all in ./libsrc/include/pixeldat...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/pixeldat'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6083: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/pixeldat'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
making all in ./libsrc/lib...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/lib'
make[2]: warning: -j8 forced in submake: resetting jobserver mode.
make[2]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6085: Operation not permitted
make[2]: Nothing to be done for 'all'.
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/lib'
making all in ./libsrc/src...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
make[2]: warning: -j8 forced in submake: resetting jobserver mode.
make[2]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6087: Operation not permitted
making all in ./libsrc/src/dcdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dcdisp'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6090: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   lutclass.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   lutextr.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rdargb.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rdcmyk.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rdgray.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rdhsv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rdimage.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rdindex.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rdrgb.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   usegray.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   useindex.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   usepal.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dcdisp -I../../.././libsrc/include/dctool -I../../.././libsrc/include/ourdisp -I../../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   usetrue.cc
rm -rf ../../.././libsrc/lib/libddply.a
ar rcv ../../.././libsrc/lib/libddply.a lutclass.o lutextr.o rdargb.o rdcmyk.o rdgray.o rdhsv.o rdimage.o rdindex.o rdrgb.o usegray.o useindex.o usepal.o usetrue.o
a - lutclass.o
a - lutextr.o
a - rdargb.o
a - rdcmyk.o
a - rdgray.o
a - rdhsv.o
a - rdimage.o
a - rdindex.o
a - rdrgb.o
a - usegray.o
a - useindex.o
a - usepal.o
a - usetrue.o
true ../../.././libsrc/lib/libddply.a lutclass.o lutextr.o rdargb.o rdcmyk.o rdgray.o rdhsv.o rdimage.o rdindex.o rdrgb.o usegray.o useindex.o usepal.o usetrue.o
ranlib ../../.././libsrc/lib/libddply.a
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dcdisp'
making all in ./libsrc/src/dctool...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dctool'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo6167: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   charset.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   transyn.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   transynd.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   transync.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sopclc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sopcli.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attr.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrtag.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrtypd.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrtyps.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrtypt.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrtypo.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrtypv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrlist.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrlsln.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrothr.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrnew.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrseq.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrmxrd.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrmxvr.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrmxls.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   attrvrfy.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   elmdict.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   elmpriv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcstream.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   uidgen.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcopti.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcopto.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcoptc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pixposn.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   strval.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   binval.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   tagval.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   condn.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   moduleb.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   modulev.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   modulew.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   iodcompb.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   iodcompv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   iodcompw.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   iodcomps.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dicomdir.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ie.cc
rm -rf ../../.././libsrc/lib/libdctl.a
ar rcv ../../.././libsrc/lib/libdctl.a charset.o transyn.o transynd.o transync.o sopclc.o sopcli.o attr.o attrtag.o attrtypd.o attrtyps.o attrtypt.o attrtypo.o attrtypv.o attrlist.o attrlsln.o attrothr.o attrnew.o attrseq.o attrmxrd.o attrmxvr.o attrmxls.o attrvrfy.o elmdict.o elmpriv.o dcstream.o uidgen.o dcopti.o dcopto.o dcoptc.o pixposn.o strval.o binval.o tagval.o condn.o moduleb.o modulev.o modulew.o iodcompb.o iodcompv.o iodcompw.o iodcomps.o dicomdir.o ie.o
a - charset.o
a - transyn.o
a - transynd.o
a - transync.o
a - sopclc.o
a - sopcli.o
a - attr.o
a - attrtag.o
a - attrtypd.o
a - attrtyps.o
a - attrtypt.o
a - attrtypo.o
a - attrtypv.o
a - attrlist.o
a - attrlsln.o
a - attrothr.o
a - attrnew.o
a - attrseq.o
a - attrmxrd.o
a - attrmxvr.o
a - attrmxls.o
a - attrvrfy.o
a - elmdict.o
a - elmpriv.o
a - dcstream.o
a - uidgen.o
a - dcopti.o
a - dcopto.o
a - dcoptc.o
a - pixposn.o
a - strval.o
a - binval.o
a - tagval.o
a - condn.o
a - moduleb.o
a - modulev.o
a - modulew.o
a - iodcompb.o
a - iodcompv.o
a - iodcompw.o
a - iodcomps.o
a - dicomdir.o
a - ie.o
true ../../.././libsrc/lib/libdctl.a charset.o transyn.o transynd.o transync.o sopclc.o sopcli.o attr.o attrtag.o attrtypd.o attrtyps.o attrtypt.o attrtypo.o attrtypv.o attrlist.o attrlsln.o attrothr.o attrnew.o attrseq.o attrmxrd.o attrmxvr.o attrmxls.o attrvrfy.o elmdict.o elmpriv.o dcstream.o uidgen.o dcopti.o dcopto.o dcoptc.o pixposn.o strval.o binval.o tagval.o condn.o moduleb.o modulev.o modulew.o iodcompb.o iodcompv.o iodcompw.o iodcomps.o dicomdir.o ie.o
ranlib ../../.././libsrc/lib/libdctl.a
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dctool'
making all in ./libsrc/src/generic...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/generic'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo11522: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   getoptns.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   datetype.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   bnopti.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   bnopto.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ioopti.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ioopto.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   txstream.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   version.cc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   platform.cc
rm -rf ../../.././libsrc/lib/libgener.a
ar rcv ../../.././libsrc/lib/libgener.a getoptns.o datetype.o bnopti.o bnopto.o ioopti.o ioopto.o txstream.o version.o platform.o
a - getoptns.o
a - datetype.o
a - bnopti.o
a - bnopto.o
a - ioopti.o
a - ioopto.o
a - txstream.o
a - version.o
a - platform.o
true ../../.././libsrc/lib/libgener.a getoptns.o datetype.o bnopti.o bnopto.o ioopti.o ioopto.o txstream.o version.o platform.o
ranlib ../../.././libsrc/lib/libgener.a
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/generic'
making all in ./libsrc/src/locale...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/locale'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo11691: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   mesgtext.cc
rm -rf ../../.././libsrc/lib/libdlcl.a
ar rcv ../../.././libsrc/lib/libdlcl.a mesgtext.o
a - mesgtext.o
true ../../.././libsrc/lib/libdlcl.a mesgtext.o
ranlib ../../.././libsrc/lib/libdlcl.a
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/locale'
making all in ./libsrc/src/ourdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/ourdisp'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo11818: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/ourdisp -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ourdisp.cc
ourdisp.cc:789:27: warning: implicit conversion from 'long' to 'double' changes value from 9223372036854775807 to 9223372036854775808 [-Wimplicit-const-int-float-conversion]
        Assert(rescaleintercept<=LONG_MAX);
                               ~~^~~~~~~~
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include/limits.h:47:19: note: expanded from macro 'LONG_MAX'
#define LONG_MAX  __LONG_MAX__
                  ^~~~~~~~~~~~
<built-in>:84:22: note: expanded from here
#define __LONG_MAX__ 9223372036854775807L
                     ^~~~~~~~~~~~~~~~~~~~
../../.././libsrc/include/generic/basetype.h:77:29: note: expanded from macro 'Assert'
#define Assert(expr)    assert(expr)    // In case we get more creative later !
                               ^~~~
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/assert.h:8:28: note: expanded from macro 'assert'
#define assert(x) ((void)((x) || (__assert_fail(#x, __FILE__, __LINE__, __func__),0)))
                           ^
1 warning generated.
rm -rf ../../.././libsrc/lib/libodply.a
ar rcv ../../.././libsrc/lib/libodply.a ourdisp.o
a - ourdisp.o
true ../../.././libsrc/lib/libodply.a ourdisp.o
ranlib ../../.././libsrc/lib/libodply.a
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/ourdisp'
making all in ./libsrc/src/dconvert...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo12017: Operation not permitted
making all in ./libsrc/src/dconvert/support...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/support'
make[4]: warning: -j8 forced in submake: resetting jobserver mode.
make[4]: jobserver mkfifo: /storage/Users/currentUser/GMfifo12022: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   planea.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   plane.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dateconv.cc
rm -rf ../../../.././libsrc/lib/libdconv.a
ar rcv ../../../.././libsrc/lib/libdconv.a planea.o plane.o dateconv.o
a - planea.o
a - plane.o
a - dateconv.o
true ../../../.././libsrc/lib/libdconv.a planea.o plane.o dateconv.o
ranlib ../../../.././libsrc/lib/libdconv.a
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/support'
making all in ./libsrc/src/dconvert/pace...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pace'
make[4]: warning: -j8 forced in submake: resetting jobserver mode.
make[4]: jobserver mkfifo: /storage/Users/currentUser/GMfifo12217: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pacedc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   paceconv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pacempln.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pacemmsc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pacemdt.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pacedmp.cc
/data/service/hnp/bin/clang++ -c    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pacedmpf.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pacehdrc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pace.cc
pacempln.cc:40:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="HF";
                             ^
pacempln.cc:44:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="FF";
                             ^
pacempln.cc:48:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="";                // :(
                             ^
pacempln.cc:57:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="P";
                           ^
pacempln.cc:61:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="S";
                           ^
pacempln.cc:65:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="DL";
                           ^
pacempln.cc:69:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="DR";
                           ^
pacempln.cc:73:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="";                  // :(
                           ^
pacempln.cc:112:10: warning: 5 enumeration values not handled in switch: 'AxialLP', 'AxialRP', 'SagittalPF'... [-Wswitch]
        switch (plane) {
                ^~~~~
pacempln.cc:273:10: warning: 5 enumeration values not handled in switch: 'AxialLP', 'AxialRP', 'SagittalPF'... [-Wswitch]
        switch (plane) {
                ^~~~~
10 warnings generated.
rm -rf ../../../.././libsrc/lib/libdpace.a
ar rcv ../../../.././libsrc/lib/libdpace.a pacedc.o paceconv.o pacempln.o pacemmsc.o pacemdt.o pacedmp.o pacedmpf.o pacehdrc.o pace.o
a - pacedc.o
a - paceconv.o
a - pacempln.o
a - pacemmsc.o
a - pacemdt.o
a - pacedmp.o
a - pacedmpf.o
a - pacehdrc.o
a - pace.o
true ../../../.././libsrc/lib/libdpace.a pacedc.o paceconv.o pacempln.o pacemmsc.o pacemdt.o pacedmp.o pacedmpf.o pacehdrc.o pace.o
ranlib ../../../.././libsrc/lib/libdpace.a
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pace'
making all in ./libsrc/src/dconvert/xxxx...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/xxxx'
make[4]: warning: -j8 forced in submake: resetting jobserver mode.
make[4]: jobserver mkfifo: /storage/Users/currentUser/GMfifo12467: Operation not permitted
make[4]: Nothing to be done for 'all'.
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/xxxx'
making all in ./libsrc/src/dconvert/imtn...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/imtn'
make[4]: warning: -j8 forced in submake: resetting jobserver mode.
make[4]: jobserver mkfifo: /storage/Users/currentUser/GMfifo12471: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   imtndc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   imtnconv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   imtnmpln.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   imtnmmsc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   imtnmdt.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   imtndmp.cc
/data/service/hnp/bin/clang++ -c    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   imtndmpf.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   imtnhdrc.cc
imtnhdrc.cc:95:35: warning: address of array 'ptr->itemname' will always evaluate to 'true' [-Wpointer-bool-conversion]
        while (i<nEntries && ptr && ptr->itemname && strcmp(ptr->itemname,index) != 0) { ++i; ++ptr; }
                                 ~~ ~~~~~^~~~~~~~
imtnhdrc.cc:301:35: warning: address of array 'ptr->itemname' will always evaluate to 'true' [-Wpointer-bool-conversion]
        while (i<nEntries && ptr && ptr->itemname && strcmp(ptr->itemname,index) != 0) { ++i; ++ptr; }
                                 ~~ ~~~~~^~~~~~~~
imtnmpln.cc:81:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="S";
                           ^
imtnmpln.cc:83:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="FF";
                             ^
imtnmpln.cc:88:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="P";
                           ^
imtnmpln.cc:90:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="FF";
                             ^
imtnmpln.cc:95:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="DR";
                           ^
imtnmpln.cc:97:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="FF";
                             ^
imtnmpln.cc:102:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="DL";
                           ^
imtnmpln.cc:104:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="FF";
                             ^
imtnmpln.cc:109:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="S";
                           ^
imtnmpln.cc:111:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="FF";
                             ^
imtnmpln.cc:116:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="P";
                           ^
imtnmpln.cc:118:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="FF";
                             ^
imtnmpln.cc:123:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="DR";
                           ^
imtnmpln.cc:125:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="FF";
                             ^
imtnmpln.cc:130:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="DL";
                           ^
imtnmpln.cc:132:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="FF";
                             ^
imtnmpln.cc:136:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="S";
                           ^
imtnmpln.cc:138:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="HF";
                             ^
imtnmpln.cc:143:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="P";
                           ^
imtnmpln.cc:145:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="HF";
                             ^
imtnmpln.cc:150:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="DR";
                           ^
imtnmpln.cc:152:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="HF";
                             ^
imtnmpln.cc:157:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="DL";
                           ^
imtnmpln.cc:159:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="HF";
                             ^
imtnmpln.cc:164:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="P";
                           ^
imtnmpln.cc:166:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="HF";
                             ^
imtnmpln.cc:171:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="S";
                           ^
imtnmpln.cc:173:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="HF";
                             ^
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   imtn.cc
2 warnings generated.
28 warnings generated.
rm -rf ../../../.././libsrc/lib/libdimtn.a
ar rcv ../../../.././libsrc/lib/libdimtn.a imtndc.o imtnconv.o imtnmpln.o imtnmmsc.o imtnmdt.o imtndmp.o imtndmpf.o imtnhdrc.o imtn.o
a - imtndc.o
a - imtnconv.o
a - imtnmpln.o
a - imtnmmsc.o
a - imtnmdt.o
a - imtndmp.o
a - imtndmpf.o
a - imtnhdrc.o
a - imtn.o
true ../../../.././libsrc/lib/libdimtn.a imtndc.o imtnconv.o imtnmpln.o imtnmmsc.o imtnmdt.o imtndmp.o imtndmpf.o imtnhdrc.o imtn.o
ranlib ../../../.././libsrc/lib/libdimtn.a
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/imtn'
making all in ./libsrc/src/dconvert/gen...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gen'
make[4]: warning: -j8 forced in submake: resetting jobserver mode.
make[4]: jobserver mkfifo: /storage/Users/currentUser/GMfifo12749: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gendc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   genconv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   genmpln.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   genmmsc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   genmdt.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gendmp.cc
/data/service/hnp/bin/clang++ -c    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gendmpf.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   genhdrc.cc
genmpln.cc:19:10: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                hfff="HF";
                                     ^
genmpln.cc:23:10: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                hfff="FF";
                                     ^
genmpln.cc:26:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                default:        hfff="UNKNOWN";         // :(
                                     ^
genmpln.cc:35:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="S";
                                   ^
genmpln.cc:39:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="P";
                                   ^
genmpln.cc:43:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="DL";
                                   ^
genmpln.cc:47:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="DR";
                                   ^
genmpln.cc:50:15: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                default:        ap="UNKNOWN";           // :(
                                   ^
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gen.cc
8 warnings generated.
rm -rf ../../../.././libsrc/lib/libdgen.a
ar rcv ../../../.././libsrc/lib/libdgen.a gendc.o genconv.o genmpln.o genmmsc.o genmdt.o gendmp.o gendmpf.o genhdrc.o gen.o
a - gendc.o
a - genconv.o
a - genmpln.o
a - genmmsc.o
a - genmdt.o
a - gendmp.o
a - gendmpf.o
a - genhdrc.o
a - gen.o
true ../../../.././libsrc/lib/libdgen.a gendc.o genconv.o genmpln.o genmmsc.o genmdt.o gendmp.o gendmpf.o genhdrc.o gen.o
ranlib ../../../.././libsrc/lib/libdgen.a
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gen'
making all in ./libsrc/src/dconvert/gaw...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gaw'
make[4]: warning: -j8 forced in submake: resetting jobserver mode.
make[4]: jobserver mkfifo: /storage/Users/currentUser/GMfifo13092: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gawdc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gawconv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gawmpln.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gawmmsc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gawmdt.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gawdmp.cc
/data/service/hnp/bin/clang++ -c    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gawdmpf.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gawhdrc.cc
gawmpln.cc:19:10: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                hfff="HF";
                                     ^
gawmpln.cc:23:10: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                hfff="FF";
                                     ^
gawmpln.cc:26:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                default:        hfff="UNKNOWN";         // :(
                                     ^
gawmpln.cc:35:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="S";
                                   ^
gawmpln.cc:39:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="P";
                                   ^
gawmpln.cc:43:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="DL";
                                   ^
gawmpln.cc:47:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="DR";
                                   ^
gawmpln.cc:50:15: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                default:        ap="UNKNOWN";           // :(
                                   ^
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gaw.cc
8 warnings generated.
rm -rf ../../../.././libsrc/lib/libdgaw.a
ar rcv ../../../.././libsrc/lib/libdgaw.a gawdc.o gawconv.o gawmpln.o gawmmsc.o gawmdt.o gawdmp.o gawdmpf.o gawhdrc.o gaw.o
a - gawdc.o
a - gawconv.o
a - gawmpln.o
a - gawmmsc.o
a - gawmdt.o
a - gawdmp.o
a - gawdmpf.o
a - gawhdrc.o
a - gaw.o
true ../../../.././libsrc/lib/libdgaw.a gawdc.o gawconv.o gawmpln.o gawmmsc.o gawmdt.o gawdmp.o gawdmpf.o gawhdrc.o gaw.o
ranlib ../../../.././libsrc/lib/libdgaw.a
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gaw'
making all in ./libsrc/src/dconvert/shim...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/shim'
make[4]: warning: -j8 forced in submake: resetting jobserver mode.
make[4]: jobserver mkfifo: /storage/Users/currentUser/GMfifo13552: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   shimdc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   shimconv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   shimmpln.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   shimmmsc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   shimmdt.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   shimdmp.cc
/data/service/hnp/bin/clang++ -c    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   shimdmpf.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   shimhdrc.cc
shimhdrc.cc:95:35: warning: address of array 'ptr->itemname' will always evaluate to 'true' [-Wpointer-bool-conversion]
        while (i<nEntries && ptr && ptr->itemname && strcmp(ptr->itemname,index) != 0) { ++i; ++ptr; }
                                 ~~ ~~~~~^~~~~~~~
shimhdrc.cc:301:35: warning: address of array 'ptr->itemname' will always evaluate to 'true' [-Wpointer-bool-conversion]
        while (i<nEntries && ptr && ptr->itemname && strcmp(ptr->itemname,index) != 0) { ++i; ++ptr; }
                                 ~~ ~~~~~^~~~~~~~
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   shim.cc
2 warnings generated.
rm -rf ../../../.././libsrc/lib/libdshim.a
ar rcv ../../../.././libsrc/lib/libdshim.a shimdc.o shimconv.o shimmpln.o shimmmsc.o shimmdt.o shimdmp.o shimdmpf.o shimhdrc.o shim.o
a - shimdc.o
a - shimconv.o
a - shimmpln.o
a - shimmmsc.o
a - shimmdt.o
a - shimdmp.o
a - shimdmpf.o
a - shimhdrc.o
a - shim.o
true ../../../.././libsrc/lib/libdshim.a shimdc.o shimconv.o shimmpln.o shimmmsc.o shimmdt.o shimdmp.o shimdmpf.o shimhdrc.o shim.o
ranlib ../../../.././libsrc/lib/libdshim.a
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/shim'
making all in ./libsrc/src/dconvert/somp...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/somp'
make[4]: warning: -j8 forced in submake: resetting jobserver mode.
make[4]: jobserver mkfifo: /storage/Users/currentUser/GMfifo13858: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sompdc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sompconv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sompmpln.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sompmmsc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sompmdt.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sompdmp.cc
/data/service/hnp/bin/clang++ -c    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sompdmpf.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   somphdrc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   somp.cc
rm -rf ../../../.././libsrc/lib/libdsomp.a
ar rcv ../../../.././libsrc/lib/libdsomp.a sompdc.o sompconv.o sompmpln.o sompmmsc.o sompmdt.o sompdmp.o sompdmpf.o somphdrc.o somp.o
a - sompdc.o
a - sompconv.o
a - sompmpln.o
a - sompmmsc.o
a - sompmdt.o
a - sompdmp.o
a - sompdmpf.o
a - somphdrc.o
a - somp.o
true ../../../.././libsrc/lib/libdsomp.a sompdc.o sompconv.o sompmpln.o sompmmsc.o sompmdt.o sompdmp.o sompdmpf.o somphdrc.o somp.o
ranlib ../../../.././libsrc/lib/libdsomp.a
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/somp'
making all in ./libsrc/src/dconvert/himr...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/himr'
make[4]: warning: -j8 forced in submake: resetting jobserver mode.
make[4]: jobserver mkfifo: /storage/Users/currentUser/GMfifo14166: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   himrdc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   himrconv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   himrmpln.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   himrmmsc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   himrmdt.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   himrdmp.cc
/data/service/hnp/bin/clang++ -c    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   himrdmpf.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   himrhdrc.cc
himrmmsc.cc:31:10: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                value1="ORIGINAL";
                       ^
himrmmsc.cc:33:10: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                value2="PRIMARY";
                       ^
himrmmsc.cc:35:10: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                value3="MPR";
                       ^
himrmpln.cc:38:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="HF";
                             ^
himrmpln.cc:42:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="FF";
                             ^
himrmpln.cc:46:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        hfff="";                // :(
                             ^
himrmpln.cc:55:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="P";
                           ^
himrmpln.cc:59:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="S";
                           ^
himrmpln.cc:63:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="DL";
                           ^
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   himr.cc
himrmpln.cc:67:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="DR";
                           ^
himrmpln.cc:71:7: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        ap="";                  // :(
                           ^
himrmpln.cc:97:10: warning: 5 enumeration values not handled in switch: 'AxialLP', 'AxialRP', 'SagittalPF'... [-Wswitch]
        switch (plane) {
                ^~~~~
3 warnings generated.
9 warnings generated.
rm -rf ../../../.././libsrc/lib/libdhimr.a
ar rcv ../../../.././libsrc/lib/libdhimr.a himrdc.o himrconv.o himrmpln.o himrmmsc.o himrmdt.o himrdmp.o himrdmpf.o himrhdrc.o himr.o
a - himrdc.o
a - himrconv.o
a - himrmpln.o
a - himrmmsc.o
a - himrmdt.o
a - himrdmp.o
a - himrdmpf.o
a - himrhdrc.o
a - himr.o
true ../../../.././libsrc/lib/libdhimr.a himrdc.o himrconv.o himrmpln.o himrmmsc.o himrmdt.o himrdmp.o himrdmpf.o himrhdrc.o himr.o
ranlib ../../../.././libsrc/lib/libdhimr.a
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/himr'
making all in ./libsrc/src/dconvert/pq...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pq'
make[4]: warning: -j8 forced in submake: resetting jobserver mode.
make[4]: jobserver mkfifo: /storage/Users/currentUser/GMfifo14290: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pqdc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pqconv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pqmpln.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pqmmsc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pqmdt.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pqdmp.cc
/data/service/hnp/bin/clang++ -c    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pqdmpf.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pqhdrc.cc
In file included from pqhdrc.cc:6:
./pqhdrc.h:230:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 0: vtype_label="asc"; break;
                                            ^
./pqhdrc.h:231:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 1: vtype_label="int"; break;
                                            ^
./pqhdrc.h:232:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 2: vtype_label="dat"; break;
                                            ^
./pqhdrc.h:233:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 3: vtype_label="tim"; break;
                                            ^
./pqhdrc.h:234:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 4: vtype_label="fil"; break;
                                            ^
./pqhdrc.h:235:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 5: vtype_label="flg"; break;
                                            ^
./pqhdrc.h:236:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 6: vtype_label="flt"; break;
                                            ^
./pqhdrc.h:238:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                vtype_label="???"; break;
                                            ^
In file included from pqdmpf.cc:4:
./pqdmpf.h:313:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 0: vtype_label="asc"; break;
                                            ^
./pqdmpf.h:314:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 1: vtype_label="int"; break;
                                            ^
./pqdmpf.h:315:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 2: vtype_label="dat"; break;
                                            ^
./pqdmpf.h:316:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 3: vtype_label="tim"; break;
                                            ^
./pqdmpf.h:317:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 4: vtype_label="fil"; break;
                                            ^
./pqdmpf.h:318:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 5: vtype_label="flg"; break;
                                            ^
./pqdmpf.h:319:24: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 6: vtype_label="flt"; break;
                                            ^
./pqdmpf.h:321:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                vtype_label="???"; break;
                                            ^
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pq.cc
pqmpln.cc:16:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                hfff="";                // default :(
                     ^
pqmpln.cc:23:10: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                hfff="HF";
                                     ^
pqmpln.cc:27:10: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                hfff="FF";
                                     ^
pqmpln.cc:37:6: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                ap="";                  // default :(
                   ^
pqmpln.cc:44:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="S";
                                   ^
pqmpln.cc:48:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="P";
                                   ^
8 warnings generated.
8 warnings generated.
6 warnings generated.
rm -rf ../../../.././libsrc/lib/libdpq.a
ar rcv ../../../.././libsrc/lib/libdpq.a pqdc.o pqconv.o pqmpln.o pqmmsc.o pqmdt.o pqdmp.o pqdmpf.o pqhdrc.o pq.o
a - pqdc.o
a - pqconv.o
a - pqmpln.o
a - pqmmsc.o
a - pqmdt.o
a - pqdmp.o
a - pqdmpf.o
a - pqhdrc.o
a - pq.o
true ../../../.././libsrc/lib/libdpq.a pqdc.o pqconv.o pqmpln.o pqmmsc.o pqmdt.o pqdmp.o pqdmpf.o pqhdrc.o pq.o
ranlib ../../../.././libsrc/lib/libdpq.a
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pq'
making all in ./libsrc/src/dconvert/signa...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/signa'
make[4]: warning: -j8 forced in submake: resetting jobserver mode.
make[4]: jobserver mkfifo: /storage/Users/currentUser/GMfifo14423: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sgndc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sgnconv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sgnmpln.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sgnmmsc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sgnmdt.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sgndmp.cc
/data/service/hnp/bin/clang++ -c    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sgndmpf.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sgnhdrc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sgn.cc
sgnmpln.cc:19:10: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                hfff="HF";
                                     ^
sgnmpln.cc:23:10: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                hfff="FF";
                                     ^
sgnmpln.cc:26:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                default:        hfff="UNKNOWN";         // :(
                                     ^
sgnmpln.cc:35:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="S";
                                   ^
sgnmpln.cc:39:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="P";
                                   ^
sgnmpln.cc:43:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="DL";
                                   ^
sgnmpln.cc:47:8: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                ap="DR";
                                   ^
sgnmpln.cc:50:15: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                default:        ap="UNKNOWN";           // :(
                                   ^
8 warnings generated.
rm -rf ../../../.././libsrc/lib/libdsgn.a
ar rcv ../../../.././libsrc/lib/libdsgn.a sgndc.o sgnconv.o sgnmpln.o sgnmmsc.o sgnmdt.o sgndmp.o sgndmpf.o sgnhdrc.o sgn.o
a - sgndc.o
a - sgnconv.o
a - sgnmpln.o
a - sgnmmsc.o
a - sgnmdt.o
a - sgndmp.o
a - sgndmpf.o
a - sgnhdrc.o
a - sgn.o
true ../../../.././libsrc/lib/libdsgn.a sgndc.o sgnconv.o sgnmpln.o sgnmmsc.o sgnmdt.o sgndmp.o sgndmpf.o sgnhdrc.o sgn.o
ranlib ../../../.././libsrc/lib/libdsgn.a
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/signa'
making all in ./libsrc/src/dconvert/ge9800...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/ge9800'
make[4]: warning: -j8 forced in submake: resetting jobserver mode.
make[4]: jobserver mkfifo: /storage/Users/currentUser/GMfifo14498: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ge9800dc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ge9800conv.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ge9800mpln.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ge9800mmsc.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ge9800mdt.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ge9800dmp.cc
/data/service/hnp/bin/clang++ -c    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ge9800dmpf.cc
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ge9800hdrc.cc
ge9800mpln.cc:57:11: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        hfff="HF";
                                             ^
ge9800mpln.cc:61:11: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        hfff="FF";
                                             ^
ge9800mpln.cc:64:18: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        default:        hfff="";                // :(
                                             ^
ge9800mpln.cc:73:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        ap="P";
                                           ^
ge9800mpln.cc:77:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        ap="S";
                                           ^
ge9800mpln.cc:81:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        ap="DL";
                                           ^
ge9800mpln.cc:85:9: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        ap="DR";
                                           ^
ge9800mpln.cc:88:16: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        default:        ap="";                  // :(
                                           ^
ge9800mmsc.cc:63:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value1="ORIGINAL";
                                               ^
ge9800mmsc.cc:64:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value2="PRIMARY";
                                               ^
ge9800mmsc.cc:65:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value3="AXIAL";
                                               ^
ge9800mmsc.cc:68:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value1="ORIGINAL";
                                               ^
ge9800mmsc.cc:69:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value2="PRIMARY";
                                               ^
ge9800mmsc.cc:70:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value3="LOCALIZER";
                                               ^
ge9800mmsc.cc:73:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value1="DERIVED";
                                               ^
ge9800mmsc.cc:74:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value2="SECONDARY";
                                               ^
ge9800mmsc.cc:75:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value3="AXIAL";
                                               ^
ge9800mmsc.cc:78:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value1="DERIVED";
                                               ^
ge9800mmsc.cc:79:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value2="SECONDARY";
                                               ^
ge9800mmsc.cc:80:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value3="AXIAL";
                                               ^
ge9800mmsc.cc:83:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value1="DERIVED";
                                               ^
ge9800mmsc.cc:84:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value2="SECONDARY";
                                               ^
ge9800mmsc.cc:85:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value3="AXIAL";
                                               ^
ge9800mmsc.cc:88:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value1="DERIVED";
                                               ^
ge9800mmsc.cc:89:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value2="SECONDARY";
                                               ^
ge9800mmsc.cc:90:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value3="OTHER";
                                               ^
ge9800mmsc.cc:93:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value1="";
                                               ^
ge9800mmsc.cc:94:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value2="";
                                               ^
ge9800mmsc.cc:95:13: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        value3="";
                                               ^
ge9800mmsc.cc:109:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 0:         str="UNDEFINED";
                                            ^
ge9800mmsc.cc:111:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 1:         str="BONE";
                                            ^
ge9800mmsc.cc:113:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 2:         str="SOFTTISSUE";
                                            ^
ge9800mmsc.cc:115:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 3:         str="QUICKSOFTTISSUE";
                                            ^
ge9800mmsc.cc:117:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        default:        str="";
                                            ^
ge9800mmsc.cc:129:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 1:         str="BODY"; break;
                                            ^
ge9800mmsc.cc:130:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 2:         str="HEAD"; break;
                                            ^
ge9800mmsc.cc:131:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 3:         str="A"; break;
                                            ^
ge9800mmsc.cc:132:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        default:        str=""; break;
                                            ^
ge9800mmsc.cc:141:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 1:         str="CW"; break;
                                            ^
ge9800mmsc.cc:142:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 2:         str="CC"; break;
                                            ^
ge9800mmsc.cc:143:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        default:        str=""; break;
                                            ^
ge9800mmsc.cc:161:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 1:         str="WHOLEBODY"; break;
                                            ^
ge9800mmsc.cc:162:17: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                        case 2:         str="HEAD"; break;
                                            ^
/data/service/hnp/bin/clang++ -c -O    -I../../../.././libsrc/include/generic -I../../../.././libsrc/include/locale -I../../../.././libsrc/include/dctool -I../../../.././libsrc/include/pixeldat -I../../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ge9800.cc
8 warnings generated.
35 warnings generated.
rm -rf ../../../.././libsrc/lib/libdge9800.a
ar rcv ../../../.././libsrc/lib/libdge9800.a ge9800dc.o ge9800conv.o ge9800mpln.o ge9800mmsc.o ge9800mdt.o ge9800dmp.o ge9800dmpf.o ge9800hdrc.o ge9800.o
a - ge9800dc.o
a - ge9800conv.o
a - ge9800mpln.o
a - ge9800mmsc.o
a - ge9800mdt.o
a - ge9800dmp.o
a - ge9800dmpf.o
a - ge9800hdrc.o
a - ge9800.o
true ../../../.././libsrc/lib/libdge9800.a ge9800dc.o ge9800conv.o ge9800mpln.o ge9800mmsc.o ge9800mdt.o ge9800dmp.o ge9800dmpf.o ge9800hdrc.o ge9800.o
ranlib ../../../.././libsrc/lib/libdge9800.a
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/ge9800'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
making all in ./libsrc/support...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/support'
make[2]: warning: -j8 forced in submake: resetting jobserver mode.
make[2]: jobserver mkfifo: /storage/Users/currentUser/GMfifo14599: Operation not permitted
make[2]: Nothing to be done for 'all'.
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/support'
making all in ./libsrc/docs...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/docs'
make[2]: warning: -j8 forced in submake: resetting jobserver mode.
make[2]: jobserver mkfifo: /storage/Users/currentUser/GMfifo14602: Operation not permitted
gawk -f ../support/modtype.awk <../standard/module.tpl | sort -b -k2,2 -k1,1 >modtype.txt
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/docs'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
making all in ./appsrc...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
make[1]: warning: -j8 forced in submake: resetting jobserver mode.
make[1]: jobserver mkfifo: /storage/Users/currentUser/GMfifo14612: Operation not permitted
making all in ./appsrc/acrnema...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/acrnema'
make[2]: warning: -j8 forced in submake: resetting jobserver mode.
make[2]: jobserver mkfifo: /storage/Users/currentUser/GMfifo14615: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ancreate.cc
ancreate.cc:628:16: warning: using the result of an assignment as a condition without parentheses [-Wparentheses]
        while (command=getCommand(cin)) {
               ~~~~~~~^~~~~~~~~~~~~~~~
ancreate.cc:628:16: note: place parentheses around the assignment to silence this warning
        while (command=getCommand(cin)) {
                      ^
               (                      )
ancreate.cc:628:16: note: use '==' to turn this assignment into an equality comparison
        while (command=getCommand(cin)) {
                      ^
                      ==
1 warning generated.
rm -rf ancreate
/data/service/hnp/bin/clang++ -o ancreate ancreate.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true ancreate
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   andump.cc
rm -rf andump
/data/service/hnp/bin/clang++ -o andump andump.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true andump
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ancp.cc
rm -rf ancp
/data/service/hnp/bin/clang++ -o ancp ancp.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true ancp
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/acrnema'
making all in ./appsrc/dcdisp...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcdisp'
make[2]: warning: -j8 forced in submake: resetting jobserver mode.
make[2]: jobserver mkfifo: /storage/Users/currentUser/GMfifo14860: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dcdisp -I../.././libsrc/include/dctool -I../.././libsrc/include/ourdisp -I../.././libsrc/include/pixeldat -I /storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcdisp.cc
rm -rf dcdisp
/data/service/hnp/bin/clang++ -o dcdisp dcdisp.o -O  -L../.././libsrc/lib -lddply -lodply -ldctl -ldlcl -lgener -L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext \
  -lm \

true dcdisp
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcdisp'
making all in ./appsrc/dcfile...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcfile'
make[2]: warning: -j8 forced in submake: resetting jobserver mode.
make[2]: jobserver mkfifo: /storage/Users/currentUser/GMfifo14933: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dccreate.cc
rm -rf dccreate
/data/service/hnp/bin/clang++ -o dccreate dccreate.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dccreate
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcentvfy.cc
rm -rf dcentvfy
/data/service/hnp/bin/clang++ -o dcentvfy dcentvfy.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcentvfy
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dclutmix.cc
In file included from dclutmix.cc:5:
In file included from ../.././libsrc/include/dctool/attrothr.h:5:
../.././libsrc/include/pixeldat/srcsink.h:319:46: warning: non-void function does not return a value [-Wreturn-type]
        Tout filter(Tin,size_t offset) { Assert(0); }
                                                    ^
dclutmix.cc:45:2: note: in instantiation of member function 'PointFilterIndependentOfOffset<unsigned short, unsigned short>::filter' requested here
        BurnInLUTFilter(const Uint16 *data,Uint16 numberOfEntries,Uint16 firstValueMapped)
        ^
1 warning generated.
rm -rf dclutmix
/data/service/hnp/bin/clang++ -o dclutmix dclutmix.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dclutmix
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcuidchg.cc
rm -rf dcuidchg
/data/service/hnp/bin/clang++ -o dcuidchg dcuidchg.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcuidchg
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcdtchg.cc
rm -rf dcdtchg
/data/service/hnp/bin/clang++ -o dcdtchg dcdtchg.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcdtchg
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dclutburn.cc
In file included from dclutburn.cc:3:
In file included from ../.././libsrc/include/dctool/attrothr.h:5:
../.././libsrc/include/pixeldat/srcsink.h:319:46: warning: non-void function does not return a value [-Wreturn-type]
        Tout filter(Tin,size_t offset) { Assert(0); }
                                                    ^
dclutburn.cc:17:2: note: in instantiation of member function 'PointFilterIndependentOfOffset<unsigned short, unsigned short>::filter' requested here
        BurnInLUTFilter(const Uint16 *data,Uint16 numberOfEntries,Uint16 firstValueMapped)
        ^
1 warning generated.
rm -rf dclutburn
/data/service/hnp/bin/clang++ -o dclutburn dclutburn.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dclutburn
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dctopdf.cc
rm -rf dctopdf
/data/service/hnp/bin/clang++ -o dctopdf dctopdf.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dctopdf
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pdftodc.cc
rm -rf pdftodc
/data/service/hnp/bin/clang++ -o pdftodc pdftodc.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true pdftodc
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pgxtodc.cc
rm -rf pgxtodc
/data/service/hnp/bin/clang++ -o pgxtodc pgxtodc.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true pgxtodc
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcencap.cc
rm -rf dcencap
/data/service/hnp/bin/clang++ -o dcencap dcencap.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcencap
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcburn.cc
In file included from dcburn.cc:3:
In file included from ../.././libsrc/include/dctool/attrothr.h:5:
../.././libsrc/include/pixeldat/srcsink.h:327:32: warning: non-void function does not return a value [-Wreturn-type]
        Tout filter(Tin) { Assert(0); }
                                      ^
dcburn.cc:14:2: note: in instantiation of member function 'PointFilterDependentOnOffset<unsigned short, unsigned short>::filter' requested here
        BurnInOverlaysFilter(int v,const Uint16 *b,unsigned long s)
        ^
1 warning generated.
rm -rf dcburn
/data/service/hnp/bin/clang++ -o dcburn dcburn.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcburn
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rawftodc.cc
rm -rf rawftodc
/data/service/hnp/bin/clang++ -o rawftodc rawftodc.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true rawftodc
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dccomb.cc
rm -rf dccomb
/data/service/hnp/bin/clang++ -o dccomb dccomb.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dccomb
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcuncat.cc
dcuncat.cc:485:6: warning: address of function 'isMultiFrameSOPClass' will always evaluate to 'true' [-Wpointer-bool-conversion]
        if (isMultiFrameSOPClass) {
        ~~  ^~~~~~~~~~~~~~~~~~~~
dcuncat.cc:485:6: note: prefix with the address-of operator to silence this warning
        if (isMultiFrameSOPClass) {
            ^
            &
dcuncat.cc:829:4: warning: bool literal returned from 'main' [-Wmain]
                        return false;
                        ^      ~~~~~
2 warnings generated.
rm -rf dcuncat
/data/service/hnp/bin/clang++ -o dcuncat dcuncat.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcuncat
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcsrmrg.cc
rm -rf dcsrmrg
/data/service/hnp/bin/clang++ -o dcsrmrg dcsrmrg.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcsrmrg
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcostosr.cc
dcostosr.cc:72:80: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
        (*list)+=newSingleCodedSequenceAttribute(TagFromName(ConceptNameCodeSequence),"333301","99RADPHARM","Lesion");
                                                                                      ^
dcostosr.cc:72:89: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
        (*list)+=newSingleCodedSequenceAttribute(TagFromName(ConceptNameCodeSequence),"333301","99RADPHARM","Lesion");
                                                                                               ^
dcostosr.cc:72:102: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
        (*list)+=newSingleCodedSequenceAttribute(TagFromName(ConceptNameCodeSequence),"333301","99RADPHARM","Lesion");
                                                                                                            ^
dcostosr.cc:123:81: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                (*ncsl)+=newSingleCodedSequenceAttribute(TagFromName(ConceptNameCodeSequence),"121206","DCM","Distance");
                                                                                              ^
dcostosr.cc:123:90: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                (*ncsl)+=newSingleCodedSequenceAttribute(TagFromName(ConceptNameCodeSequence),"121206","DCM","Distance");
                                                                                                       ^
dcostosr.cc:123:96: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                (*ncsl)+=newSingleCodedSequenceAttribute(TagFromName(ConceptNameCodeSequence),"121206","DCM","Distance");
                                                                                                             ^
dcostosr.cc:131:101: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                (*mvsl)+=newSingleCodedSequenceAttribute(TagFromName(MeasurementUnitsCodeSequence),unitsFromLabel,"UCUM",unitsFromLabel);
                                                                                                                  ^
dcostosr.cc:216:80: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
        newList+=newSingleCodedSequenceAttribute(TagFromName(ConceptNameCodeSequence),"333300","99RADPHARM","Measurements");
                                                                                      ^
dcostosr.cc:216:89: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
        newList+=newSingleCodedSequenceAttribute(TagFromName(ConceptNameCodeSequence),"333300","99RADPHARM","Measurements");
                                                                                               ^
dcostosr.cc:216:102: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
        newList+=newSingleCodedSequenceAttribute(TagFromName(ConceptNameCodeSequence),"333300","99RADPHARM","Measurements");
                                                                                                            ^
10 warnings generated.
rm -rf dcostosr
/data/service/hnp/bin/clang++ -o dcostosr dcostosr.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcostosr
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcrmmeta.cc
dcrmmeta.cc:28:10: warning: using the result of an assignment as a condition without parentheses [-Wparentheses]
        while (n=i.read(buffer,bufsize).gcount()) o.write(buffer,n);
               ~^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
dcrmmeta.cc:28:10: note: place parentheses around the assignment to silence this warning
        while (n=i.read(buffer,bufsize).gcount()) o.write(buffer,n);
                ^
               (                                )
dcrmmeta.cc:28:10: note: use '==' to turn this assignment into an equality comparison
        while (n=i.read(buffer,bufsize).gcount()) o.write(buffer,n);
                ^
                ==
1 warning generated.
rm -rf dcrmmeta
/data/service/hnp/bin/clang++ -o dcrmmeta dcrmmeta.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcrmmeta
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcsrdump.cc
rm -rf dcsrdump
/data/service/hnp/bin/clang++ -o dcsrdump dcsrdump.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcsrdump
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dccidump.cc
rm -rf dccidump
/data/service/hnp/bin/clang++ -o dccidump dccidump.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dccidump
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcsub.cc
rm -rf dcsub
/data/service/hnp/bin/clang++ -o dcsub dcsub.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcsub
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcdecmpr.cc
rm -rf dcdecmpr
/data/service/hnp/bin/clang++ -o dcdecmpr dcdecmpr.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcdecmpr
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcsort.cc
rm -rf dcsort
/data/service/hnp/bin/clang++ -o dcsort dcsort.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcsort
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcproj.cc
rm -rf dcproj
/data/service/hnp/bin/clang++ -o dcproj dcproj.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcproj
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcarith.cc
In file included from dcarith.cc:3:
In file included from ../.././libsrc/include/dctool/attrothr.h:5:
../.././libsrc/include/pixeldat/srcsink.h:319:46: warning: non-void function does not return a value [-Wreturn-type]
        Tout filter(Tin,size_t offset) { Assert(0); }
                                                    ^
dcarith.cc:14:2: note: in instantiation of member function 'PointFilterIndependentOfOffset<unsigned short, unsigned short>::filter' requested here
        MaskHighBitFilter(unsigned lowbitstokeep)
        ^
1 warning generated.
rm -rf dcarith
/data/service/hnp/bin/clang++ -o dcarith dcarith.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcarith
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dctopgm8.cc
dctopgm8.cc:550:27: warning: implicit conversion from 'long' to 'double' changes value from 9223372036854775807 to 9223372036854775808 [-Wimplicit-const-int-float-conversion]
        Assert(rescaleintercept<=LONG_MAX);
                               ~~^~~~~~~~
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include/limits.h:47:19: note: expanded from macro 'LONG_MAX'
#define LONG_MAX  __LONG_MAX__
                  ^~~~~~~~~~~~
<built-in>:84:22: note: expanded from here
#define __LONG_MAX__ 9223372036854775807L
                     ^~~~~~~~~~~~~~~~~~~~
../.././libsrc/include/generic/basetype.h:77:29: note: expanded from macro 'Assert'
#define Assert(expr)    assert(expr)    // In case we get more creative later !
                               ^~~~
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/assert.h:8:28: note: expanded from macro 'assert'
#define assert(x) ((void)((x) || (__assert_fail(#x, __FILE__, __LINE__, __func__),0)))
                           ^
1 warning generated.
rm -rf dctopgm8
/data/service/hnp/bin/clang++ -o dctopgm8 dctopgm8.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dctopgm8
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dctopgx.cc
rm -rf dctopgx
/data/service/hnp/bin/clang++ -o dctopgx dctopgx.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dctopgx
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcpost.cc
rm -rf dcpost
/data/service/hnp/bin/clang++ -o dcpost dcpost.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcpost
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcmulti.cc
dcmulti.cc:755:43: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
        for (m=nActual; m<nMax; ++m) v[m]="";           // fill missing values with zero length string rather than null; saves checks later
                                          ^
dcmulti.cc:1419:18: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
        char *badDate = "29990101";
                        ^
dcmulti.cc:1420:18: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
        char *badTime = "000000";
                        ^
dcmulti.cc:1470:18: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
        char *badDate = "29990101";
                        ^
dcmulti.cc:1471:18: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
        char *badTime = "000000";
                        ^
dcmulti.cc:1939:52: warning: illegal character encoding in string literal [-Winvalid-source-encoding]
                        else if (strcmp(cv,"113068") == 0)      { cm="Student<D5>s T-Test"; }
                                                                             ^~~~
dcmulti.cc:3676:2: warning: expression result unused [-Wunused-value]
        useDistance;
        ^~~~~~~~~~~
dcmulti.cc:4250:52: warning: array index 2 is past the end of the array (which contains 2 elements) [-Warray-bounds]
                        const char *organizationLabel = argCount == 4 ? argumentNames[2] : NULL;
                                                                        ^             ~
dcmulti.cc:4241:3: note: array 'argumentNames' declared here
                const char *argumentNames[2];
                ^
dcmulti.cc:4251:51: warning: array index 3 is past the end of the array (which contains 2 elements) [-Warray-bounds]
                        const char *organizationUID =  argCount == 4 ? argumentNames[3] : NULL;
                                                                       ^             ~
dcmulti.cc:4241:3: note: array 'argumentNames' declared here
                const char *argumentNames[2];
                ^
9 warnings generated.
rm -rf dcmulti
/data/service/hnp/bin/clang++ -o dcmulti dcmulti.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcmulti
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dctable.cc
rm -rf dctable
/data/service/hnp/bin/clang++ -o dctable dctable.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dctable
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcmkpres.cc
rm -rf dcmkpres
/data/service/hnp/bin/clang++ -o dcmkpres dcmkpres.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcmkpres
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcortho.cc
rm -rf dcortho
/data/service/hnp/bin/clang++ -o dcortho dcortho.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcortho
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   antodc.cc
rm -rf antodc
/data/service/hnp/bin/clang++ -o antodc antodc.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true antodc
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dclutdmp.cc
rm -rf dclutdmp
/data/service/hnp/bin/clang++ -o dclutdmp dclutdmp.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dclutdmp
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcbriggs.cc
rm -rf dcbriggs
/data/service/hnp/bin/clang++ -o dcbriggs dcbriggs.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcbriggs
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dccp.cc
rm -rf dccp
/data/service/hnp/bin/clang++ -o dccp dccp.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dccp
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcdict.cc
rm -rf dcdict
/data/service/hnp/bin/clang++ -o dcdict dcdict.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcdict
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcdirdmp.cc
rm -rf dcdirdmp
/data/service/hnp/bin/clang++ -o dcdirdmp dcdirdmp.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcdirdmp
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcdirmk.cc
dcdirmk.cc:1483:3: warning: non-void function does not return a value [-Wreturn-type]
                }
                ^
dcdirmk.cc:1603:3: warning: non-void function does not return a value [-Wreturn-type]
                }
                ^
dcdirmk.cc:1715:3: warning: non-void function does not return a value [-Wreturn-type]
                }
                ^
3 warnings generated.
rm -rf dcdirmk
/data/service/hnp/bin/clang++ -o dcdirmk dcdirmk.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcdirmk
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcdump.cc
rm -rf dcdump
/data/service/hnp/bin/clang++ -o dcdump dcdump.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcdump
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcfile.cc
rm -rf dcfile
/data/service/hnp/bin/clang++ -o dcfile dcfile.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcfile
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dchist.cc
rm -rf dchist
/data/service/hnp/bin/clang++ -o dchist dchist.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dchist
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dckey.cc
rm -rf dckey
/data/service/hnp/bin/clang++ -o dckey dckey.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dckey
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dciodvfy.cc
rm -rf dciodvfy
/data/service/hnp/bin/clang++ -o dciodvfy dciodvfy.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dciodvfy
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcmerge.cc
rm -rf dcmerge
/data/service/hnp/bin/clang++ -o dcmerge dcmerge.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcmerge
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcposn.cc
rm -rf dcposn
/data/service/hnp/bin/clang++ -o dcposn dcposn.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcposn
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcsmpte.cc
rm -rf dcsmpte
/data/service/hnp/bin/clang++ -o dcsmpte dcsmpte.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcsmpte
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcsqextr.cc
rm -rf dcsqextr
/data/service/hnp/bin/clang++ -o dcsqextr dcsqextr.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcsqextr
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcstats.cc
rm -rf dcstats
/data/service/hnp/bin/clang++ -o dcstats dcstats.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dcstats
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dctoraw.cc
rm -rf dctoraw
/data/service/hnp/bin/clang++ -o dctoraw dctoraw.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dctoraw
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dctopnm.cc
rm -rf dctopnm
/data/service/hnp/bin/clang++ -o dctopnm dctopnm.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true dctopnm
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pbmtoovl.cc
rm -rf pbmtoovl
/data/service/hnp/bin/clang++ -o pbmtoovl pbmtoovl.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true pbmtoovl
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pnmtodc.cc
rm -rf pnmtodc
/data/service/hnp/bin/clang++ -o pnmtodc pnmtodc.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true pnmtodc
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale -I../.././libsrc/include/dctool -I../.././libsrc/include/pixeldat      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rawtodc.cc
rm -rf rawtodc
/data/service/hnp/bin/clang++ -o rawtodc rawtodc.o -O  -L../.././libsrc/lib -ldctl -ldlcl -lgener \
  -lm \

true rawtodc
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcfile'
making all in ./appsrc/dcintro...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcintro'
make[2]: warning: -j8 forced in submake: resetting jobserver mode.
make[2]: jobserver mkfifo: /storage/Users/currentUser/GMfifo24176: Operation not permitted
make[2]: Nothing to be done for 'all'.
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcintro'
making all in ./appsrc/misc...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/misc'
make[2]: warning: -j8 forced in submake: resetting jobserver mode.
make[2]: jobserver mkfifo: /storage/Users/currentUser/GMfifo24179: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   bmpdump.cc
bmpdump.cc:83:1: warning: non-void function does not return a value in all control paths [-Wreturn-type]
}
^
1 warning generated.
rm -rf bmpdump
/data/service/hnp/bin/clang++ -o bmpdump bmpdump.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true bmpdump
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pgmtobmp.cc
rm -rf pgmtobmp
/data/service/hnp/bin/clang++ -o pgmtobmp pgmtobmp.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true pgmtobmp
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dumpwhat.cc
dumpwhat.cc:444:41: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                putDescriptor(ostr,params,'\0',offset,"char");
                                                      ^
dumpwhat.cc:898:46: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                putDescriptor(ostr,params,byteorder,offset,"f_ieee32");
                                                           ^
dumpwhat.cc:926:46: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                putDescriptor(ostr,params,byteorder,offset,"f_ieee64");
                                                           ^
dumpwhat.cc:954:46: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                putDescriptor(ostr,params,byteorder,offset,"f_vax_f ");
                                                           ^
dumpwhat.cc:1121:1: warning: non-void function does not return a value in all control paths [-Wreturn-type]
}
^
dumpwhat.cc:1245:40: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                 && elide(buffer,*outstream,params,0,"zeroes",params.stringlength))
                                                     ^
dumpwhat.cc:1248:42: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                 && elide(buffer,*outstream,params,' ',"spaces",params.stringlength))
                                                       ^
7 warnings generated.
rm -rf dumpwhat
/data/service/hnp/bin/clang++ -o dumpwhat dumpwhat.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true dumpwhat
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dcunmeta.cc
dcunmeta.cc:65:3: warning: bool literal returned from 'main' [-Wmain]
                return false;
                ^      ~~~~~
dcunmeta.cc:72:3: warning: bool literal returned from 'main' [-Wmain]
                return false;
                ^      ~~~~~
dcunmeta.cc:80:3: warning: bool literal returned from 'main' [-Wmain]
                return false;
                ^      ~~~~~
dcunmeta.cc:89:3: warning: bool literal returned from 'main' [-Wmain]
                return false;
                ^      ~~~~~
dcunmeta.cc:96:3: warning: bool literal returned from 'main' [-Wmain]
                return false;
                ^      ~~~~~
dcunmeta.cc:109:3: warning: bool literal returned from 'main' [-Wmain]
                return false;
                ^      ~~~~~
dcunmeta.cc:120:3: warning: bool literal returned from 'main' [-Wmain]
                return false;
                ^      ~~~~~
dcunmeta.cc:129:3: warning: bool literal returned from 'main' [-Wmain]
                return false;
                ^      ~~~~~
dcunmeta.cc:137:3: warning: bool literal returned from 'main' [-Wmain]
                return false;
                ^      ~~~~~
9 warnings generated.
rm -rf dcunmeta
/data/service/hnp/bin/clang++ -o dcunmeta dcunmeta.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true dcunmeta
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   binpatch.cc
rm -rf binpatch
/data/service/hnp/bin/clang++ -o binpatch binpatch.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true binpatch
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   jpegdump.cc
rm -rf jpegdump
/data/service/hnp/bin/clang++ -o jpegdump jpegdump.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true jpegdump
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   jpegsplit.cc
rm -rf jpegsplit
/data/service/hnp/bin/clang++ -o jpegsplit jpegsplit.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true jpegsplit
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pbmswbit.cc
rm -rf pbmswbit
/data/service/hnp/bin/clang++ -o pbmswbit pbmswbit.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true pbmswbit
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pnmpred.cc
rm -rf pnmpred
/data/service/hnp/bin/clang++ -o pnmpred pnmpred.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true pnmpred
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pnmtoraw.cc
rm -rf pnmtoraw
/data/service/hnp/bin/clang++ -o pnmtoraw pnmtoraw.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true pnmtoraw
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rawarith.cc
rm -rf rawarith
/data/service/hnp/bin/clang++ -o rawarith rawarith.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true rawarith
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rawdiff.cc
rm -rf rawdiff
/data/service/hnp/bin/clang++ -o rawdiff rawdiff.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true rawdiff
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rawmask.cc
rm -rf rawmask
/data/service/hnp/bin/clang++ -o rawmask rawmask.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true rawmask
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rawnjl.cc
rm -rf rawnjl
/data/service/hnp/bin/clang++ -o rawnjl rawnjl.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true rawnjl
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   rawnjl2.cc
rm -rf rawnjl2
/data/service/hnp/bin/clang++ -o rawnjl2 rawnjl2.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true rawnjl2
/data/service/hnp/bin/clang++ -c -O    -I../.././libsrc/include/generic -I../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   dumptiff.cc
dumptiff.cc:128:1: warning: non-void function does not return a value in all control paths [-Wreturn-type]
}
^
1 warning generated.
rm -rf dumptiff
/data/service/hnp/bin/clang++ -o dumptiff dumptiff.o -O  -L../.././libsrc/lib -ldlcl -lgener \
  -lm \

true dumptiff
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/misc'
making all in ./appsrc/simple...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
make[2]: warning: -j8 forced in submake: resetting jobserver mode.
make[2]: jobserver mkfifo: /storage/Users/currentUser/GMfifo26836: Operation not permitted
making all in ./appsrc/simple/ge9800...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/ge9800'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo26839: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ge98topgm.cc
rm -rf ge98topgm
/data/service/hnp/bin/clang++ -o ge98topgm ge98topgm.o -O  -L../../.././libsrc/lib \
  \

true ge98topgm
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ge98id.cc
rm -rf ge98id
/data/service/hnp/bin/clang++ -o ge98id ge98id.o -O  -L../../.././libsrc/lib \
  \

true ge98id
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/ge9800'
making all in ./appsrc/simple/genesis...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/genesis'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo26989: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gentopgm.cc
rm -rf gentopgm
/data/service/hnp/bin/clang++ -o gentopgm gentopgm.o -O  -L../../.././libsrc/lib \
  \

true gentopgm
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/genesis'
making all in ./appsrc/simple/pace...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/pace'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo27082: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pacetopgm.cc
rm -rf pacetopgm
/data/service/hnp/bin/clang++ -o pacetopgm pacetopgm.o -O  -L../../.././libsrc/lib \
  \

true pacetopgm
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/pace'
making all in ./appsrc/simple/signa...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/signa'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo27117: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sgntopgm.cc
rm -rf sgntopgm
/data/service/hnp/bin/clang++ -o sgntopgm sgntopgm.o -O  -L../../.././libsrc/lib \
  \

true sgntopgm
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/signa'
making all in ./appsrc/simple/somatom...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/somatom'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo27223: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   somtopgm.cc
rm -rf somtopgm
/data/service/hnp/bin/clang++ -o somtopgm somtopgm.o -O  -L../../.././libsrc/lib \
  \

true somtopgm
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/somatom'
making all in ./appsrc/simple/sytec...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/sytec'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo27258: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   syttopgm.cc
rm -rf syttopgm
/data/service/hnp/bin/clang++ -o syttopgm syttopgm.o -O  -L../../.././libsrc/lib \
  \

true syttopgm
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/sytec'
making all in ./appsrc/simple/vision...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/vision'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo27337: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   vsntopgm.cc
rm -rf vsntopgm
/data/service/hnp/bin/clang++ -o vsntopgm vsntopgm.o -O  -L../../.././libsrc/lib \
  \

true vsntopgm
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/vision'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
making all in ./appsrc/dconvert...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
make[2]: warning: -j8 forced in submake: resetting jobserver mode.
make[2]: jobserver mkfifo: /storage/Users/currentUser/GMfifo27391: Operation not permitted
making all in ./appsrc/dconvert/support...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/support'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo27398: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/support'
making all in ./appsrc/dconvert/xxxx...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/xxxx'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo27401: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/xxxx'
making all in ./appsrc/dconvert/pace...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pace'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo27406: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pacetodc.cc
rm -rf pacetodc
/data/service/hnp/bin/clang++ -o pacetodc pacetodc.o -O  -L../../.././libsrc/lib -ldpace -ldconv -ldctl -ldlcl -lgener \
  -lm \

true pacetodc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pacedump.cc
rm -rf pacedump
/data/service/hnp/bin/clang++ -o pacedump pacedump.o -O  -L../../.././libsrc/lib -ldpace -ldconv -ldctl -ldlcl -lgener \
  -lm \

true pacedump
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pace'
making all in ./appsrc/dconvert/imtn...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/imtn'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo27581: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   imtntodc.cc
rm -rf imtntodc
/data/service/hnp/bin/clang++ -o imtntodc imtntodc.o -O  -L../../.././libsrc/lib -ldimtn -ldconv -ldctl -ldlcl -lgener \
  -lm \

true imtntodc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   imtndump.cc
rm -rf imtndump
/data/service/hnp/bin/clang++ -o imtndump imtndump.o -O  -L../../.././libsrc/lib -ldimtn -ldconv -ldctl -ldlcl -lgener \
  -lm \

true imtndump
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/imtn'
making all in ./appsrc/dconvert/gen...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gen'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo27733: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gentodc.cc
rm -rf gentodc
/data/service/hnp/bin/clang++ -o gentodc gentodc.o -O  -L../../.././libsrc/lib -ldgen -ldconv -ldctl -ldlcl -lgener \
  -lm \

true gentodc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gendump.cc
rm -rf gendump
/data/service/hnp/bin/clang++ -o gendump gendump.o -O  -L../../.././libsrc/lib -ldgen -ldconv -ldctl -ldlcl -lgener \
  -lm \

true gendump
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gen'
making all in ./appsrc/dconvert/gaw...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gaw'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo27870: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gawtodc.cc
rm -rf gawtodc
/data/service/hnp/bin/clang++ -o gawtodc gawtodc.o -O  -L../../.././libsrc/lib -ldgaw -ldconv -ldctl -ldlcl -lgener \
  -lm \

true gawtodc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   gawdump.cc
rm -rf gawdump
/data/service/hnp/bin/clang++ -o gawdump gawdump.o -O  -L../../.././libsrc/lib -ldgaw -ldconv -ldctl -ldlcl -lgener \
  -lm \

true gawdump
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gaw'
making all in ./appsrc/dconvert/shim...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/shim'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo28012: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   shimtodc.cc
rm -rf shimtodc
/data/service/hnp/bin/clang++ -o shimtodc shimtodc.o -O  -L../../.././libsrc/lib -ldshim -ldconv -ldctl -ldlcl -lgener \
  -lm \

true shimtodc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   shimdump.cc
rm -rf shimdump
/data/service/hnp/bin/clang++ -o shimdump shimdump.o -O  -L../../.././libsrc/lib -ldshim -ldconv -ldctl -ldlcl -lgener \
  -lm \

true shimdump
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/shim'
making all in ./appsrc/dconvert/somp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/somp'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo28184: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   somptodc.cc
rm -rf somptodc
/data/service/hnp/bin/clang++ -o somptodc somptodc.o -O  -L../../.././libsrc/lib -ldsomp -ldconv -ldctl -ldlcl -lgener \
  -lm \

true somptodc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sompdump.cc
rm -rf sompdump
/data/service/hnp/bin/clang++ -o sompdump sompdump.o -O  -L../../.././libsrc/lib -ldsomp -ldconv -ldctl -ldlcl -lgener \
  -lm \

true sompdump
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/somp'
making all in ./appsrc/dconvert/himr...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/himr'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo28371: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   himrtodc.cc
rm -rf himrtodc
/data/service/hnp/bin/clang++ -o himrtodc himrtodc.o -O  -L../../.././libsrc/lib -ldhimr -ldconv -ldctl -ldlcl -lgener \
  -lm \

true himrtodc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   himrdump.cc
rm -rf himrdump
/data/service/hnp/bin/clang++ -o himrdump himrdump.o -O  -L../../.././libsrc/lib -ldhimr -ldconv -ldctl -ldlcl -lgener \
  -lm \

true himrdump
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/himr'
making all in ./appsrc/dconvert/pq...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pq'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo28516: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pqtodc.cc
rm -rf pqtodc
/data/service/hnp/bin/clang++ -o pqtodc pqtodc.o -O  -L../../.././libsrc/lib -ldpq -ldconv -ldctl -ldlcl -lgener \
  -lm \

true pqtodc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pqdump.cc
rm -rf pqdump
/data/service/hnp/bin/clang++ -o pqdump pqdump.o -O  -L../../.././libsrc/lib -ldpq -ldconv -ldctl -ldlcl -lgener \
  -lm \

true pqdump
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   pqsplit.cc
pqsplit.cc:235:25: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                case 0: vtype_label="asc"; break;
                                                    ^
pqsplit.cc:236:25: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                case 1: vtype_label="int"; break;
                                                    ^
pqsplit.cc:237:25: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                case 2: vtype_label="dat"; break;
                                                    ^
pqsplit.cc:238:25: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                case 3: vtype_label="tim"; break;
                                                    ^
pqsplit.cc:239:25: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                case 4: vtype_label="fil"; break;
                                                    ^
pqsplit.cc:240:25: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                case 5: vtype_label="flg"; break;
                                                    ^
pqsplit.cc:241:25: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                case 6: vtype_label="flt"; break;
                                                    ^
pqsplit.cc:243:18: warning: ISO C++11 does not allow conversion from string literal to 'char *' [-Wwritable-strings]
                                        vtype_label="???"; break;
                                                    ^
8 warnings generated.
rm -rf pqsplit
/data/service/hnp/bin/clang++ -o pqsplit pqsplit.o -O  -L../../.././libsrc/lib \
  -lm \

true pqsplit
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pq'
making all in ./appsrc/dconvert/toshiba...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/toshiba'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo28731: Operation not permitted
make[3]: Nothing to be done for 'all'.
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/toshiba'
making all in ./appsrc/dconvert/signa...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/signa'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo28733: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sgntodc.cc
rm -rf sgntodc
/data/service/hnp/bin/clang++ -o sgntodc sgntodc.o -O  -L../../.././libsrc/lib -ldsgn -ldconv -ldctl -ldlcl -lgener \
  -lm \

true sgntodc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   sgndump.cc
rm -rf sgndump
/data/service/hnp/bin/clang++ -o sgndump sgndump.o -O  -L../../.././libsrc/lib -ldsgn -ldconv -ldctl -ldlcl -lgener \
  -lm \

true sgndump
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/signa'
making all in ./appsrc/dconvert/ge9800...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/ge9800'
make[3]: warning: -j8 forced in submake: resetting jobserver mode.
make[3]: jobserver mkfifo: /storage/Users/currentUser/GMfifo28984: Operation not permitted
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ge9800todc.cc
rm -rf ge9800todc
/data/service/hnp/bin/clang++ -o ge9800todc ge9800todc.o -O  -L../../.././libsrc/lib -ldge9800 -ldconv -ldctl -ldlcl -lgener \
  -lm \

true ge9800todc
/data/service/hnp/bin/clang++ -c -O    -I../../.././libsrc/include/generic -I../../.././libsrc/include/locale -I../../.././libsrc/include/dctool -I../../.././libsrc/include/pixeldat -I../../.././libsrc/include/dconvert      -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   ge9800dump.cc
rm -rf ge9800dump
/data/service/hnp/bin/clang++ -o ge9800dump ge9800dump.o -O  -L../../.././libsrc/lib -ldge9800 -ldconv -ldctl -ldlcl -lgener \
  -lm \

true ge9800dump
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/ge9800'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
making all in ./support...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/support'
make[1]: warning: -j8 forced in submake: resetting jobserver mode.
make[1]: jobserver mkfifo: /storage/Users/currentUser/GMfifo29110: Operation not permitted
/data/service/hnp/bin/clang++ -c -O          -DDEFAULTUIDROOT=\"DefaultUIDRoot\" -DDEFAULTINSTANCECREATORUID=\"DefaultInstanceCreatorUID\" -DDEFAULTIMPLEMENTATIONCLASSUID=\"DefaultImplementationClassUID\" -DDEFAULTIMPLEMENTATIONVERSIONNAME=\"DefaultImplementationVersionName\" -DDEFAULTSOURCEAPPLICATIONENTITYTITLE=\"DefaultSourceApplicationEntityTitle\"  -DUSEGLIBCTIMEZONE=1 -DUSEDUMBINFINITYANDNAN=1 -DHASSTDNAMESPACEFORSTREAMPOS=1 -DUSESTANDARDHEADERSWITHOUTEXTENSION=1 -DEMITUSINGSTDNAMESPACE=1 -DHASGETHOSTID=0  -DUSEXMITSHMEXTENSION=0   mktime.cc
rm -rf mktime
/data/service/hnp/bin/clang++ -o mktime mktime.o -O  -L.././libsrc/lib \
  \

true mktime
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/support'

dicom3tools/1.00-20240118131615: linked 102 programs
dicom3tools/1.00-20240118131615: Package '5eb970f88879b3d0c0e7ef18bb72a19b24bbb2cb' built
dicom3tools/1.00-20240118131615: Build folder /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b
dicom3tools/1.00-20240118131615: Generating the package
dicom3tools/1.00-20240118131615: Packaging in folder /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/p
dicom3tools/1.00-20240118131615: Calling package()
dicom3tools/1.00-20240118131615: RUN: make IMAKE_DEFINES="'-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext'" IMAKE="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake" DEPEND="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend" MKDIRHIER="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/mkdirhier" INSTALL='/data/service/hnp/bin/busybox install' INSTPGMFLAGS= DESTDIR="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage" install
installing in ./appsrc...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
installing in ./appsrc/acrnema...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/acrnema'
+ /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/mkdirhier /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 ancreate  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 andump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 ancp  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install -m 0755 andiff.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/andiff
install in ./appsrc/acrnema done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/acrnema'
installing in ./appsrc/dcdisp...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcdisp'
/data/service/hnp/bin/busybox install  -m 0755 dcdisp  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/dcdisp done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcdisp'
installing in ./appsrc/dcfile...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcfile'
/data/service/hnp/bin/busybox install  -m 0755 dccreate  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcentvfy  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dclutmix  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcuidchg  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcdtchg  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dclutburn  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dctopdf  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 pdftodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 pgxtodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcencap  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcburn  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 rawftodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dccomb  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcuncat  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcsrmrg  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcostosr  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcrmmeta  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcsrdump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dccidump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcsub  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcdecmpr  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcsort  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcproj  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcarith  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dctopgm8  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dctopgx  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcpost  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcmulti  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dctable  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install -m 0755 dctable_decompressingprn.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dctable_decompressingprn
/data/service/hnp/bin/busybox install  -m 0755 dcmkpres  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcortho  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 antodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dclutdmp  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcbriggs  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dccp  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcdict  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcdirdmp  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcdirmk  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcdump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcfile  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dchist  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dckey  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dciodvfy  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcmerge  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcposn  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcsmpte  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcsqextr  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcstats  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dctoraw  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dctopnm  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 pbmtoovl  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 pnmtodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 rawtodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install -m 0755 dcpatmpl.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcpatmpl
/data/service/hnp/bin/busybox install -m 0755 dcswab.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcswab
/data/service/hnp/bin/busybox install -m 0755 dcjls.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcjls
/data/service/hnp/bin/busybox install -m 0755 dcunjls.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcunjls
/data/service/hnp/bin/busybox install -m 0755 dcj2k.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcj2k
/data/service/hnp/bin/busybox install -m 0755 dcjpeg.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcjpeg
/data/service/hnp/bin/busybox install -m 0755 dcunjpeg.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcunjpeg
/data/service/hnp/bin/busybox install -m 0755 dcunjpeg.all.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcunjpeg.all
/data/service/hnp/bin/busybox install -m 0755 dcunrgb.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcunrgb
/data/service/hnp/bin/busybox install -m 0755 dcanon.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcanon
/data/service/hnp/bin/busybox install -m 0755 dcmvhier.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcmvhier
/data/service/hnp/bin/busybox install -m 0755 dcmvhier.uid.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcmvhier.uid
/data/service/hnp/bin/busybox install -m 0755 dcmvhier.datedesc.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcmvhier.datedesc
/data/service/hnp/bin/busybox install -m 0755 dcmvhier.datedescnoid.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/dcmvhier.datedescnoid
make[2]: *** No rule to make target 'dcmvhier.8only', needed by 'install'.  Stop.
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcfile'
installing in ./appsrc/dcintro...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcintro'
install in ./appsrc/dcintro done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcintro'
installing in ./appsrc/misc...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/misc'
/data/service/hnp/bin/busybox install  -m 0755 bmpdump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 pgmtobmp  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dumpwhat  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dcunmeta  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 binpatch  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 jpegdump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 jpegsplit  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 pbmswbit  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 pnmpred  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 pnmtoraw  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 rawarith  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 rawdiff  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 rawmask  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 rawnjl  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 rawnjl2  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 dumptiff  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/misc done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/misc'
installing in ./appsrc/simple...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
installing in ./appsrc/simple/ge9800...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/ge9800'
/data/service/hnp/bin/busybox install  -m 0755 ge98topgm  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 ge98id  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/simple/ge9800 done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/ge9800'
installing in ./appsrc/simple/genesis...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/genesis'
/data/service/hnp/bin/busybox install  -m 0755 gentopgm  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/simple/genesis done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/genesis'
installing in ./appsrc/simple/pace...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/pace'
/data/service/hnp/bin/busybox install  -m 0755 pacetopgm  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/simple/pace done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/pace'
installing in ./appsrc/simple/signa...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/signa'
/data/service/hnp/bin/busybox install  -m 0755 sgntopgm  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/simple/signa done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/signa'
installing in ./appsrc/simple/somatom...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/somatom'
/data/service/hnp/bin/busybox install  -m 0755 somtopgm  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/simple/somatom done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/somatom'
installing in ./appsrc/simple/sytec...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/sytec'
/data/service/hnp/bin/busybox install  -m 0755 syttopgm  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/simple/sytec done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/sytec'
installing in ./appsrc/simple/vision...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/vision'
/data/service/hnp/bin/busybox install  -m 0755 vsntopgm  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/simple/vision done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/vision'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
installing in ./appsrc/dconvert...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
installing in ./appsrc/dconvert/support...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/support'
install in ./appsrc/dconvert/support done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/support'
installing in ./appsrc/dconvert/xxxx...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/xxxx'
install in ./appsrc/dconvert/xxxx done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/xxxx'
installing in ./appsrc/dconvert/pace...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pace'
/data/service/hnp/bin/busybox install  -m 0755 pacetodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 pacedump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install -m 0755 paceunid.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/paceunid
install in ./appsrc/dconvert/pace done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pace'
installing in ./appsrc/dconvert/imtn...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/imtn'
/data/service/hnp/bin/busybox install  -m 0755 imtntodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 imtndump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/dconvert/imtn done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/imtn'
installing in ./appsrc/dconvert/gen...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gen'
/data/service/hnp/bin/busybox install  -m 0755 gentodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 gendump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install -m 0755 gentodc.dat.all.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/gentodc.dat.all
install in ./appsrc/dconvert/gen done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gen'
installing in ./appsrc/dconvert/gaw...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gaw'
/data/service/hnp/bin/busybox install  -m 0755 gawtodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 gawdump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/dconvert/gaw done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gaw'
installing in ./appsrc/dconvert/shim...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/shim'
/data/service/hnp/bin/busybox install  -m 0755 shimtodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 shimdump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/dconvert/shim done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/shim'
installing in ./appsrc/dconvert/somp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/somp'
/data/service/hnp/bin/busybox install  -m 0755 somptodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 sompdump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/dconvert/somp done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/somp'
installing in ./appsrc/dconvert/himr...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/himr'
/data/service/hnp/bin/busybox install  -m 0755 himrtodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 himrdump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install -m 0755 himrunid.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/himrunid
install in ./appsrc/dconvert/himr done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/himr'
installing in ./appsrc/dconvert/pq...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pq'
/data/service/hnp/bin/busybox install  -m 0755 pqtodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 pqdump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 pqsplit  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/dconvert/pq done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pq'
installing in ./appsrc/dconvert/toshiba...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/toshiba'
/data/service/hnp/bin/busybox install -m 0755 toshtodc.script /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin/toshtodc
install in ./appsrc/dconvert/toshiba done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/toshiba'
installing in ./appsrc/dconvert/signa...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/signa'
/data/service/hnp/bin/busybox install  -m 0755 sgntodc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 sgndump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/dconvert/signa done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/signa'
installing in ./appsrc/dconvert/ge9800...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/ge9800'
/data/service/hnp/bin/busybox install  -m 0755 ge9800todc  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
/data/service/hnp/bin/busybox install  -m 0755 ge9800dump  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/bin
install in ./appsrc/dconvert/ge9800 done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/ge9800'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
installing in ./config...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/config'
install in ./config done
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/config'
installing in ./libsrc...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
installing in ./libsrc/standard...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
installing in ./libsrc/standard/elmdict...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/elmdict'
install in ./libsrc/standard/elmdict done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/elmdict'
installing in ./libsrc/standard/module...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/module'
install in ./libsrc/standard/module done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/module'
installing in ./libsrc/standard/iodcomp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/iodcomp'
install in ./libsrc/standard/iodcomp done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/iodcomp'
installing in ./libsrc/standard/strval...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/strval'
install in ./libsrc/standard/strval done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/strval'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
installing in ./libsrc/include...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
installing in ./libsrc/include/dcdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dcdisp'
install in ./libsrc/include/dcdisp done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dcdisp'
installing in ./libsrc/include/dconvert...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dconvert'
install in ./libsrc/include/dconvert done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dconvert'
installing in ./libsrc/include/dctool...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dctool'
install in ./libsrc/include/dctool done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dctool'
installing in ./libsrc/include/generic...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/generic'
install in ./libsrc/include/generic done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/generic'
installing in ./libsrc/include/locale...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/locale'
install in ./libsrc/include/locale done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/locale'
installing in ./libsrc/include/ourdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/ourdisp'
install in ./libsrc/include/ourdisp done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/ourdisp'
installing in ./libsrc/include/pixeldat...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/pixeldat'
install in ./libsrc/include/pixeldat done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/pixeldat'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
installing in ./libsrc/lib...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/lib'
+ /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/mkdirhier /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/lib
/data/service/hnp/bin/busybox install -m 0644 libddply.a /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/lib
ranlib  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/lib/libddply.a
/data/service/hnp/bin/busybox install -m 0644 libdconv.a /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/lib
ranlib  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/lib/libdconv.a
/data/service/hnp/bin/busybox install -m 0644 libdctl.a /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/lib
ranlib  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/lib/libdctl.a
/data/service/hnp/bin/busybox install -m 0644 libgener.a /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/lib
ranlib  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/lib/libgener.a
/data/service/hnp/bin/busybox install -m 0644 libdlcl.a /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/lib
ranlib  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/lib/libdlcl.a
/data/service/hnp/bin/busybox install -m 0644 libodply.a /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/lib
ranlib  /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/lib/libodply.a
install in ./libsrc/lib done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/lib'
installing in ./libsrc/src...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
installing in ./libsrc/src/dcdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dcdisp'
install in ./libsrc/src/dcdisp done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dcdisp'
installing in ./libsrc/src/dctool...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dctool'
install in ./libsrc/src/dctool done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dctool'
installing in ./libsrc/src/generic...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/generic'
install in ./libsrc/src/generic done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/generic'
installing in ./libsrc/src/locale...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/locale'
install in ./libsrc/src/locale done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/locale'
installing in ./libsrc/src/ourdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/ourdisp'
install in ./libsrc/src/ourdisp done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/ourdisp'
installing in ./libsrc/src/dconvert...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
installing in ./libsrc/src/dconvert/support...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/support'
install in ./libsrc/src/dconvert/support done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/support'
installing in ./libsrc/src/dconvert/pace...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pace'
install in ./libsrc/src/dconvert/pace done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pace'
installing in ./libsrc/src/dconvert/xxxx...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/xxxx'
install in ./libsrc/src/dconvert/xxxx done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/xxxx'
installing in ./libsrc/src/dconvert/imtn...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/imtn'
install in ./libsrc/src/dconvert/imtn done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/imtn'
installing in ./libsrc/src/dconvert/gen...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gen'
install in ./libsrc/src/dconvert/gen done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gen'
installing in ./libsrc/src/dconvert/gaw...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gaw'
install in ./libsrc/src/dconvert/gaw done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gaw'
installing in ./libsrc/src/dconvert/shim...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/shim'
install in ./libsrc/src/dconvert/shim done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/shim'
installing in ./libsrc/src/dconvert/somp...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/somp'
install in ./libsrc/src/dconvert/somp done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/somp'
installing in ./libsrc/src/dconvert/himr...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/himr'
install in ./libsrc/src/dconvert/himr done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/himr'
installing in ./libsrc/src/dconvert/pq...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pq'
install in ./libsrc/src/dconvert/pq done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pq'
installing in ./libsrc/src/dconvert/signa...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/signa'
install in ./libsrc/src/dconvert/signa done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/signa'
installing in ./libsrc/src/dconvert/ge9800...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/ge9800'
install in ./libsrc/src/dconvert/ge9800 done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/ge9800'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
installing in ./libsrc/support...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/support'
install in ./libsrc/support done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/support'
installing in ./libsrc/docs...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/docs'
install in ./libsrc/docs done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/docs'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
installing in ./support...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/support'
install in ./support done
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/support'

dicom3tools/1.00-20240118131615: RUN: make IMAKE_DEFINES="'-DStripCmd=true' '-DAnsiCCmd=/data/service/hnp/bin/clang' '-DCPlusPlusCmd=/data/service/hnp/bin/clang++' '-DX11IncludePath=/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/include -I/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/include -I/storage/Users/currentUser/.conan2/p/xtran5cc64ce81b809/p/include -I/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include' '-DDisplayLoadFlags=-L/storage/Users/currentUser/.conan2/p/libxe78304f1d8f739/p/lib -L/storage/Users/currentUser/.conan2/p/libx17963afb6a17e9/p/lib -L/storage/Users/currentUser/.conan2/p/libxc498d44a255fe8/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -lX11 -lXext'" IMAKE="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/imake" DEPEND="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/makedepend" MKDIRHIER="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/mkdirhier" INSTALL='/data/service/hnp/bin/busybox install' INSTPGMFLAGS= DESTDIR="/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage" install.man
installing man pages in ./appsrc...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
installing man pages in ./appsrc/acrnema...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/acrnema'
+ /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/hosttools/mkdirhier /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1
/data/service/hnp/bin/busybox install -m 0444 ancreate.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/ancreate.1
/data/service/hnp/bin/busybox install -m 0444 andump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/andump.1
/data/service/hnp/bin/busybox install -m 0444 ancp.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/ancp.1
/data/service/hnp/bin/busybox install -m 0444 andiff.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/andiff.1
install.man in ./appsrc/acrnema done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/acrnema'
installing man pages in ./appsrc/dcdisp...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcdisp'
/data/service/hnp/bin/busybox install -m 0444 dcdisp.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcdisp.1
install.man in ./appsrc/dcdisp done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcdisp'
installing man pages in ./appsrc/dcfile...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcfile'
/data/service/hnp/bin/busybox install -m 0444 dccreate.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dccreate.1
/data/service/hnp/bin/busybox install -m 0444 dcentvfy.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcentvfy.1
/data/service/hnp/bin/busybox install -m 0444 dclutmix.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dclutmix.1
/data/service/hnp/bin/busybox install -m 0444 dcuidchg.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcuidchg.1
/data/service/hnp/bin/busybox install -m 0444 dcdtchg.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcdtchg.1
/data/service/hnp/bin/busybox install -m 0444 dclutburn.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dclutburn.1
/data/service/hnp/bin/busybox install -m 0444 dctopdf.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dctopdf.1
/data/service/hnp/bin/busybox install -m 0444 pdftodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pdftodc.1
/data/service/hnp/bin/busybox install -m 0444 pgxtodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pgxtodc.1
/data/service/hnp/bin/busybox install -m 0444 dcencap.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcencap.1
/data/service/hnp/bin/busybox install -m 0444 dcburn.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcburn.1
/data/service/hnp/bin/busybox install -m 0444 rawftodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/rawftodc.1
/data/service/hnp/bin/busybox install -m 0444 dccomb.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dccomb.1
/data/service/hnp/bin/busybox install -m 0444 dcuncat.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcuncat.1
/data/service/hnp/bin/busybox install -m 0444 dcsrmrg.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcsrmrg.1
/data/service/hnp/bin/busybox install -m 0444 dcostosr.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcostosr.1
/data/service/hnp/bin/busybox install -m 0444 dcrmmeta.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcrmmeta.1
/data/service/hnp/bin/busybox install -m 0444 dcsrdump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcsrdump.1
/data/service/hnp/bin/busybox install -m 0444 dccidump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dccidump.1
/data/service/hnp/bin/busybox install -m 0444 dcsub.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcsub.1
/data/service/hnp/bin/busybox install -m 0444 dcdecmpr.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcdecmpr.1
/data/service/hnp/bin/busybox install -m 0444 dcsort.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcsort.1
/data/service/hnp/bin/busybox install -m 0444 dcproj.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcproj.1
/data/service/hnp/bin/busybox install -m 0444 dcarith.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcarith.1
/data/service/hnp/bin/busybox install -m 0444 dctopgm8.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dctopgm8.1
/data/service/hnp/bin/busybox install -m 0444 dctopgx.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dctopgx.1
/data/service/hnp/bin/busybox install -m 0444 dcpost.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcpost.1
/data/service/hnp/bin/busybox install -m 0444 dcmulti.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcmulti.1
/data/service/hnp/bin/busybox install -m 0444 dctable.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dctable.1
/data/service/hnp/bin/busybox install -m 0444 dctable_decompressingprn.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dctable_decompressingprn.1
/data/service/hnp/bin/busybox install -m 0444 dcmkpres.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcmkpres.1
/data/service/hnp/bin/busybox install -m 0444 dcortho.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcortho.1
/data/service/hnp/bin/busybox install -m 0444 antodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/antodc.1
/data/service/hnp/bin/busybox install -m 0444 dclutdmp.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dclutdmp.1
/data/service/hnp/bin/busybox install -m 0444 dcbriggs.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcbriggs.1
/data/service/hnp/bin/busybox install -m 0444 dccp.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dccp.1
/data/service/hnp/bin/busybox install -m 0444 dcdict.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcdict.1
/data/service/hnp/bin/busybox install -m 0444 dcdirdmp.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcdirdmp.1
/data/service/hnp/bin/busybox install -m 0444 dcdirmk.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcdirmk.1
/data/service/hnp/bin/busybox install -m 0444 dcdump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcdump.1
/data/service/hnp/bin/busybox install -m 0444 dcfile.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcfile.1
/data/service/hnp/bin/busybox install -m 0444 dchist.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dchist.1
/data/service/hnp/bin/busybox install -m 0444 dckey.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dckey.1
/data/service/hnp/bin/busybox install -m 0444 dciodvfy.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dciodvfy.1
/data/service/hnp/bin/busybox install -m 0444 dcmerge.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcmerge.1
/data/service/hnp/bin/busybox install -m 0444 dcposn.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcposn.1
/data/service/hnp/bin/busybox install -m 0444 dcsmpte.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcsmpte.1
/data/service/hnp/bin/busybox install -m 0444 dcsqextr.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcsqextr.1
/data/service/hnp/bin/busybox install -m 0444 dcstats.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcstats.1
/data/service/hnp/bin/busybox install -m 0444 dctoraw.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dctoraw.1
/data/service/hnp/bin/busybox install -m 0444 dctopnm.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dctopnm.1
/data/service/hnp/bin/busybox install -m 0444 pbmtoovl.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pbmtoovl.1
/data/service/hnp/bin/busybox install -m 0444 pnmtodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pnmtodc.1
/data/service/hnp/bin/busybox install -m 0444 rawtodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/rawtodc.1
/data/service/hnp/bin/busybox install -m 0444 dcpatmpl.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcpatmpl.1
/data/service/hnp/bin/busybox install -m 0444 dcswab.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcswab.1
/data/service/hnp/bin/busybox install -m 0444 dcjls.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcjls.1
/data/service/hnp/bin/busybox install -m 0444 dcunjls.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcunjls.1
/data/service/hnp/bin/busybox install -m 0444 dcj2k.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcj2k.1
/data/service/hnp/bin/busybox install -m 0444 dcjpeg.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcjpeg.1
/data/service/hnp/bin/busybox install -m 0444 dcunjpeg.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcunjpeg.1
/data/service/hnp/bin/busybox install -m 0444 dcunjpeg.all.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcunjpeg.all.1
/data/service/hnp/bin/busybox install -m 0444 dcunrgb.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcunrgb.1
/data/service/hnp/bin/busybox install -m 0444 dcanon.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcanon.1
/data/service/hnp/bin/busybox install -m 0444 dcmvhier.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcmvhier.1
/data/service/hnp/bin/busybox install -m 0444 dcmvhier.uid.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcmvhier.uid.1
/data/service/hnp/bin/busybox install -m 0444 dcmvhier.datedesc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcmvhier.datedesc.1
/data/service/hnp/bin/busybox install -m 0444 dcmvhier.datedescnoid.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcmvhier.datedescnoid.1
make[2]: *** No rule to make target 'dcmvhier.8only', needed by 'install.man'.  Stop.
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcfile'
installing man pages in ./appsrc/dcintro...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcintro'
/data/service/hnp/bin/busybox install -m 0444 dcintro.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcintro.1
/data/service/hnp/bin/busybox install -m 0444 optin.so /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/optin.so
/data/service/hnp/bin/busybox install -m 0444 optout.so /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/optout.so
/data/service/hnp/bin/busybox install -m 0444 gen.so /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/gen.so
/data/service/hnp/bin/busybox install -m 0444 genin.so /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/genin.so
/data/service/hnp/bin/busybox install -m 0444 genout.so /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/genout.so
/data/service/hnp/bin/busybox install -m 0444 binin.so /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/binin.so
/data/service/hnp/bin/busybox install -m 0444 binout.so /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/binout.so
install.man in ./appsrc/dcintro done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dcintro'
installing man pages in ./appsrc/misc...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/misc'
/data/service/hnp/bin/busybox install -m 0444 bmpdump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/bmpdump.1
/data/service/hnp/bin/busybox install -m 0444 pgmtobmp.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pgmtobmp.1
/data/service/hnp/bin/busybox install -m 0444 dumpwhat.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dumpwhat.1
/data/service/hnp/bin/busybox install -m 0444 dcunmeta.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dcunmeta.1
/data/service/hnp/bin/busybox install -m 0444 binpatch.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/binpatch.1
/data/service/hnp/bin/busybox install -m 0444 jpegdump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/jpegdump.1
/data/service/hnp/bin/busybox install -m 0444 jpegsplit.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/jpegsplit.1
/data/service/hnp/bin/busybox install -m 0444 pbmswbit.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pbmswbit.1
/data/service/hnp/bin/busybox install -m 0444 pnmpred.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pnmpred.1
/data/service/hnp/bin/busybox install -m 0444 pnmtoraw.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pnmtoraw.1
/data/service/hnp/bin/busybox install -m 0444 rawarith.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/rawarith.1
/data/service/hnp/bin/busybox install -m 0444 rawdiff.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/rawdiff.1
/data/service/hnp/bin/busybox install -m 0444 rawmask.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/rawmask.1
/data/service/hnp/bin/busybox install -m 0444 rawnjl.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/rawnjl.1
/data/service/hnp/bin/busybox install -m 0444 rawnjl2.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/rawnjl2.1
/data/service/hnp/bin/busybox install -m 0444 dumptiff.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/dumptiff.1
install.man in ./appsrc/misc done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/misc'
installing man pages in ./appsrc/simple...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
installing man pages in ./appsrc/simple/ge9800...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/ge9800'
/data/service/hnp/bin/busybox install -m 0444 ge98topgm.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/ge98topgm.1
/data/service/hnp/bin/busybox install -m 0444 ge98id.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/ge98id.1
install.man in ./appsrc/simple/ge9800 done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/ge9800'
installing man pages in ./appsrc/simple/genesis...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/genesis'
/data/service/hnp/bin/busybox install -m 0444 gentopgm.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/gentopgm.1
install.man in ./appsrc/simple/genesis done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/genesis'
installing man pages in ./appsrc/simple/pace...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/pace'
/data/service/hnp/bin/busybox install -m 0444 pacetopgm.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pacetopgm.1
install.man in ./appsrc/simple/pace done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/pace'
installing man pages in ./appsrc/simple/signa...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/signa'
/data/service/hnp/bin/busybox install -m 0444 sgntopgm.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/sgntopgm.1
install.man in ./appsrc/simple/signa done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/signa'
installing man pages in ./appsrc/simple/somatom...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/somatom'
/data/service/hnp/bin/busybox install -m 0444 somtopgm.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/somtopgm.1
install.man in ./appsrc/simple/somatom done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/somatom'
installing man pages in ./appsrc/simple/sytec...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/sytec'
/data/service/hnp/bin/busybox install -m 0444 syttopgm.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/syttopgm.1
install.man in ./appsrc/simple/sytec done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/sytec'
installing man pages in ./appsrc/simple/vision...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/vision'
/data/service/hnp/bin/busybox install -m 0444 vsntopgm.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/vsntopgm.1
install.man in ./appsrc/simple/vision done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple/vision'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/simple'
installing man pages in ./appsrc/dconvert...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
installing man pages in ./appsrc/dconvert/support...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/support'
install.man in ./appsrc/dconvert/support done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/support'
installing man pages in ./appsrc/dconvert/xxxx...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/xxxx'
install.man in ./appsrc/dconvert/xxxx done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/xxxx'
installing man pages in ./appsrc/dconvert/pace...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pace'
/data/service/hnp/bin/busybox install -m 0444 pacetodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pacetodc.1
/data/service/hnp/bin/busybox install -m 0444 pacedump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pacedump.1
/data/service/hnp/bin/busybox install -m 0444 paceunid.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/paceunid.1
install.man in ./appsrc/dconvert/pace done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pace'
installing man pages in ./appsrc/dconvert/imtn...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/imtn'
/data/service/hnp/bin/busybox install -m 0444 imtntodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/imtntodc.1
/data/service/hnp/bin/busybox install -m 0444 imtndump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/imtndump.1
install.man in ./appsrc/dconvert/imtn done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/imtn'
installing man pages in ./appsrc/dconvert/gen...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gen'
/data/service/hnp/bin/busybox install -m 0444 gentodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/gentodc.1
/data/service/hnp/bin/busybox install -m 0444 gendump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/gendump.1
/data/service/hnp/bin/busybox install -m 0444 gentodc.dat.all.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/gentodc.dat.all.1
install.man in ./appsrc/dconvert/gen done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gen'
installing man pages in ./appsrc/dconvert/gaw...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gaw'
/data/service/hnp/bin/busybox install -m 0444 gawtodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/gawtodc.1
/data/service/hnp/bin/busybox install -m 0444 gawdump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/gawdump.1
install.man in ./appsrc/dconvert/gaw done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/gaw'
installing man pages in ./appsrc/dconvert/shim...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/shim'
/data/service/hnp/bin/busybox install -m 0444 shimtodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/shimtodc.1
/data/service/hnp/bin/busybox install -m 0444 shimdump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/shimdump.1
install.man in ./appsrc/dconvert/shim done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/shim'
installing man pages in ./appsrc/dconvert/somp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/somp'
/data/service/hnp/bin/busybox install -m 0444 somptodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/somptodc.1
/data/service/hnp/bin/busybox install -m 0444 sompdump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/sompdump.1
install.man in ./appsrc/dconvert/somp done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/somp'
installing man pages in ./appsrc/dconvert/himr...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/himr'
/data/service/hnp/bin/busybox install -m 0444 himrtodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/himrtodc.1
/data/service/hnp/bin/busybox install -m 0444 himrdump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/himrdump.1
/data/service/hnp/bin/busybox install -m 0444 himrunid.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/himrunid.1
install.man in ./appsrc/dconvert/himr done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/himr'
installing man pages in ./appsrc/dconvert/pq...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pq'
/data/service/hnp/bin/busybox install -m 0444 pqtodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pqtodc.1
/data/service/hnp/bin/busybox install -m 0444 pqdump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pqdump.1
/data/service/hnp/bin/busybox install -m 0444 pqsplit.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/pqsplit.1
install.man in ./appsrc/dconvert/pq done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/pq'
installing man pages in ./appsrc/dconvert/toshiba...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/toshiba'
/data/service/hnp/bin/busybox install -m 0444 toshtodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/toshtodc.1
install.man in ./appsrc/dconvert/toshiba done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/toshiba'
installing man pages in ./appsrc/dconvert/signa...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/signa'
/data/service/hnp/bin/busybox install -m 0444 sgntodc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/sgntodc.1
/data/service/hnp/bin/busybox install -m 0444 sgndump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/sgndump.1
install.man in ./appsrc/dconvert/signa done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/signa'
installing man pages in ./appsrc/dconvert/ge9800...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/ge9800'
/data/service/hnp/bin/busybox install -m 0444 ge9800todc.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/ge9800todc.1
/data/service/hnp/bin/busybox install -m 0444 ge9800dump.man /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/stage/usr/local/man/man1/ge9800dump.1
install.man in ./appsrc/dconvert/ge9800 done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert/ge9800'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc/dconvert'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/appsrc'
installing man pages in ./config...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/config'
install.man in ./config done
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/config'
installing man pages in ./libsrc...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
installing man pages in ./libsrc/standard...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
installing man pages in ./libsrc/standard/elmdict...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/elmdict'
install.man in ./libsrc/standard/elmdict done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/elmdict'
installing man pages in ./libsrc/standard/module...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/module'
install.man in ./libsrc/standard/module done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/module'
installing man pages in ./libsrc/standard/iodcomp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/iodcomp'
install.man in ./libsrc/standard/iodcomp done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/iodcomp'
installing man pages in ./libsrc/standard/strval...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/strval'
install.man in ./libsrc/standard/strval done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard/strval'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/standard'
installing man pages in ./libsrc/include...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
installing man pages in ./libsrc/include/dcdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dcdisp'
install.man in ./libsrc/include/dcdisp done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dcdisp'
installing man pages in ./libsrc/include/dconvert...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dconvert'
install.man in ./libsrc/include/dconvert done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dconvert'
installing man pages in ./libsrc/include/dctool...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dctool'
install.man in ./libsrc/include/dctool done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/dctool'
installing man pages in ./libsrc/include/generic...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/generic'
install.man in ./libsrc/include/generic done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/generic'
installing man pages in ./libsrc/include/locale...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/locale'
install.man in ./libsrc/include/locale done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/locale'
installing man pages in ./libsrc/include/ourdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/ourdisp'
install.man in ./libsrc/include/ourdisp done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/ourdisp'
installing man pages in ./libsrc/include/pixeldat...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/pixeldat'
install.man in ./libsrc/include/pixeldat done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include/pixeldat'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/include'
installing man pages in ./libsrc/lib...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/lib'
install.man in ./libsrc/lib done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/lib'
installing man pages in ./libsrc/src...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
installing man pages in ./libsrc/src/dcdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dcdisp'
install.man in ./libsrc/src/dcdisp done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dcdisp'
installing man pages in ./libsrc/src/dctool...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dctool'
install.man in ./libsrc/src/dctool done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dctool'
installing man pages in ./libsrc/src/generic...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/generic'
install.man in ./libsrc/src/generic done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/generic'
installing man pages in ./libsrc/src/locale...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/locale'
install.man in ./libsrc/src/locale done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/locale'
installing man pages in ./libsrc/src/ourdisp...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/ourdisp'
install.man in ./libsrc/src/ourdisp done
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/ourdisp'
installing man pages in ./libsrc/src/dconvert...
make[3]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
installing man pages in ./libsrc/src/dconvert/support...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/support'
install.man in ./libsrc/src/dconvert/support done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/support'
installing man pages in ./libsrc/src/dconvert/pace...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pace'
install.man in ./libsrc/src/dconvert/pace done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pace'
installing man pages in ./libsrc/src/dconvert/xxxx...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/xxxx'
install.man in ./libsrc/src/dconvert/xxxx done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/xxxx'
installing man pages in ./libsrc/src/dconvert/imtn...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/imtn'
install.man in ./libsrc/src/dconvert/imtn done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/imtn'
installing man pages in ./libsrc/src/dconvert/gen...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gen'
install.man in ./libsrc/src/dconvert/gen done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gen'
installing man pages in ./libsrc/src/dconvert/gaw...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gaw'
install.man in ./libsrc/src/dconvert/gaw done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/gaw'
installing man pages in ./libsrc/src/dconvert/shim...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/shim'
install.man in ./libsrc/src/dconvert/shim done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/shim'
installing man pages in ./libsrc/src/dconvert/somp...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/somp'
install.man in ./libsrc/src/dconvert/somp done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/somp'
installing man pages in ./libsrc/src/dconvert/himr...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/himr'
install.man in ./libsrc/src/dconvert/himr done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/himr'
installing man pages in ./libsrc/src/dconvert/pq...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pq'
install.man in ./libsrc/src/dconvert/pq done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/pq'
installing man pages in ./libsrc/src/dconvert/signa...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/signa'
install.man in ./libsrc/src/dconvert/signa done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/signa'
installing man pages in ./libsrc/src/dconvert/ge9800...
make[4]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/ge9800'
install.man in ./libsrc/src/dconvert/ge9800 done
make[4]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert/ge9800'
make[3]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src/dconvert'
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/src'
installing man pages in ./libsrc/support...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/support'
install.man in ./libsrc/support done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/support'
installing man pages in ./libsrc/docs...
make[2]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/docs'
install.man in ./libsrc/docs done
make[2]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc/docs'
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/libsrc'
installing man pages in ./support...
make[1]: Entering directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/support'
install.man in ./support done
make[1]: Leaving directory '/storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/b/work/support'

dicom3tools/1.00-20240118131615: package(): Packaged 118 files
dicom3tools/1.00-20240118131615: package(): Packaged 2 '.all' files: dcunjpeg.all, gentodc.dat.all
dicom3tools/1.00-20240118131615: package(): Packaged 1 '.uid' file: dcmvhier.uid
dicom3tools/1.00-20240118131615: package(): Packaged 1 '.datedesc' file: dcmvhier.datedesc
dicom3tools/1.00-20240118131615: package(): Packaged 1 '.datedescnoid' file: dcmvhier.datedescnoid
dicom3tools/1.00-20240118131615: package(): Packaged 123 '.1' files
dicom3tools/1.00-20240118131615: package(): Packaged 7 '.so' files
dicom3tools/1.00-20240118131615: Created package revision 91ab507d3ed4d563fcc376da6c9ff115
dicom3tools/1.00-20240118131615: Package '5eb970f88879b3d0c0e7ef18bb72a19b24bbb2cb' created
dicom3tools/1.00-20240118131615: Full package reference: dicom3tools/1.00-20240118131615#dbc4912b37a88e0d156227705fe835f2:5eb970f88879b3d0c0e7ef18bb72a19b24bbb2cb#91ab507d3ed4d563fcc376da6c9ff115
dicom3tools/1.00-20240118131615: Package folder /storage/Users/currentUser/.conan2/p/b/dicomdf0e797bf327c/p

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    dicom3tools/1.00-20240118131615 (test package): /storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/archives/d/dicom3tools/1.00-20240118131615/test_package/conanfile.py
Requirements
    dicom3tools/1.00-20240118131615#dbc4912b37a88e0d156227705fe835f2 - Cache
    libx11/6.4.0#63e25e48c3af73db324ce61d0dba9cce - Cache
    libxau/1.0.11#e70832a1f31a85a0398300bf72179ad9 - Cache
    libxcb/1.16#eb6f913ae9cabe62e164fe5fb3ba9391 - Cache
    libxdmcp/1.1.5#8aaf268abc5f64d20cb46f0ec0c6fdb7 - Cache
    libxext/6.4.0#20942ab436730e84acb01dcf565fda68 - Cache
    xorgproto/2025.1#f5274e33759da898a6e8d87d7708d47c - Cache
    xtrans/1.6.0#664ea4b0b501c5f144fc094ab1a4dfc5 - Cache
Test requirements
    check/0.15.2#6d41c3078e77093b6b9dfe97b95e0f9c - Cache
Build requirements
    perl/5.42.2#13c4f5bde5668df0b7268c4d0c01073c - Cache
    xcb-proto/1.17.0#f985020ceb16e7e9ea7af4f2e57652b5 - Cache

======== Computing necessary packages ========
Requirements
    dicom3tools/1.00-20240118131615#dbc4912b37a88e0d156227705fe835f2:5eb970f88879b3d0c0e7ef18bb72a19b24bbb2cb#91ab507d3ed4d563fcc376da6c9ff115 - Cache
    libx11/6.4.0#63e25e48c3af73db324ce61d0dba9cce:c042bc3ef1476cfe65d9b8d95c3088cf1ad1a5ab#0e5934cee0577987a9f173673f0cb4a2 - Cache
    libxau/1.0.11#e70832a1f31a85a0398300bf72179ad9:b33b73a64003feb619a47ac2da762d7e7521ab18#2875a48c0f9c6168a810db745fe96324 - Cache
    libxcb/1.16#eb6f913ae9cabe62e164fe5fb3ba9391:d9d8d69421c16a44ece624cdbba864af799b6b14#ac43d5ee9e4e48933f548d4dd8c72790 - Cache
    libxdmcp/1.1.5#8aaf268abc5f64d20cb46f0ec0c6fdb7:b33b73a64003feb619a47ac2da762d7e7521ab18#b9dab63027b7d0ce0f0c04f8ceef5197 - Cache
    libxext/6.4.0#20942ab436730e84acb01dcf565fda68:e647863c487673f3505fad09e4305079038bb22d#b056ec34282b1e4cef84cb5be71b6aab - Cache
Test requirements
Build requirements
Skipped binaries
    xorgproto/2025.1, xtrans/1.6.0, check/0.15.2, perl/5.42.2, xcb-proto/1.17.0

======== Installing packages ========
libxau/1.0.11: Already installed! (1 of 6)
libxdmcp/1.1.5: Already installed! (2 of 6)
libxcb/1.16: Already installed! (3 of 6)
libx11/6.4.0: Already installed! (4 of 6)
libxext/6.4.0: Already installed! (5 of 6)
dicom3tools/1.00-20240118131615: Already installed! (6 of 6)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/archives/d/dicom3tools/1.00-20240118131615/test_package/build-release
dicom3tools/1.00-20240118131615 (test package): Test package build: build-release
dicom3tools/1.00-20240118131615 (test package): Test package build folder: /storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/archives/d/dicom3tools/1.00-20240118131615/test_package/build-release
dicom3tools/1.00-20240118131615 (test package): Writing generators to /storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/archives/d/dicom3tools/1.00-20240118131615/test_package/build-release/conan
dicom3tools/1.00-20240118131615 (test package): Generator 'VirtualRunEnv' calling 'generate()'
dicom3tools/1.00-20240118131615 (test package): Generating aggregated env files
dicom3tools/1.00-20240118131615 (test package): Generated aggregated env files: ['conanrun.sh', 'conanbuild.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
dicom3tools/1.00-20240118131615 (test package): Running test()
dicom3tools/1.00-20240118131615 (test package): RUN: /storage/Users/currentUser/.harmonybrew/bin/bash "/storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/archives/d/dicom3tools/1.00-20240118131615/test_package/test.sh"
PASS: found dccreate
PASS: found dcdump
PASS: found dciodvfy
PASS: found dckey
PASS: found dcdict
PASS: found dcstats
PASS: found dccp
PASS: dccreate wrote a DICOM file (rc=0)
PASS: created file is non-empty (658 bytes)
PASS: file has the Part 10 DICM magic at offset 128
PASS: dcdump read back the Patient ID that was set
PASS: dcdump read back the Patient Name that was set
PASS: explicit VR little endian transfer syntax recorded in the meta header
PASS: dcdict resolved PatientName to (0x0010,0x0010)
PASS: dcdict reports the PN value representation
PASS: dckey described the PatientName tag
PASS: dciodvfy produced a validation report
PASS: dciodvfy read the file dccreate produced
PASS: dcstats reported the missing pixel data
PASS: dcdump rejected a truncated data set (rc=1)
PASS: dciodvfy rejected a non-DICOM file (rc=1)
PASS: dccp re-encoded the file meta information (394 bytes)

dicom3tools test_package: 22 passed, 0 failed

[ok] dicom3tools/1.00-20240118131615 — conan create passed
[step] L1: Verifying test execution from conan create log...
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[step] L1c: No upstream make check/ctest in log (may be in test_package only)
[step] L4: Scanning patches for dangerous functions...
[warn] L4: Dangerous functions found in patches:
/storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/archives/d/dicom3tools/1.00-20240118131615/patches/0004-imake-build-on-musl-and-modern-cpp.patch
[step] L5: Baseline artifact check...
[ok] L5: bin/ has content
[step] L1e: Destructive negative test (R34)...
        [sabotage] bin/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on dicom3tools
[step] L2: Smoke test (version/help check)...
[warn] L2: ancp --version/--help failed (non-blocking)
[warn] L2: ancreate --version/--help failed (non-blocking)
[warn] L2: andiff --version/--help failed (non-blocking)
[warn] L2: andump --version/--help failed (non-blocking)
[warn] L2: antodc --version/--help failed (non-blocking)
[warn] L2: binpatch --version/--help failed (non-blocking)
[warn] L2: bmpdump --version/--help failed (non-blocking)
[ok] L2: dcanon --version OK
[warn] L2: dcarith --version/--help failed (non-blocking)
[warn] L2: dcbriggs --version/--help failed (non-blocking)
[warn] L2: dcburn --version/--help failed (non-blocking)
[warn] L2: dccidump --version/--help failed (non-blocking)
[warn] L2: dccomb --version/--help failed (non-blocking)
[warn] L2: dccp --version/--help failed (non-blocking)
[warn] L2: dccreate --version/--help failed (non-blocking)
[warn] L2: dcdecmpr --version/--help failed (non-blocking)
[warn] L2: dcdict --version/--help failed (non-blocking)
[warn] L2: dcdirdmp --version/--help failed (non-blocking)
[ok] L2: dcdirmk --version OK
[warn] L2: dcdisp --version/--help failed (non-blocking)
[warn] L2: dcdtchg --version/--help failed (non-blocking)
[warn] L2: dcdump --version/--help failed (non-blocking)
[warn] L2: dcencap --version/--help failed (non-blocking)
[warn] L2: dcentvfy --version/--help failed (non-blocking)
[warn] L2: dcfile --version/--help failed (non-blocking)
[warn] L2: dchist --version/--help failed (non-blocking)
[warn] L2: dciodvfy --version/--help failed (non-blocking)
[warn] L2: dcj2k --version/--help failed (non-blocking)
[warn] L2: dcjls --version/--help failed (non-blocking)
[warn] L2: dcjpeg --version/--help failed (non-blocking)
[warn] L2: dckey --version/--help failed (non-blocking)
[warn] L2: dclutburn --version/--help failed (non-blocking)
[warn] L2: dclutdmp --version/--help failed (non-blocking)
[warn] L2: dclutmix --version/--help failed (non-blocking)
[warn] L2: dcmerge --version/--help failed (non-blocking)
[warn] L2: dcmkpres --version/--help failed (non-blocking)
[warn] L2: dcmulti --version/--help failed (non-blocking)
[ok] L2: dcmvhier --version OK
[ok] L2: dcmvhier.datedesc --version OK
[ok] L2: dcmvhier.datedescnoid --version OK
[ok] L2: dcmvhier.uid --version OK
[warn] L2: dcortho --version/--help failed (non-blocking)
[warn] L2: dcostosr --version/--help failed (non-blocking)
[warn] L2: dcpatmpl --version/--help failed (non-blocking)
[warn] L2: dcposn --version/--help failed (non-blocking)
[warn] L2: dcpost --version/--help failed (non-blocking)
[warn] L2: dcproj --version/--help failed (non-blocking)
[warn] L2: dcrmmeta --version/--help failed (non-blocking)
[warn] L2: dcsmpte --version/--help failed (non-blocking)
[ok] L2: dcsort --version OK
[warn] L2: dcsqextr --version/--help failed (non-blocking)
[warn] L2: dcsrdump --version/--help failed (non-blocking)
[warn] L2: dcsrmrg --version/--help failed (non-blocking)
[warn] L2: dcstats --version/--help failed (non-blocking)
[warn] L2: dcsub --version/--help failed (non-blocking)
[ok] L2: dcswab --version OK
[ok] L2: dctable --version OK
[ok] L2: dctable_decompressingprn --version OK
[warn] L2: dctopdf --version/--help failed (non-blocking)
[warn] L2: dctopgm8 --version/--help failed (non-blocking)
[warn] L2: dctopgx --version/--help failed (non-blocking)
[warn] L2: dctopnm --version/--help failed (non-blocking)
[warn] L2: dctoraw --version/--help failed (non-blocking)
[warn] L2: dcuidchg --version/--help failed (non-blocking)
[warn] L2: dcuncat --version/--help failed (non-blocking)
[warn] L2: dcunjls --version/--help failed (non-blocking)
[warn] L2: dcunjpeg --version/--help failed (non-blocking)
[ok] L2: dcunjpeg.all --version OK
[ok] L2: dcunmeta --version OK
[warn] L2: dcunrgb --version/--help failed (non-blocking)
[ok] L2: dumptiff --version OK
[warn] L2: dumpwhat --version/--help failed (non-blocking)
[warn] L2: gawdump --version/--help failed (non-blocking)
[warn] L2: gawtodc --version/--help failed (non-blocking)
[warn] L2: ge9800dump --version/--help failed (non-blocking)
[warn] L2: ge9800todc --version/--help failed (non-blocking)
[warn] L2: ge98id --version/--help failed (non-blocking)
[warn] L2: ge98topgm --version/--help failed (non-blocking)
[warn] L2: gendump --version/--help failed (non-blocking)
[warn] L2: gentodc --version/--help failed (non-blocking)
[ok] L2: gentodc.dat.all --version OK
[warn] L2: gentopgm --version/--help failed (non-blocking)
[warn] L2: himrdump --version/--help failed (non-blocking)
[warn] L2: himrtodc --version/--help failed (non-blocking)
[warn] L2: himrunid --version/--help failed (non-blocking)
[warn] L2: imtndump --version/--help failed (non-blocking)
[warn] L2: imtntodc --version/--help failed (non-blocking)
[ok] L2: jpegdump --version OK
[ok] L2: jpegsplit --version OK
[warn] L2: pacedump --version/--help failed (non-blocking)
[warn] L2: pacetodc --version/--help failed (non-blocking)
[warn] L2: pacetopgm --version/--help failed (non-blocking)
[warn] L2: paceunid --version/--help failed (non-blocking)
[warn] L2: pbmswbit --version/--help failed (non-blocking)
[warn] L2: pbmtoovl --version/--help failed (non-blocking)
[warn] L2: pdftodc --version/--help failed (non-blocking)
[warn] L2: pgmtobmp --version/--help failed (non-blocking)
[warn] L2: pgxtodc --version/--help failed (non-blocking)
[warn] L2: pnmpred --version/--help failed (non-blocking)
[warn] L2: pnmtodc --version/--help failed (non-blocking)
[warn] L2: pnmtoraw --version/--help failed (non-blocking)
[warn] L2: pqdump --version/--help failed (non-blocking)
[ok] L2: pqsplit --version OK
[warn] L2: pqtodc --version/--help failed (non-blocking)
[warn] L2: rawarith --version/--help failed (non-blocking)
[warn] L2: rawdiff --version/--help failed (non-blocking)
[warn] L2: rawftodc --version/--help failed (non-blocking)
[warn] L2: rawmask --version/--help failed (non-blocking)
[warn] L2: rawnjl --version/--help failed (non-blocking)
[warn] L2: rawnjl2 --version/--help failed (non-blocking)
[warn] L2: rawtodc --version/--help failed (non-blocking)
[warn] L2: sgndump --version/--help failed (non-blocking)
[warn] L2: sgntodc --version/--help failed (non-blocking)
[warn] L2: sgntopgm --version/--help failed (non-blocking)
[warn] L2: shimdump --version/--help failed (non-blocking)
[warn] L2: shimtodc --version/--help failed (non-blocking)
[warn] L2: sompdump --version/--help failed (non-blocking)
[warn] L2: somptodc --version/--help failed (non-blocking)
[warn] L2: somtopgm --version/--help failed (non-blocking)
[warn] L2: syttopgm --version/--help failed (non-blocking)
[warn] L2: toshtodc --version/--help failed (non-blocking)
[warn] L2: vsntopgm --version/--help failed (non-blocking)

L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: ancp version/help failed, ancreate failed, andiff failed, andump failed, antodc failed, binpatch failed, bmpdump failed, dcanon --version OK, dcarith failed, dcbriggs failed, dcburn failed, dccidump failed, dccomb failed, dccp failed, dccreate failed, dcdecmpr failed, dcdict failed, dcdirdmp failed, dcdirmk --version OK, dcdisp failed, dcdtchg failed, dcdump failed, dcencap failed, dcentvfy failed, dcfile failed, dchist failed, dciodvfy failed, dcj2k failed, dcjls failed, dcjpeg failed, dckey failed, dclutburn failed, dclutdmp failed, dclutmix failed, dcmerge failed, dcmkpres failed, dcmulti failed, dcmvhier --version OK, dcmvhier.datedesc --version OK, dcmvhier.datedescnoid --version OK, dcmvhier.uid --version OK, dcortho failed, dcostosr failed, dcpatmpl failed, dcposn failed, dcpost failed, dcproj failed, dcrmmeta failed, dcsmpte failed, dcsort --version OK, dcsqextr failed, dcsrdump failed, dcsrmrg failed, dcstats failed, dcsub failed, dcswab --version OK, dctable --version OK, dctable_decompressingprn --version OK, dctopdf failed, dctopgm8 failed, dctopgx failed, dctopnm failed, dctoraw failed, dcuidchg failed, dcuncat failed, dcunjls failed, dcunjpeg failed, dcunjpeg.all --version OK, dcunmeta --version OK, dcunrgb failed, dumptiff --version OK, dumpwhat failed, gawdump failed, gawtodc failed, ge9800dump failed, ge9800todc failed, ge98id failed, ge98topgm failed, gendump failed, gentodc failed, gentodc.dat.all --version OK, gentopgm failed, himrdump failed, himrtodc failed, himrunid failed, imtndump failed, imtntodc failed, jpegdump --version OK, jpegsplit --version OK, pacedump failed, pacetodc failed, pacetopgm failed, paceunid failed, pbmswbit failed, pbmtoovl failed, pdftodc failed, pgmtobmp failed, pgxtodc failed, pnmpred failed, pnmtodc failed, pnmtoraw failed, pqdump failed, pqsplit --version OK, pqtodc failed, rawarith failed, rawdiff failed, rawftodc failed, rawmask failed, rawnjl failed, rawnjl2 failed, rawtodc failed, sgndump failed, sgntodc failed, sgntopgm failed, shimdump failed, shimtodc failed, sompdump failed, somptodc failed, somtopgm failed, syttopgm failed, toshtodc failed, vsntopgm failed
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
<!-- END VERBATIM LOG -->

结果摘要（原文末尾）：

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: ancp version/help failed, ancreate failed, andiff failed, andump failed, antodc failed, binpatch failed, bmpdump failed, dcanon --version OK, dcarith failed, dcbriggs failed, dcburn failed, dccidump failed, dccomb failed, dccp failed, dccreate failed, dcdecmpr failed, dcdict failed, dcdirdmp failed, dcdirmk --version OK, dcdisp failed, dcdtchg failed, dcdump failed, dcencap failed, dcentvfy failed, dcfile failed, dchist failed, dciodvfy failed, dcj2k failed, dcjls failed, dcjpeg failed, dckey failed, dclutburn failed, dclutdmp failed, dclutmix failed, dcmerge failed, dcmkpres failed, dcmulti failed, dcmvhier --version OK, dcmvhier.datedesc --version OK, dcmvhier.datedescnoid --version OK, dcmvhier.uid --version OK, dcortho failed, dcostosr failed, dcpatmpl failed, dcposn failed, dcpost failed, dcproj failed, dcrmmeta failed, dcsmpte failed, dcsort --version OK, dcsqextr failed, dcsrdump failed, dcsrmrg failed, dcstats failed, dcsub failed, dcswab --version OK, dctable --version OK, dctable_decompressingprn --version OK, dctopdf failed, dctopgm8 failed, dctopgx failed, dctopnm failed, dctoraw failed, dcuidchg failed, dcuncat failed, dcunjls failed, dcunjpeg failed, dcunjpeg.all --version OK, dcunmeta --version OK, dcunrgb failed, dumptiff --version OK, dumpwhat failed, gawdump failed, gawtodc failed, ge9800dump failed, ge9800todc failed, ge98id failed, ge98topgm failed, gendump failed, gentodc failed, gentodc.dat.all --version OK, gentopgm failed, himrdump failed, himrtodc failed, himrunid failed, imtndump failed, imtntodc failed, jpegdump --version OK, jpegsplit --version OK, pacedump failed, pacetodc failed, pacetopgm failed, paceunid failed, pbmswbit failed, pbmtoovl failed, pdftodc failed, pgmtobmp failed, pgxtodc failed, pnmpred failed, pnmtodc failed, pnmtoraw failed, pqdump failed, pqsplit --version OK, pqtodc failed, rawarith failed, rawdiff failed, rawftodc failed, rawmask failed, rawnjl failed, rawnjl2 failed, rawtodc failed, sgndump failed, sgntodc failed, sgntopgm failed, shimdump failed, shimtodc failed, sompdump failed, somptodc failed, somtopgm failed, syttopgm failed, toshtodc failed, vsntopgm failed
L4_RESULT=warn: dangerous functions in patches
L5_RESULT=pass: bin/ has content
```

注 1：`L4 warn` 的对象是**补丁文本**里出现的危险函数（imake/makedepend 是 1991 年的 X11 代码，
本身含 `strcpy`/`sprintf` 等），不是本包产物；产物侧的 L4 为人工补测 102/102 PASS，
见 `conan-verify-supplement.md`。

注 2：`L2` 那一长串 `failed` 是 W3 探针**只试带 rc=0 的 `--version`/`--help`** 造成的
假阴性（本包老式 CLI 的 `--version` 打印后返回非 0，其余工具不认长选项），
`L2_RESULT` 本身仍为 pass；真实业务行为由人工补测的 36 项断言覆盖
（`l2-consumer-test-evidence.md` → 36 passed, 0 failed）。

注 3：本文件与历轮同名文件**不是逐字节可复现的**——可复现的是 `L0`–`L5` 的结论行
（历轮逐行相同）。跨轮差异来自**四类**，不限于缓存分片目录名：

1. 缓存分片目录名（`p/b/<前缀><hash>`）与其下的绝对路径——每轮清缓存重建都会变；
2. 日志内嵌的时间戳（如 `Exported: … (HH:MM:SS UTC)` 与其中的修订哈希）；
3. 随本 PR 改动文件数变化的内容（如 `pr.diff` 的文件数/行数）与随机 PID（如 `GMfifo` 编号）；
4. **并行构建输出的行序交错**——上游 make 递归，两轮之间同一批编译行的相对顺序可能不同（含 `N warnings generated.`、相邻头文件名成对换位等），条数相同。

因此**不要**按「差异行是否含分片目录名」判断两轮 W3 日志等价；判据取 `L0`–`L5` 结果行与总体结论。
