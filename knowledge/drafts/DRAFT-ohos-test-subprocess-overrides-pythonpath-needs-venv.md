# DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv — 上游测试套件以子进程起服务并覆盖 PYTHONPATH 时，「注入 PYTHONPATH」的测试法失效，须改用独立 venv

> Contributor: 3211 / Status: **DRAFT** / Updated: 2026-09-20 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-ohos-pytest-host-py312-incompat` | 草稿 | 宿主 pytest 与 py3.12 不兼容、插件自动加载炸掉 → 测试跑不起来 | 那条治的是**测试运行器自身**坏掉（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` + `--assert=plain`）；本条治的是**测试进程与子进程的 import 路径不一致**，即使 pytest 完全正常也会挂。修法不同：那条禁插件，本条建 venv。二者常同时命中，需叠加使用 |
| `DRAFT-ohos-source-copy-python-no-dist-info-version-unavailable` | 草稿 | 源码直拷无 `.dist-info` → 惰性 `__version__` 抛 `PackageNotFoundError` | 那条的结论是"**消费者测试避开 `__version__`**"；本条给出相反的例外情形——**被测包自身在运行期调用 `importlib.metadata.version(自身)`**（werkzeug `serving.py`）时无法回避，必须真的产出 `.dist-info`。同时那条的建议 fallback（`package()` 补最小 dist-info）在本条成为**必需项** |
| `DRAFT-apertium-ohos-python-bare-name-test-subprocess` | 草稿 | OHOS `posix_spawn` 不搜 PATH → 子进程裸名命令 `FileNotFoundError` | 那条是子进程**找不到命令**（PATH 语义）；本条是子进程**找不到 Python 模块**（PYTHONPATH 被覆盖 + 解释器不同）。同属"子进程环境与父进程不一致"族，但根因与对策均不同（那条用绝对路径/wrapper，本条用 venv） |

**全库查证**：对 `PYTHONPATH` 覆盖（`{**os.environ`、`DevServerClient`、`dev_server`）、
`test-venv`、`sys.executable` 三项关键词，在 `knowledge/drafts/*.kv`、
`knowledge/graph/*.kv`、`knowledge/doc/*.md` 中检索，**无同主题条目**。

## Scope（何时用）

上游 pytest 套件**自己fork 子进程**、且子进程需要 import 被测包或测试依赖的 Python 包适配。

识别信号（满足任一即命中，建议逐一 grep 确认）：

| 信号 | 检查命令 |
|---|---|
| conftest 显式构造 `env={"PYTHONPATH": ...}` | `grep -n "PYTHONPATH" <src>/tests/conftest.py` |
| 子进程复用父进程解释器 | `grep -n "sys.executable" <src>/tests/conftest.py` |
| 用例被标记为需要真实服务 | `grep -rn "mark.dev_server\|live_server" <src>/tests/` |
| 被测包运行期解析自身版本 | `grep -rn "importlib.metadata" <src>/<pkg>/` |

**实测案例：werkzeug 3.1.8**。`tests/conftest.py` 的 `DevServerClient.__enter__` 这样起服务：

```python
self._proc = subprocess.Popen(
    [sys.executable, os.fspath(Path(__file__).parent / "live_apps/run.py"), ...],
    env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONPATH": tmp_dir},
    cwd=tmp_dir, close_fds=True, ...)
```

`PYTHONPATH` 被**整体覆盖**为测试的 `tmp_path`，解释器是 `sys.executable`（宿主）。

### 三个坑叠加后的表现

1. 注入的源码目录 / 依赖目录在子进程里**全部丢失**；
2. 子进程只能从**宿主 site-packages** 找被测包；
3. werkzeug `src/werkzeug/serving.py:813` 在构造 WSGI server 时执行
   `importlib.metadata.version("werkzeug")`，需要包带 `.dist-info`。

→ 子进程抛 `PackageNotFoundError: No package metadata was found for werkzeug`，
服务器根本没起来 → 父进程 `DevServerClient.wait_ready()` 在
`except (ConnectionRefusedError, FileNotFoundError): time.sleep(0.1)` 里空转死等
→ `pytest-timeout` 超时。

**关键误导**：报错不在 pytest 输出里，而在**测试用例自己落盘的服务器日志**中
（`<basetemp>/<case>/log.txt`）。只看 pytest 输出只会看到一片 Timeout，看不出根因。

**第二重误导**：宿主若**恰好**装了同名包（本次环境宿主就有 werkzeug 3.1.8），
部分 dev_server 用例会从宿主 site-packages 命中包而"假通过"——得到"本地绿、
CI 红"的结论，且 CI 上因干净环境必然全挂。这类结论不可迁移。
**同族既有条目 `E512`**（纯 Python 包 build() 自检 import 运行时包，宿主预装而 CI
干净环境缺失 → 本地通过、远程 CI 失败）已覆盖「宿主预装导致的本地/CI 结论不可迁移」
这一现象层；本条的差别在于**成因不是缺依赖、而是子进程 PYTHONPATH 被覆盖后意外
命中了宿主包**——补依赖修不了，只能靠独立 venv 切断宿主污染。诊断时两者应并列排查。

## Layer 2 — 诊断

