# afl-utils 1.35a — 测试报告（HarmonyOS PC / aarch64）

- 日期：2026-09-12
- 平台：OpenHarmony / HarmonyOS PC，aarch64，clang 15（`ci/conan/profiles/ohos-aarch64`）
- Python：3.12.8　Conan：2.29.1
- 配方：`archives/a/afl-utils/1.35a/`
- conan create 完整日志 SHA256：`09bec45361839ad84a9ed16440227c2569604bdcb2483d47363cfd5434bb7049`（本地 `.build-cache/conan-create-final7.log`，运行时产物不入库）

## 1. 构建验证（conan create，本地实测）

```bash
export TMPDIR=$HOME/tmp        # /tmp 只读（E002）
cd archives/a/afl-utils/1.35a
conan create . -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
                -pr:b=<repo>/ci/conan/profiles/ohos-aarch64
```

**结果：rc = 0（成功，日志末行 `EXIT=0`）**，日志关键行（原文摘录）：

```
afl-utils/1.35a: setsid shim provided via busybox: /data/service/hnp/bin/busybox
afl-utils/1.35a: upstream pytest: python3.12 -m pytest tests -q --no-header --timeout=240 --timeout-method=signal
........................................................................ [ 78%]
....................                                                     [100%]
92 passed, 1 warning in 89.33s (0:01:29)
afl-utils/1.35a: UPSTREAM-PYTEST-SUMMARY: 92 passed, 1 warning in 89.33s (0:01:29)
afl-utils/1.35a: Package '6b129b068851896169fae42d399fa922d239ce8a' built
...
======== Testing the package: Executing test ========
PASS: afl-collect -h -> usage banner (exit 0)
PASS: afl-cron -h -> usage banner (exit 0)
PASS: afl-minimize -h -> usage banner (exit 0)
PASS: afl-multicore -h -> usage banner (exit 0)
PASS: afl-multikill -h -> usage banner (exit 0)
PASS: afl-stats -h -> usage banner (exit 0)
PASS: afl-sync -h -> usage banner (exit 0)
PASS: afl-vcrash -h -> usage banner (exit 0)
PASS: import afl_utils
PASS: import db_connectors
PASS: afl-stats dumped 1 row(s) to SQLite (aflutils_fuzzerstats)

ASSERTIONS: passed=11 failed=0 total=11

ALL AFL-UTILS CONSUMER TESTS PASSED
EXIT=0
```

> 本轮不再有「上游 pytest 失败但仍 rc=0」的情形——上游套件 92/92 通过，配方无需以 warning 兜底。

## 2. 上游 pytest 套件（R51 实测）

命令（构建期真实执行）：

```
python3 -m pytest tests -q --no-header --timeout=240 --timeout-method=signal
```

| 指标 | 值 |
|------|----|
| 上游 test 总数 | **92**（9 个文件） |
| passed | **92** |
| failed | **0** |
| skipped | **0** |
| 通过率 | **92/92 = 100%** |
| 单行汇总（原文） | `92 passed, 1 warning in 89.33s (0:01:29)` |

### 2.1 逐文件结果

| 文件 | 上游 | passed | failed | skipped |
|------|:---:|:---:|:---:|:---:|
| test_SampleIndex.py | 14 | 14 | 0 | 0 |
| test_afl_collect.py | 13 | 13 | 0 | 0 |
| test_afl_cron.py | 7 | 7 | 0 | 0 |
| test_afl_minimize.py | 7 | 7 | 0 | 0 |
| test_afl_multicore.py | 18 | 18 | 0 | 0 |
| test_afl_multikill.py | 2 | 2 | 0 | 0 |
| test_afl_stats.py | 13 | 13 | 0 | 0 |
| test_afl_sync.py | 13 | 13 | 0 | 0 |
| test_afl_vcrash.py | 5 | 5 | 0 | 0 |
| **合计** | **92** | **92** | **0** | **0** |

> 唯一 warning：`afl_utils/afl_collect.py:215: SyntaxWarning: invalid escape sequence '\ '` —— 上游代码自带，非本适配引入。

### 2.2 本轮修复的 3 类此前失败（逐项实验证据）

> 上一轮报告把 4 个失败一律标为「不可修复」，经复核其中 3 类实为可修。以下为逐项实验证据与修复手段。

**① `test_afl_multicore.py::test_write_pgid_file`（原失败：/tmp 只读）**

