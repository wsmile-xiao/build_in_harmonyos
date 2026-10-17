# E-DRAFT: libyal/autotools 上游套件：`TESTS` runner 的 TEST_PREFIX 依赖源码目录名，且只驱动部分 `check_PROGRAMS`

- **触发实例**：libbfio 20170123 适配与返修（2026-09-18/19，任务 libbfio-20170123，分支 feat/libbfio-20170123）
- **错误签名**：`Missing test executable: \./.*_test_.*\.exe`（伴随 `shell-init: error retrieving current directory` 或 `./test_library.sh: No such file or directory`）
- **类别**：upstream-test-harness（autotools 测试套件驱动面）
- **严重度**：2（不改上游即确定性失败/漏测，处置模式固定；不影响库本身）

## 症状

从 release/orig tarball（顶层目录名形如 `libbfio-20170123`）直接 `make check`：

```text
FAIL: test_write_functions.sh
=============================

Missing test executable: ./bfio-20170123_test_handle_write.exe

FAIL test_write_functions.sh (exit status: 1)
# TOTAL: 2 / # PASS: 1 / # FAIL: 1
```

同一棵树、同一条命令，把顶层目录名换成上游 git 检出惯用的 `libbfio` 后：

```text
# TOTAL: 2
# PASS:  2
# FAIL:  0
```

即失败**与平台无关**（任何平台从 release tarball 直跑 `make check` 都会命中），
只是 HarmonyOS 设备上更容易被同时出现的另外两个现象掩盖：

- 两个 `TESTS` 入口带 `#!/bin/bash`，而设备无 `/bin/bash` → 直接执行报
  `./test_library.sh: No such file or directory`（内核按 shebang 找解释器 ENOENT，
  措辞会被读成"文件不存在"）；
- hnp bash 在部分路径上 getcwd 失败 → `shell-init: error retrieving current directory`，
  脚本用 `${PWD}` 推导的前缀为空。

## 根因

libyal 家族 2017 年代布局（本条目逐字实测的只有 libbfio 20170123）的 `tests/*.sh` 从**源码树目录名**
推导测试程序前缀，两个脚本的正则**不一致**：

```bash
# tests/test_library.sh
TEST_PREFIX=`dirname ${PWD}`;
TEST_PREFIX=`basename ${TEST_PREFIX} | sed 's/^lib\([^-]*\).*$/\1/'`;   # 有 .*$ → 去掉 -<版本>

# tests/test_write_functions.sh
TEST_PREFIX=`dirname ${PWD}`;
TEST_PREFIX=`basename ${TEST_PREFIX} | sed 's/^lib\([^-]*\)/\1/'`;      # 少 .*$ → 保留 -<版本>
```

在 git 检出（目录名 `libbfio`）下两者都得 `bfio`，与产物名 `bfio_test_*` 一致；
在 release/orig tarball（目录名 `libbfio-20170123`）下后者得 `bfio-20170123`，
于是去找 `./bfio-20170123_test_handle_write.exe` —— 必然 `Missing test executable`。
上游自己的 `make distcheck` 也应在同一布局下命中（未被发现而已）。

第二处（同一族、影响**计数**）：automake 的 `TESTS` 只驱动 `check_PROGRAMS` 的**子集**。
libbfio 20170123 实测：

| 注册面 | 数量 | 内容 |
|--------|-----:|------|
| `check_PROGRAMS`（L31–L41） | 10 | error、support、handle、pool、handle_read、handle_seek、handle_write、pool_read、pool_seek、pool_write |
| `TESTS`（L15–L17） | 2 | test_library.sh（驱动 error/support/handle/pool）、test_write_functions.sh（驱动 handle_write/pool_write） |

即 `make check` 只**编译**全部 10 个、只**执行**其中 6 个；
`handle_read`/`handle_seek`/`pool_read`/`pool_seek` 在 `tests/*.sh` 中零引用。
按 `TESTS` 的口径清点会漏报 4 个，按"实际被驱动的程序"清点会漏报更多。

## 最小修复（不改上游一个字节）

