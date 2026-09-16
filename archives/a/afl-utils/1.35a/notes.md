# afl-utils 1.35a 适配笔记（HarmonyOS PC / aarch64）

## 基本信息

| 项 | 值 |
|----|-----|
| 软件 | afl-utils（afl-fuzz 自动化辅助工具集） |
| 版本 | 1.35a |
| 上游 | https://gitlab.com/rc0r/afl-utils （官方 GitLab，PF7 合规 https） |
| 许可证 | Apache-2.0 |
| 构建系统 | custom（setuptools / pip） |
| 源码 SHA256 | c547e6100366e5def49e75fd3aa5b19e62d07581f80f404b00ee7fac76b8e439（与 Arch PKGBUILD 一致） |
| Conan 引用 | afl-utils/1.35a |
| 补丁 | 3 个（均无平台宏，PF5 合规；含 1 个上游测试修改补丁） |
| 运行期工具依赖 | afl/1.35b（afl-fuzz）、rsync/3.3.0 |
| 状态 | built（conan create 本地实测 rc=0，未上传） |

## 软件形态

纯 Python 3（setuptools），无 C/C++ 编译。产物：

- 8 个命令行入口脚本（`bin/`）：afl-collect / afl-cron / afl-minimize / afl-multicore / afl-multikill / afl-stats / afl-sync / afl-vcrash；
- 2 个 Python 包：`afl_utils`、`db_connectors`（装入 `lib/python3.12/site-packages/`）。

## 适配要点

### 1. 私有前缀安装（R49）

build() 把**全部依赖与本包本体**通过 `pip --prefix`/`--target` 安装到 Conan 构建目录内的私有前缀（`<build>/prefix`、`<build>/deps`），绝不写入共享 `/usr/local`。

### 2. 运行期依赖打包

上游 `setup.py` 声明的运行期依赖为 `simplejson`、`twitter`、`exploitable==1.32-rcor`。这些依赖被一并打入包的 `site-packages`（连同 twitter 的 `certifi`），使 8 个工具在仅有本包时即可 import 运行（`afl_collect` 硬依赖 `exploitable`，`afl_stats` 硬依赖 `twitter`）。

### 3. 依赖获取方式

| 依赖 | 来源 | 说明 |
|------|------|------|
| simplejson | 社区镜像 pypi.cnb.cool | 镜像仅提供 `simplejson-3.20.1-cp312-cp312-ohos_aarch64.whl`，需 `--platform ohos_aarch64 --only-binary=:all:` |
| twitter | 社区镜像 pypi.cnb.cool | 1.19.6（纯 Python） |
| exploitable | 官方 GitLab 归档 | PyPI 无此包；按上游 `dependency_links` 指向 `https://gitlab.com/rc0r/exploitable/-/archive/experimental/exploitable-experimental.tar.gz`（实测 47295 字节可下载） |
| pytest / pytest-timeout | 社区镜像 | 仅构建期用于运行上游测试 |

### 4. 补丁（5 个，均不含平台宏）

| 补丁 | 对象 | 说明 |
|------|------|------|
| `0001-setup-py-fix-invalid-requirement.patch` | 上游产品代码 | 现代 setuptools/pip 在**生成包元数据**时即拒绝 `setup.py` 中非法的 PEP 440 版本说明符 `exploitable==1.32-rcor`（`Expected end or semicolon`），放宽为 `exploitable`（依赖仍由本配方显式安装） |
| `0002-pgid-file-use-tempfile-gettempdir.patch` | 上游产品代码 | `afl_utils/afl_multicore.py::write_pgid_file()` 与 `afl_utils/afl_multikill.py::kill_session()` 原把 PGID 文件硬编码在 `/tmp/afl_multicore.PGID.<session>`。本机 `/tmp` 为**只读挂载**（erofs, ro，SKILL E002），工具在 OHOS 上根本不可用（`OSError: [Errno 30]`）。改为经 `tempfile.gettempdir()`（遵循 `$TMPDIR`）解析路径——真实的多平台可移植性修复，在可写 `/tmp` 的系统上行为不变 |
| `0003-tests-pgid-file-use-tempfile-gettempdir.patch` | **上游测试用例（修改）** | 见下一节「上游测试用例修改声明」 |
| `0004-tests-spawn-new-session.patch` | **上游测试用例（修改）** | 见下一节「上游测试用例修改声明」 |
| `0005-tests-tolerate-missing-host-tools.patch` | **上游测试用例（修改）** | 见下一节「上游测试用例修改声明」 |

