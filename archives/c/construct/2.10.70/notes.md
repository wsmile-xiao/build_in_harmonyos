# construct 2.10.70 适配笔记

## 编译环境
- 构建系统: custom（纯 Python，无编译器）
- 编译日期: 2026-09-23
- 编译器: clang/clang++（仅环境检查，实际不使用）
- 状态: built

## 编译步骤

纯 Python noarch，无 configure/make：

1. `pip install setuptools wheel pytest`
2. `pip install --no-deps --prefix=<build>/staging <source>`
3. 取回 sdist 未随附的 `tests/declarativeunittest.py`（见下）
4. 运行上游套件（`pytest tests`）
5. `package()`：拷 `<staging>/lib/pythonX.Y/site-packages/construct` 到
   `<package_folder>/lib/pythonX.Y/site-packages/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 5 个测试文件全部收集失败：`ModuleNotFoundError: No module named 'tests.declarativeunittest'` | PyPI sdist **未随附** `tests/declarativeunittest.py`（`MANIFEST.in` 只有 `include README.rst` / `include LICENSE`），而 5 个测试文件均 `from tests.declarativeunittest import *` | 构建期从上游 tag `v2.10.70` 的 raw URL 取回该文件（实测 2014B）后运行；取不到则显式失败（不静默跳过） |
| 2 | pytest 无法启动 | `typeguard` 的 pytest 插件与 pytest 版本不兼容（`parser.addini("string")` 断言失败） | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` |
| 3 | pytest 断言重写抛 `TypeError: required field "lineno" missing from alias` | 本机 pytest 断言重写缺陷 | `--assert=plain` |

## 上游测试结果（R51 如实申报）

口径：`pytest tests --assert=plain`（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`），
并先取回 sdist 缺失的 `tests/declarativeunittest.py`。

结果见 test_package/MANIFEST.yml（以实际运行输出为准）。

## 依赖版本

无运行期依赖（纯 Python 自包含）。extras（arrow/cloudpickle/cryptography/
lz4/numpy/ruamel.yaml）未启用。

## 备注

本包与 `pyxdg` 共用同一纯 Python 打包范式。`scripts/ohc/init_build.py` 的
嵌套源码提升缺陷（见 pyxdg notes.md）**未命中本包** —— construct 的 sdist
根目录无 `docs/`，故无 `docs/Makefile` 可被误命中。
---

**编译结束**: 2026-09-23 18:54
**最终状态**: built
