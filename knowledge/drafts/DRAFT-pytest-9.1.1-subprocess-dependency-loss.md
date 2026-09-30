# draft-pytest-9.1.1-subprocess-dependency-loss

## 症状

在 Conan `build()` 里以「宿主解释器 + PYTHONPATH」方式跑 pytest 自带套件时，子进程类用例
统一失败，且**全部**是同一个缺失模块：

```
ModuleNotFoundError: No module named 'pluggy'
```

实测同一套件两种供给方式：

| 供给方式 | 失败数 |
|---|---|
| 宿主解释器 + `PYTHONPATH` 拼依赖 site-packages | **141** |
| 经 `PYTHONUSERBASE` 指向的自包含根 | **0** |

剩余 6 项以 `--deselect` 具名排除，经探针证实均为设备能力缺失（无可写文件系统支持硬链接、
运行 uid 无 `/etc/passwd` 条目、`/usr` 权限 0711 不可列），与供给方式无关。

值得注意的是，这 141 项失败**看起来像打包缺陷**（依赖没打进去），但实际包是完好的——
`grep -c "No module named"` 显示它们全部出自派生子进程，父进程会话内导入一切正常。

## 根因

上游自带套件里有两处会主动切断「靠环境变量传依赖」的通道：

**① `src/_pytest/pytester.py:710` 重定向 HOME**

```python
# Ensure no user config is used.
tmphome = str(self.path)
mp.setenv("HOME", tmphome)
mp.setenv("USERPROFILE", tmphome)
```

HOME 一改，**user site**（`$HOME/.local/lib/pythonX.Y/site-packages`）就从子进程的
`sys.path` 里消失。只装在 user site 的依赖（pluggy / iniconfig / pygments）在子进程中
立刻不可导入。

**② `testing/test_debugging.py:949` 覆盖 PYTHONPATH**

```python
monkeypatch.setenv("PYTHONPATH", str(pytester.path))
```

这里是 `setenv`（**覆盖**）而不是追加，于是父进程拿来传依赖的 PYTHONPATH 在子进程里
被整条替换掉，任何只经 PYTHONPATH 可见的模块随之丢失。

两条路径独立生效、效果叠加，因此「拼 PYTHONPATH」这种写法在该套件上**没有可用的修正
参数**——只要套件派生足够多子进程，就一定会撞上。

三向探针（本机实测）：

| 条件 | `import pluggy` |
|---|---|
| 正常 HOME | ✅ |
| `HOME=<tmphome>`（pytester 的做法） | ❌ `No module named 'pluggy'` |
| `HOME=<tmphome>` + 显式 PYTHONPATH 给出依赖 | ✅ 救回 |
| `HOME=<tmphome>` + `PYTHONPATH` 被覆盖 + `PYTHONUSERBASE=<root>` | ✅ 救回（新方案） |

## 修复

把依赖供给从「环境变量拼路径」换成「一个自包含根 + 指向它的 `PYTHONUSERBASE`」：

```python
root = os.path.join(self.build_folder, "suite-root")
site_dir = os.path.join(root, *self._site_relpath())   # lib/pythonX.Y/site-packages
os.makedirs(site_dir, exist_ok=True)

# ① 被测包自身 —— 含 dist-info，见下
for name in ("pytest", "_pytest"):
    shutil.copytree(os.path.join(site, name), os.path.join(site_dir, name))
shutil.copy2(os.path.join(site, "py.py"), os.path.join(site_dir, "py.py"))
for entry in os.listdir(site):
    if entry.endswith(".dist-info"):
        shutil.copytree(os.path.join(site, entry), os.path.join(site_dir, entry))

# ② 全部运行时依赖，逐个从各自 package_folder 取
#    注意布局不统一：packaging/pluggy 在 lib/pythonX.Y/site-packages，
#    pygments 在 lib/python/site-packages（无版本段）→ 按目录搜索而非硬编码
# ③ 套件自身的 dev 依赖：按 URL+sha256 直取固定通用 wheel，再 --no-index 装本地文件（见下）
# ④ 运行：env["PYTHONUSERBASE"] = root；env.pop("PYTHONPATH")
subprocess.run([sys.executable, "-m", "pytest", tests, ...], env=env)
```

关键点：

- **`PYTHONUSERBASE` 由 site.py 在每次解释器启动时解析**，与 HOME 无关、与 PYTHONPATH
  无关，所以子进程无论被怎样改环境都仍能看到依赖；
