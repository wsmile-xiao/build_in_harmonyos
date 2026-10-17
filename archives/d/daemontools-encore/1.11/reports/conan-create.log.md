# conan-create.log — 逐字留档（原文件不随 PR 入库）

- 原始文件: `archives/d/daemontools-encore/1.11/reports/conan-create.log`（本机工作区，未入库）
- 字节数: 21114
- 行数: 385
- sha256: `00d9679235783e90b0be2fca6321b42ec1f09787caf6b08461e794c0ff490513`
- 说明: conan-verify 的 G2 **干净轮**（先按第 7.2 节四步真清 conan 缓存；含 `Apply patch` / `RUN: make -j1 -B programs man` / `Calling build()` / `TOTAL=31 PASS=31`）
- 生成命令: `python3 scripts/ohc-run.py conan-verify daemontools-encore 1.11 --project-dir <repo>（清缓存后）`
- 逐字性: fenced 内容与原文件逐字节一致（含行尾空格与末尾空行）；头部字节数/行数/sha256 均对原文件计算

以下为原文件逐字内容（```text 代码块）：

```text

======== Exporting recipe to the cache ========
daemontools-encore/1.11@ohpcd/stable: Exporting package recipe: /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/conanfile.py
daemontools-encore/1.11@ohpcd/stable: exports: File 'conandata.yml' found. Exporting it...
daemontools-encore/1.11@ohpcd/stable: Calling export_sources()
daemontools-encore/1.11@ohpcd/stable: Copied 1 '.yml' file: conandata.yml
daemontools-encore/1.11@ohpcd/stable: Copied 1 '.py' file: conanfile.py
daemontools-encore/1.11@ohpcd/stable: Copied 1 '.patch' file: 0001-MAN-optional-setuser.patch
daemontools-encore/1.11@ohpcd/stable: Exported to cache folder: /storage/Users/currentUser/.conan2/p/daemoa1891eddd2fd8/e
daemontools-encore/1.11@ohpcd/stable: Exported: daemontools-encore/1.11@ohpcd/stable#3a0d9c9ac9198f8ed1d37f8be18fd9c8 (2026-09-11 11:38:51 UTC)

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
    daemontools-encore/1.11@ohpcd/stable#3a0d9c9ac9198f8ed1d37f8be18fd9c8 - Cache

======== Computing necessary packages ========
Connecting to remote 'ohpcd' anonymously
daemontools-encore/1.11@ohpcd/stable: Main binary package '6b129b068851896169fae42d399fa922d239ce8a' missing
daemontools-encore/1.11@ohpcd/stable: Checking 11 compatible configurations
daemontools-encore/1.11@ohpcd/stable: Compatible configurations not found in cache, checking servers
daemontools-encore/1.11@ohpcd/stable: '7a45daa5a53e1e1e2f88f46c8c5d42c55b8041f7': compiler.cppstd=98
daemontools-encore/1.11@ohpcd/stable: '82803953774dd8ef49af18e200a16f3642cfae9d': compiler.cppstd=gnu98
daemontools-encore/1.11@ohpcd/stable: '8ac2a79ad39b36194df9085b36c9d86fa5599f02': compiler.cppstd=11
daemontools-encore/1.11@ohpcd/stable: '7f9f31995579bd0e1e9a725bfd253c9c7553a331': compiler.cppstd=gnu11
daemontools-encore/1.11@ohpcd/stable: '20ce5ca62dba04ef245a37652eafaea893be3909': compiler.cppstd=14
daemontools-encore/1.11@ohpcd/stable: '1c21bc3ded24ff47b1a195f6cb801f864247735c': compiler.cppstd=gnu14
daemontools-encore/1.11@ohpcd/stable: 'eda5abb401cbed7c3f6f2ad04bfecec451641886': compiler.cppstd=gnu17
daemontools-encore/1.11@ohpcd/stable: '69cb9bbff6b978dbd5b9122e0a14671a692c43e9': compiler.cppstd=20
daemontools-encore/1.11@ohpcd/stable: '57551ed2580a3a49716d342ade5714c03470032d': compiler.cppstd=gnu20
daemontools-encore/1.11@ohpcd/stable: 'da04b77fe39bcbcfe9926450ff73c2349d9b48b8': compiler.cppstd=23
daemontools-encore/1.11@ohpcd/stable: '1c92d4b02dd3fd6c66325064d993005ded38ba97': compiler.cppstd=gnu23
daemontools-encore/1.11@ohpcd/stable: No compatible configuration found

A new experimental approach for binary compatibility detection is available.
    Enable it by setting the core.graph:compatibility_mode=optimized conf
    and get improved performance when querying multiple compatible binaries in remotes.

