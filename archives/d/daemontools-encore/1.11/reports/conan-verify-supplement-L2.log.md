# conan-verify-supplement-L2.log — 逐字留档（原文件不随 PR 入库）

- 原始文件: `archives/d/daemontools-encore/1.11/reports/conan-verify-supplement-L2.log`（本机工作区，未入库）
- 字节数: 3495
- 行数: 69
- sha256: `2e7acbe2c3f0724a66f73721e9435dad72c513bbedee3dcc5ea712a3a3a83f91`
- 说明: L2 平台功能矩阵：直接运行包内二进制
- 生成命令: `见文件内 $ 命令行`
- 逐字性: fenced 内容与原文件逐字节一致（含行尾空格与末尾空行）；头部字节数/行数/sha256 均对原文件计算

以下为原文件逐字内容（```text 代码块）：

```text
### L2 supplement — direct runs of packaged binaries
package: /storage/Users/currentUser/.conan2/p/b/daemo37628b650ddb4/p

$ file bin/svscanboot
/storage/Users/currentUser/.conan2/p/b/daemo37628b650ddb4/p/bin/svscanboot: /bin/sh script
$ head -1 bin/svscanboot
#!/bin/sh

$ bin/envdir /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/env1 /bin/sh -c 'echo $Message'
This is a test. This is only a test.
rc=0

$ printf 'one\ntwo\n' | bin/multilog t /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/log
rc=0
$ cat -v /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/log/current
@400000006aa3703819f86e0c one
@400000006aa3703819f871f4 two

$ printf 'ONE\n' | bin/tai64n | bin/tai64nlocal
2026-09-11 11:06:22.478744500 ONE
rc=0

$ bin/softlimit -c 0 python3 -c 'import resource;print(resource.getrlimit(resource.RLIMIT_CORE)[0])'
0
rc=0
$ bin/setlock /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/lock /bin/sh -c 'echo lock-held'
lock-held
rc=0

--- unsupervised service directory (exists, no supervise running) ---
$ bin/svok /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/service
rc=100
$ bin/svstat /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/service
/storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/service: unable to open supervise/ok: file does not exist
rc=0
$ bin/svc /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/service
svc: warning: unable to control /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/service: file does not exist
rc=0

--- nonexistent service directory ---
$ bin/svok /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/nonexistent
svok: fatal: unable to chdir to /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/nonexistent: file does not exist
rc=111
$ bin/svstat /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/nonexistent
/storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/nonexistent: unable to chdir: file does not exist
rc=0
$ bin/svc /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/nonexistent
svc: warning: unable to chdir to /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/nonexistent: file does not exist
rc=0
$ bin/supervise /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/nonexistent
supervise: fatal: unable to chdir to /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/nonexistent: file does not exist
rc=111

--- supervisory control channel (FIFO) capability on this device ---
$ bin/supervise /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/service
supervise: fatal: unable to read supervise/control: file does not exist
rc=111
ls /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/service:
total 32768
drwxrws--x 3 20001006 file_manager 3440 2026-09-11 11:06 .
drwxrws--x 5 20001006 file_manager 3440 2026-09-11 11:06 ..
-rwxrwx--- 1 20001006 file_manager   25 2026-09-11 11:06 run
drwxrws--x 2 20001006 file_manager 3440 2026-09-11 11:06 supervise
$ ls -la /storage/Users/currentUser/tmp/daemontools-encore-1.11/l2-evidence/service/supervise
total 24576
drwxrws--x 2 20001006 file_manager 3440 2026-09-11 11:06 .
drwxrws--x 3 20001006 file_manager 3440 2026-09-11 11:06 ..
-rw-rw---- 1 20001006 file_manager    0 2026-09-11 11:06 lock
-rw-rw---- 1 20001006 file_manager    0 2026-09-11 11:06 status
```
