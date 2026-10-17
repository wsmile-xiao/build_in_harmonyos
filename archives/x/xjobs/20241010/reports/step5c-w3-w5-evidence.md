# Public H1 step5c W3/W5 evidence transcript

This text export exposes the stage outputs needed to review the candidate without publishing device identifiers or private filesystem paths. It is derived from the retained H1 archive; absolute RUNROOT prefixes are replaced with `$H1_ROOT`.

- Original H1 archive SHA-256: `5b026d8a7f2dcc21be49c1853286db47ca1efc0c3ee027d29de4515dd51c6b37`
- Original W3 log SHA-256: `a37fcabd7c00422de83becb8338ea04d330dd1feabc1072cdc425aadefb9d3fb`
- Tested base: c611 `c611f7d61b422eda200fc49481cf0d404e63f10c`
- Tested `pr.diff` SHA-256: `0a20e982ed6d470aa575a0b21b772feadfc048211ef468c4c6402361ed004615` (15 xjobs paths; the later report/evidence additions are documentation-only and were not in that H1 invocation)

## `candidate/reports/w3-local-ci.log`

Original file SHA-256: `a37fcabd7c00422de83becb8338ea04d330dd1feabc1072cdc425aadefb9d3fb`. Redacted text SHA-256: `ed97414907698b005fa7477edddca5c348e1869b776f0f4227a39d731df0a2ba`.

