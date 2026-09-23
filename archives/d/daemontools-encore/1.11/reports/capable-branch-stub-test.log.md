# capable-branch-stub-test.log — 逐字留档（原文件不随 PR 入库）

- 原始文件: `archives/d/daemontools-encore/1.11/reports/capable-branch-stub-test.log`（本机工作区，未入库）
- 字节数: 8206
- 行数: 84
- sha256: `dd979b9f0e21527f02b0bf62892eb4f38a6ddb7bc825ccd8b88fa0b2700ea09e`
- 说明: FIFO 可用分支的桩件逻辑测试（本设备 mkfifo 被拒，该分支不可达）
- 生成命令: `sh make-stubs.sh <shadow> <pkg> <mode>，再由 run-capable.py 以 os.mkfifo 强制成功运行未改动脚本`
- 逐字性: fenced 内容与原文件逐字节一致（含行尾空格与末尾空行）；头部字节数/行数/sha256 均对原文件计算

以下为原文件逐字内容（```text 代码块）：

```text
### FIFO-capable branch of test_package/test_daemontools.py — stub-based logic test
### Why: this device denies mkfifo(2), so the branch is unreachable here; it is exercised by
### running the UNCHANGED script with os.mkfifo forced to succeed and with stub
### supervise/svok/svup/svc/svstat implementing the semantics documented by upstream
### rts.tests/*.exp. All other tools (envdir/envini/envuidgid/fghack/multilog/pgrphack/
### readproctitle/setlock/setuidgid/setuser/softlimit/svscan/svscanboot/tai64n/tai64nlocal)
### are the real packaged binaries; svok/svstat/svc are stubbed in this harness, so this is
### control-flow evidence for the probe branch, not independent behavioural evidence for them.
### Package: /storage/Users/currentUser/.conan2/p/b/daemo7c8a6b9e3a117/p
### Script:  archives/d/daemontools-encore/1.11/test_package/test_daemontools.py

=========== stub mode: happy
PASS  svok reports 100 for an existing but unsupervised directory  |  rc=100 out=''
PASS  svok reports 111 for a nonexistent directory  |  rc=111 out='svok: fatal: unable to chdir to /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-3duvo8f1/'
PASS  svstat reports an unsupervised service and a missing directory  |  rc=0 out='/storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-3duvo8f1/test.sv: unable to open supervis'
PASS  svc warns about an unsupervised service and a missing directory  |  rc=0 out='svc: warning: unable to control /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-3duvo8f1/'
PASS  supervise reports a missing service directory  |  rc=111 out='supervise: fatal: unable to chdir to /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-3duv'
PASS  supervise comes up and svok reports the service as supervised
PASS  svup reports the service as up once supervise started it
PASS  svc -x stops the service  |  rc=0
PASS  svstat reports supervise not running after svc -x  |  /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-3duvo8f1/test.sv: supervise not running
TOTAL=34 PASS=34 FAIL=0
--- leftover stub processes: 0

=========== stub mode: svup-down
PASS  svok reports 100 for an existing but unsupervised directory  |  rc=100 out=''
PASS  svok reports 111 for a nonexistent directory  |  rc=111 out='svok: fatal: unable to chdir to /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-8z53icku/'
PASS  svstat reports an unsupervised service and a missing directory  |  rc=0 out='/storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-8z53icku/test.sv: unable to open supervis'
PASS  svc warns about an unsupervised service and a missing directory  |  rc=0 out='svc: warning: unable to control /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-8z53icku/'
PASS  supervise reports a missing service directory  |  rc=111 out='supervise: fatal: unable to chdir to /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-8z53'
PASS  supervise comes up and svok reports the service as supervised
FAIL  svup reports the service as up once supervise started it
PASS  svc -x stops the service  |  rc=0
PASS  svstat reports supervise not running after svc -x  |  /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-8z53icku/test.sv: supervise not running
TOTAL=34 PASS=33 FAIL=1
  FAILED: svup reports the service as up once supervise started it
--- leftover stub processes: 0

=========== stub mode: neverup
PASS  svok reports 100 for an existing but unsupervised directory  |  rc=100 out=''
PASS  svok reports 111 for a nonexistent directory  |  rc=111 out='svok: fatal: unable to chdir to /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-js3cdmex/'
PASS  svstat reports an unsupervised service and a missing directory  |  rc=0 out='/storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-js3cdmex/test.sv: unable to open supervis'
PASS  svc warns about an unsupervised service and a missing directory  |  rc=0 out='svc: warning: unable to control /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-js3cdmex/'
PASS  supervise reports a missing service directory  |  rc=111 out='supervise: fatal: unable to chdir to /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-js3c'
FAIL  supervise comes up and svok reports the service as supervised
FAIL  supervise controls its service while mkfifo(2) is available  |  svok never reported the service as supervised
TOTAL=32 PASS=30 FAIL=2
  FAILED: supervise comes up and svok reports the service as supervised
  FAILED: supervise controls its service while mkfifo(2) is available
--- leftover stub processes: 0

=========== stub mode: svcfail
PASS  svok reports 100 for an existing but unsupervised directory  |  rc=100 out=''
PASS  svok reports 111 for a nonexistent directory  |  rc=111 out='svok: fatal: unable to chdir to /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-71ga72si/'
PASS  svstat reports an unsupervised service and a missing directory  |  rc=0 out='/storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-71ga72si/test.sv: unable to open supervis'
PASS  svc warns about an unsupervised service and a missing directory  |  rc=0 out='svc: warning: unable to control /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-71ga72si/'
PASS  supervise reports a missing service directory  |  rc=111 out='supervise: fatal: unable to chdir to /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-71ga'
PASS  supervise comes up and svok reports the service as supervised
PASS  svup reports the service as up once supervise started it
FAIL  svc -x stops the service  |  rc=100
TOTAL=33 PASS=32 FAIL=1
  FAILED: svc -x stops the service
--- leftover stub processes: 0

=========== stub mode: stubborn
PASS  svok reports 100 for an existing but unsupervised directory  |  rc=100 out=''
PASS  svok reports 111 for a nonexistent directory  |  rc=111 out='svok: fatal: unable to chdir to /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-ul55i05u/'
PASS  svstat reports an unsupervised service and a missing directory  |  rc=0 out='/storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-ul55i05u/test.sv: unable to open supervis'
PASS  svc warns about an unsupervised service and a missing directory  |  rc=0 out='svc: warning: unable to control /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-ul55i05u/'
PASS  supervise reports a missing service directory  |  rc=111 out='supervise: fatal: unable to chdir to /storage/Users/currentUser/tmp/daemontools-encore-1.11/capable-branch-harness/run/daemontools-test-ul55'
PASS  supervise comes up and svok reports the service as supervised
PASS  svup reports the service as up once supervise started it
PASS  svc -x stops the service  |  rc=0
FAIL  supervise exits once the service is stopped  |  supervise exited only after SIGTERM
TOTAL=34 PASS=33 FAIL=1
  FAILED: supervise exits once the service is stopped
--- leftover stub processes: 0

### Accounting summary — the TOTAL lines below are the ones produced by the runs above:
###   happy      TOTAL=34 PASS=34 FAIL=0 -> a PASSING capable-platform run is exactly 34
###   svup-down  TOTAL=34 PASS=33 FAIL=1 -> service never reports up
###   neverup    TOTAL=32 PASS=30 FAIL=2 -> svok never reports the service supervised
###   svcfail    TOTAL=33 PASS=32 FAIL=1 -> svc -x fails
###   stubborn   TOTAL=34 PASS=33 FAIL=1 -> supervise ignores svc -x and needs SIGTERM
```
