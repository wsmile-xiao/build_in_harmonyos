# werkzeug 3.1.8 — OHOS（鸿蒙 PC）适配笔记

## 概述

Werkzeug 是 Pallets 出品的 WSGI 工具库（Flask 的核心依赖），提供 Request /
Response 包装、路由（Map/Rule）、HTTP 头解析、密码哈希、调试器与开发服务器等。
本包为**纯 Python**（`src/werkzeug/`，52 个 .py），无 C 扩展、无平台相关代码，
`os=OHOS, arch=armv8`，路径 A 基础适配。

上游版本对应：3.1.8（最新 3.1.x）。构建后端 flit_core，src 布局。

## 编译环境

| 项 | 值 |
|---|---|
| 构建系统 | pyproject（flake flit_core 后端；本配方走纯复制，不做 PEP 517 构建） |
| 编译日期 | 2026-09-20 |
| 目标 | aarch64-linux-ohos（`os=OHOS, arch=armv8`） |
| 工具链 | clang 15（OHOS profile；纯 Python 实际不调用编译器） |
| 状态 | built（本地 `conan create` exit=0） |

## 编译步骤

```bash
conan create archives/w/werkzeug/3.1.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

纯 Python 无编译步骤：
1. `source()` 下载 PyPI sdist（sha256 校验）并解压
2. `build()` 建独立 venv、装测试依赖、`pip install` 被测源码，跑上游 pytest 套件
3. `package()` 把 `src/werkzeug` 拷入 `<pkg>/lib/python3.12/site-packages/`，并补最小 `.dist-info`
4. `package_info()` 声明 `PYTHONPATH`（runenv + buildenv）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | dev_server 类用例全部超时；dev server 子进程日志报 `PackageNotFoundError: No package metadata was found for werkzeug` | `werkzeug/serving.py:813` 在构造 WSGI server 时执行 `importlib.metadata.version("werkzeug")`；仅把源码目录放进 site-packages（无 `.dist-info`）会抛 `PackageNotFoundError`，服务器起不来 → `wait_ready()` 死等 → pytest-timeout | `package()` 补最小 `.dist-info`（METADATA + 空 RECORD），先例 cookiecutter 2.7.1 |
| 2 | 往 `PYTHONPATH` 注入源码目录（jinja2 3.1.6 的可用做法）对本包**完全无效** | `tests/conftest.py` 的 `DevServerClient` 以子进程起服务器，env 为 `{**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONPATH": tmp_dir}` —— **整体覆盖** PYTHONPATH，且用 `sys.executable` | 按上游 tox（`uv-venv-lock-runner` + `package = "wheel"`）思路：构建期建独立 venv → `pip install` 被测源码（同时得到包元数据）→ 用该 venv 的 python 跑套件。子进程继承 venv executable，site-packages 与 `importlib.metadata` 均命中 |
| 3 | `markupsafe`（C 扩展）在 venv 里找不到 | markupsafe 是 C 扩展，只能由 Conan 提供，不能从 pip 装 | 把 Conan 的 markupsafe site-packages 写成 `.pth` 挂进 venv |
| 4 | 屏蔽宿主插件后，`tests/test_debug.py` 收集即 ERROR：`PytestUnknownMarkWarning: Unknown pytest.mark.timeout` | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 屏蔽了 autoload，pytest-timeout 的标记未注册；上游 `pyproject.toml` 设 `filterwarnings = ["error", ...]` 把警告放大为错误 | 显式 `-p timeout` 载入插件，并传 `--timeout=120 --timeout-method=thread`（把"挂起"转成可诊断的失败） |
| 5 | `tests/test_serving.py::test_server[unix socket]` 卡死 | OHOS SELinux 禁止 AF_UNIX 路径型 socket 的 `bind()`（`PermissionError: [Errno 1] Operation not permitted`），进程内退避为死等 | 配方内 `_unix_socket_bindable()` **探针实测**：被拒才 `--deselect` 并如实记录；平台限制（知识 **E024**，仓内先例 libfstrm/libmalcontent/kdbusaddons/carbon-c-relay）。不写死跳过，平台放开即自动恢复执行 |
| 6 | 探针最初误报 `AF_UNIX path too long` | AF_UNIX `sun_path` 上限约 108 字节，而 `conan build_folder` 路径实测 >108 字符（basetemp 落在其下），**掩盖**了真实根因 | 把 basetemp 放到 `$HOME` 下的短路径（`.ohc-pytest-basetemp-werkzeug-3.1.8`），探针即报出准确的 `EPERM`。**这是本包踩到的真实坑**：诊断平台性 socket 失败前必须先换短路径 |
| 7 | 宿主 pytest 5.4.3 与 py3.12 不兼容 | 断言重写钩子报 `TypeError: required field "lineno" missing from alias`（setuptools 84.0.0 / jinja2 3.1.6 同一先例） | 不在宿主跑，改为构建期从平台 pip 镜像取新版 pytest 到独立 venv |
| 8 | pytest 默认 basetemp 会 `INTERNALERROR: not owned by the current user` | OHOS 新建目录属主被文件系统强制显示为挂载属主（20001006） | 传 `--basetemp` 走 `_given_basetemp` 分支绕过（E543 同款），且用 $HOME 短路径（见 #6） |
| 9 | **CI 上 venv 建出来了却起不来**：`ConanException: bootstrapped pip is not usable inside the test venv`，其后是 `Fatal Python error: init_fs_encoding: failed to get the Python codec of the filesystem encoding` / `ModuleNotFoundError: No module named 'encodings'`，且 `sys.prefix` 指向 **base**（`<home>/usr/local`）而非 venv | 两个叠加的构造缺陷：① 初版先试**带 pip 的普通 venv**，本平台 ensurepip 不可靠（缺 `_bundled` wheel），该步**中途失败**留下残缺骨架，再对半成品 `--clear` 重建——「目录齐全、`bin/python` 也在，但解释器起不来」正是这样来的；② 建完**从未验证解释器能否启动**，只检查 rc 与 `bin/python` 是否存在，于是坏 venv 一路带到 `pip --version` 才炸，把「venv 没建好」伪装成「pip 不可用」 | ① 去掉「先试带 pip 的 venv」——一律 `venv --without-pip`（彻底绕开 ensurepip），只留一条构造路径，不再有两段式；② 抽出 `build_with()`：建完**当场**用 `py -c "import encodings, sys; print(sys.prefix)"` 实测启动，失败即换 **virtualenv** `--no-seed`（另一套独立实现，也是本包 test 依赖里已声明的一项），两者皆不可用才抛错；③ `_run` 额外清掉 `PYTHONHOME`（会把 venv 的 stdlib 定位整个带偏）。验证：ensurepip 坏掉的条件下 `conan create` exit=0，日志 `venv --without-pip: interpreter ready (...)`，上游 **967 passed / 1 skipped / 1 deselected**，消费者 **22/22** |
| 10 | **CI #54059 全套件超时且无法归因**：日志只有 `+++++++++++ Timeout +++++++++++` 与 `conftest.py:198 wait_ready → time.sleep(0.1)` 的栈，**没有用例名、没有失败清单、没有汇总行**；同一 PR 连续三次构建分别栽在 `mkdir: resource temporarily unavailable`、`curl: No such file or directory`、本次 pytest 超时 | 两个叠加因素：① 上游 `conftest.py:198` 的 `wait_ready()` 是**无界 `while True`**——dev-server 子进程起不来就是**挂死**而非失败（worker 资源饥饿时子进程起不动，正是 CI 三次失败呈现的基础设施瞬时特征）；② 原用 `--timeout-method=thread`，pytest-timeout 在 dump 栈后调 **`os._exit(1)`**，把**整个 run** 杀掉——所以连"哪个用例挂死"都留不下来，R51 的失败清单也一并丢失 | ① 改 `--timeout-method=signal`（仓内先例 afl-utils 1.35a）：把挂死变成**该用例的一次普通失败**（`FAILED <nodeid> - Failed: Timeout (>120.0s) from pytest-timeout`），run 继续、其余用例结果完整保留、失败可归因；② 加**定向重跑**（仅一次、且仅当失败**全部**是超时）：按 node id 原样重跑那些超时用例——不跳过、不改断言、不删用例，所有用例仍真实执行；重跑仍超时才抛错，两次输出都写进 `upstream-pytest-report.txt`。任何**非超时**失败（真断言失败）一律**不**重跑，直接失败。实测：`signal` 法下完整套件仍 **967 passed, 1 skipped, 1 deselected**；定向重跑命令形态实测 `2 passed` |

## 源码修改

**无补丁**（`patches: {}`）。3.1.8 已是 Python 3.12/3.13 兼容版本，源码零改动。

## 依赖版本

| 类型 | 依赖 | 说明 |
|---|---|---|
| 运行 | `markupsafe/3.0.3` | pyproject `dependencies = ["markupsafe>=2.1.1"]`；ohpcd 已发布，实测 `conan download` 可拉取 |
| 构建期测试 | pytest>=7, pytest-timeout, ephemeral-port-reserve, watchdog, cffi, cryptography | 上游 `[dependency-groups] tests` 的子集；**ohpcd 均无**（注意 ohpcd 的 `cffi/0.24.1` 是 Common Lisp 的 cffi，与 Python cffi 无关），按 PF4 不写 `test_requires`，改为构建期从平台 pip 镜像取到独立 venv |

## 验证结果

```bash
# 上游套件（在 conan create 内运行；此处为独立复现命令）
<test-venv>/bin/python -m pytest tests -q --no-header \
  -p no:cacheprovider -p timeout --timeout=120 --timeout-method=thread \
  --basetemp=$HOME/.ohc-pytest-basetemp-werkzeug-3.1.8 \
  --deselect 'tests/test_serving.py::test_server[unix socket]'
# → 967 passed, 1 skipped, 1 deselected, 1 warning in 21.45s

# 消费者测试
python3 test_package/test_werkzeug.py <site-packages>
# → 22/22 checks passed

# 完整门禁
conan create archives/w/werkzeug/3.1.8 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → exit=0；upstream pytest: 967 passed, 1 skipped, 1 deselected
#   （deselected: tests/test_serving.py::test_server[unix socket]）
```

**R51 如实申报**：上游测试 **25 个 test_*.py 模块**（顶层 16 +
`tests/middleware/` 6 + `tests/sansio/` 3）+ conftest + 资源，实测
**967 passed / 1 skipped / 1 deselected**，**零失败**
（通过率 = 967/967 = 100%）。
- 1 skipped：上游自身 `skipif`，与本平台无关
- 1 deselected：`test_server[unix socket]`，平台限制 E024（AF_UNIX bind 被 SELinux 拒绝）

## 交付物

纯 Python 包，无二进制产物；`package_type = "python-require"`，无 `bindirs`，
故**不需要** `commands.json`（R38 不适用）。

```
<pkg>/lib/python3.12/site-packages/
├── werkzeug/                      # 52 个 .py（src 布局拷贝）
└── werkzeug-3.1.8.dist-info/      # 最小元数据（METADATA + RECORD）
```

## 注意事项

- **`.dist-info` 不是可选项**：删掉它会让 dev_server 类用例全部失败
  （`PackageNotFoundError`），因为 werkzeug 自身在运行期解析发行版版本。
- **测试必须用 venv，不能用 PYTHONPATH 注入**：本包的 conftest 会覆盖子进程
  PYTHONPATH 并复用 `sys.executable`；这是与 jinja2 3.1.6（同族、纯 PYTHONPATH
  注入可行）的关键差异，照抄会得到满屏超时。
- **AF_UNIX 诊断先换短路径**：`conan build_folder` 路径 >108 字符会让 socket
  用例先撞 `ENAMETOOLONG`，把平台限制（EPERM）伪装成路径问题。见 #6。
- 宿主环境若**恰好**装有同名 werkzeug，会让部分 dev_server 用例"假通过"
  （子进程从宿主 site-packages 找到包）；venv 方案正是为消除这类污染。
---

**编译结束**: 2026-09-20 05:25
**最终状态**: built
