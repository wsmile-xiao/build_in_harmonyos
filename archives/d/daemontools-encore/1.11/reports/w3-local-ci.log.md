# w3-local-ci.log — 逐字留档（原文件不随 PR 入库）

- 原始文件: `archives/d/daemontools-encore/1.11/reports/w3-local-ci.log`（本机工作区，未入库）
- 字节数: 25764
- 行数: 511
- sha256: `06797aaeb781a7f8f69ace542e021708514bfcced270dd0a60c1cc921df62061`
- 说明: finish 的 Step 5 本地 CI 模拟（W3），与本轮提交内容一致
- 生成命令: `python3 scripts/ohc-run.py finish daemontools-encore 1.11 built --project-dir <repo>`
- 逐字性: fenced 内容与原文件逐字节一致（含行尾空格与末尾空行）；头部字节数/行数/sha256 均对原文件计算

以下为原文件逐字内容（```text 代码块）：

```text
$ setup.sh (RC=0)
[step] Conan environment setup...
[step] Conan version: Conan version 2.29.1
[step] Disabling conancenter (private CI, not needed)
conancenter: https://center2.conan.io [Verify SSL: True, Enabled: False]
[step] remote 已就绪: ohpcd
[step] Importing profile from /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/ci/conan/profiles/ohos-aarch64
[step] Profile file available at: /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/ci/conan/profiles/ohos-aarch64
[step] Conan environment ready ✅
[step]   remote: ohpcd
[step]   profile: ohos-aarch64
[step]   conan: Conan version 2.29.1


$ build_and_test.sh archives/d/daemontools-encore/1.11 (RC=0)
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
[step] CI_PACKAGES received: archives/d/daemontools-encore/1.11
[step] Found 1 package(s) to build

━━━ Building: daemontools-encore/1.11 ━━━
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
  检查模式: prdiff (26 个文件)

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
  [try 1/1.1/3] daemontools-encore-1.11.tar.gz ← https://untroubled.org/daemontools-encore/daemontools-encore-1.11.tar.gz...
  [ok] daemontools-encore-1.11.tar.gz (92KB) via mirror 1
  [done] Pre-downloaded 1 files, conandata.yml updated to file:// URLs
[step] Running conan create (output logged to /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/.ci_logs/conan_build_daemontools-encore_1.11.log)...

======== Exporting recipe to the cache ========
daemontools-encore/1.11: Exporting package recipe: /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/conanfile.py
daemontools-encore/1.11: exports: File 'conandata.yml' found. Exporting it...
daemontools-encore/1.11: Calling export_sources()
daemontools-encore/1.11: Copied 1 '.yml' file: conandata.yml
daemontools-encore/1.11: Copied 1 '.py' file: conanfile.py
daemontools-encore/1.11: Copied 1 '.patch' file: 0001-MAN-optional-setuser.patch
daemontools-encore/1.11: Exported to cache folder: /storage/Users/currentUser/.conan2/p/daemo009762bd38deb/e
daemontools-encore/1.11: Exported: daemontools-encore/1.11#de4c9e1fcdc866f5ca56b7b52b7c7e4d (2026-09-11 11:40:38 UTC)

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
    daemontools-encore/1.11#de4c9e1fcdc866f5ca56b7b52b7c7e4d - Cache

======== Computing necessary packages ========
daemontools-encore/1.11: Forced build from source
Requirements
    daemontools-encore/1.11#de4c9e1fcdc866f5ca56b7b52b7c7e4d:6b129b068851896169fae42d399fa922d239ce8a - Build

======== Installing packages ========
daemontools-encore/1.11: Calling source() in /storage/Users/currentUser/.conan2/p/daemo009762bd38deb/s
daemontools-encore/1.11: Sources correctly downloaded from file:///storage/Users/currentUser/ws/wt-daemontools-encore-1.11/.build-cache/predl_cache/26a88fb6_daemontools-encore-1.11.tar.gz
daemontools-encore/1.11: Uncompressing 26a88fb6_daemontools-encore-1.11.tar.gz to .