Requirements
    daemontools-encore/1.11@ohpcd/stable#3a0d9c9ac9198f8ed1d37f8be18fd9c8:6b129b068851896169fae42d399fa922d239ce8a - Build

======== Installing packages ========
daemontools-encore/1.11@ohpcd/stable: Calling source() in /storage/Users/currentUser/.conan2/p/daemoa1891eddd2fd8/s
daemontools-encore/1.11@ohpcd/stable: Sources correctly downloaded from https://untroubled.org/daemontools-encore/daemontools-encore-1.11.tar.gz
daemontools-encore/1.11@ohpcd/stable: Uncompressing daemontools-encore-1.11.tar.gz to .

-------- Installing package daemontools-encore/1.11@ohpcd/stable (1 of 1) --------
daemontools-encore/1.11@ohpcd/stable: Building from source
daemontools-encore/1.11@ohpcd/stable: Package daemontools-encore/1.11@ohpcd/stable:6b129b068851896169fae42d399fa922d239ce8a
daemontools-encore/1.11@ohpcd/stable: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
daemontools-encore/1.11@ohpcd/stable: Copying sources to build folder
daemontools-encore/1.11@ohpcd/stable: Building your package in /storage/Users/currentUser/.conan2/p/b/daemo51816424e0840/b
daemontools-encore/1.11@ohpcd/stable: Calling generate()
daemontools-encore/1.11@ohpcd/stable: Generators folder: /storage/Users/currentUser/.conan2/p/b/daemo51816424e0840/b/build-release/conan
daemontools-encore/1.11@ohpcd/stable: Generating aggregated env files
daemontools-encore/1.11@ohpcd/stable: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
daemontools-encore/1.11@ohpcd/stable: Calling build()
daemontools-encore/1.11@ohpcd/stable: Apply patch (bugfix): MAN install manifest: mark the setuser.8 entry with the installer's own '?' optional prefix. Release 1.11 neither ships setuser.8 nor builds it (the Makefile man target builds setuidgid.8 while MAN still asks for setuser.8) so the unpatched upstream `make install` always aborts with "installer: fatal: unable to read setuser.8: file does not exist"
daemontools-encore/1.11@ohpcd/stable: conf-cc: /data/service/hnp/bin/clang -O3 -DNDEBUG -Wall -Wshadow -Wcast-align -Wwrite-strings
daemontools-encore/1.11@ohpcd/stable: conf-ld: /data/service/hnp/bin/clang 
daemontools-encore/1.11@ohpcd/stable: RUN: make -j1 -B programs man
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

daemontools-encore/1.11@ohpcd/stable: Package '6b129b068851896169fae42d399fa922d239ce8a' built
daemontools-encore/1.11@ohpcd/stable: Build folder /storage/Users/currentUser/.conan2/p/b/daemo51816424e0840/b/build-release
daemontools-encore/1.11@ohpcd/stable: Generating the package
daemontools-encore/1.11@ohpcd/stable: Packaging in folder /storage/Users/currentUser/.conan2/p/b/daemo51816424e0840/p
daemontools-encore/1.11@ohpcd/stable: Calling package()
daemontools-encore/1.11@ohpcd/stable: RUN: make -j1 install
./installer `head -n 1 conf-bin` <BIN
./installer `head -n 1 conf-man` <MAN

daemontools-encore/1.11@ohpcd/stable: package(): Packaged 21 files
daemontools-encore/1.11@ohpcd/stable: package(): Packaged 19 '.8' files
daemontools-encore/1.11@ohpcd/stable: Created package revision 95a0a81ad2eb1eef4e131ab0d2e836db
daemontools-encore/1.11@ohpcd/stable: Package '6b129b068851896169fae42d399fa922d239ce8a' created
daemontools-encore/1.11@ohpcd/stable: Full package reference: daemontools-encore/1.11@ohpcd/stable#3a0d9c9ac9198f8ed1d37f8be18fd9c8:6b129b068851896169fae42d399fa922d239ce8a#95a0a81ad2eb1eef4e131ab0d2e836db
daemontools-encore/1.11@ohpcd/stable: Package folder /storage/Users/currentUser/.conan2/p/b/daemo51816424e0840/p

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    daemontools-encore/1.11@ohpcd/stable (test package): /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/conanfile.py
Requirements
    daemontools-encore/1.11@ohpcd/stable#3a0d9c9ac9198f8ed1d37f8be18fd9c8 - Cache

======== Computing necessary packages ========
Requirements
    daemontools-encore/1.11@ohpcd/stable#3a0d9c9ac9198f8ed1d37f8be18fd9c8:6b129b068851896169fae42d399fa922d239ce8a#95a0a81ad2eb1eef4e131ab0d2e836db - Cache

