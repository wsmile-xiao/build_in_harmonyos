# libdatovka 0.7.3 adaptation notes

## Build environment
- Build system: autotools (configure + make)
- Date: 2026-09-16
- Compiler: clang (HarmonyOS PC aarch64, native build)
- Status: built (pending device preflight)

## Configure
```
./configure --disable-doc --enable-openssl-backend --disable-nls \
  --disable-fatalwarnings --with-libcurl --enable-test \
  --enable-static --disable-shared \
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
```

## Dependencies (all published recipes with conanfile.py in-tree)
- curl/8.15.0 (repo-hardened `curl`, not CCI `libcurl`; bti/034 precedent)
- libxml2/2.15.3.1 (repo-unique; CCI 2.15.3 pulls cmake/4.4.3 tool -> KeyError OHOS)
- expat/2.8.2.1
- openssl/3.5.6.1 (override, matches curl pin; 1.1.1w EOL + conflicts curl >=3 range)
- gnutls dropped (was test-only requires): only test/simline consumes it
  (libserver.la LIBADD @LIBGNUTLS_LIBS@, server.c includes gnutls.h);
  test/offline LDADD has no gnutls. gnutls chain (nettle->gmp w/o OHOS
  binary) forces m4 source build whose configure needs missing
  /data/service/hnp/bin/bash (Error 127). Probe stubbed via
  LIBGNUTLS_CFLAGS=-I. / LIBGNUTLS_LIBS=-L. configure vars; build() compiles
  only src/ and runs test/offline check, skipping simline.
- json-c >= 0.9 (hard upstream req) vendored as static 0.18 in build():
  same S3 tarball as hardened json-c/0.18 recipe; CCI/ohpcd share version
  0.18 so preflight picks CCI (SYSTEM_NAME=OHOS unknown to cmake) while
  CI picks ohpcd — no unique version exists, hence vendoring.
- pkgconf/3.0.5 tool_requires (hardened in-tree): device has no system
  pkg-config (configure "checking for pkg-config... no" -> hard error).
  Package ships bin/pkgconf without bin/pkg-config alias, so build()
  creates a hmbs-shims/pkg-config symlink (cassbeam/1.1 precedent) and
  passes PKG_CONFIG + PATH prefix inline to configure.