-------- Installing package daemontools-encore/1.11 (1 of 1) --------
daemontools-encore/1.11: Building from source
daemontools-encore/1.11: Package daemontools-encore/1.11:6b129b068851896169fae42d399fa922d239ce8a
daemontools-encore/1.11: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
daemontools-encore/1.11: Copying sources to build folder
daemontools-encore/1.11: Building your package in /storage/Users/currentUser/.conan2/p/b/daemo3c49decf81de9/b
daemontools-encore/1.11: Calling generate()
daemontools-encore/1.11: Generators folder: /storage/Users/currentUser/.conan2/p/b/daemo3c49decf81de9/b/build-release/conan
daemontools-encore/1.11: Generating aggregated env files
daemontools-encore/1.11: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
daemontools-encore/1.11: Calling build()
daemontools-encore/1.11: Apply patch (bugfix): MAN install manifest: mark the setuser.8 entry with the installer's own '?' optional prefix. Release 1.11 neither ships setuser.8 nor builds it (the Makefile man target builds setuidgid.8 while MAN still asks for setuser.8) so the unpatched upstream `make install` always aborts with "installer: fatal: unable to read setuser.8: file does not exist"
daemontools-encore/1.11: conf-cc: /data/service/hnp/bin/clang -O3 -DNDEBUG -Wall -Wshadow -Wcast-align -Wwrite-strings
daemontools-encore/1.11: conf-ld: /data/service/hnp/bin/clang 
daemontools-encore/1.11: RUN: make -j1 -B programs man
sh find-systype.sh > systype
rm -f load
sh print-ld.sh > load
chmod 555 load
rm -f compile
sh print-cc.sh > compile
chmod 555 compile
rm -f choose
cat warn-auto.sh choose.sh > choose
chmod 555 choose
./choose c trydrent direntry.h1 direntry.h2 > direntry.h
./choose c tryattribute hasattribute.h1 hasattribute.h2 > hasattribute.h
./compile envdir.c
rm -f makelib
sh print-ar.sh > makelib
chmod 555 makelib
./compile alloc.c
./compile alloc_re.c
./compile buffer.c
./compile buffer_0.c
buffer_0.c:5:5: warning: a function definition without a prototype is deprecated in all versions of C and is not supported in C2x [-Wdeprecated-non-prototype]
int buffer_0_read(fd,buf,len) int fd; char *buf; int len;
    ^
1 warning generated.
./compile buffer_1.c
./compile buffer_2.c
./compile buffer_copy.c
./compile buffer_copyline.c
./compile buffer_get.c
buffer_get.c:12:11: warning: passing arguments to a function without a prototype is deprecated in all versions of C and is not supported in C2x [-Wdeprecated-non-prototype]
    r = op(fd,buf,len);
          ^
1 warning generated.
./compile buffer_gets.c
./compile buffer_put.c
buffer_put.c:13:11: warning: passing arguments to a function without a prototype is deprecated in all versions of C and is not supported in C2x [-Wdeprecated-non-prototype]
    w = op(fd,buf,len);
          ^
1 warning generated.
./compile buffer_read.c
./compile buffer_write.c
./compile closeonexec.c
./compile env.c
./compile error.c
./compile error_str.c
./compile fd_copy.c
./compile fd_move.c
./choose cl trymkffo hasmkffo.h1 hasmkffo.h2 > hasmkffo.h
./compile fifo.c
./choose cl tryflock hasflock.h1 hasflock.h2 > hasflock.h
./compile lock_ex.c
./compile lock_exnb.c
./compile ndelay_off.c
./compile ndelay_on.c
./compile open_append.c
./compile open_read.c
./compile open_trunc.c
./compile open_write.c
./compile openreadclose.c
./compile pathexec_env.c
./compile pathexec_run.c
./compile chkshsgr.c
chkshsgr.c:12:19: warning: cast from 'short *' to 'gid_t *' (aka 'unsigned int *') increases required alignment from 2 to 4 [-Wcast-align]
  if (getgroups(1,(gid_t*)x) == 0) if (setgroups(1,(gid_t*)x) == -1) _exit(1);
                  ^~~~~~~~~