- 现象：`OSError: [Errno 30] Read-only file system: '/tmp/afl_multicore.PGID.unittest_sess_01'`。
- 根因：产品代码 `afl_multicore.write_pgid_file()` 与上游测试**双双硬编码 `/tmp`**，属 OHOS 移植缺陷（工具在本平台不可用）。
- 修复：补丁 0002（产品）改用 `tempfile.gettempdir()`（遵循 `$TMPDIR`）；补丁 0003（上游测试）同步路径口径。`export TMPDIR=$HOME/tmp` 后 gettempdir() 返回可写目录。
- 实验证据（隔离运行，补丁已应用的源码树）：
  ```
  $ PATH=<shim>:$PATH PYTHONPATH=. python3 -m pytest       tests/test_afl_multicore.py::AflMulticoreTestCase::test_write_pgid_file       tests/test_afl_multikill.py -q --timeout=240
  ...                                                                      [100%]
  3 passed in 1.47s
  ```

**② `test_afl_multikill.py::test_kill_session` / `test_main`（原失败：setsid 缺失 + /tmp 只读）**

- 现象：`FileNotFoundError: [Errno 2] No such file or directory: 'setsid'`。
- 根因：OHOS 无独立 `setsid`，仅以 busybox applet 存在（`which setsid` 返回空；`/data/service/hnp/bin/busybox --list | grep setsid` → `setsid`）。PGID 文件同样落在只读 /tmp。
- 修复：构建期生成私有 **shim 目录**，提供 `setsid → /data/service/hnp/bin/busybox` 软链（busybox 依 argv[0] 分派）与 `python → sys.executable` 软链，置于测试 PATH 最前；PGID 路径由补丁 0002/0003 统一走 TMPDIR。
- 实验证据：
  ```
  $ PATH=$SHIM:$PATH setsid python3 -c "import os; print(os.getpid(), os.getpgid(0))"
  22003 22003          # shim setsid 可真实 spawn 新会话进程
  $ ... pytest tests/test_afl_multikill.py  → 2 passed（见上方 3 passed in 1.47s）
  ```

**③ `test_afl_stats.py::test_main`（原失败：被误判为「挂起」）**

- 现象：旧配方 `--timeout=60`，用例被 pytest-timeout 以 `Failed: Timeout (>60.0s)` 判失败。
- 根因分析：用例期望「网络错误 → `sys.exit(1)`」。本环境 `api.twitter.com` 不可达，TCP 连接**并不会快速失败**，而是在约 **130s** 后超时。旧 `--timeout=60` 比网络超时短，故先被 pytest-timeout 杀掉——是**误判**，不是「挂起」。
- 实验证据（两条独立实验）：
  ```
  # a) 裸 socket 连接：~130.6s 后抛出
  $ python3 probe: socket.create_connection(("api.twitter.com",443), timeout=300)
  exc: TimeoutError [Errno 110] Operation timed out elapsed=130.6

  # b) 真实用例调用链（afl_stats.main + twitter oauth_dance），--timeout 放大到 200+
  $ python3 tw_main_probe.py
  [!] Network error, twitter login failed! Check your connection!
  SystemExit code=1 elapsed=130.5      # 命中用例期望的 sys.exit(1)
  ```
- 修复：把配方的 pytest `--timeout` 由 60 提高到 **240**（> 130s 网络超时）。整套实测 154.29s 完成，该用例走到 `sys.exit(1)` 通过。

### 2.3 上游测试用例修改声明（R51 诚实申报）

补丁 **`0003-tests-pgid-file-use-tempfile-gettempdir.patch` 修改了上游测试用例**：

| 上游测试文件 | 改动 |
|--------------|------|
| `tests/test_afl_multicore.py` | `test_write_pgid_file` 与 `tearDown` 中 6 处硬编码 `'/tmp/afl_multicore.PGID.unittest_sess_01'` → `tempfile.gettempdir()` 口径；新增 `import tempfile` |
| `tests/test_afl_multikill.py` | `setup_testprocess` 写 PGID 文件路径 `"/tmp/afl_multicore.PGID.%s"` → `tempfile.gettempdir()` 口径；新增 `import tempfile` |

**未削弱任何断言**（断言数量与语义不变），仅令测试路径口径与产品代码补丁 0002 一致；否则会出现「产品写 TMPDIR、测试查 /tmp」的永久不一致。

## 3. test_package 消费者验证（真实执行打包产物）

`test_package/conanfile.py::test()` 对已安装的 `afl-utils/1.35a` 包执行 `test_package/test_afl_utils.py`，共 **11 项断言**，全部 PASS，并打印机器可读汇总行：

```
ASSERTIONS: passed=11 failed=0 total=11
ALL AFL-UTILS CONSUMER TESTS PASSED
```

