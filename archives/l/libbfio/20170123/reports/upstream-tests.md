# libbfio 20170123 上游测试执行报告（R51 三步法）

- 环境: HarmonyOS PC aarch64 设备原生构建与运行
  （`uname -a` = `HarmonyOS localhost HongMeng Kernel 1.12.0 ... aarch64 Toybox`）；
  编译 clang 15.0.4（`/data/service/hnp/bin/clang`，默认 target `aarch64-unknown-linux-ohos`）
- 源码: libbfio_20170123.orig.tar.gz，
  sha256 `d45eaa2c7bc5d75905bbd1d04f9730e17bb4b638417343db1af410f3b17a15dd`
- 源码布局: 以与上游 git 检出等价的目录名 `libbfio/` 展开
  （`tar xzf ... -C <dir> --strip-components=1`，与配方 `get(strip_root=True)`
  得到的源码根同形）。原因见「§4 执行形态」的 TEST_PREFIX 一条。
- 构建: 与配方 `build()` 完全相同的三处内联适配（config.guess 加 HarmonyOS 分支、
  config.sub 两处锚点加 `linux-ohos`、configure 的 `umask 077`→`022`）后树内构建——
  `CC=clang ./configure --prefix=<sb>/prefix --enable-static --disable-shared --disable-nls`
  → `make -j4`，rc=0。

## §1 清点（N = 12，计数单位＝automake 注册的可执行测试单元）

| 单元类别 | 数量 | 来源（tests/Makefile.am） |
|----------|-----:|---------------------------|
| `check_PROGRAMS` 测试程序 | 10 | L31–L41（error、support、handle、pool、handle_read、handle_seek、handle_write、pool_read、pool_seek、pool_write） |
| `TESTS` 测试入口脚本 | 2 | L15–L17（test_library.sh、test_write_functions.sh） |
| **合计** | **12** | |

候选数法取值与差额归因（R51：取最大值，不混用口径）：

| 口径 | 数 | 说明 |
|------|----|------|
| ① 本版本 `check_PROGRAMS` 程序 | 10 | 仅可执行测试程序 |
| ② 本版本 tests/ 测试源全集（`bfio_test_*.c`） | 11 | 10 程序 + 支持源 `bfio_test_memory.c`（无独立入口/无 main，编入 handle/pool 的 SOURCES，L59/L104） |
| ③ 本版本 automake 测试单元（`TESTS` + `check_PROGRAMS`） | **12** | **本报告采用**；两类注册项分别列出行，不互相替代 |
| ④ 上游仓库当前 HEAD 的 `check_PROGRAMS` | 12 | 构成与本版本不同：2017 年 API 重写后新增 `file`/`file_io_handle`/`file_pool`/`file_range`/`file_range_io_handle`/`memory_range`/`memory_range_io_handle`/`system_string` 等，并移除 `handle_read`/`handle_seek`/`handle_write`/`pool_read`/`pool_seek`/`pool_write`；与本包 20170123 源码树无关，仅登记口径差异 |

③ 与 ④ 数值相同但构成不同，**本包一切计数以 20170123 源码树为准**。

另：`tests/Makefile.am` 还有 `check_SCRIPTS` 3 个脚本（test_library.sh、test_runner.sh、
test_write_functions.sh）与 `EXTRA_DIST` 的输入夹具 `input/raw/test.raw`。前者是
「check 需要就绪的脚本」——其中 test_runner.sh 是被两个 runner `source` 复用的函数库——
后者是数据夹具，**都不是测试注册项**，不计入 N（若把它们算进来会得到 13/15 之类的
混用口径）。本报告登记的 12 已是 20170123 源码树在合法测试计数口径下的最大值。

## §2 实际运行（12/12 全部真实执行，无跳过、无未执行）

### 2.1 `make check`（automake `TESTS` 两个入口）

```bash
make -j1 check LOG_COMPILER=/data/service/hnp/bin/bash
```

rc=0，`tests/test-suite.log` 汇总（逐字）：

```text
# TOTAL: 2
# PASS:  2
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
```

两个 runner 各自的逐字执行记录：

