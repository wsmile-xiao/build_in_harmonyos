# upstream-install-scenarios.log — 逐字留档（原文件不随 PR 入库）

- 原始文件: `archives/d/daemontools-encore/1.11/reports/upstream-install-scenarios.log`（本机工作区，未入库）
- 字节数: 1416
- 行数: 34
- sha256: `d169a198b92ce35aeaf5053face373beee406d72c0598253fae9fa37bc9b8b0e`
- 说明: 上游 make install 三段场景（未修补+未预建目录 / 未修补+预建目录 / 打补丁+预建目录）
- 生成命令: `sh verify-install-scenarios.sh`
- 逐字性: fenced 内容与原文件逐字节一致（含行尾空格与末尾空行）；头部字节数/行数/sha256 均对原文件计算

以下为原文件逐字内容（```text 代码块）：

```text
### daemontools-encore 1.11 install scenarios (device: HarmonyOS PC, HMDFS case-insensitive)
### tree: /storage/Users/currentUser/tmp/daemontools-encore-1.11/upstream-pristine/daemontools-encore-1.11  (pristine upstream tarball, sha256 3bab6cf1de2bdefa607d42a8f50577f2664b6a29b273b98cd0b3b8f7781d8b72)

=========== scenario A (pre-created man8=no, patch=no)
share/man/man8: absent before install
11:c:::644:/man8/:setuser.8:
./installer `head -n 1 conf-bin` <BIN
./installer `head -n 1 conf-man` <MAN
installer: fatal: unable to write /storage/Users/currentUser/tmp/daemontools-encore-1.11/scenario-A/share/man/man8/envdir.8: access denied
make: *** [Makefile:231: install] Error 111
make install rc=2
programs installed: 20
man pages installed: 0

=========== scenario B (pre-created man8=yes, patch=no)
share/man/man8 mode before install: drwxrws--x 2771
11:c:::644:/man8/:setuser.8:
./installer `head -n 1 conf-bin` <BIN
./installer `head -n 1 conf-man` <MAN
installer: fatal: unable to read setuser.8: file does not exist
make: *** [Makefile:231: install] Error 111
make install rc=2
programs installed: 20
man pages installed: 9

=========== scenario C (pre-created man8=yes, patch=yes)
share/man/man8 mode before install: drwxrws--x 2771
11:?c:::644:/man8/:setuser.8:
./installer `head -n 1 conf-bin` <BIN
./installer `head -n 1 conf-man` <MAN
make install rc=0
programs installed: 20
man pages installed: 19

```