chkshsgr.c:12:52: warning: cast from 'short *' to 'gid_t *' (aka 'unsigned int *') increases required alignment from 2 to 4 [-Wcast-align]
  if (getgroups(1,(gid_t*)x) == 0) if (setgroups(1,(gid_t*)x) == -1) _exit(1);
                                                   ^~~~~~~~~
2 warnings generated.
./load chkshsgr 
./chkshsgr || ( cat warn-shsgr; exit 1 )
./choose clr tryshsgr hasshsgr.h1 hasshsgr.h2 > hasshsgr.h
./compile prot.c
./compile readclose.c
./compile seek_set.c
./compile sgetopt.c
./compile sig.c
./choose cl trysgprm hassgprm.h1 hassgprm.h2 > hassgprm.h
./compile sig_block.c
./choose cl trysgact hassgact.h1 hassgact.h2 > hassgact.h
./compile sig_catch.c
./compile sig_pause.c
./compile stralloc_append.c
./compile stralloc_catb.c
./compile stralloc_cat.c
./compile stralloc_cats.c
./compile stralloc_copyb.c
./compile stralloc_copy.c
./compile stralloc_copys.c
./compile stralloc_ready.c
./compile strerr_die.c
./compile strerr_sys.c
./compile subgetopt.c
./choose cl trywaitp haswaitp.h1 haswaitp.h2 > haswaitp.h
./compile wait_nohang.c
wait_nohang.c:7:5: warning: a function definition without a prototype is deprecated in all versions of C and is not supported in C2x [-Wdeprecated-non-prototype]
int wait_nohang(wstat) int *wstat;
    ^
1 warning generated.
./compile wait_pid.c
wait_pid.c:10:5: warning: a function definition without a prototype is deprecated in all versions of C and is not supported in C2x [-Wdeprecated-non-prototype]
int wait_pid(wstat,pid) int *wstat; int pid;
    ^
1 warning generated.
./makelib unix.a alloc.o alloc_re.o buffer.o buffer_0.o buffer_1.o buffer_2.o buffer_copy.o buffer_copyline.o buffer_get.o buffer_gets.o buffer_put.o buffer_read.o buffer_write.o closeonexec.o env.o error.o error_str.o fd_copy.o fd_move.o fifo.o lock_ex.o lock_exnb.o ndelay_off.o ndelay_on.o open_append.o open_read.o open_trunc.o open_write.o openreadclose.o pathexec_env.o pathexec_run.o prot.o readclose.o seek_set.o sgetopt.o sig.o sig_block.o sig_catch.o sig_pause.o stralloc_append.o stralloc_catb.o stralloc_cat.o stralloc_cats.o stralloc_copyb.o stralloc_copy.o stralloc_copys.o stralloc_ready.o strerr_die.o strerr_sys.o subgetopt.o wait_nohang.o wait_pid.o
./compile byte_chr.c
./choose cl trymemrchr hasmemrchr.h1 hasmemrchr.h2 > hasmemrchr.h
./compile byte_rchr.c
./compile fmt_uint.c
./compile fmt_uint0.c
./compile fmt_ulong.c
./compile scan_ulong.c
./compile scan_8long.c
./compile str_chr.c
./compile str_start.c
./makelib byte.a byte_chr.o byte_rchr.o fmt_uint.o fmt_uint0.o fmt_ulong.o scan_ulong.o scan_8long.o str_chr.o str_start.o
./load envdir unix.a byte.a 
./compile envini.c
./load envini unix.a byte.a 
./compile envuidgid.c
./load envuidgid unix.a byte.a 
./compile fghack.c
./load fghack unix.a byte.a 
./compile installer.c
./compile getln.c
./compile getln2.c
./makelib getln.a getln.o getln2.o
./load installer getln.a unix.a byte.a 
./compile matchtest.c
./compile match.c
./load matchtest match.o unix.a byte.a 
./compile multilog.c
./choose clr tryulong64 uint64.h1 uint64.h2 > uint64.h
./choose clr trypoll iopause.h1 iopause.h2 > iopause.h
./compile deepsleep.c
./compile timestamp.c
./choose c trysysel select.h1 select.h2 > select.h
./compile iopause.c
In file included from iopause.c:4:
./select.h:11:12: warning: a function declaration without a prototype is deprecated in all versions of C and is treated as a zero-parameter prototype in C2x, conflicting with a previous declaration [-Wdeprecated-non-prototype]
extern int select();
           ^
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/sys/select.h:40:5: note: conflicting prototype is here
int select (int, fd_set *__restrict, fd_set *__restrict, fd_set *__restrict, struct timeval *__restrict);
    ^
