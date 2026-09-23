# fifo-probe-raw.log — 逐字留档（原文件不随 PR 入库）

- 原始文件: `archives/d/daemontools-encore/1.11/reports/fifo-probe-raw.log`（本机工作区，未入库）
- 字节数: 1017
- 行数: 30
- sha256: `1fc66a956d2eef5d04f4fa70b592030623203ccd5fd5a2239896a084647ab321`
- 说明: 本设备（HarmonyOS PC / HongMeng Kernel 1.12.0 / aarch64）对**四类特殊文件节点创建路径**的原始探测输出：CLI `mkfifo`、`os.mkfifo(2)`、`os.mknod(S_IFIFO)`、AF_UNIX `bind()`，四者全部 EPERM。这是 `supervise` 控制通道不可用、上游 9 个 supervise/svscan 用例 NOT_RUN 的直接根因证据
- 生成命令: `mkfifo probe.fifo` / `python3 -c "import os;os.mkfifo('p2',0o600)"` / `python3 -c "import os,stat;os.mknod('p3',stat.S_IFIFO|0o600)"` / `python3 -c "import socket;s=socket.socket(socket.AF_UNIX);s.bind('p4')"`（逐条带 `echo rc=$?`，工作目录 `${TMPDIR:-$HOME/tmp}/fifo-probe-e6340`）
- 逐字性: fenced 内容与原文件逐字节一致（含行尾空格与末尾空行）；头部字节数/行数/sha256 均对原文件计算

以下为原文件逐字内容（```text 代码块）：

```text
### FIFO 能力探测原始输出  2026-09-11T20:20:57+08:00
### 设备: HarmonyOS PC / HongMeng Kernel HongMeng Kernel 1.12.0 / aarch64
### 工作目录: /storage/Users/currentUser/fifo-probe-e6340

$ mkfifo probe.fifo
mkfifo: cannot create fifo 'probe.fifo': Operation not permitted
rc=1

$ python3 -c "import os;os.mkfifo('p2',0o600)"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
PermissionError: [Errno 1] Operation not permitted
rc=1

$ python3 -c "import os,stat;os.mknod('p3',stat.S_IFIFO|0o600)"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
PermissionError: [Errno 1] Operation not permitted
rc=1

$ python3 -c "import socket;s=socket.socket(socket.AF_UNIX);s.bind('p4')"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
PermissionError: [Errno 1] Operation not permitted
rc=1

$ ls -la
total 98304
drwxrws--x   2 20001006 file_manager   3440 2026-09-11 20:20 .
drwxrws--x 608 20001006 file_manager 118784 2026-09-11 20:20 ..
```
