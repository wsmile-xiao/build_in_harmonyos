# markupsafe 3.0.3 适配笔记

## 概述

markupsafe 是 Pallets 的 HTML/XML 安全字符串库，提供 `Markup`、`escape`、
`escape_silent` 等 API，是 Jinja2 的**唯一**运行时依赖。

- 上游：https://github.com/pallets/markupsafe
- 版本：3.0.3
- 构建系统：无（纯 Python 包，直接拷贝到 site-packages）
- 许可：BSD-3-Clause
- 编译日期：2026-09-16
- 状态：built

## 版本选择与并存关系（重要）

本包 3.0.3 与同仓在途的 **markupsafe/1.1.1** 是**两条互不可替代的版本线**：

| 消费方 | 需要 markupsafe | 原因 |
|---|---|---|
| **Jinja2 2.10.1**（requests 2.22.0 时代链）| **<= 2.0.1** | `jinja2/utils.py` 导入 `soft_unicode`，该符号在 MarkupSafe **2.1 被移除** |
| **Jinja2 3.1.6**（flask 3.x / httpbin 链）| **>= 2.1.1** | 不再使用 `soft_unicode`，且要求新 API |

因此两者**必须在同一 remote 并存**（ohpcd 支持同包多版本），配方里也各自
`version` 独立。消费者断言里固化了这条分界线（见下）。

## 依赖

**无运行时依赖。** 注意一个易误判点：

`markupsafe/__init__.py:12-13` 有

```python
if t.TYPE_CHECKING:
    import typing_extensions as te
```

实测确认 `typing_extensions` **仅在 `TYPE_CHECKING` 分支内导入**（`te.` 的全部
使用点也都在类型标注位置），即**仅类型检查期需要**，运行时完全不需要 →
**不得**把它写成 `requires()`。ohpcd/main 也没有该包，若误加会被依赖闸拦下。

## 交付形态：纯 Python 回退（与 1.1.1 一致）

上游提供可选 C 加速器 `src/markupsafe/_speedups.c`，但 `__init__.py` 优雅降级：

```python
try:
    from ._speedups import _escape_inner
except ImportError:
    from ._native import _escape_inner
```

**本配方只交付纯 Python 回退**，理由：

- 本包是 `python-require` 类型，塞入 `.so` 会绑定**构建机的 CPython ABI 与架构**
  （`_speedups.cpython-312-aarch64-linux-ohos.so`），消费方机器未必匹配；
- 这是上游**受支持**的模式（非 hack），仓库既有先例同款
  （markupsafe 1.1.1 / yarl / frozenlist / aiohttp）。

`package()` 内跳过 `.c` / `.h`，只拷贝：
`__init__.py`、`_native.py`、`_speedups.pyi`、`py.typed`。

> `_native.py` 全文仅一个函数，把 `& > < ' "` 依次替换为实体，其中引号用
> **数字实体** `&#39;` / `&#34;`（区别于某些实现用 `&apos;` / `&quot;`）——
> 消费者测试正是用这两个形式来**反证纯 Python 回退确实生效**。

## 上游测试

`tests/` 随 sdist 提供（5 个测试文件：`test_escape.py`、
`test_exception_custom_html.py`、`test_ext_init.py`、`test_leak.py`、
`test_markupsafe.py`，加 `conftest.py`）。

`conftest.py` 用 `pytest.fixture(params=(_native, _speedups))` **双参数化**，
并对 `_speedups` 标 `pytest.mark.skipif(_speedups is None)`：

```python
params=(
    _native,
    pytest.param(_speedups,
                 marks=pytest.mark.skipif(_speedups is None,
                                          reason="speedups unavailable")),
)
```

本包不交付 `_speedups`，故该组**按上游自身规则跳过**（非失败、非本适配跳过）。

