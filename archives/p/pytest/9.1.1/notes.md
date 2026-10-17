# pytest 9.1.1 适配笔记（HarmonyOS PC / OHOS armv8）

## 一、为什么引入 pytest

本包不是终端用户软件，而是**测试基础设施**。

`archives/x/xkeyboard-config/2.48.1` 的上游套件由 meson 注册，注册条件是
上游 `meson.build` 里写死的：

```meson
python = pymod.find_installation('python3', modules: ['pytest'],
                                 required: false)     # 第 91-92 行
pytest = find_program('pytest-3', 'pytest', required: false)   # 第 133 行
enable_pytest = python.found() and pytest.found()              # 第 134 行
```

两个 `required: false` 意味着：**pytest 缺失时构建不会失败，而是 pytest
套件根本不执行**。实测在干净 worker 上正是这一情形——`conan create` 记录

```
Program python3 (pytest) found: NO
Program pytest-3 pytest found: NO
```

于是 5516 个用例静默不跑。本包把这两个条件（可导入的模块 + PATH 上的
程序）作为交付物补齐，供给依赖 pytest 的消费方。

## 二、源码与校验

| 项 | 值 |
|---|---|
| 上游 | https://github.com/pytest-dev/pytest |
| 版本 | 9.1.1 |
| sdist | `pytest-9.1.1.tar.gz` |
| URL | `https://files.pythonhosted.org/packages/e4/47/b9efed96c114afcfa3c9d3fe98a76a1d14c74a9e266d397cf6eb64be5e01/pytest-9.1.1.tar.gz` |
| sha256 | `1088fbde8f2b49d95a549a195707afa7a76a3ce9bcadc26b6d71f0ffda5fe313` |
| 许可 | MIT |

sha256 取自 PyPI JSON API 的 `digests.sha256`，本机下载后复算一致。

## 三、交付物组成（两个条件都要满足）

`package_folder` 结构：

```
bin/pytest, bin/py.test          ← find_program 命中的目标
lib/python3.12/site-packages/
    pytest/                      ← 可导入模块（find_installation 的 modules 检查）
    _pytest/                     ← 引擎实现（含 _pytest/_py）
    py.py                        ← 见下节
    pytest-9.1.1.dist-info/      ← METADATA / top_level.txt / entry_points.txt
```

`package_info()` 同时注入两类环境变量，且 `buildenv_info` 与
`runenv_info` 都注入：

- `PYTHONPATH` → `lib/python3.12/site-packages`（满足 `import pytest`）
- `PATH` → `bin`（满足 `find_program('pytest')`）

**必须两个都注入**：上游 `enable_pytest` 是二者的逻辑与，只给其中一个
仍然不会注册套件。构建期也必须注入（`buildenv_info`），因为上游套件是在
消费方 `build()` 期间执行的，不是运行期。

### 关于 py.py

pytest 9.x 的 sdist 在 `src/py.py` 自带一个**顶层模块**（不是第三方
pylib 包），内容是：

```python
import _pytest._py.error as error
import _pytest._py.path as path
sys.modules["py.error"] = error
sys.modules["py.path"] = path
```

而 `_pytest/compat.py:20` 在**模块加载时**即 `import py`。若打包时漏掉
该文件，任何 pytest 调用都会在收集阶段直接
`ModuleNotFoundError: No module named 'py'`（本地实测复现过一次）。
因此配方把它作为必需文件校验存在后才复制。

## 四、构建方式

沿用仓内已发布 python 包的范式（`python3-rdflib/7.1.4`、`packaging/26.3`、
`pluggy/1.6.0`）：**直接铺模块树**，不走 setuptools 构建。

原因：上游 `pyproject.toml` 要求 `setuptools>=77` + `setuptools-scm`，
而本机解释器自带 `setuptools 75.6.0`，`pip install .` 会因 build backend
解析失败而报 `metadata-generation-failed`（本地实测）。sdist 中
`src/_pytest/_version.py` 已烘焙版本号：