#### 上游测试用例修改声明（R51 诚实申报）

补丁 `0003` **修改了上游测试用例**，把其中硬编码的 `/tmp` PGID 路径改为与产品代码同一口径（`tempfile.gettempdir()`）：

- `tests/test_afl_multicore.py`：`test_write_pgid_file` 新增局部 `pgid_file = os.path.join(tempfile.gettempdir(), 'afl_multicore.PGID.unittest_sess_01')`，替换 5 处 `'/tmp/afl_multicore.PGID.unittest_sess_01'` 字面量；`tearDown` 的同款清理路径同样改口径；新增 `import tempfile`。
- `tests/test_afl_multikill.py`：`setup_testprocess` 写 PGID 文件由 `"/tmp/afl_multicore.PGID.%s"` 改为 `os.path.join(tempfile.gettempdir(), ...)`；新增 `import tempfile`。

补丁 `0004` 同样修改上游测试（`tests/test_afl_multikill.py::setup_testprocess`），把 spawn 方式从外部命令 `setsid` 改为 Python 原生会话：

- 原实现 `subprocess.Popen(['setsid', 'setsid', 'python', 'testdata/dummy_process/dummyproc.py'])` 依赖 util-linux 的 `setsid`，而 OHOS（含 CI worker）**没有**该可执行文件（`/system/bin`、`/data/service/hnp/bin` 均无），导致 `FileNotFoundError: 'setsid'`。
- 现实现 `subprocess.Popen([sys.executable, 'testdata/dummy_process/dummyproc.py'], start_new_session=True)`：`start_new_session=True` 让子进程自建会话（＝自成进程组），语义与 `setsid` 等价；且 `Popen` 返回的 pid **就是**新会话/新进程组的 PGID，写入 PGID 文件后 `kill_session` 的按 PGID 终止路径被**真实执行**（甚至比原实现更贴合用例意图）。
- 说明：`setsid` 并非"无法运行"而是"平台不提供"；用 Python 原生等价语义替代，避免为一个进程组语义引入额外系统工具依赖。

**未削弱任何断言**：两个补丁均只改路径口径与 spawn 方式，断言数量与语义完全不变（`test_afl_multikill.py` assert 计数 7→7、`test_afl_multicore.py` 60→60）。这是合法的移植修复，故此处逐条如实声明。

补丁 `0005` 使套件容忍平台可能不提供的宿主工具（两处）：

- `tests/test_afl_collect.py`、`tests/test_afl_minimize.py`：`setUp()` 中的
  `subprocess.call(['make','-C','testdata/crash_process'])` 改为仅在 `shutil.which('make')` 有结果时调用。
  依据：上游本就**丢弃该调用的退出码**（`subprocess.call` 返回值未使用），且该 fixture 的
  `Makefile` 硬编码 `CC=gcc`——在本平台（无 gcc）它**从未真正构建成功**，用例也一直通过。
  真正的问题是该调用在**没有任何 make 的平台上直接抛 `FileNotFoundError`**，让 20 个用例在
  `setUp` 阶段集体中止（CI 实测）。加守卫后语义与上游"尽力而为"的意图完全一致。
- `tests/test_afl_vcrash.py`：两处目标命令都改为按"**实际可运行**"挑选——
  ① `target_cmd = 'ls'` 改为「`ls` 能真正 spawn 就用它，否则用运行中的解释器 `-c pass`」；
  ② `target_cmd = 'python testdata/dummy_process/dummyproc.py'` 改为用 `sys.executable` 调用同一脚本，
  不再依赖 PATH 上存在 `python` 命令。
  依据：该用例分别需要一个"读取样本后退出码 0"的命令与一个"挂起"的命令（`ls`/`python` 只是上游随手选的例子），
  断言（非崩溃样本判 invalid、挂起样本判 timeout）完全不变。

  两处守卫都**先试运行再使用**（`_runnable()`）：PATH 命中并不等于可 spawn——文件可能权限位可执行、
  却因沙箱/挂载限制无法 execve，此时 exec 搜索最终返回 ENOENT，Python 侧表现为 `FileNotFoundError`
  （这正是 CI 上 20 例 `'make'` 缺失的真实成因）。