1 warning generated.
./compile tai_now.c
./compile tai_pack.c
./compile tai_sub.c
./compile tai_unpack.c
./compile taia_add.c
./compile taia_approx.c
./compile taia_frac.c
./compile taia_less.c
./compile taia_now.c
./compile taia_pack.c
./compile taia_sub.c
./compile taia_uint.c
./makelib time.a iopause.o tai_now.o tai_pack.o tai_sub.o tai_unpack.o taia_add.o taia_approx.o taia_frac.o taia_less.o taia_now.o taia_pack.o taia_sub.o taia_uint.o
./load multilog deepsleep.o match.o timestamp.o time.a unix.a byte.a 
./compile pgrphack.c
./load pgrphack unix.a byte.a 
./compile readproctitle.c
./load readproctitle unix.a byte.a 
./compile setlock.c
./load setlock unix.a byte.a 
./compile setuidgid.c
./load setuidgid unix.a byte.a 
./compile setuser.c
./load setuser unix.a byte.a 
./compile sleeper.c
./load sleeper byte.a unix.a 
./compile softlimit.c
./load softlimit unix.a byte.a 
./compile supervise.c
echo 'const char conf_supervise[] = "'`head -n 1 conf-supervise`'";' >conf_supervise.c
./compile svpath.c
./load supervise deepsleep.o svpath.o time.a unix.a byte.a 
./compile svc.c
./load svc svpath.o unix.a byte.a 
./compile svok.c
./load svok svpath.o unix.a byte.a 
./compile svscan.c
./load svscan unix.a byte.a 
cat warn-auto.sh svscanboot.sh > svscanboot
chmod 755 svscanboot
./compile svstat.c
./load svstat svpath.o time.a unix.a byte.a 
./compile svup.c
./load svup svpath.o unix.a byte.a 
./compile tai64n.c
./load tai64n timestamp.o time.a unix.a byte.a 
./compile tai64nlocal.c
./load tai64nlocal unix.a byte.a 
cat warn-auto.sh > dosubst
echo "sed -e 's}@SUPERVISEDIR@}supervise}g'" >> dosubst
chmod 755 dosubst
./dosubst <supervise.8.in >supervise.8
./dosubst <svc.8.in >svc.8
./dosubst <svok.8.in >svok.8
./dosubst <svstat.8.in >svstat.8
./dosubst <svup.8.in >svup.8

daemontools-encore/1.11: Package '6b129b068851896169fae42d399fa922d239ce8a' built
daemontools-encore/1.11: Build folder /storage/Users/currentUser/.conan2/p/b/daemo3c49decf81de9/b/build-release
daemontools-encore/1.11: Generating the package
daemontools-encore/1.11: Packaging in folder /storage/Users/currentUser/.conan2/p/b/daemo3c49decf81de9/p
daemontools-encore/1.11: Calling package()
daemontools-encore/1.11: RUN: make -j1 install
./installer `head -n 1 conf-bin` <BIN
./installer `head -n 1 conf-man` <MAN