## Issues and fixes
| # | Issue | Root cause | Fix |
|---|-------|------------|-----|
| 1 | config.status subs1.awk permission denied on HMDFS | configure `umask 077` + setgid dirs -> drwx--S--- | replace `umask 077` with `umask 022` in configure |
| 2 | doc build needs docbook-xsl/libxslt | not in OHOS repo | `--disable-doc` |
| 3 | gpgme/libgcrypt chain heavy | optional backend | `--enable-openssl-backend` |
| 4 | online tests need live ISDS network | no credentials in CI | run only test/offline, document online as not-run |
| 5 | configure "pkg-config not found" on device | no system pkg-config; pkgconf pkg ships only bin/pkgconf | tool_requires pkgconf/3.0.5 + hmbs-shims/pkg-config symlink, PKG_CONFIG/PATH passed inline to configure |
| 6 | configure "OpenSSL librypto not found" | upstream uses raw AC_SEARCH_LIBS link test (no pkg-config); device link lacks conan openssl -L/-l | openssl as DIRECT require (override=True left cpp_info/package_folder invisible) + _dep_flags() passes -I/-L/-lssl/-lcrypto/-ldl/-lpthread as single-quoted inline CPPFLAGS/LDFLAGS/LIBS |
| 7 | configure "Upgrade your expat to 2.0.0" (XML_ExpatVersionInfo in -lexpat... no) | same class: expat probed by raw AC_CHECK_LIB + version compile check, bypasses pkg-config; device link lacks conan expat -I/-L | reuse _dep_flags("expat") and merge with openssl flags into the same inline CPPFLAGS/LDFLAGS (curl/libxml2 use PKG_CHECK_MODULES and already pass, untouched; no global LIBS, see #8) |
| 8 | configure "cannot run C compiled programs" (cross-compiling RUN probe, rc=77) with --build==--host | global LIBS=-lcrypto/-lssl/-lexpat pre-injected into configure: AC_PROG_CC RUN probe links $LIBS into conftest, and expat/2.8.2.1 defaults shared=True so conftest needs libexpat.so at runtime with no loader path (E467/E566; openssl/3.5.6.1 is no-shared static, innocent) | drop LIBS from configure, keep -I/-L only (AC_SEARCH_LIBS/AC_CHECK_LIB are link-only and append -l themselves); scoped LD_LIBRARY_PATH (dep libdirs via _dep_libdirs) inline on the `make check` RUN phase only (see #9 for the compile-phase correction) |
| 9 | test/offline link fails: "Error loading shared library libxml2.so.16 (needed by .../llvm/bin/lld)" + "xmlFreeDoc: symbol not found" -> "linker command failed due to signal", b64decode Error 1 (preflight 2026-09-16, twice) | SDK lld is dynamically linked against its own libxml2.so.16 in <sdk>/native/llvm/lib, but the inherited LD_LIBRARY_PATH lists the conan libxml2 dir first, so lld loads the incompatible conan copy (E321-draft / babeltrace DRAFT-6048 err 7 / E2175 / E266). The #8 "compile with no loader env" strategy failed because env="conanbuild" re-injects LD_LIBRARY_PATH into every self.run | NEW strategy (differs from #8): SDK llvm/lib FIRST via inline LD_LIBRARY_PATH= prefixes on every compile/link command (vendored json-c cmake calls, explicit configure, make -C src, offline `check TESTS=` build phase). New _sdk_llvm_lib() derives the dir from the active compiler (`-print-resource-dir` dirname x2, realpath dirname x2 + lib with libxml2.so.16 existence check, then HNP/harmonybrew globs; never raises) and _scoped_ld_prefix() orders SDK : conan dep libdirs : cleansed existing entries (also strips the musl whitespace-segment trap). Test-run phase (`make check`) keeps strictly conan-only LD_LIBRARY_PATH (binaries up-to-date, no lld runs; E341 host-leak rule). make -C src switched from Autotools.make to self.run (same targets/vars) because Autotools.make has no command-prefix hook |
| 10 | isds-datestring2tm "2001-34" fails on device: expected tm_mon=1, got=34 (preflight 2026-09-16, TOTAL=61 PASS=59 FAIL=2) | Upstream src/unix.c relies on glibc strptime %Y-%j normalizing tm_mon/tm_mday (year + day-of-year 34 -> Feb 3). musl/OHOS strptime leaves month/day untouched, and the caller's struct is passed directly, so the earlier failed %m parse leaks month=34 into the SUCCESS result. Evidence: unix.c passes `time` straight into three strptime attempts; Alpine aports carries test-skip-invalid-datestring.patch for the same musl case | patches/0001: zeroed temp struct per format attempt (copy out only on success) + manual %Y-%j parse (sscanf %4d-%3d with trailing rejection, yday range vs leap year, ordinal-to-month/day table). Library fix, test file untouched, glibc behavior unchanged ("2001-34" still -> 2001-02-03) |
| 11 | utf82locale "non-ASCII text in C locale" fails on device: expected NULL, conversion succeeded (preflight 2026-09-16, still failing 2026-09-17 after codeset-name branching: OHOS CODESET is not UTF-8 yet its iconv succeeds) | Test assumes C locale codeset is ASCII and iconv is strict (glibc ANSI_X3.4-1968, UTF-8->ASCII fails -> NULL). OHOS iconv is lenient: succeeds on unconvertible input without failing, so neither NULL nor round-trip expectation fits. Library is correct; expectation is glibc-specific. Evidence: src/utils.c _isds_utf82locale converts UTF-8 to nl_langinfo(CODESET); v1 patch proved CODESET is not matched as UTF-8 on device (failure message still "correct is NULL"); Alpine aports carries test-skip-non-utf-locale.patch for musl | patches/0002 v2 (behavior-driven, differs from v1 name-branching): log CODESET, hard ASCII round-trip guard (a broken converter still fails), probe conversion — NULL->NULL TEST, UTF-8->round-trip TEST, lenient-platform success->explicit SKIP_TESTS with reason (visible in log, automake program still PASS, suite intact) |
| 12 | package() make install dies at install-libLTLIBRARIES: libtool install -c .libs/libdatovka.a then chmod cannot access p/lib/libdatovka.a (preflight 2026-09-17; offline suite already 61/61 green) | HMBS-provided install shim copy never landed so libtool follow-up chmod missed its target; package() passed no TMPDIR/SHELL install args and had no fallback. Same class as ctpl/0.3.5 + cubelib/4.9.1 (HMBS shim single-file-only, HMBS_CAP_CHMOD=0, missing mkdir -p). Not a compiler issue: configure done 33.7s, src + offline build/check green | package(): local cp/mkdir install shim (os.open 0o755, -c/-m/-d/multi-source, mkdir -p dest/dirname, chmod best-effort) + redirect INSTALL vars in generated Makefiles + install args -j1 SHELL/CONFIG_SHELL/TMPDIR/TMP/TEMP + _repair_install() diagnose + fallback-copy genuine .libs/libdatovka.a. Install redirection only, no test change |
| 13 | package() top-level make install recurses into test/ and builds test/simline libserver: libserver_la-time_conversion.lo fails with '../config.h' file not found (preflight 2026-09-17; offline suite 61/61 green, src lib built) | automake install-am depends on all-am in every SUBDIRS entry, so install forces a build of simline which was deliberately never built: server.c hard-includes <gnutls/gnutls.h> (gnutls intentionally absent, configure vars stubbed) and its VPATH compile of src/*.c resolves ../config.h against the source tree instead of the build root. Previous round's install-shim fixed only the copy tool, not the recursion. test/ holds no installable artifacts (check/noinst) | package(): install scoped to SUBDIRS=src (src installs lib + public headers; top dir's own install-am such as .pc data still runs). Single word, no quoting split; src/ defines no SUBDIRS so no oscats-style propagation hazard. Install scope only, test suite untouched |
| 14 | test_package CMake configure fails: The CMAKE_C_COMPILER /data/service/hnp/bin/clang could not be found (preflight 2026-09-17; main package built, offline 61/61 green; log shows only a clang++ PATH-fallback WARN, C fallback missing) | test_package generate() v1 verified conf compilers by file-existence + X_OK only; the C path can exist yet be unexecutable (Error 127 inaccessible), so no C fallback was set and the broken absolute path was baked into conan_toolchain.cmake. Main recipe already probes via spawn; test_package did not | test_package: probe-verify each conf compiler by spawning --version (_cand_works, mirrors main recipe); healthy path probes OK so no override; broken path falls back to PATH-proven clang/clang++ (CXX prefers same-dir clang++ sibling of resolved CC) pinned via tc.cache_variables. Consumer generate() only, test bodies/counts untouched |

| 15 | test_package CMake still fails after spawn-probe round: C compiler identification is unknown for conf /data/service/hnp/bin/clang while CXX fell back to harmonybrew clang++ (preflight 2026-09-17; HMBS readonly_tmp diagnosis) | Two holes left by #14, not a broken binary: (1) test_package runs in a FRESH conan context, main build TMPDIR never arrives, so CMake try_compile on readonly /tmp dies with identification unknown even for a healthy compiler; (2) C/CXX resolved independently, mixing SDKs (HNP clang + harmonybrew clang++). Previous install-shim/SUBDIRS/spawn-probe rounds never touched test_package TMPDIR | test_package generate(): persist hmbs_tmp FIRST via Environment scope=build (_writable_tmpdir mkstemp probe + SHELL/CONFIG_SHELL + HMBS caps, mirrors main recipe) so probes and CMake try_compile share the writable root; then resolve CC/CXX as a sibling-consistent pair (keep conf CXX only if working and same-dir as final CC when CC was overridden, else same-dir clang++ sibling of final CC, then PATH fallback) pinned via tc.cache_variables. Healthy runner: zero overrides. Test bodies/counts untouched |

| 16 | test_package CMake仍失败（与#15同指纹第2次）：CXX回退harmonybrew后检查通过，唯独conf HNP clang报C identification unknown；--version探针曾通过 | 与#15假设不同：二进制能跑，坏的是编译链接步——与主包#9同类（SDK lld加载conan版libxml2导致链接崩溃，CMake即报identification unknown），而test_package从无LD定序；且C/CXX分属两个SDK目录。仅做TMPDIR+单向回退不够 | test_package generate()：新增_dep_libdirs/_sdk_llvm_lib/_scoped_ld_value/_persist_ld_path（主包同源，libxml2.so.16存在性校验）；generate内先预导出SDK-first LD到os.environ，终解后经Environment scope=build持久化hmbs_ld；C/CXX双向归一（CXX落到异目录回退时C跟随同目录clang兄弟，探针通过才搬）；test()执行改conan-only LD内联前缀（禁SDK泄漏）。健康机零覆盖，测试体与计数不动 |

| 17 | test_package仍败（同指纹第3次）：LD持久化已生效（harmonybrew llvm/lib排第一）但conf HNP clang鉴定照败，且无C回退（--version又通过） | 前两轮“存在即健康/报版本即健康”假设皆错：--version只证驱动能启动，不证能产出可执行文件（链接步坏同样报identification unknown）。与聚合经验“缺编译器”断言不符：同机同环境下换个编译器即过，属编译器可用性判别粒度问题 | test_package新增_compile_probe（build_folder/hmbs-ccprobe内真实编译链接trivial源码，不执行； infra异常弃权True，只有真实编译失败才False并截断3000字符输出）：conf C在--version通过后追加冒烟，不过即降级；C的PATH候选逐个双门禁（版本+冒烟）；CXX兄弟与PATH候选改C++冒烟；C向CXX目录归位同样要求兄弟冒烟通过。健康机仅多一次hello级编译，零覆盖；测试体与计数不动 |
| 18 | test_package同指纹第4次：裸编译冒烟通过（无C回退）但CMake C identification unknown照败；第5策略周期禁沿用同根因假设 | 前三轮（#15 TMPDIR+#16 LD定序+#17裸编译冒烟）皆错：均假设“编译器二进制或其直调环境坏”，只换喂给CMakeToolchain的CC路径。证伪：LD持久化行后仍用conf HNP clang失败，而裸`clang src -o out`冒烟通过；且本工程project()仅启用C语言，CXX回退与本次失败无关。真故障域在CMake工具链层（toolchain文件烘焙的绝对路径+sysroot/target flags下的try_compile），而非编译器二进制。继续调CC选择属于同一命令的第4次重复 | 新路线（经验1 apply：libe57format绕过project直接编译；dcap/2.47.14+libconfini/1.16.4直接CC先例）：build()改CMake优先、失败即_direct_compile_fallback——同test.c直调已验证CC编译链接（cpp_info聚合的-I/-D/-L/-l真标志，SDK-first LD前缀，产物落cpp.build.bindir/test_libdatovka供test()原样执行计数），健康机CMake成功则零改动。测试体与计数不动，失败如实抛错无stub |
| 19 | 直连回退已触发但失败：test.c报libdatovka/isds.h找不到，产物为相对路径./test_libdatovka（2026-09-17预检；回退CC已正确选中harmonybrew clang且冒烟通过） | 上轮回退只信cpp_info声明的include根（-I包/include），但头文件实际不在该根下（SUBDIRS=src限定安装或垫片拷贝缺口），属声明路径与文件系统真相不一致；另bindir解析为相对路径致test()不可靠；且openssl/3.x顶层libs为空（ssl/crypto只在components），直链会缺ssl/crypto | 文件系统为准：在包内walk定位isds.h真位置并追加其目录及父目录-I（含包顶诊断）；聚合components的-I/-L/-l；产物改build_folder绝对路径并镜像到bindir，test()双位置查找。测试体与计数不动 |

| 20 | 直连回退文件系统搜索证实包内无include/（top仅conaninfo/conanmanifest/lib，isds.h记为missing） | 生产端缺口而非消费端：make install SUBDIRS=src（#13为避开gnutls依赖的simline构建）根本不安装公开头文件，之前注释称src/会装headers被证伪；上游唯一公共同头为include/libdatovka/isds.h（FreeBSD/FreshPorts 0.7.3 plist与man isds.h.libdatovka(3)互证）。继续调消费端-I已无意义 | 主配方package()新增_install_public_headers()：install加repair后拷贝源码树真isds.h（优先src/isds.h，有界搜索、跳过test树）到包include/libdatovka/isds.h，缺失则fail-closed抛错；修正#13注释。测试体与计数不动 |
| 21 | 直连回退触发但链接失败：test_package报undefined json_tokener_parse/json_object_*(soap.c)，链接行有-ldatovka/-lcurl/-lxml2/-lcrypto/-lssl/-lexpat唯独无-ljson-c（2026-09-17预检compile阶段） | 生产端缺口而非消费端：vendored json-c（_build_vendored_jsonc于build_folder/jsonc-prefix构建）只经PKG_CONFIG_PATH暴露给configure，从未装入package；package_info.libs仅["datovka"]，故CMakeDeps与direct-CC聚合皆无-ljson-c，而静态libdatovka.a的soap.o未决json符号必须由消费端链接。继续调-I/-L顺序无意义 | 主配方package()新增_install_vendored_jsonc()：拷贝jsonc-prefix/lib内真libjson-c.a（.so*若有亦带）到包lib/，缺失fail-closed；package_info.libs改为["datovka","json-c"]（依赖在后）；test_package _direct_compile_flags加文件系统兜底（包内搜libjson-c缺-l即补-L/-l）。无stub，测试体与计数不动 |

## Upstream tests
- test/offline: automake `make -C test/offline check`, real PASS/FAIL parsed into HMBS_UPSTREAM_TEST_RESULT.
- test/online: requires live ISDS credentials, not executed (see MANIFEST.yml).
- 2026-09-17 preflight: 59/61, two musl/OHOS locale failures fixed by
  patches/0001 (library: portable %Y-%j conversion, no test change; verified
  60/61 in next preflight) and patches/0002 v2 (test: behavior-driven C-locale
  handling — ASCII guard plus probe, explicit skip only for lenient platform
  iconv). Alpine carries equivalent musl skips (test-skip-invalid-datestring,
  test-skip-non-utf-locale); ours keep suite and program counts intact.

## test_package
- test.c calls isds_init / isds_ctx_create / isds_ctx_free / isds_strerror / isds_cleanup (5 assertions), prints HMBS_TEST_PACKAGE_RESULT.
- test() re-emits HMBS_UPSTREAM_TEST_RESULT summary reference for cache-hit rounds (main build marker is authoritative).

## Verification
- Pending HMBS device preflight (conan create + test_package + offline make check).
