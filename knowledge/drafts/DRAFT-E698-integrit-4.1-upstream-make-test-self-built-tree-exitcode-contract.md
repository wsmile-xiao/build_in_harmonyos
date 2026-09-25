# 上游 `make test` 自建文件树 + 退出码契约测试的清点与打包处置

- **草稿 ID**: DRAFT-E698-INTEGRIT-4.1-UPSTREAM-MAKE-TEST-SELF-BUILT-TREE-EXITCODE-CONTRACT
- **严重度**: 3
- **类别**: tests, upstream-test, autotools, hmdfs, permission-semantics, conan-recipe
- **来源**: integrit 4.1 适配（HarmonyOS PC aarch64，任务卡 7495）

## 错误特征

上游测试由 `make test` 驱动一个 shell 脚本，脚本**自己建文件树、自己写配置、自己逐条断言**，
fail-fast（第一条失败即 `exit 1`）。实测 integrit 的形态：

```text
+ ./integrit -C test-23480/test.conf -c -u
+ status=1
+ test 1 '=' 2
+ >&2
+ echo 'test: TEST FAILED: check error exit status'
test: TEST FAILED: check error exit status
+ rm -rf test-23480
+ exit 1
make: *** [Makefile:135: test] Error 1
```

**辨别性指纹**：
1. `make: *** [Makefile:<N>: test] Error 1` —— 失败目标名是 `test` 而非 `check`/`all`；
2. 失败行形如 `test <实际值> '=' <期望值>` 紧跟 `TEST FAILED: <断言描述>`；
3. 日志里**没有编译错误**（编译早已完成，死在测试阶段）；
4. 计数矛盾：`grep -c 'TEST FAILED' <脚本>` = **总断言数**，但实际只跑到**第一个失败**为止。

## 根因分析（本例实测）

integrit 的 `test/test` 共 **31 条断言**（`grep -c 'TEST FAILED' test/test` = 31，每个
`|| { echo "test: TEST FAILED: …"; exit 1; }` 守卫即一条）。实测 **30 PASS / 1 FAIL**，
失败的是**末位 #31**：

```c
/* integrit.h:29-31 */
INTEGRIT_EXIT_NOCHANGE = 0,
INTEGRIT_EXIT_CHANGES  = 1,
INTEGRIT_EXIT_FAILURE  = 2
```

```sh
# test/test:71-75 —— 期望「文件不可读 ⇒ EXIT_FAILURE(2)」
touch $modfile && chmod 000 $modfile
./integrit -C $testdir/test.conf -c -u > $testdir/test.out; status=$?
test $status = 2 || { echo "test: TEST FAILED: check error exit status"; ...; exit 1; }
```

HMDFS 把 `chmod 000` 改写成 `-rw-rw----`，文件仍可读 ⇒ integrit 读到空文件、
校验和变化 ⇒ 返回 `EXIT_CHANGES(1)` 而非 `EXIT_FAILURE(2)`。**属平台权限语义限制，
不是被测程序的缺陷**（与 E479-draft-5CC4 / DRAFT-pex-permission-semantics /
DRAFT-c-ares-lite HostAliasUnreadable 同族，本条不重复其根因，只补**测试侧的判读与处置**）。

设备探针（可直接复现，落 `$TASK_DIR`，非 `/tmp`）：

```sh
cd "$TASK_DIR" && echo probe > permtest.txt && chmod 000 permtest.txt \
  && ls -la permtest.txt && cat permtest.txt && echo READ_OK
# → -rw-rw---- … permtest.txt   （000 被改写为 660）
# → probe
# → READ_OK(chmod 000 未生效)
```

实测 **6/6** 可写路径（`$TMPDIR`、`$TASK_DIR`、`$HOME/tmp`、`$HOME`、worktree、cwd）
`chmod 000` 全部失效 ⇒ 设备上不存在能让该断言通过的路径。

## 同类测试脚本的第二个常见坑：数据库/产物自身在被检查的 root 下

「无变化 ⇒ 期望 rc=0」这类断言若**不把测试自身写出的产物排除在 root 外**，就永远拿不到 0：