- **不用 venv**：`python -m venv` 会写 `pyvenv.cfg` 并依赖 `sys._base_executable`，在 CI
  沙箱里生成的解释器会在执行任何代码前就失败
  （`Fatal Python error: init_fs_encoding ... No module named 'encodings'`），连「依赖是否
  可用」都无法探测；
- **第 ④ 步显式 `env.pop("PYTHONPATH")`**：留着会让宿主环境意外参与，遮蔽打包缺陷；
- 同时解除了「调用方 user-site 必须可读」的隐含要求（本机 `~/.local` 权限 0770，
  CI 以不同 uid 运行时读不到）。

### 两个连带陷阱（都被实测捕获过）

**a) 不能按名解析 dev 依赖——索引会选到本机跑不了的构建。** 让 pip 按名安装
（`pytest-xdist` 依赖 `pytest`）时它下载的 wheel 覆盖了已铺的 `pytest` 与 `pygments`，
实测 `pygments` 2.20.0.1 → 2.21.0、suite 的 skip 数 76 → 43 —— 即**部分用例跑的是下载来的
wheel，而不是被测包**。改成 `--no-deps` + 逐个列出还不够，因为 CI worker 的索引选中了
`hypothesis-6.165.3-cp310-abi3-ohos_aarch64.whl`：

- 该版本**不发布通用 wheel**，且这个文件 **PyPI 本身不收录**；
- 它在本设备上导入即失败
  （`ImportError: Error loading shared library ...: Permission denied`）；
- 本机解释器标签恰好排除它、静默选中纯 Python 的 6.155.7 —— 两台主机跑的代码不同，
  本机因此复现不出。

用 pip 平台标签约束（`--platform any` 等）也会翻车：worker 实测同一索引此后**完全给不出**
hypothesis（`from versions: none`）。

最终修法：把 11 个通用 wheel 的 **URL + PyPI sha256 钉进配方**，用 `download()` 取回本地文件，
再 `pip install --no-deps --no-index <本地 wheel>`。索引被排除在决策之外，两台主机装入字节相同；
镜像只作兜底且经校验与 PyPI 字节一致。

**b) 缺 dist-info 会让整个 session 在 fixture 阶段崩。** 套件自己会查元数据：

```python
# testing/conftest.py:174
pygments_version = Version(importlib.metadata.version("pygments"))
```
```python
# testing/test_entry_points.py:8
dist = importlib.metadata.distribution("pytest")
```

`pluggy`/`iniconfig` 自带 `*.dist-info`，但 `pygments/2.20.0.1` 的包目录**不含元数据**，
而 `_stage_suite_root` 早期也没有把被测包自己的 dist-info 一起铺进去。实测后果：22 个
color/code-highlight 用例在 fixture setup 报 `PackageNotFoundError`，外加
`test_pytest_entry_points_are_identical` 直接失败。修法：铺入被测包 dist-info + 对缺元数据
的依赖**按模块自报 `__version__` 合成**（读不到即失败，不臆造）。

**c) 套件还依赖外部命令 `bash`，而 CI 的 PATH 里没有。** 两个上游文件需要它：

```python
# testing/test_argcomplete.py:54 — 直接 shell 出去与自己的补全实现对比
files = _wrapcall(["bash", "-c", f"compgen -A directory -- '{prefix}'"])
```
```python
# testing/test_parseopt.py:299 — 拿不到 bash 就静默跳过
except FileNotFoundError:
    pytest.skip("bash is not available")
```

CI worker 的 `PATH`（`/data/app/bin:/system/bin:/system/sbin:/vendor/bin` 加 `~/.local/bin`）
里**没有 bash**；本地开发机有，所以这个缺口只在 CI 暴露。实测后果：argcomplete 用例报
`FileNotFoundError: [Errno 2] No such file or directory: 'bash'` 而**失败**，parseopt 的
bash 依赖用例报 `SKIPPED ... bash is not available`（——**静默变成"跳过"**，最容易被读成"没问题"）。

**仅把 bash 加进 `PATH` 是不够的** —— 这一点用一次 CI 才确认。当时配方已在 `PATH` 前置含
bash 软链的 `suite-bin/`（CI 日志确有 `bash supplied to the suite`），但结果与未供给时**逐字相同**
（同样 `1 failed, 4137 passed, 67 skipped`），即零效果。根因：worker 解释器对裸名走 posix_spawn
快路径，直接调 `os.posix_spawn("bash", ...)`，而本平台 musl 的 `posix_spawn` **不搜索 PATH**
（搜 PATH 的是 `posix_spawnp`）；本机同一用例能过，是因为本机 subprocess.py 走 fork/exec 并按
`os.get_exec_path` 搜索 PATH。