`build()` 内以 `subprocess` 调 pytest 并回填真实通过率（R51），
环境处理沿用 1.1.1 的既有结论：
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`（宿主 pytest 插件与 py3.12 不兼容）+
`--assert=plain`（断言重写钩子与 py3.12 字节码不兼容）。

## 消费者测试（test_package）

`test_package/test_markupsafe.py`，全部为真实 API 断言（R34）：

| 组 | 断言 |
|---|---|
| 导入自证 | `markupsafe.__file__` 必须位于被测包目录内（防宿主已安装版本串味）|
| 核心转义 | `escape("<b>&")`、`escape(None)`、`escape_silent(None)`、`Markup + escape`、`unescape`、`Markup.escape` |
| **纯 Python 模式反证** | `import markupsafe._speedups` **必须 ImportError**；且 `_native._escape_inner("a<b") == "a&lt;b"` |
| 引号实体（仅行为） | `escape("'") == "&#39;"`、`escape('"') == "&#34;"` —— **不**用于证明回退（见下）|
| `striptags()` 语义 | `Markup("<b>T</b>").striptags() == "T"`；`Markup("Main &raquo;\t<em>About</em>")` → `"Main » About"` |
| **3.x 契约（版本分界线）** | `not hasattr(markupsafe, "soft_unicode")`；且 `callable(markupsafe.soft_str)` |

### `__version__` 为何不断言

3.0.3 的 `__version__` 由 `__getattr__` 经 `importlib.metadata.version("markupsafe")`
惰性解析，需要已安装的 `markupsafe-*.dist-info`。本包是**源码直拷**形态（只交付可导入的
`markupsafe/` 目录），故在干净环境下必然抛 `PackageNotFoundError`。**隔离实测**：

```
$ PYTHONPATH=<pkg>/markupsafe python3 -S -c "import markupsafe; print(markupsafe.__version__)"
PackageNotFoundError: No package metadata was found for markupsafe
```

> ⚠️ 初版曾断言 `__version__ == "3.0.3"` 且"看似通过"——**那是因为构建机上恰好 pip 装了
> markupsafe，其 `.dist-info` 满足了这次查找**，属**被环境喂数据**的假通过。已在测试中
> 改为 API 断言，并加导入自证防再犯。相关判据见草稿
> `DRAFT-ohos-source-copy-python-no-dist-info-version-unavailable`。

### 引号实体**不能**证明回退生效（实测订正）

初版注释称 `&#39;`/`&#34;` 是 `_native` 的"独有形式"，据此推断纯 Python 回退生效。
**实测证伪**：`_speedups.c` 的 `DO_ESCAPE` 宏对 `"` 与 `'` **逐字节写入**
`&` `#` `3` `4` `;` 与 `&` `#` `3` `9` `;`，**输出与 `_native.py` 完全相同**。
故该断言对两套实现无区分力，已降级为纯行为断言；回退证明改由
`import markupsafe._speedups 必须失败` 承担。

### 关于 `soft_str`（跨文件一致性订正）

`soft_unicode` 的**缺席**正是本版本不可用于 Jinja2 2.10.1 的原因；将来若该符号回归，
断言会立即失败，提示版本并存假设需重新评估。

而 `soft_str` **并未随之移除**——实测 3.0.3 的 `src/markupsafe/__init__.py:64` 仍定义
`def soft_str(...)`，且可调用（`soft_str(None) == "None"`）。**两点必须区分**，不可
一起断言为"已移除"。本文件与 `test_package/MANIFEST.yml` 的旧表述已按实测订正。

## 验证结果

```
conan create archives/m/markupsafe/3.0.3 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
→ exit=0
```

| 项 | 实测结果 |
|---|---|
| `conan create` | **exit=0**，Package created |
| 上游 pytest | **39 passed, 41 skipped, 2 warnings in 0.19s** |
| skip 构成 | 41 skipped **全部**是 `conftest.py` 对 `_speedups` 的参数化组（上游自身 `pytest.mark.skipif(_speedups is None)`）——本包只交付纯 Python 回退，故按上游规则跳过；**无 failed** |
| 消费者测试 | `markupsafe 3.0.3 consumer API: PASS`（4 组断言全过）|

> 数字自洽性核对：`conftest.py` 对 `(_native, _speedups)` 双参数化，
> 故 39（`_native` 通过）+ 41（`_speedups` 跳过）= 80 个用例，
> 与上游测试规模一致。

## 注意事项

1. **不要把 `typing_extensions` 写成依赖**——它只在 `TYPE_CHECKING` 下导入；
2. **不要交付 `_speedups.c` 编译出的 `.so`**——会绑定构建机 ABI/架构；
3. **3.0.3 与 1.1.1 必须并存**，不可用一句"升级到最新"互相替代；
4. `--assert=plain` 必需（本机 pytest 5.4.3 的断言重写与 py3.12 不兼容）。
