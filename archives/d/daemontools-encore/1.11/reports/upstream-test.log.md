# upstream-test.log — 逐字留档（原文件不随 PR 入库）

- 原始文件: `archives/d/daemontools-encore/1.11/reports/upstream-test.log`（本机工作区，未入库）
- 字节数: 14082
- 行数: 300
- sha256: `06ff1e8a042ac4f085f83c860a82b10dbcfa8be92a4f999810376f15b823fde7`
- 说明: 上游回归套件逐用例运行（cat 00-preamble.sh + <case>.sh → cat -v → diff <case>.exp）
- 生成命令: `sh run-rts-suite.sh <conan build tree> <out-dir> 90`
- 逐字性: fenced 内容与原文件逐字节一致（含行尾空格与末尾空行）；头部字节数/行数/sha256 均对原文件计算

以下为原文件逐字内容（```text 代码块）：

```text
daemontools-encore 1.11 — upstream regression suite (rts.tests), per-case run on the device
tree: /storage/Users/currentUser/.conan2/p/b/daemo5cdac5efc9ae4/b  (conan build folder of the trusted conan-verify round, commit cf7bea0d9051b8993dd847543af726fab04212e0)
conf-cc: /data/service/hnp/bin/clang -O3 -DNDEBUG -Wall -Wshadow -Wcast-align -Wwrite-strings
conf-ld: /data/service/hnp/bin/clang 
runner : sh run-rts-suite.sh <build-tree> <out-dir> 90
         per case: cat rts.tests/00-preamble.sh rts.tests/<case>.sh > <case>.script
                   timeout -k 5 90 env - TMPDIR=<writable> HOME=<sandbox> /bin/sh <case>.script > <case>.raw
                   cat -v <case>.raw > <case>.out ; diff -u rts.tests/<case>.exp <case>.out
         (upstream make rts does: cat rts.tests/*.sh > rts.sh ; env - /bin/sh rts.sh 2>&1 | cat -v > rts ; diff -u rts.exp rts)
why per case: the 9 supervise/svscan cases drive supervise, which cannot create its control FIFO on
              HarmonyOS (EPERM), and the suite's own waitok helper then polls forever -> the aggregate
              'make rts' target never returns (measured: 1200 s timeout, empty rts output file).

=== summary ===
PASS envdir (script_rc=0 diff_rc=0)
PASS envini (script_rc=0 diff_rc=0)
PASS envuidgid (script_rc=0 diff_rc=0)
PASS fghack (script_rc=0 diff_rc=0)
PASS matchtest (script_rc=0 diff_rc=0)
PASS multilog (script_rc=0 diff_rc=0)
PASS nonexistent (script_rc=0 diff_rc=0)
PASS pgrphack (script_rc=0 diff_rc=0)
PASS readproctitle (script_rc=0 diff_rc=0)
PASS setlock (script_rc=0 diff_rc=0)
PASS softlimit (script_rc=0 diff_rc=0)
FAIL supervise-base (script_rc=124 diff_rc=1)
FAIL supervise-downtime (script_rc=124 diff_rc=1)
FAIL supervise-lock (script_rc=124 diff_rc=1)
FAIL supervise-notify (script_rc=0 diff_rc=1)
FAIL supervise-restart (script_rc=124 diff_rc=1)
FAIL supervise-start (script_rc=124 diff_rc=1)
FAIL supervise-stop (script_rc=0 diff_rc=1)
FAIL svc (script_rc=0 diff_rc=1)
FAIL svscan (script_rc=124 diff_rc=1)
PASS tai64n (script_rc=0 diff_rc=0)

==================================================================
CASE envdir : PASS (output matches rts.tests/envdir.exp exactly)
--- first fatal/supervise line in the raw output (if any) ---
envdir: fatal: unable to switch to directory env1: symbolic link loop
envdir: fatal: unable to read env1/Message: symbolic link loop
==================================================================
CASE envini : PASS (output matches rts.tests/envini.exp exactly)
--- first fatal/supervise line in the raw output (if any) ---
envini: fatal: unable to read envi: symbolic link loop
==================================================================
CASE envuidgid : PASS (output matches rts.tests/envuidgid.exp exactly)
--- first fatal/supervise line in the raw output (if any) ---
envuidgid: fatal: unable to run ./nonexistent: file does not exist
==================================================================
CASE fghack : PASS (output matches rts.tests/fghack.exp exactly)
--- first fatal/supervise line in the raw output (if any) ---
fghack: fatal: unable to run ./nonexistent: file does not exist
==================================================================
CASE matchtest : PASS (output matches rts.tests/matchtest.exp exactly)
--- first fatal/supervise line in the raw output (if any) ---
(none)
==================================================================
CASE multilog : PASS (output matches rts.tests/multilog.exp exactly)
--- first fatal/supervise line in the raw output (if any) ---
(none)
==================================================================
CASE nonexistent : PASS (output matches rts.tests/nonexistent.exp exactly)
--- first fatal/supervise line in the raw output (if any) ---
svok: fatal: unable to chdir to nonexistent: file does not exist
supervise: fatal: unable to chdir to nonexistent: file does not exist
==================================================================
CASE pgrphack : PASS (output matches rts.tests/pgrphack.exp exactly)
--- first fatal/supervise line in the raw output (if any) ---
pgrphack: fatal: unable to run ./nonexistent: file does not exist
==================================================================
CASE readproctitle : PASS (output matches rts.tests/readproctitle.exp exactly)
--- first fatal/supervise line in the raw output (if any) ---
(none)
==================================================================
CASE setlock : PASS (output matches rts.tests/setlock.exp exactly)
--- first fatal/supervise line in the raw output (if any) ---
setlock: fatal: unable to open nonexistent/lock: file does not exist
setlock: fatal: unable to lock lock: temporary failure
==================================================================
CASE softlimit : PASS (output matches rts.tests/softlimit.exp exactly)
--- first fatal/supervise line in the raw output (if any) ---
softlimit: fatal: unable to run ./nonexistent: file does not exist
==================================================================
CASE tai64n : PASS (output matches rts.tests/tai64n.exp exactly)
--- first fatal/supervise line in the raw output (if any) ---
(none)
==================================================================
CASE supervise-base : FAIL (output differs from rts.tests/supervise-base.exp)
--- diff -u rts.tests/supervise-base.exp <output> (first 40 lines) ---
--- rts.tests/supervise-base.exp	2018-10-14 08:48:50.000000000 +0800
+++ /storage/Users/currentUser/tmp/daemontools-encore-1.11/rts-trusted/supervise-base.out	2026-09-11 10:51:36.938362188 +0800
@@ -1,35 +1,2 @@
 --- supervise starts, svok works, svup works, svstat works, svc -x works
-100
-100
-100
-test.sv: down x seconds, stopped
-0
-0
-test.sv: supervise not running
-0
---- svc -ox works
-hi
---- svstat and svup work for up services
-.: up (pid x) x seconds, normally down, once, running
-0
-.: up (pid x) x seconds, normally down, once, running
-0
-.: no log service
-0
-0
-100
-0
---- svstat and svup work for logged services
-.: up (pid x) x seconds, normally down, once, running
-. log: up (pid x) x seconds, normally down, once, running
-0
-.: up (pid x) x seconds, normally down, once, running
-0
-. log: up (pid x) x seconds, normally down, once, running
-0
-0
-0
-0
---- svc -u works
-first
-second
+supervise: fatal: unable to read supervise/control: file does not exist
--- first fatal/supervise line in the raw output (if any) ---
supervise: fatal: unable to read supervise/control: file does not exist
==================================================================
CASE supervise-downtime : FAIL (output differs from rts.tests/supervise-downtime.exp)
--- diff -u rts.tests/supervise-downtime.exp <output> (first 40 lines) ---
--- rts.tests/supervise-downtime.exp	2018-10-14 08:48:50.000000000 +0800
+++ /storage/Users/currentUser/tmp/daemontools-encore-1.11/rts-trusted/supervise-downtime.out	2026-09-11 10:53:07.182360938 +0800
@@ -1,3 +1,2 @@
 --- supervise has reasonable downtimes
-test.sv: down ok
-test.sv log: down ok
+supervise: fatal: unable to read supervise/control: file does not exist
--- first fatal/supervise line in the raw output (if any) ---
supervise: fatal: unable to read supervise/control: file does not exist
==================================================================
CASE supervise-lock : FAIL (output differs from rts.tests/supervise-lock.exp)
--- diff -u rts.tests/supervise-lock.exp <output> (first 40 lines) ---
--- rts.tests/supervise-lock.exp	2018-10-14 08:48:50.000000000 +0800
+++ /storage/Users/currentUser/tmp/daemontools-encore-1.11/rts-trusted/supervise-lock.out	2026-09-11 10:54:37.418366094 +0800
@@ -1,14 +1,2 @@
 --- supervise leaves locked service intact
-prw------- 0 control
--rw------- 0 lock
-prw------- 0 ok
--rw-r--r-- 20 status
-supervise: fatal: unable to acquire supervise/lock: temporary failure
-111
-prw------- 0 control
--rw------- 0 lock
-prw------- 0 ok
--rw-r--r-- 20 status
-0
-test.sv: supervise not running
-0
+supervise: fatal: unable to read supervise/control: file does not exist
--- first fatal/supervise line in the raw output (if any) ---
supervise: fatal: unable to read supervise/control: file does not exist
==================================================================
CASE supervise-notify : FAIL (output differs from rts.tests/supervise-notify.exp)
--- diff -u rts.tests/supervise-notify.exp <output> (first 40 lines) ---
--- rts.tests/supervise-notify.exp	2018-10-14 08:48:50.000000000 +0800
+++ /storage/Users/currentUser/tmp/daemontools-encore-1.11/rts-trusted/supervise-notify.out	2026-09-11 10:54:38.914362813 +0800
@@ -1,8 +1,3 @@
 --- supervise runs notify properly
-run exit 1
-run start 0
-start exit 0
-start start 0
-stop exit 0
-stop start 0
+supervise: fatal: unable to read supervise/control: file does not exist
 
--- first fatal/supervise line in the raw output (if any) ---
supervise: fatal: unable to read supervise/control: file does not exist
==================================================================
CASE supervise-restart : FAIL (output differs from rts.tests/supervise-restart.exp)
--- diff -u rts.tests/supervise-restart.exp <output> (first 40 lines) ---
--- rts.tests/supervise-restart.exp	2018-10-14 08:48:50.000000000 +0800
+++ /storage/Users/currentUser/tmp/daemontools-encore-1.11/rts-trusted/supervise-restart.out	2026-09-11 10:56:09.146361563 +0800
@@ -1,14 +1,3 @@
 --- supervise restarts service exiting 0
-started
-running
-rerunning
-
---- supervise restarts service exiting 1
-started
-running
-rerunning
-
---- supervise restarts service exiting 100
-started
-running
-
+supervise: fatal: unable to read supervise/control: file does not exist
+Signal 15 
--- first fatal/supervise line in the raw output (if any) ---
supervise: fatal: unable to read supervise/control: file does not exist
==================================================================
CASE supervise-start : FAIL (output differs from rts.tests/supervise-start.exp)
--- diff -u rts.tests/supervise-start.exp <output> (first 40 lines) ---
--- rts.tests/supervise-start.exp	2018-10-14 08:48:50.000000000 +0800
+++ /storage/Users/currentUser/tmp/daemontools-encore-1.11/rts-trusted/supervise-start.out	2026-09-11 10:57:39.398361875 +0800
@@ -1,2 +1,3 @@
 --- svc -o works first time with start
-ok
+supervise: fatal: unable to read supervise/control: file does not exist
+Signal 15 
--- first fatal/supervise line in the raw output (if any) ---
supervise: fatal: unable to read supervise/control: file does not exist
==================================================================
CASE supervise-stop : FAIL (output differs from rts.tests/supervise-stop.exp)
--- diff -u rts.tests/supervise-stop.exp <output> (first 40 lines) ---
--- rts.tests/supervise-stop.exp	2018-10-14 08:48:50.000000000 +0800
+++ /storage/Users/currentUser/tmp/daemontools-encore-1.11/rts-trusted/supervise-stop.out	2026-09-11 10:57:39.878362031 +0800
@@ -1,7 +1,6 @@
 --- supervise runs stop on down
-in stop
+supervise: fatal: unable to read supervise/control: file does not exist
 
 --- supervise stops log after main
-Caught CONT
-Caught TERM
+supervise: fatal: unable to read supervise/control: file does not exist
 
--- first fatal/supervise line in the raw output (if any) ---
supervise: fatal: unable to read supervise/control: file does not exist
supervise: fatal: unable to read supervise/control: file does not exist
==================================================================
CASE svc : FAIL (output differs from rts.tests/svc.exp)
--- diff -u rts.tests/svc.exp <output> (first 40 lines) ---
--- rts.tests/svc.exp	2018-10-14 08:48:50.000000000 +0800
+++ /storage/Users/currentUser/tmp/daemontools-encore-1.11/rts-trusted/svc.out	2026-09-11 10:57:51.486361875 +0800
@@ -1,12 +1,13 @@
 --- svc sends right signals
-Caught ALRM
-Caught CONT
-Caught HUP
-Caught INT
-Caught TERM
-Caught QUIT
-Caught USR1
-Caught USR2
-Caught WINCH
-Caught CONT
-Caught TERM
+supervise: fatal: unable to read supervise/control: file does not exist
+svc: warning: unable to control test.sv: file does not exist
+svc: warning: unable to control test.sv: file does not exist
+svc: warning: unable to control test.sv: file does not exist
+svc: warning: unable to control test.sv: file does not exist
+svc: warning: unable to control test.sv: file does not exist
+svc: warning: unable to control test.sv: file does not exist
+svc: warning: unable to control test.sv: file does not exist
+svc: warning: unable to control test.sv: file does not exist
+svc: warning: unable to control test.sv: file does not exist
+svc: warning: unable to control test.sv: file does not exist
+svc: warning: unable to control test.sv: file does not exist
--- first fatal/supervise line in the raw output (if any) ---
supervise: fatal: unable to read supervise/control: file does not exist
==================================================================
CASE svscan : FAIL (output differs from rts.tests/svscan.exp)
--- diff -u rts.tests/svscan.exp <output> (first 40 lines) ---
--- rts.tests/svscan.exp	2018-10-14 08:48:50.000000000 +0800
+++ /storage/Users/currentUser/tmp/daemontools-encore-1.11/rts-trusted/svscan.out	2026-09-11 10:59:21.734362656 +0800
@@ -1,11 +1,2 @@
 --- svscan setup
 --- svscan start
---- svscan out
-==> svc0/output <==
-svc0 ran
-
-==> svc1/output <==
-svc1 ran
-
-==> svc2/output <==
-svc2 ran
--- first fatal/supervise line in the raw output (if any) ---
(none)
==================================================================
=== upstream aggregate entry point, for contrast ===
$ cd <copy of the trusted build tree> && timeout 300 make -j1 rts
rc=124 (killed by the 300 s timeout), elapsed=300 s, 'rts' output file absent
leftovers in the tree: rts-tmp/ (env1 env2 envi lock test.status ...)
tail of the run:
  make: *** Deleting file 'rts'
  Signal 15 
  make: *** [Makefile:360: rts] Error 143
=> the aggregate target cannot be used on this device; the per-case runs above are the same
   upstream files and the same comparison, with a per-case timeout so a blocked case cannot
   stall the rest.
```