```python
__version__ = version = '9.1.1'
```

故无需 setuptools-scm 现场推断，直接铺树即得等价产物。

`bin/pytest` 与 `bin/py.test` 由配方生成，shebang 用
`#!/usr/bin/env python3`，内容调用 `_pytest.config._console_main`
（与上游 `entry_points.txt` 的 `console_scripts` 定义一致）。

## 五、运行期依赖

按上游该版本的 `Requires-Dist` 精确声明（非推测）：

| 依赖 | 版本 | 状态 |
|---|---|---|
| iniconfig | 2.3.0 | 本批新增（`archives/i/iniconfig`） |
| packaging | 26.3 | 制品仓已发布 |
| pluggy | 1.6.0 | 制品仓已发布 |
| pygments | 2.20.0.1 | 制品仓已发布 |

`colorama`（仅 win32）、`exceptiongroup`/`tomli`（仅 py<3.11）不适用于
本平台，故不声明。

### 依赖必须带 `run=True`，否则消费者拿不到它们

四个依赖全部以 `self.requires(..., run=True)` 声明，这一项是**承重的**、不是修饰：

本包 `package_type = "application"`，而 Conan 对 application 的下游传播规则是把
`headers`/`libs` 一律置 False、只保留 `run`。不带 `run=True` 时，四个依赖在
`conan install` 输出里被列入 **`Skipped binaries`**，它们各自的 `runenv_info` 也就
不会进入消费者环境——依赖的包目录明明在磁盘上，`import pytest` 仍然报
`No module named 'pluggy'`。

本机实测（假 application 工具 + 四个真实依赖，消费者读自己的 conanrun 环境）：

| 声明方式 | 消费者 PYTHONPATH 中 pluggy / iniconfig 命中 |
|---|---|
| 普通 `requires` | 0 / 0（CI 正是这样失败的） |
| `run=True` | 1 / 1 |

`no_skip=True` **不能**替代：它只解除 skip，仍不传播环境。构建上下文同理——用
`tool_requires("pytest/9.1.1")` 引入时（xkeyboard-config 就是这种用法），
`conanbuildenv` 里同样只有带 `run=True` 才有这些条目。

### 另有一处依赖自身的缺口，由本包代为补齐

`packaging/26.3` 通过 Conan 1.x 的 `env_info` 对象导出路径，而 Conan 2 忽略该对象
（CI 打印为 `WARN: deprecated: 'env_info' used in: packaging/26.3`）。后果不是一句
警告，而是消费者环境真的缺条目：本机实测消费者 `conanrun` 的 `PYTHONPATH` 里有
pytest/iniconfig/pygments/pluggy，**唯独没有任何 packaging 条目**，于是
`import pytest` 的 packaging 解析依赖宿主解释器恰好自带的那份。

修 `packaging/26.3` 本身在本 PR 内不可行（它已发布、本仓一 PR 只放一个包），而且
"消费者需要什么"本来就是 pytest 的契约——四个依赖正是为此才以 `run=True` 声明。
故由本包 `package_info()` 代为发布四个依赖的 site-packages：按 `_find_site_packages()`
探测（pygments 装到 `lib/python/site-packages`、其余为 `lib/python3.12/...`，不硬编码），
任一依赖取不到目录即 `output.warning` 具名告警而非静默漏项。成功时打印
`published N dependency site-packages path(s)`（实测 N=4）。

## 六、上游套件的执行方式（全套 51 模块）

配方在 `build()` 里执行 pytest **自带套件的全部模块**（`testing/`，collect
得 4231 个节点），并解析会话汇总行记录数字。实测结果：

```
4164 passed, 41 skipped, 6 deselected, 13 xfailed, 7 xpassed in 648.51s
rc = 0
```

（collect 得 4231 个节点 = 4164 + 41 + 6 + 13 + 7，全套执行、无子集。）