```bash
# 1) 用与上游 git 检出等价的目录名展开源码（tar --strip-components=1 → libbfio/）
#    与配方 get(strip_root=True) 得到的源码根同形；产物名与 TEST_PREFIX 随之对齐
# 2) 设备无 /bin/bash：用 automake 的 LOG_COMPILER 指定一个**能力探测通过**的
#    设备 bash（E386 的 capability-tested shell；构建目录内 `bash -c pwd` rc=0、stderr 空）
make -j1 check LOG_COMPILER=/data/service/hnp/bin/bash
# → # TOTAL: 2 / # PASS: 2 / # FAIL: 0

# 3) 上游 TESTS 未驱动的程序按 test_library.sh 的 run_test_with_input 同约定补跑
cd tests && for t in handle_read handle_seek pool_read pool_seek; do
    ./bfio_test_$t input/raw/test.raw; echo "rc=$?"; done
# 写测试按官方参数形态：./bfio_test_handle_write <tmp>/write 0|1000
```

设备复现（本次实测，落 `$TASK_DIR`，可直接执行）：

```bash
TASK_DIR=$HOME/tmp/libbfio-20170123
sh "$TASK_DIR/run-upstream-check-canonical.sh"      # 通过轮：configure/make/make check/逐程序
sh "$TASK_DIR/run-upstream-check.sh"                # 对照轮：tarball 目录名 → FAIL 1（证明目录名一条）
```

⚠️ **两个脚本开头都 `rm -rf "$SB"`**：`<sb>` = `$TMPDIR/libbfio-upstream-check{,2}`，
其中的 `configure.log`/`make.log`/`make-check.log`/`tests/*.log` 正是
`archives/l/libbfio/20170123/reports/upstream-tests.md` §5 登记 sha256 的原件
（实测重跑会让 `make.log`/`make-check.log` 两行与磁盘不再匹配）。要复核时请先复制脚本、
把 `SB=` 改到别处再跑，不要直接原地重跑。

`LOG_COMPILER` 是 make 命令行变量，**上游脚本与 Makefile.am 零改动**；
`log` 侧证据：`tests/test-suite.log`、`tests/test_library.sh.log`、
`tests/test_write_functions.sh.log`。

## 计数口径（与官方审查 rule4 的"少报"直接相关）

- N 取 **automake 注册项**：`check_PROGRAMS` + `TESTS` —— libbfio 20170123 = 10 + 2 = **12**；
- 另单列 `tests/` 测试源全集 11（10 程序 + 支持源 `bfio_test_memory.c`，无 main、编入
  handle/pool 的 `SOURCES`）、`check_SCRIPTS` 3（含被两个 runner `source` 复用的
  `test_runner.sh`）与 `input/raw/test.raw` 夹具，**均不计入 N**；
- `test_package` 消费者用例单独成行（"鸿蒙特有测试"），不进上游分母。

## 影响面与边界

- 适用：**按判定信号适用，不按家族名默认适用**——任何"`TESTS` 为 .sh runner +
  `check_PROGRAMS` 为 C 程序"且 runner 用 `basename $(dirname $PWD)` 推导前缀的 autotools 包；
  判定信号 = 源码根目录名含 `-<版本>` 且 runner 内存在 `TEST_PREFIX` 推导。
  同族其它包（libesedb/libvhdi/libevtx …）的 2017 年代修订已随上游仓库重置不可获取
  （2026-09-19 实测 `raw.githubusercontent.com/libyal/<pkg>/main/tests/test_write_functions.sh`
  返回 404，现代版本改为 `check_AUTOTESTS` 布局、无该脚本），故本条**不作逐包断言**；
  复核两行命令：`curl -sS -o /dev/null -w '%{http_code}\n' https://raw.githubusercontent.com/libyal/<pkg>/main/tests/test_write_functions.sh`
  与 `grep -n 'TEST_PREFIX=' tests/*.sh`。
- 不适用/不要做：**不要**改上游 `tests/*.sh` 的 sed（属改上游测试用例，且会让
  test_library.sh 与 test_write_functions.sh 的语义分歧永久化）；**不要**靠 `make -C` 或
  软链接伪造目录名（`configure` 固化了绝对路径，移动/改名构建树会连带失效）。
- 与 E386 的分工：E386 覆盖"能力探测 shell + `LOG_COMPILER` + getcwd/EOF 现象"；
  本条覆盖"目录名 → TEST_PREFIX"缺陷与"`TESTS` 只驱动子集"的计数口径。
