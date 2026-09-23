# pgrphack-negative-test.log — 逐字留档（原文件不随 PR 入库）

- 原始文件: `archives/d/daemontools-encore/1.11/reports/pgrphack-negative-test.log`（本机工作区，未入库）
- 字节数: 1401
- 行数: 20
- sha256: `541761166dc8adeaff29b2d8cefade9041d97218dc9901b8958a8e14df013d53`
- 说明: pgrphack 假通过路径的破坏性负测试（AI Review 第三轮 P3）
- 生成命令: `见文件内 $ 命令行`
- 逐字性: fenced 内容与原文件逐字节一致（含行尾空格与末尾空行）；头部字节数/行数/sha256 均对原文件计算

以下为原文件逐字内容（```text 代码块）：

```text
### Destructive negative test for the pgrphack process-group assertion
### (AI review round 3, P3: the assertion used int(stdout.strip() or '-1'), so a child
###  that printed nothing yielded -1 != caller pgrp and PASSED - a silent false pass.)
### Package under test: /storage/Users/currentUser/.conan2/p/b/daemod6ce966938b22/p (all 20 real binaries)

--- 1) real packaged binaries:
$ python3 test_daemontools.py /storage/Users/currentUser/.conan2/p/b/daemod6ce966938b22/p/bin
PASS  pgrphack really leaves the caller's process group  |  rc=0 caller pgrp=39480 child pgrp=39570
TOTAL=31 PASS=31 FAIL=0

--- 2) sabotaged copy: pgrphack replaced by a stub that exits 0 and prints nothing
$ cp /storage/Users/currentUser/.conan2/p/b/daemod6ce966938b22/p/bin/* /storage/Users/currentUser/tmp/daemontools-encore-1.11/negprobe/ ; printf '#!/bin/sh\nexit 0\n' > /storage/Users/currentUser/tmp/daemontools-encore-1.11/negprobe/pgrphack
$ python3 test_daemontools.py /storage/Users/currentUser/tmp/daemontools-encore-1.11/negprobe
FAIL  pgrphack runs its child in a new process group  |  rc=0 out=''
FAIL  pgrphack really leaves the caller's process group  |  rc=0 caller pgrp=39480 child pgrp=None
TOTAL=31 PASS=29 FAIL=2
  FAILED: pgrphack runs its child in a new process group
  FAILED: pgrphack really leaves the caller's process group

=> the assertion now fails on empty child output instead of passing.
```