daemontools-encore/1.11: package(): Packaged 21 files
daemontools-encore/1.11: package(): Packaged 19 '.8' files
daemontools-encore/1.11: Created package revision 95a0a81ad2eb1eef4e131ab0d2e836db
daemontools-encore/1.11: Package '6b129b068851896169fae42d399fa922d239ce8a' created
daemontools-encore/1.11: Full package reference: daemontools-encore/1.11#de4c9e1fcdc866f5ca56b7b52b7c7e4d:6b129b068851896169fae42d399fa922d239ce8a#95a0a81ad2eb1eef4e131ab0d2e836db
daemontools-encore/1.11: Package folder /storage/Users/currentUser/.conan2/p/b/daemo3c49decf81de9/p

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    daemontools-encore/1.11 (test package): /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/conanfile.py
Requirements
    daemontools-encore/1.11#de4c9e1fcdc866f5ca56b7b52b7c7e4d - Cache

======== Computing necessary packages ========
Requirements
    daemontools-encore/1.11#de4c9e1fcdc866f5ca56b7b52b7c7e4d:6b129b068851896169fae42d399fa922d239ce8a#95a0a81ad2eb1eef4e131ab0d2e836db - Cache

======== Installing packages ========
daemontools-encore/1.11: Already installed! (1 of 1)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/build-release
daemontools-encore/1.11 (test package): Test package build: build-release
daemontools-encore/1.11 (test package): Test package build folder: /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/build-release
daemontools-encore/1.11 (test package): Generating aggregated env files
daemontools-encore/1.11 (test package): Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
daemontools-encore/1.11 (test package): Running test()
daemontools-encore/1.11 (test package): RUN: "/data/service/hnp/python.org/python_3.12/bin/python3.12" "/storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/test_daemontools.py" "/storage/Users/currentUser/.conan2/p/b/daemo3c49decf81de9/p/bin"
[info] bin dir : /storage/Users/currentUser/.conan2/p/b/daemo3c49decf81de9/p/bin
[info] work dir: /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/build-release/daemontools-test-p0i6o0po
PASS  package ships the 20 upstream programs  |  20 programs executable
PASS  envdir sets variables from the directory  |  rc=0 out='This is a test. This is only a test.'
PASS  envdir removes variables whose file is empty  |  rc=0 out='[<unset>]'
PASS  envdir -p prefixes variables  |  rc=0 out='This is a test. This is only a test.'
PASS  envdir reports usage on missing arguments  |  rc=111 out='envdir: usage: envdir [ -p prefix ] dir child'
PASS  envini reads global and section variables  |  rc=0 out='This is a test.\nThis is only a test.'
PASS  envini -p prefixes global variables  |  rc=0 out='This is a test.'
PASS  fghack runs its child and keeps stdout connected  |  rc=0 out='fghack-child-ran'
PASS  fghack reports usage on missing arguments  |  rc=100 out='fghack: usage: fghack child'
PASS  pgrphack runs its child and it reports its own process group id  |  rc=0 out='child-pgrp=19180'
PASS  pgrphack really leaves the caller's process group  |  rc=0 caller pgrp=18422 child pgrp=19184
PASS  setlock runs the child while holding the lock file  |  rc=0 out='lock-held'
PASS  setlock creates the lock file  |  /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/build-release/daemontools-test-p0i6o0po/lock
PASS  setlock -n fails while the lock is already held  |  rc=0 out='inner-rc=111\nsetlock: fatal: unable to lock /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test'
PASS  setlock -nx exits quietly while the lock is already held  |  rc=0 out='innerx-rc=0'
PASS  softlimit -c 0 lowers the child core limit  |  rc=0 out='core=0'
PASS  softlimit passes the child through unchanged otherwise  |  rc=0 out='softlimit-child-ran'
PASS  tai64n stamps every line with a 12 byte TAI64N label  |  rc=0 out='@400000006aa3e8db1a316414 ONE\n@400000006aa3e8db1a3167fc TWO'
PASS  tai64n labels two lines  |  labels=2
PASS  tai64nlocal converts TAI64N lines back to local time  |  rc=0 out='2026-09-11 19:41:05.439444500 ONE\n2026-09-11 19:41:05.439445500 TWO'
PASS  tai64nlocal passes non-stamped lines through  |  rc=0 out='plain-line'
PASS  multilog writes timestamped lines into dir/current  |  rc=0 current='@400000006aa3e8db1e1ea7bc line-a\n@400000006aa3e8db1e1eaba4 line-b'
PASS  multilog =status keeps the fixed status record  |  rc=0 bytes=1001 newlines=998
PASS  multilog e forwards matched lines to stderr  |  rc=0 stderr='err-line'
PASS  readproctitle reports usage on missing arguments  |  rc=100 out=''
PASS  svok reports 100 for an existing but unsupervised directory  |  rc=100 out=''
PASS  svok reports 111 for a nonexistent directory  |  rc=111 out='svok: fatal: unable to chdir to /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/bui'
PASS  svstat reports an unsupervised service and a missing directory  |  rc=0 out='/storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/build-release/daemontools-test-p0i6'
PASS  svc warns about an unsupervised service and a missing directory  |  rc=0 out='svc: warning: unable to control /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/bui'
PASS  supervise reports a missing service directory  |  rc=111 out='supervise: fatal: unable to chdir to /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_packag'
[info] mkfifo(2) unavailable on this platform: [Errno 1] Operation not permitted
PASS  supervise fails fast with the documented control-channel error (mkfifo unavailable)  |  rc=111 out='supervise: fatal: unable to read supervise/control: file does not exist'