CI 侧实测（构建 #64062，tip `ed947c8fe4`，即已含 bash/posix_spawn 修法、尚未含
`run=True` 与依赖路径发布的那一版）：上游套件 `rc=0`，`4141 passed, 0 failed,
64 skipped`，日志中**不再出现** `FileNotFoundError: 'bash'` —— 该失败在加 shim 之前
的真实 CI 运行里发生过（`1 failed, 4137 passed, 67 skipped`），故可确认修法在 CI 侧生效。
本机同形 PATH 为 `4164 passed, 41 skipped`；CI 多出的 23 项是环境差异导致的**跳过**
（不是失败），因此门禁仍以本机数字为基准。

### 为什么不能只给宿主解释器拼 PYTHONPATH

上游有测试会**派生子 pytest 进程**，机制有两条，独立生效：

- `src/_pytest/pytester.py` 在每个用例前执行 `mp.setenv("HOME", tmphome)`，
  把 HOME 改到临时目录 —— **user site**（`$HOME/.local/lib/pythonX.Y/site-packages`）
  因此从子进程的 `sys.path` 里消失；
- `testing/test_debugging.py` 用 `monkeypatch.setenv("PYTHONPATH", ...)`
  **覆盖**（而非追加）PYTHONPATH。

只经 `PYTHONPATH` 传递依赖的实现，在这两种情形下都会让依赖在子进程中消失，
用例以 `ModuleNotFoundError: No module named 'pluggy'` 失败——这与本包是否
打包正确无关。实测同一套件：

| 方案 | 失败数 |
|---|---|
| 宿主编译器 + `PYTHONPATH` | 141 |
| 经 `PYTHONUSERBASE` 供给的自包含根 | **0** |

`PYTHONUSERBASE` 之所以能同时扛住这两条：site.py 在**每次解释器启动时**把
user site 解析为 `$PYTHONUSERBASE/lib/pythonX.Y/site-packages`，与 HOME 无关、
也与 PYTHONPATH 无关。探针实测：HOME 被改且 PYTHONPATH 被覆盖时，不设该变量
的普通解释器无法 `import pluggy`，设了就能导入 pytest / pluggy / iniconfig /
xmlschema / hypothesis 全套。

配方**不用 venv**：`python -m venv` 会写 `pyvenv.cfg` 并依赖
`sys._base_executable`，在 CI 沙箱里生成的解释器会在执行任何代码前就失败
（`Fatal Python error: init_fs_encoding ... No module named 'encodings'`）。
改为「铺目录 + 指向 `PYTHONUSERBASE`」只用原装解释器，启动期不导入任何额外东西。

同时这也解除了"调用方 user-site 必须可读"的隐含要求（`~/.local` 权限 0770，
CI 以不同 uid 运行时读不到）。

### bash 供给（否则 argcomplete 用例失败、parseopt 用例静默跳过）

上游有两个文件需要 `bash`：

- `testing/test_argcomplete.py` 直接 shell 出去跑 `bash -c "compgen ..."`，把结果与 pytest
  自己的补全实现对比；
- `testing/test_parseopt.py` 先跑 `bash --version`，调用失败就
  `pytest.skip("bash is not available")`。

CI worker 的 `PATH` 是 `/data/app/bin:/system/bin:/system/sbin:/vendor/bin` 加
`~/.local/bin`，其中**没有 bash**。实测后果：argcomplete 用例报
`FileNotFoundError: [Errno 2] No such file or directory: 'bash'` 而失败，parseopt 的
bash 依赖用例报 `SKIPPED ... bash is not available`（本地开发机有 bash，所以只在 CI 暴露）。