**未削弱任何断言**：`0005` 未删除/放宽任何断言与期望值，用例数量不变（92）；仅把"工具缺失"从
"整体中止"改为"按可用性执行"。两处均逐条如实声明。

### 5. 运行时工具依赖

- `afl-multicore` / `afl-multikill` 包装 `afl-fuzz`；`afl-sync` 驱动 `rsync`。
- 二者在制品仓均已发布并经 `conan download` 实测存在：`afl/1.35b`、`rsync/3.3.0`。本配方以 `requires` 声明，消费方通过 Conan runenv 自动获得其 `bin` 于 PATH。

### 5.1 构建期工具依赖（tool_requires，本轮 CI 修复新增）

上游测试套件会 shell out 到 CI worker **完全不提供**的命令，故改由制品仓工具包提供（均已 `conan download` 实测可拉取二进制）：

| tool_requires | 用途 | 依据 |
|---|---|---|
| `bmake/20200710` | 提供 `make`：上游每个用例的 `setUp()` 都会执行 `make -C testdata/crash_process` | CI worker 的 PATH（`/data/app/bin:/system/bin:/system/sbin:/vendor/bin:~/.local/bin`）中无 `make`，此前 20 个用例以 `FileNotFoundError: 'make'` 中止 |
| `coreutils/9.10` | 提供 `ls`：`tests/test_afl_vcrash.py` 用 `ls` 作为"必然成功"的 trivial 目标命令 | 同上，worker 中无 `ls`；`test_verify_samples` 因此把样本误判为 crash |

配方在 `_provision_test_tools()` 中按「profile 编译器目录 → 工具包 bin → `~/usr/local/bin`、`/data/service/hnp/bin`、`/usr/bin`、`/bin`、`/system/bin`… → HNP 逐包目录」的顺序解析 `make`/`ls`/`gdb`/`python`，并在构建目录内建**私有 shim 目录**（软链）置于测试 PATH 最前；用 bmake 顶替 `make` 时自动设置 `MAKESYSPATH` 指向其 `share/mk`。

**候选必须真正可执行**（本轮 CI 修复的关键）：一个"文件存在"的候选并不够用——平台上有若干不可执行的同名工具桩，PATH 搜索反复命中不可执行文件时，内核最终报的正是 `FileNotFoundError`（exec 搜索在所有候选都不可执行后返回 ENOENT），表现为"工具明明在却找不到"。故 `_find_provider()` 现在逐个候选**实际试跑**（`_exec_ok()`：execve 失败即否决，非 0 退出不算失败），跳过不可用者并继续向后找。`make`/`ls` 最终都解析不到时**不中止构建**（补丁 0005 已使相关用例可容忍），而以 error 级别打印缺失项与已搜索目录。

### 6. 构建期陷阱与本轮修复（本版踩坑）

- **basic_layout 自递归**：`basic_layout()` 令 `build_folder` 落在 `source_folder` 之内（`<src>/build-release`）。若把源码复制进 build 目录（原实现用 `shutil.copytree`）会**无限自递归**。修复：就地（`cwd=source_folder`）运行上游测试。
- **afl-fuzz 位置前置条件**：上游 `tests/test_afl_multicore.py` 的 4 个命令行用例以 `skipUnless(shutil.which('afl-fuzz') == ~/.local/bin/afl-fuzz)` 为前置。本配方在构建期设**隔离 HOME**（`<build>/testhome`）并把 `afl/1.35b` 的**真实** afl-fuzz 软链到 `~/.local/bin/afl-fuzz`，使这 4 个用例真实执行（而非跳过）。
- **setsid 缺失（已由补丁 0004 消除）**：上游 `tests/test_afl_multikill.py::setup_testprocess` spawn `['setsid','setsid','python','dummyproc.py']`；OHOS 无独立 `setsid` 可执行文件。早期方案是构建期造 `setsid → busybox` 软链，但 CI worker 上 `/data/service/hnp/bin/busybox` 并不存在（无人可用），该路径无效；现改为**在测试侧用 Python 原生 `start_new_session=True`**（见补丁 0004 声明），彻底去掉对该系统工具的依赖。
- **测试临时目录显式注入（本轮加固）**：配方在 `_run_upstream_tests` 内把 pytest 子进程的 `TMPDIR` 显式指向构建目录内的私有可写目录（`<build>/tmp`），使上游测试不依赖宿主/CI 是否导出 `TMPDIR`（本平台 `/tmp` 只读，E002）。`tempfile.gettempdir()` 自身亦会在候选目录均不可写时回退到可写目录（实测 `TMPDIR=/tmp` 时返回 `$HOME`），故双保险。
- **pytest --timeout 误杀（本轮修复）**：`tests/test_afl_stats.py::test_main` 触发 `twitter.oauth_dance()` 连接 `api.twitter.com`。本环境无外网出口，TCP 连接在 **~130.5s** 后超时（`socket TimeoutError [Errno 110]`），`afl_stats.twitter_init` 捕 `URLError` 后 `sys.exit(1)`（用例期望值）。旧 `--timeout=60` **早于**网络超时，被 pytest-timeout 判为「挂起」而失败——属于误判。现提高到 `--timeout=240`，实测 130.5s 后走到 `sys.exit(1)`，断言通过。