TOTAL=31 PASS=31 FAIL=0

[ok] daemontools-encore/1.11 — conan create passed
[step] L1: Verifying test execution from conan create log...
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[step] L1c: No upstream make check/ctest in log (may be in test_package only)
[step] L4: Scanning patches for dangerous functions...
[step] L5: Baseline artifact check...
[ok] L5: bin/ has content
[step] L1e: Destructive negative test (R34)...
        [sabotage] bin/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on daemontools-encore
[step] L2: Smoke test (version/help check)...
[warn] L2: envdir --version/--help failed (non-blocking)
[warn] L2: envini --version/--help failed (non-blocking)
[warn] L2: envuidgid --version/--help failed (non-blocking)
[warn] L2: fghack --version/--help failed (non-blocking)
[ok] L2: multilog --version OK
[warn] L2: pgrphack --version/--help failed (non-blocking)
[ok] L2: readproctitle --version OK
[warn] L2: setlock --version/--help failed (non-blocking)
[warn] L2: setuidgid --version/--help failed (non-blocking)
[warn] L2: setuser --version/--help failed (non-blocking)
[warn] L2: softlimit --version/--help failed (non-blocking)
[warn] L2: supervise --version/--help failed (non-blocking)
[ok] L2: svc --version OK
[warn] L2: svok --version/--help failed (non-blocking)
[warn] L2: svscan --version/--help failed (non-blocking)
[warn] L2: svscanboot --version/--help failed (non-blocking)
[warn] L2: svstat --version/--help failed (non-blocking)
[warn] L2: svup --version/--help failed (non-blocking)
[ok] L2: tai64n --version OK
[ok] L2: tai64nlocal --version OK

L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: envdir version/help failed, envini failed, envuidgid failed, fghack failed, multilog --version OK, pgrphack failed, readproctitle --version OK, setlock failed, setuidgid failed, setuser failed, softlimit failed, supervise failed, svc --version OK, svok failed, svscan failed, svscanboot failed, svstat failed, svup failed, tai64n --version OK, tai64nlocal --version OK
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
