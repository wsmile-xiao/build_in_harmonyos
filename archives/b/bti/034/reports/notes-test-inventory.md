# bti 034 上游测试清点证据

bti 上游**没有任何测试套件**。本文件的逐字 shell 记录给出三条独立证据：
（1）pristine 解包树（23 个文件）里没有任何子目录，因此不存在 `tests/` 或 `test/`；
（2）`Makefile.am` 中 `grep -nE 'check|TESTS'` 与 `grep -nE 'check_PROGRAMS|TESTS *='`
均无输出（rc=1），即没有 `check_PROGRAMS`/`TESTS` 目标；
（3）在已完成 `configure` 的构建树里 `make check` 输出
`make: Nothing to be done for 'check'.`（rc=0）。

因此上游测试用例总数 N=0，`test_package` 的 4 项断言是新增的鸿蒙特有测试（不计入上游分母）。

## 逐字证据

- 原始文件：`/storage/Users/currentUser/tmp/bti-034/evidence/upstream-test-inventory.txt`
- 原始字节数：812
- 原始行数：22（`wc -l`，即换行符个数）
- sha256（原始文件逐字节）：`58b93be90f05bb70364e0d33706506306b091d71acd552233c57430ef30d8771`
- 抽取命令（块内含末尾换行，不额外剥除）：

````text
sed -n '/^```text$/,/^```$/p' notes-test-inventory.md | sed '1d;$d' > upstream-test-inventory.txt
````

```text
# 上游测试清点（pristine 解包树，shell 记录）
$ sha256sum bti-034.tar.gz
46e586c8b3ecc645d7ce206ecb9f2dcb6c7ab71984eef8d094ca5e30b6bfe09f  /storage/Users/currentUser/tmp/bti-034/src/bti-034-kernel.tar.gz
$ tarfile 解包后 cd $PRISTINE && pwd
/storage/Users/currentUser/tmp/bti-034/pristine/bti-034
$ find . -maxdepth 2 -type d | sort   # 只有顶层目录，无 tests/ 或 test/
.
$ find . -type f | wc -l
23
$ grep -nE 'check|TESTS' Makefile.am   # 无输出 = 无测试目标
grep rc=1
$ grep -nE 'check_PROGRAMS|TESTS *=' Makefile.am
grep rc=1
$ ls tests test 2>&1
ls: tests: No such file or directory
ls: test: No such file or directory
ls rc=1

$ cd /storage/Users/currentUser/builds/bti-034.work   # 已完成原生 configure 的树
$ make check
make: Nothing to be done for 'check'.
rc=0
```