**只把 bash 加进 `PATH` 并不够** —— 这是本轮用一次 CI 才确认的事实。当时配方已在 `PATH`
前置一个含 bash 软链的 `suite-bin/`（CI 日志里确有 `bash supplied to the suite`），但 CI 结果
与未供给时**逐字相同**（同样 `1 failed, 4137 passed, 67 skipped`），即该供给零效果。
根因：worker 的解释器对裸名走 posix_spawn 快路径，直接调
`os.posix_spawn("bash", ...)`，而本平台 musl 的 `posix_spawn` 是**不搜索 PATH** 的变体
（搜 PATH 的是 `posix_spawnp`），裸名因此永远解析不到。本机同一用例能过，是因为本机
解释器的 subprocess.py 不走该快路径、改走 fork/exec 并按 `os.get_exec_path` 搜索 PATH。

修法两条并用：

- `_supply_bash()`：按 `shutil.which("bash")` → `/data/service/hnp/bin/bash` → `/bin/bash`
  → `/usr/bin/bash` 的顺序**探测**（不硬编码单一路径），校验能输出版本号且是 GNU bash，
  再建只含 `bash` 软链的 `suite-bin/` 前置到 `PATH`（其余条目不受影响）；探不到时打印告警
  写明"argcomplete 用例会失败、parseopt 用例会跳过"，不静默降级。
- `_write_spawn_compat()`：往自包含根里放 `_ohos_spawn_compat.py` 和一个 `.pth`
  （`zz_ohos_spawn_compat.pth`）。`.pth` 在该解释器每次启动时执行，把 `os.posix_spawn`
  包一层：路径不含分隔符（即裸名）时先用 `shutil.which` 按 `PATH` 解析，再调用原函数；
  带绝对路径的调用原样透传。用 `.pth` 而非 `sitecustomize`，是因为宿主若已有同名模块会
  赢得导入、静默丢掉补丁。

实测：`os.posix_spawn("bash", ...)` 在 `PATH` 确有 bash 时仍报 ENOENT；载入该 shim 后
同一调用成功执行 bash。

全套（CI 同形 PATH，即 `PATH` 中无 bash）：`4164 passed, 41 skipped, 6 deselected,
13 xfailed, 7 xpassed in 648.51s`，rc=0。

### 6 项具名排除（`--deselect`，节点名可复核）

这 6 项经探针证实为**设备能力缺失**，不是打包缺陷：

| 节点 | 探针结论 |
|---|---|
| `_py/test_local.py::TestPOSIXLocalPath::test_hardlink` | 设备上**没有任何可写文件系统支持硬链接**（`os.link` 在 /data/storage/el2、/storage/Users、/dev/shm、HMDFS 等逐个实测均 EACCES） |
| `_py/test_local.py::TestPOSIXLocalPath::{test_owner,test_chown_identity,test_chown_dangling_link,test_chown_identity_rec_mayfail}` | 运行 uid **无 `/etc/passwd` 记录**（`pwd.getpwuid(os.getuid())` 抛 `KeyError`）；`pwd` 是读同一数据库的 C 扩展，无法在不换解释器的前提下顶替 |
| `test_argcomplete.py::TestArgComplete::test_remove_dir_prefix` | `/usr` 权限 `0711`（`drwx--x--x`）不可列，Python completer 与 bash `compgen` 都返回空，"两者不同"的断言失去前提 |

常规解法 user namespace（映射 uid 为 0 + 挂 tmpfs）被设备 seccomp 策略拒绝：
`unshare()` 收到 `SIGSYS`（与阻止 SysV 共享内存的是同一策略）。

**除这 6 项之外的任何失败都会让 build 失败**：配方在 `rc != 0` 时抛
`ConanException` 并打印失败节点，因此本门禁是真实门禁，而非"记录失败但放行"。

## 七、运行期要求

- 消费方解释器的 `major.minor` 需与打包时一致（本包铺在
  `lib/python3.12/site-packages`）。
- 消费方须以 `tool_requires`（或 `requires`）引入，使
  `buildenv_info` 生效——上游套件在**构建期**执行，只配
  `runenv_info` 不够。
