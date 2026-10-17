# setuptools 84.0.0 适配笔记

## 编译环境
- 构建系统: custom（纯 Python，无编译步骤）
- 编译日期: 2026-09-19
- 编译器: 无（纯 Python，无 C 扩展）
- 状态: built

## 本包为何存在

`setuptools` 是**缺失的构建期依赖**，且 conan 的 `python` 包**不自带**它
（其 site-packages 只有 `README.txt`），ohpcd 此前也未发布：

- greenlet/3.5.6 的 CI #10488 在执行 `setup.py` 时报
  `ModuleNotFoundError: No module named 'setuptools'` —— 当时配方只能从
  "恰好存在"的宿主路径借用（本机有 `<home>/usr/local/lib/python3.12/site-packages`，
  CI 没有）；
- 仓内 lxml / pillow / cppy 的先例同样是宿主借用。

发布到 ohpcd 后，这种依赖宿主环境的借用就变成了**可声明、可复现**的依赖。

## 编译步骤

`setuptools` 是**纯 Python** 包，没有真正的编译阶段：

```bash
# 1) 取源码 + 校验 sha256（conandata.yml，PyPI 官方 URL）
# 2) build()：自举安装到登台目录（不依赖宿主预装 setuptools）
python3 setup.py install --root=<stage> --prefix=/usr \
        --single-version-externally-managed --record=/dev/null
# 3) build()：真实运行上游 pytest 套件（R51）
python3 -m pytest setuptools/tests -q --no-header -p no:cacheprovider \
        --basetemp=<build_folder>/pytest-basetemp
# 4) package()：按登台树原样拷入 lib/python3.12/site-packages
# 5) package_info()：runenv_info/buildenv_info 声明 PYTHONPATH
```

配方用 `package_type = "python-require"`（无二进制产物、不产生 bindirs →
无需 commands.json，R38 不适用），与仓内纯 Python 包先例一致。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 若按"借用宿主 setuptools"的老路，CI 必然失败（greenlet CI #10488 的 `No module named 'setuptools'`） | setuptools 的 `setup.py` 首行 `import setuptools`；老做法依赖宿主某条路径恰好存在，而本机与 CI 的可用路径**恰好互为不存在** | **自举**：构建 cwd 位于解包根，`import setuptools` 即解析到源码树自身（实测 `__file__` 指向解包目录、`__version__=84.0.0`），**完全不需要宿主预装** |
| 2 | 纯手工 copy 包目录树后，`setuptools.__version__` 取不到值 | `setuptools/version.py` 经 `importlib.metadata.version('setuptools')` 取版本，必须有 **dist-info** 元数据 | 经 `setup.py install` 装配元数据（产出 `setuptools-84.0.0.dist-info`），并在 `package()` 内校验 `setuptools` / `_distutils_hack` / `distutils-precedence.pth` / `dist-info` **四者齐备** |
| 3 | 上游 pytest 套件依赖多且未发布制品仓 | 上游 `[project.optional-dependencies].test` 含 pytest>=6 / virtualenv / wheel / packaging / jaraco.path/envs/text/functools / filelock / ini2toml / tomli-w / build / pyproject-hooks / pytest-xdist / pytest-timeout / pytest-home / pytest-subprocess；实测 `conan search` 在 ohpcd 均为 **0 个** | 按 **PF4** 不得写成 `test_requires` → 构建期从平台 pip 镜像取到 `<build_folder>/test-deps`，再作为 PYTHONPATH 运行上游套件；**取依赖失败即抛错**（附 pip 尾部输出），不以"跳过"冒充通过 |
| 4 | OHOS 上 pytest 默认 basetemp 报 `INTERNALERROR: not owned by the current user` | 文件系统把新建文件/目录属主强制显示为挂载属主（20001006），与进程 uid 不一致，pytest 默认 `<tmp>/pytest-of-<user>` 属主检查必然失败 | 传 `--basetemp=<build_folder>/pytest-basetemp` 走 `_given_basetemp` 分支（无属主检查）；同 `meson 1.11.0.1` 先例 |
| 5 | 设备自带 pytest 过旧（5.4.3），无法收集上游套件（`pytest.ini` 要求 `--import-mode importlib`，5.4.3 不支持） | 设备解释器的 pytest 版本低于上游要求（`pytest >= 6, != 8.1.*`） | 由上游 test extra 的 `pytest>=6` 约束自动带入较新版本（实测可从平台 pip 镜像取得），不再依赖设备自带版本 |
| 6 | **CI 上 `conan create` 失败（本地却通过）**：`ConanException: upstream pytest 运行器异常退出（exit=1），且未解析到失败用例`；报错文本 `pytest.PytestConfigWarning: Failed to import filter module 'coverage': ignore:Couldn't import C tracer:coverage.exceptions.CoverageWarning`（CI #52255） | **test extra 清单不完整，且缺失项恰好在本地被"环境偶然满足"**。① 上游 `pytest.ini:91` 的 filterwarnings 项引用 `coverage.exceptions.CoverageWarning`，但上游把 coverage 只列在 **cover** extra（pytest-cov）里，test extra 不含它；`pytest.ini` 首行是 `error`（警告即错误）→ coverage 缺失时 pytest **配置期** `apply_warning_filters()` 抛的 `PytestConfigWarning` 直接中止 run（此时**尚未收集**，输出无任何 `FAILED` 行，故被正确判为"运行器异常退出"而非测试失败）。② 另一处收集期硬依赖：`setuptools/tests/compat/py39.py` 顶层 `from jaraco.test.cpython import ...`，缺 `jaraco.test` 时 3 个测试文件 ImportError → `Interrupted: 6 errors during collection`。**本地宿主 python 恰好装了 coverage 7.8.0 + pytest_cov + jaraco.test**（实测），CI worker 没有 → 同一配方两地结果相反 | 把两项显式补进 `UPSTREAM_TEST_REQUIRES`：`coverage`、`jaraco.test>=5.5`。不以 `--override-ini=filterwarnings=` 关掉上游的严格策略（那会掩盖真实告警），只补齐上游**隐含要求**的依赖 |