修法两条并用：

- `_supply_bash()`：按 `shutil.which("bash")` → `/data/service/hnp/bin/bash` → `/bin/bash` →
  `/usr/bin/bash` **探测**（不硬编码单一路径，两端主机都不假设），校验是可用 GNU bash 后建只含
  `bash` 软链的 `suite-bin/` 前置到 `PATH`；探不到则打印告警写明后果，**不静默降级**。
- `_write_spawn_compat()`：往自包含根写 `_ohos_spawn_compat.py` 与 `zz_ohos_spawn_compat.pth`。
  `.pth` 在解释器每次启动时执行，把 `os.posix_spawn` 包一层：裸名先用 `shutil.which` 按 `PATH`
  解析再调原函数，绝对路径原样透传。用 `.pth` 而非 `sitecustomize`，是避免宿主已有同名模块
  赢得导入、静默丢掉补丁。

实测：`os.posix_spawn("bash", ...)` 在 `PATH` 确有 bash 时仍 ENOENT；载入该 shim 后同一调用成功。

CI 同形 PATH（`PATH` 中无 bash）全套：`4164 passed, 41 skipped, 6 deselected, 13 xfailed,
7 xpassed in 648.51s`，rc=0。

## 验证

```
pytest/9.1.1: synthesised distribution metadata for pygments 2.20.0
pytest/9.1.1: suite root ready (pytest 9.1.1)
pytest/9.1.1: pytest upstream suite rc=0
pytest/9.1.1:   4164 passed, 41 skipped, 6 deselected, 13 xfailed, 7 xpassed in 648.51s
pytest/9.1.1: pytest upstream suite summary: 4164 passed, 0 failed, 6 device-impossible case(s) deselected
pytest/9.1.1: Package '875cce8d1981e9c176f3e1747d91402e628e0608' created
PYTEST_CONSUMER=PASS assertions=41
EXIT=0
```

（collect 4231 = 4164 + 41 + 6 + 13 + 7，全套执行、无子集。）

自包含性最小复现（双杀探针）：

```
HOME=<tmp> PYTHONUSERBASE=<root> PYTHONPATH=<tmp> \
  python3 -c "import pytest, _pytest, py, pluggy, iniconfig, xmlschema, hypothesis"
# → 成功：HOME 被改、PYTHONPATH 被覆盖，依赖仍全部可见
```

配方另在运行前做**导入来源校验**：探针打印 `pytest.__file__`，断言其落在自包含根之下；
否则抛 `ConanException`。这防止「跑起来但其实用的是别处的副本」这类静默错误。

## 适用范围

任何「在 `build()` 中执行上游自测」且**该套件会 spawn 子解释器**的包。判定不依赖具体
上游，只看两个条件是否同时成立：

1. 套件会派生新的解释器进程（pytest 的 `runpytest_subprocess`、子进程跑 CLI、并行 worker 等）；
2. 依赖只经环境变量（PYTHONPATH / HOME 决定的 user site）对子进程可见。

Python 生态里 setuptools / coverage / tox / pip 自家的套件都属此类；cxxtest、meson
的 `test()` 若内部调 Python 脚本同理。反过来，纯 in-process 的套件（只 import 不 spawn）
用 PYTHONPATH 就够了，不必付这份代价（本机铺根 + pip 装 dev 依赖约 40s）。

## 与既有条目的关系

- **E427**「shadow CI 隔离 HOME 后不要只改 HOME；需给 Python 保留真实 site-packages」——
  同源（HOME 一改 user site 就没了），但方向相反：E427 讲 CI 自己跑 conan 时不要把
  环境隔离坏，本条讲**被被测套件派生的子 pytest** 看不到依赖；修法也不同（E427 配环境变量，
  本条铺自包含根 + `PYTHONUSERBASE`）。
- **DRAFT-ohos-pytest-host-py312-incompat**「宿主 pytest 插件与 py3.12 字节码不兼容」——
  正交：那条是插件在 import 阶段先崩（`AssertionError` / `lineno missing from alias`），
  本条是插件与依赖都正常、只是子进程找不到模块。
- 查重范围：`knowledge/graph`、`knowledge/drafts`、`knowledge/doc`、`knowledge/operations`。
  `PYTHONNOUSERSITE` / `usersite` / `sys.path`→user/`.local` 三组判别词**零命中**；
  `setenv("HOME", tmphome)` 与「子进程丢依赖」写法零命中。最邻近的 E427/E292 已逐条比对
  （见上）。