```text
$ setup.sh (RC=0)
[step] Conan environment setup...
[step] Conan version: Conan version 2.29.1
[step] Disabling conancenter (private CI, not needed)
conancenter: https://center2.conan.io [Verify SSL: True, Enabled: False]
[step] remote 'ohpcd' 不存在, 自动添加 (匿名读取)
[step] remote 已添加: ohpcd → https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/
[step] Importing profile from $H1_ROOT/framework/ci/conan/profiles/ohos-aarch64
[step] Profile file available at: $H1_ROOT/framework/ci/conan/profiles/ohos-aarch64
[step] Conan environment ready ✅
[step]   remote: ohpcd
[step]   profile: ohos-aarch64
[step]   conan: Conan version 2.29.1


$ build_and_test.sh archives/x/xjobs/20241010 (RC=0)
[step] Conan build + test pipeline (CI, no AI)
[step]   scan_root: archives
[step]   profile: ohos-aarch64
[step]   channel: (no channel — plain name/version)
[step] Validating package build timeout overrides...
[step] G0: Knowledge graph integrity check...
        [ok] G0: Knowledge graph integrity check passed (541 entries)
G0_RESULT=pass
[step] G0e: Root directory whitelist check...
        [ok] G0e: Root directory whitelist passed
[step] CI_PACKAGES received: archives/x/xjobs/20241010
[step] Found 1 package(s) to build

━━━ Building: xjobs/20241010 ━━━
[step] L0: Quality gate checks...
[step] L0i: Checking dependency availability in registry (R36)...
        [ok] dependency in registry: flex/2.6.4
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
  .kv 文件数: 541

[step] KC1: 草稿泄漏检测...
[OK] KC1: 草稿泄漏检测通过

[step] KC2: 模板占位符残留检测...
[OK] KC2: 模板占位符残留检测通过

[step] KC3: rec_auto_fix 格式校验...
[OK] KC3: rec_auto_fix 格式校验通过

[step] KC4: 非标准字段检测...
[OK] KC4: 非标准字段检测通过

[step] KC5: index.tsv 行数一致性...
[OK] KC5: index.tsv 一致 (541 = 541)

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
  检查模式: prdiff (15 个文件)

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
  [try 1/1.1/3] xjobs-20241010.tgz ← https://www.maier-komor.de/xjobs/xjobs-20241010.tgz...
  [fail] [Errno 2] No such file or directory: 'curl'
  [try 1/1.2/3] xjobs-20241010.tgz ← https://www.maier-komor.de/xjobs/xjobs-20241010.tgz...
  [fail] [Errno 2] No such file or directory: 'curl'
  [try 1/1.3/3] xjobs-20241010.tgz ← https://www.maier-komor.de/xjobs/xjobs-20241010.tgz...
  [fail] [Errno 2] No such file or directory: 'curl'
  [WARN] Failed to pre-download xjobs-20241010.tgz, will rely on conan's download
  [done] No files pre-downloaded
[step] Running conan create (output logged to $H1_ROOT/framework/.ci_logs/conan_build_xjobs_20241010.log)...

======== Exporting recipe to the cache ========
xjobs/20241010: Exporting package recipe: $H1_ROOT/framework/archives/x/xjobs/20241010/conanfile.py
xjobs/20241010: exports: File 'conandata.yml' found. Exporting it...
xjobs/20241010: Calling export_sources()
xjobs/20241010: Copied 1 '.yml' file: conandata.yml
xjobs/20241010: Copied 1 '.py' file: conanfile.py
xjobs/20241010: Copied 4 '.patch' files: 0001-jobctrl.c.patch, 0002-config.sub.patch, 0003-xjobs.c.patch, 0004-long-version-option.patch
xjobs/20241010: Exported to cache folder: $H1_ROOT/conan-home/p/xjobsdb3b22c31ffc4/e
xjobs/20241010: Exported: xjobs/20241010#eae728123455f9a994c97fb151aeeb90 (2026-09-28 18:48:15 UTC)

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
PATH=+(path)$DEVICE_STORAGE/usr/local/bin
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
PATH=+(path)$DEVICE_STORAGE/usr/local/bin
PATH=+(path)/data/service/hnp/bin
LD_LIBRARY_PATH=+(path)/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib


======== Computing dependency graph ========
Graph root
    cli
Requirements
    xjobs/20241010#eae728123455f9a994c97fb151aeeb90 - Cache
Build requirements
    flex/2.6.4#dae8938545a70afe5596b280fc4ad124 - Cache

======== Computing necessary packages ========
Connecting to remote 'ohpcd' anonymously
xjobs/20241010: Forced build from source
Requirements
    xjobs/20241010#eae728123455f9a994c97fb151aeeb90:6b129b068851896169fae42d399fa922d239ce8a - Build
Build requirements
    flex/2.6.4#dae8938545a70afe5596b280fc4ad124:6b129b068851896169fae42d399fa922d239ce8a#26202157a6a9e4d69163006bc32a3c6f - Download (ohpcd)

======== Installing packages ========

-------- Downloading 1 package --------
Downloading binary packages in 20 parallel threads
flex/2.6.4: Retrieving package 6b129b068851896169fae42d399fa922d239ce8a from remote 'ohpcd'
flex/2.6.4: Package installed 6b129b068851896169fae42d399fa922d239ce8a
flex/2.6.4: Downloaded package revision 26202157a6a9e4d69163006bc32a3c6f
xjobs/20241010: Calling source() in $H1_ROOT/conan-home/p/xjobsdb3b22c31ffc4/s
xjobs/20241010: Sources correctly downloaded from https://www.maier-komor.de/xjobs/xjobs-20241010.tgz
xjobs/20241010: Uncompressing xjobs-20241010.tgz to .

-------- Installing package xjobs/20241010 (2 of 2) --------
xjobs/20241010: Building from source
xjobs/20241010: Package xjobs/20241010:6b129b068851896169fae42d399fa922d239ce8a
xjobs/20241010: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
xjobs/20241010: Copying sources to build folder
xjobs/20241010: Building your package in $H1_ROOT/conan-home/p/b/xjobs0b5d12a67a6d5/b
xjobs/20241010: Calling generate()
xjobs/20241010: Generators folder: $H1_ROOT/conan-home/p/b/xjobs0b5d12a67a6d5/b
xjobs/20241010: Generating aggregated env files
xjobs/20241010: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
xjobs/20241010: Calling build()
xjobs/20241010: Apply patch (bugfix): 0001 Return failure for unsuccessful child jobs and honor TMPDIR for captured output
xjobs/20241010: Apply patch (portability): 0002 Allow Autoconf to canonicalize the aarch64 Linux OHOS triplet
xjobs/20241010: Apply patch (bugfix): 0003 Preserve single-character command arguments after --
xjobs/20241010: Apply patch (portability): 0004 Accept the conventional --version option used by the framework staging verifier
xjobs/20241010: RUN: "$H1_ROOT/conan-home/p/b/xjobs0b5d12a67a6d5/b/configure" --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos 
checking build system type... aarch64-unknown-linux-ohos
checking host system type... aarch64-unknown-linux-ohos
checking target system type... aarch64-unknown-linux-ohos
checking for aarch64-unknown-linux-ohos-gcc... /data/service/hnp/bin/clang
checking whether the C compiler works... yes
checking for C compiler default output file name... a.out
checking for suffix of executables... 
checking whether we are cross compiling... no
checking for suffix of object files... o
checking whether the compiler supports GNU C... yes
checking whether /data/service/hnp/bin/clang accepts -g... yes
checking for /data/service/hnp/bin/clang option to enable C11 features... none needed
checking for flex... flex
checking for lex output file root... lex.yy
checking for lex library... none needed
checking for library containing yywrap... no
checking whether yytext is a pointer... yes
checking for a BSD-compatible install... /system/bin/install -c
checking for rm... /usr/bin/rm
checking for cp... /usr/bin/cp
checking for C/C++ restrict keyword... __restrict__
checking for inline... inline
checking whether to enable assertions... yes
checking return type of signal handlers... void
checking for special C compiler options needed for large files... no
checking for _FILE_OFFSET_BITS value needed for large files... no
checking for malloc in -lumem... no
checking for library containing ceil... none required
checking for library containing wait4... none required
checking for library containing strlcpy... none required
checking for stdio.h... yes
checking for stdlib.h... yes
checking for string.h... yes
checking for inttypes.h... yes
checking for stdint.h... yes
checking for strings.h... yes
checking for sys/stat.h... yes
checking for sys/types.h... yes
checking for unistd.h... yes
checking for vfork.h... no
checking for sys/param.h... yes
checking for pid_t... yes
checking for fork... yes
checking for vfork... yes
checking for getpagesize... yes
checking for working fork... yes
checking for working vfork... (cached) yes
checking for working mmap... yes
checking for stropts.h... yes
checking for ncurses.h... no
checking for curses.h... no
checking for term.h... no
checking for library containing tigetstr... no
checking for library containing tparm... no
configure: creating ./config.status
config.status: creating Makefile
config.status: creating config.h

xjobs/20241010: RUN: make -j1
mkdir build
/data/service/hnp/bin/clang -MM -MG -MT build/xjobs.o -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H xjobs.c -o build/xjobs.d
/data/service/hnp/bin/clang -MM -MG -MT build/settings.o -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H settings.c -o build/settings.d
/data/service/hnp/bin/clang -MM -MG -MT build/colortty.o -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H colortty.c -o build/colortty.d
/data/service/hnp/bin/clang -MM -MG -MT build/jobctrl.o -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H jobctrl.c -o build/jobctrl.d
/data/service/hnp/bin/clang -MM -MG -MT build/log.o -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H log.c -o build/log.d
/data/service/hnp/bin/clang -MM -MG -MT build/support.o -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H support.c -o build/support.d
/data/service/hnp/bin/clang -MM -MG -MT build/lexextra.o -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H lexextra.c -o build/lexextra.d
flex -t tokenizer.l > tokenizer.c
/data/service/hnp/bin/clang -MM -MG -MT build/tokenizer.o -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H tokenizer.c -o build/tokenizer.d
rm tokenizer.c
flex -t tokenizer.l > tokenizer.c
/data/service/hnp/bin/clang -MM -MG -MT build/tokenizer.o -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H tokenizer.c -o build/tokenizer.d
/data/service/hnp/bin/clang -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H -c xjobs.c -o build/xjobs.o
/data/service/hnp/bin/clang -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H -c settings.c -o build/settings.o
/data/service/hnp/bin/clang -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H -c colortty.c -o build/colortty.o
/data/service/hnp/bin/clang -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H -c jobctrl.c -o build/jobctrl.o
/data/service/hnp/bin/clang -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H -c log.c -o build/log.o
/data/service/hnp/bin/clang -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H -c support.c -o build/support.o
/data/service/hnp/bin/clang -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H -c lexextra.c -o build/lexextra.o
/data/service/hnp/bin/clang -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H -c tokenizer.c -o build/tokenizer.o
/data/service/hnp/bin/clang -fPIC -O2 -O3 -fPIE -DHAVE_CONFIG_H -L$DEVICE_STORAGE/usr/local/lib -pie -Wl,-z,relro,-z,now build/xjobs.o build/settings.o build/colortty.o build/jobctrl.o build/log.o build/support.o build/lexextra.o build/tokenizer.o  -o xjobs

xjobs/20241010: Package '6b129b068851896169fae42d399fa922d239ce8a' built
xjobs/20241010: Build folder $H1_ROOT/conan-home/p/b/xjobs0b5d12a67a6d5/b
xjobs/20241010: Generating the package
xjobs/20241010: Packaging in folder $H1_ROOT/conan-home/p/b/xjobs0b5d12a67a6d5/p
xjobs/20241010: Calling package()
xjobs/20241010: package(): Packaged 2 files: xjobs, COPYING
xjobs/20241010: package(): Packaged 1 '.1' file: xjobs.1
xjobs/20241010: Created package revision fb9caf4236ef575d6896d23ce415b72f
xjobs/20241010: Package '6b129b068851896169fae42d399fa922d239ce8a' created
xjobs/20241010: Full package reference: xjobs/20241010#eae728123455f9a994c97fb151aeeb90:6b129b068851896169fae42d399fa922d239ce8a#fb9caf4236ef575d6896d23ce415b72f
xjobs/20241010: Package folder $H1_ROOT/conan-home/p/b/xjobs0b5d12a67a6d5/p

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    xjobs/20241010 (test package): $H1_ROOT/framework/archives/x/xjobs/20241010/test_package/conanfile.py
Requirements
    xjobs/20241010#eae728123455f9a994c97fb151aeeb90 - Cache
Build requirements
    flex/2.6.4#dae8938545a70afe5596b280fc4ad124 - Cache

======== Computing necessary packages ========
Requirements
    xjobs/20241010#eae728123455f9a994c97fb151aeeb90:6b129b068851896169fae42d399fa922d239ce8a#fb9caf4236ef575d6896d23ce415b72f - Cache
Build requirements
Skipped binaries
    flex/2.6.4

======== Installing packages ========
xjobs/20241010: Already installed! (1 of 1)

======== Testing the package ========
xjobs/20241010 (test package): Test package build: 
xjobs/20241010 (test package): Test package build folder: $H1_ROOT/framework/archives/x/xjobs/20241010/test_package
xjobs/20241010 (test package): Writing generators to $H1_ROOT/framework/archives/x/xjobs/20241010/test_package
xjobs/20241010 (test package): Generator 'VirtualRunEnv' calling 'generate()'
xjobs/20241010 (test package): Generating aggregated env files
xjobs/20241010 (test package): Generated aggregated env files: ['conanrun.sh', 'conanbuild.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
xjobs/20241010 (test package): Running test()
xjobs/20241010 (test package): RUN: $DEVICE_STORAGE/usr/local/bin/python3 $H1_ROOT/framework/archives/x/xjobs/20241010/test_package/functional.py $H1_ROOT/conan-home/p/b/xjobs0b5d12a67a6d5/p/bin/xjobs $H1_ROOT/framework/archives/x/xjobs/20241010/test_package/xjobs-test-results
{
  "total": 8,
  "passed": 8,
  "failed": 0,
  "checks": [
    {
      "name": "framework-compatible --version option",
      "passed": true,
      "detail": "exit=0, stdout='xjobs version 1.2.0\\nCopyright 2006-2024, Thomas Maier-Komor\\nLicense: GPLv2'"
    },
    {
      "name": "six jobs started",
      "passed": true,
      "detail": "started=6"
    },
    {
      "name": "six jobs finished",
      "passed": true,
      "detail": "finished=6, active=0"
    },
    {
      "name": "parallel limit two",
      "passed": true,
      "detail": "exit=0, max_active=2"
    },
    {
      "name": "single-character template argument and spaced job argument preserved",
      "passed": true,
      "detail": "started=[{'item': 'argument with spaces', 'pid': 45117}]"
    },
    {
      "name": "stdout redirected to spaced path",
      "passed": true,
      "detail": "exit=0, content='payload:redirect-target\\n'"
    },
    {
      "name": "failed child sets nonzero exit and -e stops queued jobs",
      "passed": true,
      "detail": "exit=1, started=['before', 'fail']"
    },
    {
      "name": "SIGINT stops queued jobs and reaps running child",
      "passed": true,
      "detail": "exit=0, started=['cancel-first'], finished=['cancel-first'], child_alive=False, stderr=\u001b[K\u001b[0msummary: \u001b[K\u001b[34m1 succeeded, \u001b[0mexecuted in 1.114s\n"
    }
  ]
}

[ok] xjobs/20241010 — conan create passed
[step] L1: Verifying test execution from conan create log...
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[step] L1c: No upstream make check/ctest in log (may be in test_package only)
[step] L4: Scanning patches for dangerous functions...
[step] L5: Baseline artifact check...
[ok] L5: bin/ has content
[step] L1e: Destructive negative test (R34)...
        [sabotage] bin/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on xjobs
[step] L2: Smoke test (version/help check)...
[ok] L2: xjobs --version OK

L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: xjobs --version OK
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

## `root/w3.rc`

Original file SHA-256: `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`. Redacted text SHA-256: `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`.

```text
0
```

## `root/w3.started.json`

Original file SHA-256: `a5803e34241735dc9f00cf904ebaf1cc9472ff9443409725b6381cd70aeb28f5`. Redacted text SHA-256: `f6a5c14b0a4e901efd99add55ba9630a06f34445ad73ba5526f8bf8c2fe965fb`.

```text
{
  "expression": "from ohc.workflow_checks import run_local_ci; raise SystemExit(run_local_ci('xjobs', '20241010', pdir='$H1_ROOT/framework'))",
  "uid": [H1 UID],
  "unix": 1790621282.3104432
}
```

## `root/w3.finished.json`

Original file SHA-256: `f34f18fb4f0283692afec06b714f4356ce498529dc9e8435b1979f951fd25272`. Redacted text SHA-256: `f34f18fb4f0283692afec06b714f4356ce498529dc9e8435b1979f951fd25272`.

```text
{
  "rc": 0,
  "unix": 1790621335.849388
}
```

## `root/w3.stderr`

Original file SHA-256: `425422c27fb7c36e5e68a5174abdc491e2e41ae5fa55a43e9d29bc6086f92674`. Redacted text SHA-256: `e7ced2112405861d053d2eff4035e1557887e23b3cfbb68444f9eb72110b758d`.

```text
  ℹ️ W3: 本地 CI 模拟验证 (xjobs/20241010), 超时预算 3600s ...
  ℹ️   [1/2] setup.sh...
  ✅   ✅ setup.sh 通过
  ℹ️   [2/2] build_and_test.sh xjobs/20241010...
  ✅   ✅ 本地 CI 模拟通过 (日志: $H1_ROOT/framework/archives/x/xjobs/20241010/reports/w3-local-ci.log)