| 现象 | 判定 |
|---|---|
| 子进程日志报 `No module named '<pkg>'` | PYTHONPATH 被覆盖（坑 1/2） |
| 子进程日志报 `PackageNotFoundError: No package metadata was found for <pkg>` | 命中坑 3：包缺 `.dist-info` |
| pytest 输出大量 `Failed: Timeout (>Ns) from pytest-timeout` 且栈落在 conftest 的 `wait_ready()` | 服务未起来，回看上述子进程日志 |
| 注入 PYTHONPATH 后本地部分通过、CI 全挂 | 宿主污染导致假通过 |

## Layer 3 — 方案

### 首选：建独立 venv 并 `pip install` 被测包（与上游 tox 同思路）

上游 werkzeug 的 `pyproject.toml` 正是这么做的：
`[tool.tox.env_run_base] runner = "uv-venv-lock-runner"`、`package = "wheel"`。
本配方复刻该思路：

```python
# build() 内
# 1) 建隔离 venv
python3 -m venv <build>/test-venv
# 2) 装上游声明的测试依赖（从平台 pip 镜像）
<venv>/bin/python -m pip install --index-url <平台镜像> \
    "pytest>=7" pytest-timeout ephemeral-port-reserve watchdog cffi cryptography
# 3) 装被测包本体（同时得到 .dist-info 包元数据）
<venv>/bin/python -m pip install --no-deps <source_folder>
# 4) C 扩展依赖只能由 Conan 提供 → 以 .pth 挂进 venv
echo <conan-dep-site-packages> > <venv>/lib/pythonX.Y/site-packages/zz-dep.pth
# 5) 用 venv 的 python 跑套件
<venv>/bin/python -m pytest tests -q -p no:cacheprovider \
    --basetemp=<短路径>
```

**为什么它能同时解决三个坑**：
- 子进程的 `sys.executable` = venv python → site-packages 命中被测包（坑 1/2）；
- `pip install` 产生 `.dist-info` → `importlib.metadata` 正常（坑 3）；
- 与宿主环境彻底隔离 → 消除宿主污染与宿主 pytest 不兼容（顺带解决
  `DRAFT-ohos-pytest-host-py312-incompat`）。

**验收前置**：运行套件前先显式校验 venv 能 import 被测包与其依赖，
失败即抛 `ConanException`（R51：不以跳过冒充通过）。

### 两个必须配套的细节

1. **`-p timeout` 要显式加载**：若同时用了 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`
   （为屏蔽宿主不兼容插件），pytest-timeout 的标记不再注册，上游
   `@pytest.mark.timeout(2)` 会变成未知标记；上游若设
   `filterwarnings = ["error", ...]`，该警告被放大为**收集期 ERROR**。
   必须显式 `-p timeout` 并传 `--timeout=<n> --timeout-method=thread`
   ——后者的真正价值是把"挂起"转成**可诊断的失败**而非无限等待。
2. **basetemp 用短路径**：AF_UNIX 路径型 socket 的 `sun_path` 上限约 108 字节，
   而 conan 的 `build_folder` 路径实测 >108 字符。把 basetemp 放在
   `build_folder` 下会让 socket 类用例先撞 `ENAMETOOLONG`，**掩盖**真实根因
   （OHOS SELinux 拒绝 bind → EPERM / `E024`）。放在 `$HOME` 下的短路径即可
   让根因显形。

### 兜底：探针 + `--deselect`（仅在 venv 不可行时）

若目标环境无法建 venv / 无 pip 源，退而排除子进程类用例，但**必须**：
① 先用探针实测确认根因确属子进程环境而非库缺陷；
② 在 `MANIFEST.yml` / `manifest.yaml` / `notes.md` 逐条如实申报；
③ 写清"平台/环境放行后如何恢复执行"。
**禁止**把排除当成"通过"计入通过率分子。

## 反面模式（forbid）

| 模式 | 为什么禁止 | 后果 |
|---|---|---|
| 用 PYTHONPATH 注入"通过"了含子进程起服务的套件 | 子进程覆盖 PYTHONPATH 时注入必然无效；若因宿主恰好装同名包而通过，等于用污染伪造本地绿 | 本地结论不可迁移到 CI，浪费整轮 CI 额度 |
| 静默跳过/排除超时的子进程类用例而不申报 | R51 要求实测并如实回填 | 通过率分母失真，评审据假绿放行 |

## 验证记录

| 项 | 值 |
|---|---|
| 案例 | werkzeug 3.1.8（OHOS aarch64, clang 15, `os=OHOS`） |
| PYTHONPATH 注入法结果 | dev_server 类 25 用例全部超时（子进程日志：`PackageNotFoundError: No package metadata was found for werkzeug`） |
| venv 方案结果 | **967 passed, 1 skipped, 1 deselected**（21.5s，`conan create` 内同一结果） |
| 唯一排除项 | `test_server[unix socket]`，平台限制 `E024`（AF_UNIX bind 被 SELinux 拒绝，探针实测后 deselect） |
| 断言总数（消费者测试） | 22/22 |

## 关联

- `E024` — Unix domain socket bind 受限（平台限制，本条 socket 用例的根因）
- `DRAFT-ohos-source-copy-python-no-dist-info-version-unavailable` — `.dist-info` 与 `importlib.metadata`
- `DRAFT-ohos-pytest-host-py312-incompat` — 宿主 pytest 与 py3.12 不兼容
- `DRAFT-apertium-ohos-python-bare-name-test-subprocess` — 子进程环境不一致的另一分支