======== Installing packages ========
daemontools-encore/1.11@ohpcd/stable: Already installed! (1 of 1)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/build-release
daemontools-encore/1.11@ohpcd/stable (test package): Test package build: build-release
daemontools-encore/1.11@ohpcd/stable (test package): Test package build folder: /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/build-release
daemontools-encore/1.11@ohpcd/stable (test package): Generating aggregated env files
daemontools-encore/1.11@ohpcd/stable (test package): Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
daemontools-encore/1.11@ohpcd/stable (test package): Running test()
daemontools-encore/1.11@ohpcd/stable (test package): RUN: "/data/service/hnp/python.org/python_3.12/bin/python3.12" "/storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/test_daemontools.py" "/storage/Users/currentUser/.conan2/p/b/daemo51816424e0840/p/bin"
[info] bin dir : /storage/Users/currentUser/.conan2/p/b/daemo51816424e0840/p/bin
[info] work dir: /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/build-release/daemontools-test-08yt8y87
PASS  package ships the 20 upstream programs  |  20 programs executable
PASS  envdir sets variables from the directory  |  rc=0 out='This is a test. This is only a test.'
PASS  envdir removes variables whose file is empty  |  rc=0 out='[<unset>]'
PASS  envdir -p prefixes variables  |  rc=0 out='This is a test. This is only a test.'
PASS  envdir reports usage on missing arguments  |  rc=111 out='envdir: usage: envdir [ -p prefix ] dir child'
PASS  envini reads global and section variables  |  rc=0 out='This is a test.\nThis is only a test.'
PASS  envini -p prefixes global variables  |  rc=0 out='This is a test.'
PASS  fghack runs its child and keeps stdout connected  |  rc=0 out='fghack-child-ran'
PASS  fghack reports usage on missing arguments  |  rc=100 out='fghack: usage: fghack child'
PASS  pgrphack runs its child and it reports its own process group id  |  rc=0 out='child-pgrp=17500'
PASS  pgrphack really leaves the caller's process group  |  rc=0 caller pgrp=16556 child pgrp=17501
PASS  setlock runs the child while holding the lock file  |  rc=0 out='lock-held'
PASS  setlock creates the lock file  |  /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/build-release/daemontools-test-08yt8y87/lock
PASS  setlock -n fails while the lock is already held  |  rc=0 out='inner-rc=111\nsetlock: fatal: unable to lock /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test'
PASS  setlock -nx exits quietly while the lock is already held  |  rc=0 out='innerx-rc=0'
PASS  softlimit -c 0 lowers the child core limit  |  rc=0 out='core=0'
PASS  softlimit passes the child through unchanged otherwise  |  rc=0 out='softlimit-child-ran'
PASS  tai64n stamps every line with a 12 byte TAI64N label  |  rc=0 out='@400000006aa3e8722cb50f8c ONE\n@400000006aa3e8722cb51374 TWO'
PASS  tai64n labels two lines  |  labels=2
PASS  tai64nlocal converts TAI64N lines back to local time  |  rc=0 out='2026-09-11 19:39:20.750063500 ONE\n2026-09-11 19:39:20.750064500 TWO'
PASS  tai64nlocal passes non-stamped lines through  |  rc=0 out='plain-line'
PASS  multilog writes timestamped lines into dir/current  |  rc=0 current='@400000006aa3e8723075ad84 line-a\n@400000006aa3e8723075b16c line-b'
PASS  multilog =status keeps the fixed status record  |  rc=0 bytes=1001 newlines=998
PASS  multilog e forwards matched lines to stderr  |  rc=0 stderr='err-line'
PASS  readproctitle reports usage on missing arguments  |  rc=100 out=''
PASS  svok reports 100 for an existing but unsupervised directory  |  rc=100 out=''
PASS  svok reports 111 for a nonexistent directory  |  rc=111 out='svok: fatal: unable to chdir to /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/bui'
PASS  svstat reports an unsupervised service and a missing directory  |  rc=0 out='/storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/build-release/daemontools-test-08yt'
PASS  svc warns about an unsupervised service and a missing directory  |  rc=0 out='svc: warning: unable to control /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_package/bui'
PASS  supervise reports a missing service directory  |  rc=111 out='supervise: fatal: unable to chdir to /storage/Users/currentUser/ws/wt-daemontools-encore-1.11/archives/d/daemontools-encore/1.11/test_packag'
[info] mkfifo(2) unavailable on this platform: [Errno 1] Operation not permitted
PASS  supervise fails fast with the documented control-channel error (mkfifo unavailable)  |  rc=111 out='supervise: fatal: unable to read supervise/control: file does not exist'

TOTAL=31 PASS=31 FAIL=0

```