```

## `root/w5-completeness.rc`

Original file SHA-256: `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865`. Redacted text SHA-256: `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865`.

```text
1
```

## `root/w5-completeness.started.json`

Original file SHA-256: `c25db1fe47333175e4c534fd4b208a0ec8864352088c3c838a4beb550aa7fd5f`. Redacted text SHA-256: `14968528875cd971d024dffe3e9698a8422a55facb7be6a630ddad5b2042bbac`.

```text
{
  "expression": "from ohc.workflow_checks import check_knowledge_completeness; raise SystemExit(check_knowledge_completeness(pdir='$H1_ROOT/framework'))",
  "uid": [H1 UID],
  "unix": 1790621335.8499115
}
```

## `root/w5-completeness.finished.json`

Original file SHA-256: `1475f52fc42498509bdea23f08d7fe82bde93a908147bc828c1270d2510b7fd7`. Redacted text SHA-256: `1475f52fc42498509bdea23f08d7fe82bde93a908147bc828c1270d2510b7fd7`.

```text
{
  "rc": 1,
  "unix": 1790621337.53578
}
```

## `root/w5-completeness.stderr`

Original file SHA-256: `5c5cd5893d733d2881750497da0c3f1a00d9dd4a5b07698468fb675f00b7f193`. Redacted text SHA-256: `5c5cd5893d733d2881750497da0c3f1a00d9dd4a5b07698468fb675f00b7f193`.

```text
  ℹ️ W5: 知识图谱完整性检查...
  ✅   ✅ doc↔kv 配套完整 (541 对)
  ⚠️   ⚠️ 字段缺失:
  ⚠️      E219.kv: root_cause 为空
  ⚠️      E253.kv: root_cause 为空
  ⚠️      E305.kv: root_cause 为空
  ⚠️      E305.kv: rec_approach 为空
  ✅   ✅ graph validate 通过
  ℹ️   📝 发现 1965 个草稿待审:
  ℹ️      DRAFT-0001-qt6-to-qt5-api-compat.kv
  ℹ️      DRAFT-001.kv
  ℹ️      DRAFT-10004-qtwayland-qt-tests-deep-path-socket-tmpdir-qpa.kv
  ℹ️      DRAFT-10130-rgb-1.1.1-autotools-destdir-vs-baked-abs-datadir-nesting.kv
  ℹ️      DRAFT-10251-libnfc-tools-1.8.0-automake-per-target-cppflags-empty-override.kv
  ℹ️      ... 还有 1960 个
  ℹ️      ... 还有 1960 个
  ❌   ❌ 知识图谱完整性检查发现 1 类问题