```sh
# integrit 的 conf 把 known/current db 放在 root 内，若不加排除，db 自身被当成
# 「未知新文件」⇒ check 恒返回 1，断言 `test 0 '=' 0` 必失败。
# 上游自己的解法就是 make-config -i 追加排除段：
! $root/known.cdb
! $root/curr.cdb
```

**判读要点**：看到「明明什么都没改却报 changed」先查 root 是否包含了测试自己写的
db/日志/输出文件，**不要**当成被测程序逻辑错误去改码。

## 推荐方案（打包侧处置，四条）

**方法**: 计数 → 归因 → 分层验证 → 如实登记

1. **先清点总断言数**：`grep -c 'TEST FAILED' <test脚本>` 得 N（fail-fast 脚本的
   「实际跑到」不等于 N，必须单独清点）；`TOTAL = PASS + FAIL + SKIP + NOT_RUN`。
2. **平台权限类失败按环境限制归因**，不要改测试期望值、不要删断言、不要写成 PASS；
   若失败项依赖权限位语义，改用**不依赖权限位的等价路径**在同一契约上补验证。
   integrit 用例：`integrit -C <不存在的conf>` ⇒ **rc=2**，同样证明
   `EXIT_FAILURE(2)` 契约在本设备可测，与 chmod 路径互补。
3. **`build()` 里跑上游测试时打印真实退出码**而不是吞掉：

   ```python
   self.run('make test; rc=$?; echo "MAKE_TEST_RC=$rc (N assertions)"; exit 0',
            cwd=self.build_folder)
   ```

   这样 CI 日志保留真实结论、审计可核，同时已知的环境限制不至于让整包判失败。
4. **测试脚本无执行位**（tarball 里就是 `-rw-r--r--`）时 `chmod +x <script>`
   —— 属生成物面操作，不进 git。

**test_package 补强**：消费者测试用**退出码契约分层断言**（0/1/2 各验一次）
+ 二进制自报版本指纹，比单纯 `--version` 强，且能在权限受限平台全绿。
integrit 的 `test_package/test.sh` 9 条断言在设备实测 **9/9 PASS（rc=0）**。

## 影响面

任何「上游测试自己建临时文件树 / 自己写数据库或日志 / 用权限位做断言」的 autotools、
makefile 类老 C 项目。典型形态：`test/` 目录下 `test`、`run-tests.sh`、`TESTS=`
等 fail-fast shell 驱动器（**不是** ctest/pytest/automake parallel-tests 注册制）。

## 关联

- **similar_to**: E479-draft-5CC4（chmod 000 权限语义失效根因）、
  DRAFT-pex-1.20140409-permission-semantics、
  DRAFT-c-ares-lite（chmod(fn,0) 拒绝读取语义缺失）、
  E011 / E114（config.status `umask 077` HMDFS 临时目录族）、
  E328（monorepo 保留完整上游分母）
- **本条新增价值**: 不重复上述根因，补的是**测试侧判读与打包处置**——
  fail-fast 断言清点法、平台限制与代码缺陷的分界、退出码契约的等价路径补验证、
  「测试产物自身在 root 内」导致假 changed 的判读。

## 复现命令（设备可直接执行）

```sh
# 1) 断言总数清点
cd "$TASK_DIR/w0/src/integrit-4.1" && grep -c 'TEST FAILED' test/test    # → 31

# 2) 跑上游测试（沙箱 HOME）
HOME="$TASK_DIR/test-home" make test; echo "rc=$?"

# 3) 权限语义探针
cd "$TASK_DIR" && echo probe > permtest.txt && chmod 000 permtest.txt \
  && ls -la permtest.txt && cat permtest.txt && echo READ_OK

# 4) 等价路径验证 EXIT_FAILURE(2) 契约（不依赖权限位）
"$TASK_DIR/w0/src/integrit-4.1/integrit" -C "$TASK_DIR/no-such.conf" -c; echo "rc=$?"
```

证据留档：`$TASK_DIR/w0/w0-5-maketest.md`（含 31=30+1 计数、chmod 探针原文、
期望 2 实得 1 逐字）。
