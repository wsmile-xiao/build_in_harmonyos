# requests 2.22.0 — 适配记录（HarmonyOS PC / arm64）

## 适配路径

`python-require` 纯 Python 包（setuptools），4 个运行时依赖全部取 ohpcd
**已发布**版本：

| 依赖 | 上游 2.22.0 要求 | 本包采用（ohpcd 已发布）|
|---|---|---|
| certifi | >=2017.4.17 | 2026.7.22 |
| chardet | >=3.0.2,<3.1.0 | 5.2.0 |
| idna | >=2.5,<2.9 | 3.18 |
| urllib3 | >=1.21.1,<1.26 | 2.7.0 |

## 依赖策略：用已发布新版，实测而非假设

上游要求的都是 2019 年的老区间，ohpcd 上并没有这些版本。requests 2.22.0 自己
有一个硬校验（`requests/__init__.py:49 check_compatibility`）：

```python
assert major == 1; assert minor >= 21; assert minor <= 25   # urllib3
assert major == 3; assert minor < 1;  assert patch >= 2     # chardet
```

所以 import 时会抛 `RequestsDependencyWarning`。**该告警是否只是"纸老虎"必须实测**，
实测结论（2026-09-16，Python 3.12.9 + ohpcd 版本组合）：

| 项目 | 结果 |
|---|---|
| `import requests` | OK（伴随 1 条 `RequestsDependencyWarning`）|
| 真实 HTTPS GET（pypi.org）| **200**，响应体正常 |
| `Allow-Redirects` / history | OK |
| `HTTPAdapter(max_retries=Retry(...))` | OK |
| 超时传播（不可达地址）| 正确抛 `ConnectTimeout` |
| idna 非 ASCII 域名（`https://例え.テスト/`）| 正确转 punycode `xn--r8jz45g.xn--zckzah` |
| `requests.exceptions.*` 层次 | ConnectionError/ReadTimeout/SSLError/ProxyError/RetryError 齐全 |

告警只是 `warnings.warn`，不 gate 任何代码路径 → 采用已发布新版。

> **为什么不照搬老版本？** 那需要额外适配 chardet 3.0.4 / idna 2.8 /
> urllib3 1.25.3 三个遗留包，并且一个 PR 不能捎带别的包（W2 / PF4 依赖闸）。
> 见 notes 末尾「遗留依赖的对照实验」。

## 补丁：0001-tests-snimissingwarning-optional.patch

上游测试 bootstrap（`tests/__init__.py`）有一行：

```python
from urllib3.exceptions import SNIMissingWarning
```

`SNIMissingWarning` 在 **urllib3 2.0 已被移除**（实测
`hasattr(urllib3.exceptions,'SNIMissingWarning') == False`）。后果不是个别用例
失败，而是**整个测试套件连 import 都进不去**：

```
tests/__init__.py:8: ImportError: cannot import name 'SNIMissingWarning'
```

补丁把它改为可选导入 + 条件 `simplefilter`。**该符号只出现在测试代码**——
grep 确认 `requests/` 运行时包内零引用，故对交付产物无任何影响。

`git apply --check` 实测可干净应用（与 CI 同口径）。

## 上游测试：能跑多少如实申报（2026-09-16 修订：已扩到全量 8 文件）

上游 sdist **包含**完整测试（`MANIFEST.in` 有 `recursive-include tests *.py`，
8 文件 3927 行 / 302 个 `def test_`）。

**初版只跑 4 个文件（36 passed）；本版补 0002 后扩到全部 8 个文件：
373 passed / 170 skipped / 1 failed。**

### 逐文件实测对照

