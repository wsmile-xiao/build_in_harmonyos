# make-clean-scenario.log — 逐字留档（原文件不随 PR 入库）

- 原始文件: `archives/d/daemontools-encore/1.11/reports/make-clean-scenario.log`（本机工作区，未入库）
- 字节数: 1136
- 行数: 31
- sha256: `b21f169a5353d40a923ee63737c4d978207eb5f0c150aa87f8614e460a252a34`
- 说明: 上游 make clean 在大小写不敏感 HMDFS 上误删 MAN/TARGETS 的原始复现
- 生成命令: `见文件内 $ 命令行（在 pristine 副本内执行）`
- 逐字性: fenced 内容与原文件逐字节一致（含行尾空格与末尾空行）；头部字节数/行数/sha256 均对原文件计算

以下为原文件逐字内容（```text 代码块）：

```text
### daemontools-encore 1.11 — upstream `make clean` scenario on case-insensitive HMDFS
tree: /storage/Users/currentUser/tmp/daemontools-encore-1.11/make-clean-scenario2/tree (pristine upstream 1.11 tarball + patches/0001-MAN-optional-setuser.patch applied)

$ stat -c '%A %a' $HOME
drwxrws--x 2771

$ python3 -c "import os;print(os.path.samefile('MAN','man'))"
True

$ grep -n 'man' TARGETS | head -3     # TARGETS (the clean list) contains both names
65:man
$ grep -n '^man:\|^targets:' Makefile   # the Makefile targets with those names
272:man: \
661:targets: \

$ make -j1 clean
rm -f $( cat TARGETS )
rc=0

$ ls MAN TARGETS     # both shipped files are gone (case-insensitive match on man/targets)
ls: MAN: No such file or directory
ls: TARGETS: No such file or directory

$ make -j1 -B programs
rc=0

$ make -j1 install   (conf-bin=/storage/Users/currentUser/tmp/daemontools-encore-1.11/make-clean-scenario2/dest/bin conf-man=/storage/Users/currentUser/tmp/daemontools-encore-1.11/make-clean-scenario2/dest/share/man)
make: *** No rule to make target 'MAN', needed by 'install'.  Stop.
rc=2

installed programs: 0  man pages: 0
```
