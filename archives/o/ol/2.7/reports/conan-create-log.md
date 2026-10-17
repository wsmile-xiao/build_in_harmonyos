# ol 2.7 `conan create` 日志（逐字留档）

> 运行期日志按仓库规则不入库（`.gitignore` 的 `**/conan-create.log`），故逐字转为
> 本文件留档。代码块是采信轮（清缓存后的干净轮）日志的**逐字节**复制，含末尾空行；
> 把代码块内容单独取出做 `sha256sum` 可复算为下方声明的同一值。
> （`finish` 内嵌重跑会把 `reports/conan-create.log` 覆盖成缓存轮，故此处用干净轮副本。）

- 原文件：采信轮 `reports/conan-create.log`（conan-verify G2 写出）
- 字节数：15871
- 行数：220
- sha256：`d5a110bd720ca7cc037741e6f2b47df01c45b75b932e4697174654a304ec761d`
- 生成命令：`conan-verify ol 2.7`（内部执行
  `conan create archives/o/ol/2.7 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`）
- 干净轮标志：`Calling build()` 出现 2 次、`Apply patch` 2 次；测试汇总行
  `upstream check: rc=0 group_rcs={'language-tests': 0, 'rosettacode-tests': 0, 'ffi-tests': 0, 'check-reference': 0} groups=5 test_rows=211 result_rows=210 fail_rows=0 ok_cells=210 unrun=['tests/fasl-binary.bin']`