```

## `root/w5-gap.rc`

Original file SHA-256: `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`. Redacted text SHA-256: `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`.

```text
0
```

## `root/w5-gap.started.json`

Original file SHA-256: `98956e908945ba8e81fc038e2e81cb984a290b8e19b0fb08e4a5f38c0b622115`. Redacted text SHA-256: `a57107bb24ef76a02bd26a04b7699b201c2c13667202072f6e8b575def79522c`.

```text
{
  "expression": "from ohc.check_knowledge_gap import check_knowledge_gap; raise SystemExit(check_knowledge_gap('xjobs', '20241010', pdir='$H1_ROOT/framework'))",
  "uid": [H1 UID],
  "unix": 1790621337.536121
}
```

## `root/w5-gap.finished.json`

Original file SHA-256: `fef6219fc17910a7603b81e1d6b6b0ab7e69777fd1213cf066491b34d3e546ac`. Redacted text SHA-256: `fef6219fc17910a7603b81e1d6b6b0ab7e69777fd1213cf066491b34d3e546ac`.

```text
{
  "rc": 0,
  "unix": 1790621337.6310441
}
```

## `root/w5-gap.stderr`

Original file SHA-256: `df477f902cffa370f61db666bbae284f80908be22fa8cbfbd6e0821602a057b9`. Redacted text SHA-256: `df477f902cffa370f61db666bbae284f80908be22fa8cbfbd6e0821602a057b9`.

```text
  ℹ️ notes.md: total=0 extracted=0 pending=0 failed=0
  ℹ️ manifest.yaml: knowledge_count=4 unreferenced=0
  ✅ ✅ 知识完整性检查通过