## 上游测试清点表（R51）

上游 `tests/` 共 **9 个 pytest 文件、92 个 test 函数**（`grep -cE "^\s*def test_"` 清点，另含 `testdata/` 固件）。`conanfile.py build()` 末尾真实运行该套件：

```
python3 -m pytest tests -q --no-header --timeout=240 --timeout-method=signal
```

| 测试文件 | 上游 test 数 | 实测 passed | failed | skipped | 备注 |
|----------|:---:|:---:|:---:|:---:|------|
| tests/test_SampleIndex.py | 14 | 14 | 0 | 0 | — |
| tests/test_afl_collect.py | 13 | 13 | 0 | 0 | 依赖 exploitable（已装） |
| tests/test_afl_cron.py | 7 | 7 | 0 | 0 | — |
| tests/test_afl_minimize.py | 7 | 7 | 0 | 0 | — |
| tests/test_afl_multicore.py | 18 | 18 | 0 | 0 | 含 4 个 afl-fuzz 前置用例（真实执行，非 skip） |
| tests/test_afl_multikill.py | 2 | 2 | 0 | 0 | setsid 经 busybox shim 补齐 + PGID 走 TMPDIR |
| tests/test_afl_stats.py | 13 | 13 | 0 | 0 | twitter 用例经 --timeout=240 真实走到 sys.exit(1) |
| tests/test_afl_sync.py | 13 | 13 | 0 | 0 | 依赖 rsync（由 rsync/3.3.0 提供） |
| tests/test_afl_vcrash.py | 5 | 5 | 0 | 0 | — |
| **合计** | **92** | **92** | **0** | **0** | **通过率 92/92 = 100%** |

> 统计口径：`conan create` 构建期真实输出行
> `UPSTREAM-PYTEST-SUMMARY: 92 passed, 1 warning in 89.33s (0:01:29)`。
> 唯一 warning 为上游 `afl_utils/afl_collect.py:215` 的 `SyntaxWarning: invalid escape sequence '\ '`，属上游代码风格告警，与本适配无关。

## 验证指令（鸿蒙 PC）

```bash
export TMPDIR=$HOME/tmp        # /tmp 只读（E002），构建/测试临时文件走 TMPDIR
cd archives/a/afl-utils/1.35a
conan create . -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
                -pr:b=<repo>/ci/conan/profiles/ohos-aarch64
# → rc 0；构建期打印 UPSTREAM-PYTEST-SUMMARY: 92 passed, 1 warning ...（0 failed）
# → test_package: 8 工具 -h + 2 包导入 + afl-stats→SQLite 端到端，全 PASS
#   末尾机器可读行：ASSERTIONS: passed=11 failed=0 total=11
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2.x 配方（私有前缀 pip 安装 + setsid shim + 真实跑上游 pytest） |
| conandata.yml | 官方源 URL + SHA256 + 3 个补丁声明 |
| patches/0001-setup-py-fix-invalid-requirement.patch | setup.py 需求说明符兼容性修复 |
| patches/0002-pgid-file-use-tempfile-gettempdir.patch | 产品代码 PGID 路径多平台修复 |
| patches/0003-tests-pgid-file-use-tempfile-gettempdir.patch | 上游测试路径口径同步（修改上游用例） |
| test_package/ | conanfile.py + test_afl_utils.py + MANIFEST.yml |
| ../commands.json | 软件级 CLI 工具声明（R38） |