```text

======== Exporting recipe to the cache ========
ol/2.7@ohpcd/stable: Exporting package recipe: /storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/conanfile.py
ol/2.7@ohpcd/stable: exports: File 'conandata.yml' found. Exporting it...
ol/2.7@ohpcd/stable: Calling export_sources()
ol/2.7@ohpcd/stable: Copied 1 '.yml' file: conandata.yml
ol/2.7@ohpcd/stable: Copied 1 '.py' file: conanfile.py
ol/2.7@ohpcd/stable: Copied 2 '.patch' files: 0001-GNUmakefile.patch, 0002-tests-rosettacode-object_serialization.scm.patch
ol/2.7@ohpcd/stable: Exported to cache folder: /storage/Users/currentUser/.conan2/p/ol765f244bcd50f/e
ol/2.7@ohpcd/stable: Exported: ol/2.7@ohpcd/stable#85a5ad153f1eb979eb971ad9d3d365eb (2026-09-13 12:56:43 UTC)

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
    ol/2.7@ohpcd/stable#85a5ad153f1eb979eb971ad9d3d365eb - Cache

======== Computing necessary packages ========
Connecting to remote 'ohpcd' anonymously
ol/2.7@ohpcd/stable: Main binary package '6b129b068851896169fae42d399fa922d239ce8a' missing
ol/2.7@ohpcd/stable: Checking 11 compatible configurations
ol/2.7@ohpcd/stable: Compatible configurations not found in cache, checking servers
ol/2.7@ohpcd/stable: '7a45daa5a53e1e1e2f88f46c8c5d42c55b8041f7': compiler.cppstd=98
ol/2.7@ohpcd/stable: '82803953774dd8ef49af18e200a16f3642cfae9d': compiler.cppstd=gnu98
ol/2.7@ohpcd/stable: '8ac2a79ad39b36194df9085b36c9d86fa5599f02': compiler.cppstd=11
ol/2.7@ohpcd/stable: '7f9f31995579bd0e1e9a725bfd253c9c7553a331': compiler.cppstd=gnu11
ol/2.7@ohpcd/stable: '20ce5ca62dba04ef245a37652eafaea893be3909': compiler.cppstd=14
ol/2.7@ohpcd/stable: '1c21bc3ded24ff47b1a195f6cb801f864247735c': compiler.cppstd=gnu14
ol/2.7@ohpcd/stable: 'eda5abb401cbed7c3f6f2ad04bfecec451641886': compiler.cppstd=gnu17
ol/2.7@ohpcd/stable: '69cb9bbff6b978dbd5b9122e0a14671a692c43e9': compiler.cppstd=20
ol/2.7@ohpcd/stable: '57551ed2580a3a49716d342ade5714c03470032d': compiler.cppstd=gnu20
ol/2.7@ohpcd/stable: 'da04b77fe39bcbcfe9926450ff73c2349d9b48b8': compiler.cppstd=23
ol/2.7@ohpcd/stable: '1c92d4b02dd3fd6c66325064d993005ded38ba97': compiler.cppstd=gnu23
ol/2.7@ohpcd/stable: No compatible configuration found

A new experimental approach for binary compatibility detection is available.
    Enable it by setting the core.graph:compatibility_mode=optimized conf
    and get improved performance when querying multiple compatible binaries in remotes.

Requirements
    ol/2.7@ohpcd/stable#85a5ad153f1eb979eb971ad9d3d365eb:6b129b068851896169fae42d399fa922d239ce8a - Build

======== Installing packages ========
ol/2.7@ohpcd/stable: Calling source() in /storage/Users/currentUser/.conan2/p/ol765f244bcd50f/s
ol/2.7@ohpcd/stable: Sources correctly downloaded from https://ghfast.top/https://github.com/yuriy-chumak/ol/archive/refs/tags/2.7.tar.gz
ol/2.7@ohpcd/stable: Uncompressing 2.7.tar.gz to .

-------- Installing package ol/2.7@ohpcd/stable (1 of 1) --------
ol/2.7@ohpcd/stable: Building from source
ol/2.7@ohpcd/stable: Package ol/2.7@ohpcd/stable:6b129b068851896169fae42d399fa922d239ce8a
ol/2.7@ohpcd/stable: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
ol/2.7@ohpcd/stable: Copying sources to build folder
ol/2.7@ohpcd/stable: Building your package in /storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/b
ol/2.7@ohpcd/stable: Generating aggregated env files
ol/2.7@ohpcd/stable: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
ol/2.7@ohpcd/stable: Calling build()
ol/2.7@ohpcd/stable: Apply patch (bugfix): libol.so 链接补 -Wl,-soname,libol.so：上游 -shared 未设 SONAME，产出的 .so 动态段无 DT_SONAME，下游链接器无法按 SONAME 寻址（CI L5a 门禁失败）
ol/2.7@ohpcd/stable: Apply patch (portability): tests/rosettacode/object_serialization.scm: 序列化落盘从硬编码 /tmp 改到构建树内相对路径 tmp/（OHOS 的 /tmp 是 root 属主只读挂载，fasl-save 必然失败）
ol/2.7@ohpcd/stable: RUN: make release -j1 CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr" HAVE_SOCKETS=1 HAVE_DLOPEN=1 HAVE_SECCOMP=1 HAVE_MEMFD_CREATE=1
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

ol/2.7@ohpcd/stable: RUN: rm -rf "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-language-tests" && cp -a "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/b" "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-language-tests"

ol/2.7@ohpcd/stable: RUN: rm -rf "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-rosettacode-tests" && cp -a "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/b" "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-rosettacode-tests"

ol/2.7@ohpcd/stable: RUN: rm -rf "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-ffi-tests" && cp -a "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/b" "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-ffi-tests"

ol/2.7@ohpcd/stable: RUN: rm -rf "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-check-reference" && cp -a "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/b" "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-check-reference"

ol/2.7@ohpcd/stable: running upstream test suite in 4 isolated parallel groups: language-tests, rosettacode-tests, ffi-tests, check-reference
ol/2.7@ohpcd/stable: RUN: ( cd "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-language-tests" && make -j1 CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr" HAVE_SOCKETS=1 HAVE_DLOPEN=1 HAVE_SECCOMP=1 HAVE_MEMFD_CREATE=1 language-tests > "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-language-tests/upstream-language-tests.log" 2>&1; echo "UPSTREAM_GROUP_language-tests_RC=$?" >> "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-language-tests/upstream-language-tests.log" ) & ( cd "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-rosettacode-tests" && make -j1 CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr" HAVE_SOCKETS=1 HAVE_DLOPEN=1 HAVE_SECCOMP=1 HAVE_MEMFD_CREATE=1 rosettacode-tests > "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-rosettacode-tests/upstream-rosettacode-tests.log" 2>&1; echo "UPSTREAM_GROUP_rosettacode-tests_RC=$?" >> "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-rosettacode-tests/upstream-rosettacode-tests.log" ) & ( cd "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-ffi-tests" && make -j1 CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr" HAVE_SOCKETS=1 HAVE_DLOPEN=1 HAVE_SECCOMP=1 HAVE_MEMFD_CREATE=1 ffi-tests > "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-ffi-tests/upstream-ffi-tests.log" 2>&1; echo "UPSTREAM_GROUP_ffi-tests_RC=$?" >> "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-ffi-tests/upstream-ffi-tests.log" ) & ( cd "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-check-reference" && make -j1 CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr" HAVE_SOCKETS=1 HAVE_DLOPEN=1 HAVE_SECCOMP=1 HAVE_MEMFD_CREATE=1 check-reference > "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-check-reference/upstream-check-reference.log" 2>&1; echo "UPSTREAM_GROUP_check-reference_RC=$?" >> "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/ol-test-check-reference/upstream-check-reference.log" ) & wait

ol/2.7@ohpcd/stable: upstream check: rc=0 group_rcs={'language-tests': 0, 'rosettacode-tests': 0, 'ffi-tests': 0, 'check-reference': 0} groups=5 test_rows=211 result_rows=210 fail_rows=0 ok_cells=210 unrun=['tests/fasl-binary.bin']
ol/2.7@ohpcd/stable: Package '6b129b068851896169fae42d399fa922d239ce8a' built
ol/2.7@ohpcd/stable: Build folder /storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/b/build-release
ol/2.7@ohpcd/stable: Generating the package
ol/2.7@ohpcd/stable: Packaging in folder /storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/p
ol/2.7@ohpcd/stable: Calling package()
ol/2.7@ohpcd/stable: RUN: LD_LIBRARY_PATH= /data/service/hnp/bin/llvm-objcopy --remove-section .codesign "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/p/bin/ol" 2>/dev/null || true

ol/2.7@ohpcd/stable: RUN: LD_LIBRARY_PATH= /data/service/hnp/bin/binary-sign-tool sign -inFile "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/p/bin/ol" -outFile "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/p/bin/ol" -selfSign 1
09-13 21:01:48.596 INFO  - add codesign section success
09-13 21:01:48.609 INFO  - write code sign data success

ol/2.7@ohpcd/stable: RUN: LD_LIBRARY_PATH= /data/service/hnp/bin/llvm-objcopy --remove-section .codesign "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/p/bin/olvm" 2>/dev/null || true

ol/2.7@ohpcd/stable: RUN: LD_LIBRARY_PATH= /data/service/hnp/bin/binary-sign-tool sign -inFile "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/p/bin/olvm" -outFile "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/p/bin/olvm" -selfSign 1
09-13 21:01:48.823 INFO  - add codesign section success
09-13 21:01:48.829 INFO  - write code sign data success

ol/2.7@ohpcd/stable: package(): Packaged 7 files
ol/2.7@ohpcd/stable: package(): Packaged 1 '.so' file: libol.so
ol/2.7@ohpcd/stable: package(): Packaged 260 '.scm' files
ol/2.7@ohpcd/stable: package(): Packaged 3 '.md' files: README.md, README.md, README.md
ol/2.7@ohpcd/stable: package(): Packaged 6 '.lisp' files
ol/2.7@ohpcd/stable: package(): Packaged 2 '.h' files: ol.h, vm.h
ol/2.7@ohpcd/stable: package(): Packaged 1 '.gz' file: ol.1.gz
ol/2.7@ohpcd/stable: Created package revision 1c521cbd7fc5b1fb90fa30b7462b7b6f
ol/2.7@ohpcd/stable: Package '6b129b068851896169fae42d399fa922d239ce8a' created
ol/2.7@ohpcd/stable: Full package reference: ol/2.7@ohpcd/stable#85a5ad153f1eb979eb971ad9d3d365eb:6b129b068851896169fae42d399fa922d239ce8a#1c521cbd7fc5b1fb90fa30b7462b7b6f
ol/2.7@ohpcd/stable: Package folder /storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/p

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    ol/2.7@ohpcd/stable (test package): /storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/conanfile.py
Requirements
    ol/2.7@ohpcd/stable#85a5ad153f1eb979eb971ad9d3d365eb - Cache

======== Computing necessary packages ========
Requirements
    ol/2.7@ohpcd/stable#85a5ad153f1eb979eb971ad9d3d365eb:6b129b068851896169fae42d399fa922d239ce8a#1c521cbd7fc5b1fb90fa30b7462b7b6f - Cache

======== Installing packages ========
ol/2.7@ohpcd/stable: Already installed! (1 of 1)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/build-release
ol/2.7@ohpcd/stable (test package): Test package build: build-release
ol/2.7@ohpcd/stable (test package): Test package build folder: /storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/build-release
ol/2.7@ohpcd/stable (test package): Writing generators to /storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/build-release/conan
ol/2.7@ohpcd/stable (test package): Generator 'VirtualRunEnv' calling 'generate()'
ol/2.7@ohpcd/stable (test package): Generating aggregated env files
ol/2.7@ohpcd/stable (test package): Generated aggregated env files: ['conanrun.sh', 'conanbuild.sh']

======== Testing the package: Building ========
ol/2.7@ohpcd/stable (test package): Calling build()
ol/2.7@ohpcd/stable (test package): RUN: /data/service/hnp/bin/clang embed_test.c -o "/storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/build-release/embed_test" -I"/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/p/include" -L"/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/p/lib" -lol -Wl,-rpath,"/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/p/lib"


======== Testing the package: Executing test ========
ol/2.7@ohpcd/stable (test package): Running test()
ol/2.7@ohpcd/stable (test package): RUN: /storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/build-release/embed_test
PASS: (* 6 7) evaluates to 42
PASS: (+ 1 2 39) evaluates to 42
PASS: defining (fact n) succeeds
PASS: (fact 5) evaluates to 120
PASS: string-length "Otus Lisp" == 9
embed_test: failures=0
embed_test: ALL PASS

ol/2.7@ohpcd/stable (test package): RUN: "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/p/bin/ol" "/storage/Users/currentUser/ws/worktrees/ol-2.7/archives/o/ol/2.7/test_package/harness.scm"
PASS: arith
PASS: mul
PASS: string-append
PASS: string-length
PASS: list-map
PASS: factorial
PASS: gcd
harness: failures=0

ol/2.7@ohpcd/stable (test package): RUN: "/storage/Users/currentUser/.conan2/p/b/ol0a989f8dafd7d/p/bin/olvm" --version
olvm (Otus Lisp Virtual Machine) 2.7
Copyright (c) 2014-2026 Yuriy Chumak
License LGPLv3+: GNU LGPL version 3 or later <http://gnu.org/licenses/>
License MIT: <https://en.wikipedia.org/wiki/MIT_License>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

```