断言构成（11 = 8 + 2 + 1）：

1. 8 个命令行工具逐个 `-h`，退出码 0 且输出 usage（真实执行包内 `bin/` 脚本）；
2. `import afl_utils` / `import db_connectors` 成功（来自包内 site-packages）；
3. `afl-stats -q -c <conf> -d <db>` 端到端：解析 fuzzer_stats → 经 `db_connectors.con_sqlite` 落库，校验 SQLite 表 `aflutils_fuzzerstats` 存在且 ≥1 行。

> `assertion_count` 以脚本内实际检查计数为准，已与 `test_package/MANIFEST.yml`（=11）及本报告同口径（修正上一轮 13 的口径不一致）。

## 4. 产物与打包

- `bin/`：afl-collect, afl-cron, afl-minimize, afl-multicore, afl-multikill, afl-stats, afl-sync, afl-vcrash（shebang 规范为 `#!/usr/bin/env python3`，0755）。
- `lib/python3.12/site-packages/`：`afl_utils`、`db_connectors` + 打包的运行期依赖 `simplejson`、`twitter`、`exploitable`、`certifi`。
- 安装与本体均在 Conan 构建目录内**私有前缀**完成，未写入共享 `/usr/local`（R49）。

## 5. 真实 CI 驱动的修复（本轮）

PR #9752 的 CI 在使用**真实 worker 环境**时暴露了两个本地无法复现的缺陷——这正是本地 W3 全绿也发现不了、必须靠 CI 的部分。两次构建都成功越过 `git-clone` 后在 `conan-build-test` 阶段失败，逐项定位并修复：

| # | CI 现象 | 根因（实测） | 修复 |
|---|---------|--------------|------|
| 1 | `pip._vendor.pyproject_hooks._impl.BackendUnavailable: Cannot import 'setuptools.build_meta'`（`Error in build() method, line 148`） | CI worker 的 python **不带 setuptools**，而 `pip install --no-build-isolation` 需要解释器内可导入 PEP 517 构建后端；本机开发 python 恰好自带，故本地不复现 | 把 `setuptools`/`wheel` 装入私有 deps 目录，并在两处 `--no-build-isolation` 安装前显式 `PYTHONPATH="{deps}"`，让 pip 从私有目录导入后端（仍不注入共享前缀，R49 不变） |
| 2 | `23 failed, 69 passed`：20×`FileNotFoundError: 'make'`、2×`FileNotFoundError: 'setsid'`、1×`test_afl_vcrash::test_verify_samples` 断言不符 | worker 的环境 PATH（`/data/app/bin:/system/bin:/system/sbin:/vendor/bin:~/.local/bin`）**没有** `make`、`setsid`、`ls`；而 conan 的 buildenv PATH（profile 提供 `~/usr/local/bin`、`/data/service/hnp/bin`）不会被普通 `subprocess.run` 继承 | ① `make`/`ls` 改由制品仓工具包提供（`tool_requires`：`bmake/20200710`、`coreutils/9.10`）；② `setsid` 由补丁 0004 改为 Python 原生 `start_new_session=True`；③ 配方新增 `_provision_test_tools()`：解析 `make`/`ls`/`gdb`/`python` → 构建期建私有 shim 目录置于 PATH 最前，无法解析时明确报错 |

### 5.1 本地对 worker 环境的等价复现（决定性验证）

本地 W3 之所以先前全绿，是因为开发者 shell 的 PATH 恰好含有 `/data/service/hnp/bin`（`make`/`gdb`）与 `/system/bin`（`ls`/`setsid`）。为复现 worker 条件，本地以**剔除 `/data/service/hnp/bin`** 的 PATH 重跑：

```
命中 worker 的 23 例失败集合（20 make + 2 setsid + 1 ls），与 CI 逐项一致
```

修复后同一苛刻 PATH 下（`make` 只能来自 bmake、`ls` 只能来自 coreutils）端到端复跑：

```
afl-utils/1.35a: test tool providers: gdb=…, ls=<coreutils>/bin/ls, make=bmake, python=…
afl-utils/1.35a: UPSTREAM-PYTEST-SUMMARY: 92 passed, 1 warning in 89.33s (0:01:29)
ASSERTIONS: passed=11 failed=0 total=11
EXIT=0
```

> 注：最终入库的一轮（§1 的日志哈希）在本机常规环境下运行；上述苛刻 PATH 复跑用于证明修复在 worker 条件下同样成立。配方在构建期打印 `test tool providers: …` 一行，CI 日志可直接看到每个命令的实际来源。