```text
$ cat tests/test_library.sh.log
Testing: error  (PASS)
Testing: support  (PASS)
Testing: handle with input: input/raw/test.raw (PASS)
Testing: pool with input: input/raw/test.raw (PASS)
PASS test_library.sh (exit status: 0)

$ cat tests/test_write_functions.sh.log
Testing writing file size: 0	(PASS)
Testing API write function: libbfio_handle_write  (PASS)
Testing writing file size: 1000	(PASS)
Testing API write function: libbfio_handle_write  (PASS)
Testing writing file size: 0	(PASS)
Testing API write function: libbfio_pool_write  (PASS)
Testing writing file size: 1000	(PASS)
Testing API write function: libbfio_pool_write  (PASS)
PASS test_write_functions.sh (exit status: 0)
```

### 2.2 上游 `TESTS` 未驱动的 4 个 `check_PROGRAMS`

20170123 版的 `test_library.sh`（`LIBRARY_TESTS="error support"`、
`LIBRARY_TESTS_WITH_INPUT="handle pool"`）与 `test_write_functions.sh`
（`TEST_FUNCTIONS="handle_write pool_write"`）合计只驱动 10 个程序中的 6 个；
`handle_read`、`handle_seek`、`pool_read`、`pool_seek` 在 `tests/*.sh` 中
**没有任何引用**，`make check` 只编译不执行。本报告按 `test_library.sh`
的 `run_test_with_input` 同一调用约定（`input` 目录 + `*` glob → 逐文件
`<程序> <输入文件>`）补跑这 4 个，执行回显（命令行是脚本内循环的等价单行形态，
输出行逐字取自 `<td>/run2.out`）：

```text
$ cd tests && for t in handle_read handle_seek pool_read pool_seek; do ./bfio_test_$t input/raw/test.raw; echo "rc=$?"; done
bfio_test_handle_read input/raw/test.raw -> rc=0
bfio_test_handle_seek input/raw/test.raw -> rc=0
bfio_test_pool_read input/raw/test.raw -> rc=0
bfio_test_pool_seek input/raw/test.raw -> rc=0
```

### 2.3 10 个 `check_PROGRAMS` 全量直跑复核（含 runner 已驱动的 6 个）

执行回显（写测试的 `<tmp>` = 脚本内 `<sb>/write-tmp`；输出行逐字取自 `<td>/run2.out`）：

```text
bfio_test_error -> rc=0
bfio_test_support -> rc=0
bfio_test_handle input/raw/test.raw -> rc=0
bfio_test_pool input/raw/test.raw -> rc=0
bfio_test_handle_read input/raw/test.raw -> rc=0
bfio_test_handle_seek input/raw/test.raw -> rc=0
bfio_test_pool_read input/raw/test.raw -> rc=0
bfio_test_pool_seek input/raw/test.raw -> rc=0
bfio_test_handle_write <tmp>/write 0 -> rc=0
bfio_test_handle_write <tmp>/write 1000 -> rc=0
bfio_test_pool_write <tmp>/write 0 -> rc=0
bfio_test_pool_write <tmp>/write 1000 -> rc=0
PASS=10 FAIL=0（程序口径；写测试按官方参数形态 <程序> <文件> <大小>，0 与 1000 两档）
```

`bfio_test_memory.c`（支持源，口径②）无独立执行形态，其失败注入功能
随所编入的 handle/pool 两程序实跑覆盖。

**12/12 覆盖**：`TESTS` 2 个 runner（§2.1）+ `check_PROGRAMS` 10 个程序
（6 个由 runner 驱动、4 个按同约定直跑，§2.2/§2.3）全部真实执行且通过，
无 SKIP、无 NOT_RUN。

## §3 计数口径与 PR 正文对应

| PR 正文行 | 数 | 本报告依据 |
|-----------|----|-----------|
| 上游 · 单元测试 | 10 | §2.3 的 10 个 `check_PROGRAMS` 程序 |
| 上游 · 其他测试 | 2 | §2.1 的 2 个 automake `TESTS` 入口 |
| 上游 · 合计 | 12 | §1 |
| 适配后 · 上游测试用例通过率 | 12/12（100%） | §2.1 + §2.2 + §2.3，无未执行项 |

## §4 执行形态要点（E386：能力探测 shell + 不改上游脚本）

