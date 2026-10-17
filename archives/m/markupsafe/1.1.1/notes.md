# markupsafe 1.1.1 — 适配记录（HarmonyOS PC / arm64）

## 为什么是这个版本

**1.1.1 是刻意的非最新 pin，不是随手挑的旧版。**

```
jinja2-2.10.1/jinja2/utils.py:647:
    from markupsafe import Markup, escape, soft_unicode
```

`soft_unicode` 在 **MarkupSafe 2.1 中被移除**。也就是说 Jinja2 2.10.1 的消费方
最多只能用 markupsafe ≤ 2.0.1；ohpcd 上当时的 markupsafe 只有 2.1+，故必须专门
适配 1.1.1（本任务上游版本要求）。

## 适配路径

纯 Python 包（`python-require`），走仓库既有 Python 包模式：

1. `source()` 从 PyPI 官方托管取得 sdist 并校验 sha256；
2. `build()` 运行上游 pytest 套件回填真实通过率（R51）；
3. `package()` 把 `src/markupsafe/` 拷进 `lib/python3.12/site-packages/markupsafe/`；
4. `package_info()` 用 `runenv_info/buildenv_info` 声明 PYTHONPATH。

## 关键决策：C 加速模块不交付

上游 `setup.py` 声明了可选 C 扩展 `markupsafe._speedups`
（`src/markupsafe/_speedups.c`），且编译失败时有自动降级逻辑
（`ve_build_ext` → `BuildFailed` → `run_setup(False)`）。
`markupsafe/__init__.py` 的导入也是容错的：

```python
try:
    from ._speedups import escape, escape_silent, soft_unicode
except ImportError:
    from ._native import escape, escape_silent, soft_unicode
```

**本配方只交付纯 Python 回退**，理由：

- 本机（aarch64 OHOS 原生）实测 `_speedups` 可以编译成功
  （`_speedups.cpython-312-aarch64-linux-ohos.so`），但 `python-require` 包
  里塞一个 `.so` 会绑定**构建机的 CPython ABI 与架构**，消费方机器未必匹配；
- 仓库内同类可选 C 扩展的 Python 包（`yarl`、`frozenlist`、`aiohttp`）
  一律走纯 Python 回退，口径一致；
- 功能等价：上游测试显示纯 Python 路径除 `_speedups` 组被 skip 外全部通过。

## 测试实测（2026-09-16）

上游 pytest 套件（`tests/`，4 个测试文件 + conftest）：

```
$ PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python3 -m pytest tests -q
32 passed, 11 skipped in 0.13s
```

- 跳过项即 conftest.py 参数化出来的 `_speedups` 组
  （上游自带 `skipif(_speedups is None)` 规则），属于平台的既定结果，不是失败；
- **踩坑**：本机 site-packages 的 pytest 5.4.3 + typeguard 插件在 Python 3.12 上
  直接崩（`TypeError: required field "lineno" missing from alias`），
  必须 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 才跑得起来——配方 build() 内已固化该变量。

## 消费方契约（Jinja2 2.10.1）

`test_package/test_markupsafe.py` 除常规 API 外显式断言：

```python
assert callable(soft_unicode)
assert soft_unicode(123) == "123"
```

这是本 pin 存在的理由，故必须作为消费者测试固化，防止后续被"顺手升版本"破坏。