| 7 | **补了 #6 的两项依赖后 CI 仍以同一形态失败**：`ImportError: cannot import name 'os_helper' from 'setuptools.tests.compat.py39'` → `Interrupted: 4 errors during collection`（CI #53591，worker CI-015；#6 的修复已在同一 SHA 上生效，失败位于**其后**） | #6 只补到 `jaraco.test`，但 `compat/py39.py` 那一行有**两跳**：`try_import('os_helper') or from_test_support('can_symlink')`。第一跳由 jaraco.test 提供；第二跳 `from_test_support()` 内部是 **`import test.support`**（jaraco.test 自己的实现），而**本平台 CPython 根本不带 stdlib `test` 包**——实测制品仓 `python/3.12.9` 的 `lib/python3.12/` 下无 `test/` 目录（该解释器 `find_spec('test')` 为 False，且它还缺 `_sqlite3`）。所以缺的不是某个第三方包，而是**解释器自身的一项标准库组件**，pip 装不出来。缺它时 `compat/py39.py` 顶层 import 失败，连带 3 个导入它的模块（`test_dist` / `test_find_packages` / `test_find_py_modules`）在**收集期**全灭 | 构建期补一层**最小 shim**（`test/support/os_helper.py`），只实现收集到的用例实际用到的唯一符号 `os_helper.can_symlink`（全套件仅两处 `skipif` 使用）。三点约束：① **仅在目标解释器确实缺 stdlib test 时安装**（先 `py -c "import test.support"` 探测；健康平台返回 None 不动 PYTHONPATH，避免遮蔽真包）；② `can_symlink()` **真实探测** `os.symlink` 能力而非硬编码，平台不支持时用例照旧跳过，**不把失败掩盖成通过**；③ 装完自检 `import test.support.os_helper` 且 `can_symlink()` 可调用，失败即抛错（R51）。实测本平台符号链接可用，故这两个用例**真正执行**而非被跳过 |

## 源码修改

**无补丁**。本适配未修改任何上游文件：

- 自举安装是上游 `setup.py` 的固有行为（cwd 在源码根即可）；
- pytest 的 `--basetemp` 只是**运行参数**，不改上游测试代码。

## 依赖版本