- 两个 `TESTS` 入口带 `#!/bin/bash` 而设备无 `/bin/bash`；直接执行会因
  解释器缺失失败。处置：用 automake 的 `LOG_COMPILER` 指定一个
  **能力探测通过**的设备 bash，`make check` 照常调用两个脚本：

  ```bash
  # 能力探测（构建目录内；rc=0、stdout 为 cwd、stderr 为空才接受）
  $ cd <src> && /data/service/hnp/bin/bash -c 'pwd'
  /storage/Users/currentUser/ws/tmp/libbfio-upstream-check2/libbfio   # rc=0，stderr 空
  # 已接受：GNU bash 5.3.0（/data/service/hnp/bin/bash）
  ```

  `LOG_COMPILER` 是 make 命令行变量，**上游脚本与 Makefile.am 一个字节都未改**。
- **TEST_PREFIX 与源码目录名（上游脚本缺陷，与平台无关）**：
  `test_write_functions.sh` 用
  `sed 's/^lib\([^-]*\)/\1/'` 推导测试程序前缀，比 `test_library.sh` 的
  `sed 's/^lib\([^-]*\).*$/\1/'` 少一个 `.*$`。在 release/orig tarball 的顶层
  目录名 `libbfio-20170123` 下它会得到 `bfio-20170123`（而构建产物是
  `bfio_test_*`），实测报
  `Missing test executable: ./bfio-20170123_test_handle_write.exe`
  （同一构建树、同一命令，目录名换成上游 git 检出惯用的 `libbfio` 后 rc=0）。
  该缺陷与 HarmonyOS 无关，任何平台从 release tarball 直接 `make check`
  都会命中；本 PR 不改上游脚本，改用等价目录名运行，并把偏差如实登记。

## §5 原件与逐字副本

原始文件（`<sb>` = `/storage/Users/currentUser/ws/tmp/libbfio-upstream-check2`；
`<td>` = `/storage/Users/currentUser/tmp/libbfio-20170123`，两者都是任务临时目录，
随任务保留）：

| 原件 | sha256 | 字节 | 行 | 生成命令 |
|------|--------|-----:|----|----------|
| `<sb>/configure.log` | `dba5d3bf7381ef4a15090ad3b0ec66b9ae69605204daa8bdaeaacbbc45bb2a10` | 16475 | 368 | `CC=clang ./configure --prefix=... --enable-static --disable-shared --disable-nls` |
| `<sb>/make.log` | `a7257c96884fbf8be7af1dd5f0f2c13c11dae9b5449f202e30da549202d87b49` | 84450 | 413 | `make -j4` |
| `<sb>/make-check.log` | `56f4230e25e8734f4bfc5ca464ac364bc7d174bf714c7fbe7b85908b8f3368f6` | 14701 | 134 | `make -j1 check LOG_COMPILER=/data/service/hnp/bin/bash` |
| `<sb>/libbfio/tests/test-suite.log` | `16833c9944e69d58967203f2082a5c44d4248f35cf6e1febfd3c3776c9470ad2` | 236 | 14 | `make check` 自动生成 |
| `<sb>/libbfio/tests/test_library.sh.log` | `d436dd5a58840b4a1cbcd23647e16dff3e61df7e653bc8aad0c4d5334226efa4` | 192 | 5 | 同上 |
| `<sb>/libbfio/tests/test_write_functions.sh.log` | `72ff671b71458f62d3708b9e74d9b5c39c5ad3d72af4816caeb4346cd29140e1` | 420 | 9 | 同上 |
| `<td>/run2.out`（§2.2/§2.3 的执行回显） | `1efb703d07921d392e92825dc23a8e5643e0f7b6477db0e9a68d49ced354855c` | 1442 | 34 | `sh <td>/run-upstream-check-canonical.sh`（重跑会重建 `<sb>`） |

复现脚本：`<td>/run-upstream-check-canonical.sh`
（`<td>` = `$TASK_DIR` = `$HOME/tmp/libbfio-20170123`；含本次运行的完整命令序列与
三处内联适配的逐字实现。脚本内的写测试临时目录是 `<sb>/write-tmp`，§2.3 为可读性
缩写成 `<tmp>`；§2.2/§2.3 展示的是脚本内循环的等价单行形态，**输出行本身逐字取自
`<td>/run2.out`**）。

对照轮（证明 §4 的目录名一条，非通过轮）：把同一源码展开为
`libbfio-20170123/` 后 `make check` 得
`# TOTAL: 2 / # PASS: 1 / # FAIL: 1`，失败项逐字为
`Missing test executable: ./bfio-20170123_test_handle_write.exe`
（`test_write_functions.sh.log` sha256
`425ad616bc09fac69d27b644913d3a9e681ef9e32e47c8fd2daa0b221f7ba7ab`，110 字节 3 行）。
