# pathspec 0.6.0 — 适配记录（HarmonyOS PC / arm64）

## 适配路径

`python-require` 纯 Python 库（setuptools，零运行时依赖），沿用仓库既有
Python 包模式：sdist（PyPI 官方，sha256 校验）→ 上游测试回填 →
拷 `pathspec/` 进 `lib/python3.12/site-packages/` → `package_info()` 声明
PYTHONPATH。

## 无需源码补丁（与 jinja2 2.10.1 的对照）

本批同期的 jinja2 2.10.1 因 `from collections import Mapping`（py3.10 移除）
必须打补丁，pathspec **不需要**。原因在 `pathspec/compat.py` 的分支优先级：

```python
try:
    # Python 3.6+.
    from collections.abc import Collection as collection_type
except ImportError:
    # Python 2.7 - 3.5.
    from collections import Container as collection_type
```

新名在 try 分支优先命中，旧名只是低版本回退——py3.12 上走的是
`collections.abc`，不会失败。

> **口径**：判断某库是否需要 collections 补丁，要看**分支优先级**（try 里
> 是新名还是旧名），不是"源码里有没有出现旧的 collections 名字"。

## R38：不需要 commands.json

判定依据（PF8 配方闸对纯库包要求**无** commands.json）：

- `setup.py` 中既无 `scripts=`，也无 `entry_points=`／`console_scripts`；
- 源码树无 `bin/`、`scripts/` 目录；
- 构建产物只有 `pathspec/` 包本身（.py），无任何可执行文件。

故 `package_type = "python-require"`，不创建 commands.json。

## 上游测试

测试**位于包内**（`pathspec/tests/`，不是顶层 `tests/`），随
`find_packages()` 一起分发；`setup.py` 声明 `test_suite='pathspec.tests'`。

```
$ PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=<src> \
  python3 -m pytest pathspec/tests -q --assert=plain -p no:cacheprovider
42 passed, 2 skipped, 42 warnings in 0.12s
```

unittest 口径一致（`python3 -m unittest discover -s pathspec/tests -t .`：
`Ran 44 tests ... OK (skipped=2)`）。配方 `build()` 优先用 pytest 取单行统计，
pytest 不可用时自动回退 unittest discover。

## 消费者契约（test_package）

`test_pathspec.py` 覆盖 gitwildmatch 与 gitignore 两套语义、否定模式优先级
（`!test_*.py` 覆盖 `*.py`）、anchored 模式（`/root-only.txt` 不匹配子目录）、
`Pattern.compile()` 与 `Pattern.include`，并断言 `pathspec.compat.
collection_type` 已从 `collections.abc` 解析成功。