```

## `root/markers-before.json`

Original file SHA-256: `79bdeac56b973705228261d66ddc4132767b8f903cb1737ca0b9c14b0ddc6dde`. Redacted text SHA-256: `79bdeac56b973705228261d66ddc4132767b8f903cb1737ca0b9c14b0ddc6dde`.

```text
{
  "baseline_markers": {
    "archives/c/cloog/0.21.1/.build-closed": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "archives/c/cloog/0.21.1/.staging-verified": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "archives/k/kics/2.1.20/.staging-verified": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "archives/t/thc/3.8/.staging-verified": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "baseline_unchanged": true,
  "ci_result_exists": false,
  "knowledge_done_exists": false,
  "knowledge_done_sha256": null,
  "w3_log_exists": false
}
```

## `root/markers-after.json`

Original file SHA-256: `08edc5804d4408bc9fb086f1cb383f55bfa3de00f90b43311a8c43b1010f00ee`. Redacted text SHA-256: `08edc5804d4408bc9fb086f1cb383f55bfa3de00f90b43311a8c43b1010f00ee`.

```text
{
  "baseline_markers": {
    "archives/c/cloog/0.21.1/.build-closed": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "archives/c/cloog/0.21.1/.staging-verified": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "archives/k/kics/2.1.20/.staging-verified": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "archives/t/thc/3.8/.staging-verified": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "baseline_unchanged": true,
  "ci_result_exists": false,
  "knowledge_done_exists": true,
  "knowledge_done_sha256": "f93e67c856a982a7b945a449b46d5bb3eab197fb8f4e8b57ecf347d40a53161a",
  "w3_log_exists": true
}
```

