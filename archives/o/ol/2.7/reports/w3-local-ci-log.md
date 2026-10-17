# ol 2.7 本地 CI 模拟（W3）日志（逐字留档）

> 运行期日志不入库（仓库规则禁止 `*.log` 进 PR），逐字转为本文件留档。
> 代码块为原文件**逐字节**复制（含末尾空行），可用 `sha256sum` 复算。
> 原文件是 `finish` 内嵌的本地 CI 模拟产物 `reports/w3-local-ci.log`，
> 执行入口 `ci/conan/setup.sh` + `ci/conan/build_and_test.sh archives/o/ol/2.7`
> （`conan create --build=ol/*` 强制重建，非缓存轮）。

- 字节数：19382
- 行数：334
- sha256：`ab763d6035328c53d4868469c5421c294c757f08b55ace5aebdca01b8d1f0a79`
- 结论行：`L0_RESULT=pass`、`L1_RESULT=pass`（上游测试 + test_package）、
  `L2_RESULT=pass`（`ol --version` / `olvm --version`）、`L4_RESULT=pass`（补丁扫描）、
  `L5_RESULT=pass`（含 L5a SONAME 门禁：`libol.so` 带 `DT_SONAME=libol.so`）

```text
$ setup.sh (RC=0)
[step] Conan environment setup...
[step] Conan version: Conan version 2.29.1
[step] Disabling conancenter (private CI, not needed)
conancenter: https://center2.conan.io [Verify SSL: True, Enabled: False]
[step] remote 已就绪: ohpcd
[step] Importing profile from /storage/Users/currentUser/ws/worktrees/ol-2.7/ci/conan/profiles/ohos-aarch64
[step] Profile file available at: /storage/Users/currentUser/ws/worktrees/ol-2.7/ci/conan/profiles/ohos-aarch64
[step] Conan environment ready ✅
[step]   remote: ohpcd
[step]   profile: ohos-aarch64
[step]   conan: Conan version 2.29.1


$ build_and_test.sh archives/o/ol/2.7 (RC=0)
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
[step] CI_PACKAGES received: archives/o/ol/2.7
[step] Found 1 package(s) to build

━━━ Building: ol/2.7 ━━━
[step] L0: Quality gate checks...
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
  检查模式: prdiff (12 个文件)

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
  [try 1/1.1/3] 2.7.tar.gz ← https://gh-proxy.com/https://github.com/yuriy-chumak/ol/archive/refs/tags/2.7.ta...
  [ok] 2.7.tar.gz (2683KB) via mirror 1
  [try 1/2.1/3] 2.7.tar.gz ← https://gh-proxy.com/https://github.com/yuriy-chumak/ol/archive/refs/tags/2.7.ta...
  [ok] 2.7.tar.gz (2683KB) via mirror 1
  [done] Pre-downloaded 2 files, conandata.yml updated to file:// URLs
[step] Running conan create (output logged to /storage/Users/currentUser/ws/worktrees/ol-2.7/.ci_logs/conan_build_ol_2.7.log)...

======== Exporting recipe to the cache ========
ol/2.7: Exporting package recipe: /storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/conanfile.py
ol/2.7: exports: File 'conandata.yml' found. Exporting it...
ol/2.7: Calling export_sources()
ol/2.7: Copied 1 '.yml' file: conandata.yml
ol/2.7: Copied 1 '.py' file: conanfile.py
ol/2.7: Copied 2 '.patch' files: 0001-GNUmakefile.patch, 0002-tests-rosettacode-object_serialization.scm.patch
ol/2.7: Exported to cache folder: /storage/Users/currentUser/.conan2/p/ol75ee018e0c5c2/e
ol/2.7: Exported: ol/2.7#b25e92f35562418b06b4879ff3bd9987 (2026-09-13 13:07:03 UTC)

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
    ol/2.7#b25e92f35562418b06b4879ff3bd9987 - Cache

======== Computing necessary packages ========
ol/2.7: Forced build from source
Requirements
    ol/2.7#b25e92f35562418b06b4879ff3bd9987:6b129b068851896169fae42d399fa922d239ce8a - Build

======== Installing packages ========
ol/2.7: Calling source() in /storage/Users/currentUser/.conan2/p/ol75ee018e0c5c2/s
ol/2.7: Sources correctly downloaded from file:///storage/Users/currentUser/ws/worktrees/ol-2.7/.build-cache/predl_cache/1438ba1e_2.7.tar.gz
ol/2.7: Uncompressing 1438ba1e_2.7.tar.gz to .

-------- Installing package ol/2.7 (1 of 1) --------
ol/2.7: Building from source
ol/2.7: Package ol/2.7:6b129b068851896169fae42d399fa922d239ce8a
ol/2.7: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
ol/2.7: Copying sources to build folder
ol/2.7: Building your package in /storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/b
ol/2.7: Generating aggregated env files
ol/2.7: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
ol/2.7: Calling build()
ol/2.7: Apply patch (bugfix): libol.so 链接补 -Wl,-soname,libol.so：上游 -shared 未设 SONAME，产出的 .so 动态段无 DT_SONAME，下游链接器无法按 SONAME 寻址（CI L5a 门禁失败）
ol/2.7: Apply patch (portability): tests/rosettacode/object_serialization.scm: 序列化落盘从硬编码 /tmp 改到构建树内相对路径 tmp/（OHOS 的 /tmp 是 root 属主只读挂载，fasl-save 必然失败）
ol/2.7: RUN: make release -j1 CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr" HAVE_SOCKETS=1 HAVE_DLOPEN=1 HAVE_SECCOMP=1 HAVE_MEMFD_CREATE=1
GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
sed -e '/\/\/ <!--/,/\/\/ -->/d' src/olvm.c >includes/ol/vm.h
/data/service/hnp/bin/clang src/olvm.c -o vm \
   extensions/ffi.c -Iincludes \
   -std=gnu99 -Wno-int-to-pointer-cast  -z noexecstack  -DHAVE_SOCKETS=1 -DHAVE_DLOPEN=1 -DHAVE_SECCOMP=1 -fno-exceptions     -fno-unwind-tables -fno-asynchronous-unwind-tables   -DHAVE_MEMFD_CREATE=1 -lm -D_FILE_OFFSET_BITS=64  -O2 -DNDEBUG -Wno-unused-result -g0  -O2 -DNDEBUG -Wno-unused-result -g0 -DPREFIX=\"/usr\"  -ldl -Xlinker --export-dynamic -lm
Ok.
/data/service/hnp/bin/clang src/olvm.c -o ol \
   extensions/ffi.c -Iincludes \
   -std=gnu99 -Wno-int-to-pointer-cast  -z noexecstack  -DHAVE_SOCKETS=1 -DHAVE_DLOPEN=1 -DHAVE_SECCOMP=1 -fno-exceptions     -fno-unwind-tables -fno-asynchronous-unwind-tables   -DHAVE_MEMFD_CREATE=1 -lm -D_FILE_OFFSET_BITS=64  -O2 -DNDEBUG -Wno-unused-result -g0 -DPREFIX=\"/usr\"  -ldl -Xlinker --export-dynamic \
   src/repl.S -DREPL=repl
Ok.
cp vm olvm
strip olvm
#strip olvm -R .eh_frame
#strip olvm -R .eh_frame_hdr
/data/service/hnp/bin/clang src/olvm.c -o libol.so \
   extensions/ffi.c -Iincludes \
   -std=gnu99 -Wno-int-to-pointer-cast  -z noexecstack  -DHAVE_SOCKETS=1 -DHAVE_DLOPEN=1 -DHAVE_SECCOMP=1 -fno-exceptions     -fno-unwind-tables -fno-asynchronous-unwind-tables   -DHAVE_MEMFD_CREATE=1 -lm -D_FILE_OFFSET_BITS=64  -O2 -DNDEBUG -Wno-unused-result -g0 -DPREFIX=\"/usr\"  -ldl -Xlinker --export-dynamic \
   src/repl.S -DREPL=repl \
   -DOLVM_NOMAIN -shared -fPIC -Wl,-soname,libol.so
Ok.

ol/2.7: RUN: rm -rf "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-language-tests" && cp -a "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/b" "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-language-tests"

ol/2.7: RUN: rm -rf "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-rosettacode-tests" && cp -a "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/b" "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-rosettacode-tests"

ol/2.7: RUN: rm -rf "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-ffi-tests" && cp -a "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/b" "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-ffi-tests"

ol/2.7: RUN: rm -rf "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-check-reference" && cp -a "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/b" "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-check-reference"

ol/2.7: running upstream test suite in 4 isolated parallel groups: language-tests, rosettacode-tests, ffi-tests, check-reference
ol/2.7: RUN: ( cd "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-language-tests" && make -j1 CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr" HAVE_SOCKETS=1 HAVE_DLOPEN=1 HAVE_SECCOMP=1 HAVE_MEMFD_CREATE=1 language-tests > "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-language-tests/upstream-language-tests.log" 2>&1; echo "UPSTREAM_GROUP_language-tests_RC=$?" >> "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-language-tests/upstream-language-tests.log" ) & ( cd "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-rosettacode-tests" && make -j1 CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr" HAVE_SOCKETS=1 HAVE_DLOPEN=1 HAVE_SECCOMP=1 HAVE_MEMFD_CREATE=1 rosettacode-tests > "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-rosettacode-tests/upstream-rosettacode-tests.log" 2>&1; echo "UPSTREAM_GROUP_rosettacode-tests_RC=$?" >> "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-rosettacode-tests/upstream-rosettacode-tests.log" ) & ( cd "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-ffi-tests" && make -j1 CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr" HAVE_SOCKETS=1 HAVE_DLOPEN=1 HAVE_SECCOMP=1 HAVE_MEMFD_CREATE=1 ffi-tests > "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-ffi-tests/upstream-ffi-tests.log" 2>&1; echo "UPSTREAM_GROUP_ffi-tests_RC=$?" >> "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-ffi-tests/upstream-ffi-tests.log" ) & ( cd "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-check-reference" && make -j1 CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr" HAVE_SOCKETS=1 HAVE_DLOPEN=1 HAVE_SECCOMP=1 HAVE_MEMFD_CREATE=1 check-reference > "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-check-reference/upstream-check-reference.log" 2>&1; echo "UPSTREAM_GROUP_check-reference_RC=$?" >> "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/ol-test-check-reference/upstream-check-reference.log" ) & wait

ol/2.7: upstream check: rc=0 group_rcs={'language-tests': 0, 'rosettacode-tests': 0, 'ffi-tests': 0, 'check-reference': 0} groups=5 test_rows=211 result_rows=210 fail_rows=0 ok_cells=210 unrun=['tests/fasl-binary.bin']
ol/2.7: Package '6b129b068851896169fae42d399fa922d239ce8a' built
ol/2.7: Build folder /storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/b/build-release
ol/2.7: Generating the package
ol/2.7: Packaging in folder /storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/p
ol/2.7: Calling package()
ol/2.7: RUN: LD_LIBRARY_PATH= /data/service/hnp/bin/llvm-objcopy --remove-section .codesign "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/p/bin/ol" 2>/dev/null || true

ol/2.7: RUN: LD_LIBRARY_PATH= /data/service/hnp/bin/binary-sign-tool sign -inFile "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/p/bin/ol" -outFile "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/p/bin/ol" -selfSign 1
09-13 21:12:05.903 INFO  - add codesign section success
09-13 21:12:05.918 INFO  - write code sign data success

ol/2.7: RUN: LD_LIBRARY_PATH= /data/service/hnp/bin/llvm-objcopy --remove-section .codesign "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/p/bin/olvm" 2>/dev/null || true

ol/2.7: RUN: LD_LIBRARY_PATH= /data/service/hnp/bin/binary-sign-tool sign -inFile "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/p/bin/olvm" -outFile "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/p/bin/olvm" -selfSign 1
09-13 21:12:06.096 INFO  - add codesign section success
09-13 21:12:06.100 INFO  - write code sign data success

ol/2.7: package(): Packaged 7 files
ol/2.7: package(): Packaged 1 '.so' file: libol.so
ol/2.7: package(): Packaged 260 '.scm' files
ol/2.7: package(): Packaged 3 '.md' files: README.md, README.md, README.md
ol/2.7: package(): Packaged 6 '.lisp' files
ol/2.7: package(): Packaged 2 '.h' files: ol.h, vm.h
ol/2.7: package(): Packaged 1 '.gz' file: ol.1.gz
ol/2.7: Created package revision 1c521cbd7fc5b1fb90fa30b7462b7b6f
ol/2.7: Package '6b129b068851896169fae42d399fa922d239ce8a' created
ol/2.7: Full package reference: ol/2.7#b25e92f35562418b06b4879ff3bd9987:6b129b068851896169fae42d399fa922d239ce8a#1c521cbd7fc5b1fb90fa30b7462b7b6f
ol/2.7: Package folder /storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/p

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    ol/2.7 (test package): /storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/conanfile.py
Requirements
    ol/2.7#b25e92f35562418b06b4879ff3bd9987 - Cache

======== Computing necessary packages ========
Requirements
    ol/2.7#b25e92f35562418b06b4879ff3bd9987:6b129b068851896169fae42d399fa922d239ce8a#1c521cbd7fc5b1fb90fa30b7462b7b6f - Cache

======== Installing packages ========
ol/2.7: Already installed! (1 of 1)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/build-release
ol/2.7 (test package): Test package build: build-release
ol/2.7 (test package): Test package build folder: /storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/build-release
ol/2.7 (test package): Writing generators to /storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/build-release/conan
ol/2.7 (test package): Generator 'VirtualRunEnv' calling 'generate()'
ol/2.7 (test package): Generating aggregated env files
ol/2.7 (test package): Generated aggregated env files: ['conanrun.sh', 'conanbuild.sh']

======== Testing the package: Building ========
ol/2.7 (test package): Calling build()
ol/2.7 (test package): RUN: /data/service/hnp/bin/clang embed_test.c -o "/storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/build-release/embed_test" -I"/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/p/include" -L"/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/p/lib" -lol -Wl,-rpath,"/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/p/lib"


======== Testing the package: Executing test ========
ol/2.7 (test package): Running test()
ol/2.7 (test package): RUN: /storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/build-release/embed_test
PASS: (* 6 7) evaluates to 42
PASS: (+ 1 2 39) evaluates to 42
PASS: defining (fact n) succeeds
PASS: (fact 5) evaluates to 120
PASS: string-length "Otus Lisp" == 9
embed_test: failures=0
embed_test: ALL PASS

ol/2.7 (test package): RUN: "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/p/bin/ol" "/storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/harness.scm"
PASS: arith
PASS: mul
PASS: string-append
PASS: string-length
PASS: list-map
PASS: factorial
PASS: gcd
harness: failures=0

ol/2.7 (test package): RUN: "/storage/Users/currentUser/.conan2/p/b/olb6bcd0595a40d/p/bin/olvm" --version
olvm (Otus Lisp Virtual Machine) 2.7
Copyright (c) 2014-2026 Yuriy Chumak
License LGPLv3+: GNU LGPL version 3 or later <http://gnu.org/licenses/>
License MIT: <https://en.wikipedia.org/wiki/MIT_License>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

[ok] ol/2.7 — conan create passed
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
        [sabotage] include/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on ol
[step] L2: Smoke test (version/help check)...
[ok] L2: ol --version OK
[ok] L2: olvm --version OK

L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: ol --version OK, olvm --version OK
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