| 依赖 | 版本 | 性质 | 来源 |
|------|------|------|------|
| （运行时） | **无** | setuptools 三方依赖全部 vendored | `setuptools/_vendor/`：packaging 26.0、wheel 0.46.3、more_itertools 10.8.0、platformdirs 4.4.0、tomli 2.4.0、zipp 3.23.0、importlib_metadata 8.7.1、jaraco.text 4.0.0、jaraco_context 6.1.0、jaraco_functools 4.4.0、autocommand 2.2.2、backports.tarfile 1.2.0 |
| pytest 等测试依赖 | 见上表 #3 | 构建期测试用 | 平台 pip 镜像（构建期，非入库依赖） |
| python3 | 3.12.9（宿主解释器） | 运行/测试解释器 | 设备自带 |

## 验证结果

```bash
# 完整本地验证（profile: ci/conan/profiles/ohos-aarch64）
conan create archives/s/setuptools/84.0.0 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
→ exit=0
  [upstream-pytest] 1 failed, 928 passed, 17 skipped, 51 deselected,
                    12 xfailed, 3 xpassed in 859.60s (0:14:19)
  WARN: 上游 pytest 存在 1 项已知平台环境性失败（均在允许清单内）: ['test_wheel_mode']
  Package '6b129b068851896169fae42d399fa922d239ce8a' created
  setuptools 84.0.0 consumer API: 19/19 passed
  consumer API: PASS
```

- **上游测试（R51，build() 内真实运行）**：实测
  **1 failed / 928 passed / 17 skipped / 51 deselected / 12 xfailed / 3 xpassed**。
  - `1 failed` = `test_wheel_mode`（`test_wheel.py:689`，断言
    `oct(stat.S_IMODE(...)) == "0o777"` 实得 `0o770`）。根因实测为
    **OHOS hmdfs 不忠实保存 POSIX mode 位**：对全新文件 `chmod 0o777` → `0o770`，
    且 "others" 三位被整体丢弃（`0o500`→`0o660`、`0o604`→`0o660`、`0o705`→`0o760`）。
    该断言在 OHOS 上**不可能通过**，属平台限制；已列入 `ALLOWED_TEST_FAILURES`
    并在配方内逐条注明根因（同仓先例：meson 1.11.0.1 的
    `test_install_umask` / `test_installed_modes*`）。
  - `51 deselected` = 以**上游自带的** `uses_network` 标记排除（`-m "not uses_network"`）。
    构建沙箱无外网（实测 `urlopen` github raw 超时）：这些用例经
    `retrieve_file()` 取远端 setup.cfg，两次运行结果不稳定（一次通过一次失败），
    属网络可用性抖动而非适配缺陷；用上游标记排除可消除不确定性且不掩盖真实缺陷。
  - `17 skipped / 12 xfailed / 3 xpassed` 均为上游自身的版本/平台/预期失败标记。
  - **未设宽松豁免**：清单外失败、或运行器异常退出导致解析不到失败项，均抛
    `ConanException` 使 `conan create` 失败（实测曾以 `2 failed` 命中，其中
    网络用例被正确报为「清单外失败」）。
- **test_package 消费者测试（R34 真实 API）**：**19/19 passed**，见
  `test_package/test_setuptools.py`——除导入/版本/`_distutils_hack` 劫持/
  `build_meta` 入口外，**真实构建**了一个最小 wheel + sdist + METADATA。

## 注意事项

- **dist-info 不是装饰**：`setuptools/version.py` 通过
  `importlib.metadata.version('setuptools')` 取版本。任何只 copy `setuptools/`
  目录而不装元数据的做法，都会让 `setuptools.__version__` 取不到值——这类
  缺陷在"能 import 就行"的粗测下不会暴露，要到下游取版本时才炸。
- **自举是本包的关键性质**：它使 setuptools 的构建**不依赖宿主预装 setuptools**，
  这正是解决 greenlet CI #10488 那类失败的根因手段。若将来有包在构建期需要
  setuptools，应声明 `tool_requires("setuptools/84.0.0")`，而不是继续从宿主路径借用。
- 上游 vendored 了 `wheel` 与 `packaging`；消费方 site-packages 里**不应**再
  出现独立的 `wheel/` 或 `packaging/` 目录（`test_setuptools.py` 有对应断言）。