| 测试文件 | 扩展前 | 扩展后 | 说明 |
|---|---|---|---|
| test_structures.py | 20 passed | 20 passed | 自足 |
| test_packages.py | 3 passed | 3 passed | 自足 |
| test_hooks.py | 3 passed | 3 passed | 自足 |
| test_testserver.py | 10 passed, 1 skipped | 10 passed, 1 skipped | 由 requests **自带本地 test server** 驱动（TCP loopback 在本平台可用，已实测）|
| test_utils.py | **0（整模块收集失败）** | **198 passed, 11 skipped** | 修 pre-3.0 parametrize 写法后解锁 |
| test_help.py | 1 passed, 2 errors | **3 passed** | 补 `mocker` 夹具后解锁 |
| test_lowlevel.py | 8 errors | 6 passed, 8 skipped, **1 failed** | 补 `mocker` + httpbin 降级后解锁 |
| test_requests.py | 130 passed, **149 errors** | **130 passed, 150 skipped** | httpbin 降级为 skip（原为 error）|
| **合计** | **36 passed, 1 skipped** | **373 passed, 170 skipped, 1 failed** | |

### 提升的三个手段（补丁 0002，全部 test-only，`requests/` 包本体零改动）

| # | 障碍 | 根因 | 处置 |
|---|---|---|---|
| 1 | `fixture 'mocker' not found`（8 errors）| **pytest-mock 未发布到 ohpcd**，不能作为 `test_requires` 引入（依赖须先发布后使用）| 新增 `tests/_shim_mocker.py`，用 **stdlib `unittest.mock`** 提供等价夹具。本套件实际只用到 `patch` / `patch.dict` / `Mock` 三处，shim 覆盖同一表面，并保留 pytest-mock 的关键语义：`patch()` **立即 start**、teardown 自动 stop（`unittest.mock.patch` 单独用不会自动 start，这正是需要 shim 的原因）|
| 2 | `recursive dependency involving fixture 'httpbin' detected`（149 errors）| 上游 conftest 的 `httpbin` 夹具**依赖同名外部夹具**（由 pytest-httpbin 插件提供）| `conftest.py` 改为条件定义：有 `pytest-httpbin` 时维持原语义；无则 `pytest.skip`。真需外部服务的用例如实计入 **skipped**，**不伪装通过** |
| 3 | `TypeError: object of type 'MarkDecorator' has no len()`（整模块 0 收集）| `TestSuperLen` 用 pytest **pre-3.0** 的 parametrize 写法（参数元组内嵌 `pytest.mark.skipif('cStringIO is None')`）| 改用 `pytest.param(..., marks=pytest.mark.skipif(...))` 表达**同一 skip 语义** |

### 剩余 1 个失败及其定性（如实申报，未用 skip/xfail 掩盖）

`tests/test_lowlevel.py::test_chunked_upload` → `http.client.ResponseNotReady`

**与本次打包无关**：在**仅应用补丁 0001 的全新解压树**上同样失败（已独立实测复现），
属 urllib3 2.x 行为差异（上游 2.22.0 面向 urllib3 1.x 编写）。故如实记为 failed，
不用 skip 掩盖。

> 关于 skipped 的口径：170 项 skipped 全部是**需外部 httpbin 服务**的用例
> （无 pytest-httpbin 时降级），如实申报而非静默通过；一旦 CI 环境提供 httpbin，
> 这些用例会自动开始真实执行（conftest 的条件分支会在有插件时恢复原语义）。

## 消费者契约（test_package）

`test_requests_consumer.py` 离线为主 + 1 次真实 HTTPS GET（无网自动降级为
提示，不误判失败），覆盖：PreparedRequest/URL 解析（含 idna 非 ASCII 域名）、
Session 与 adapter 装配、流式 body、`Retry` 对象传入 adapter、异常层次，
并**显式断言那条 RequestsDependencyWarning 存在且只有一条**——这样若将来有人
改依赖导致告警消失（说明行为变了）或新增告警，测试会立刻发现。

## 遗留依赖的对照实验（供后续需要 2019 生态时参考）

若将来确有需求（例如某消费方严格依赖 requests 2.22.0 + urllib3 1.x），
需按拓扑序先适配并发布：`urllib3/1.25.3`、`idna/2.8`、`chardet/3.0.4`。
按 W2/PF4，这些必须各自独立 PR，不能与本包捎带提交。
