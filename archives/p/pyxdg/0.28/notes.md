# pyxdg 0.28 适配笔记

## 编译环境
- 构建系统: custom（纯 Python，无编译器）
- 编译日期: 2026-09-23
- 编译器: clang/clang++（仅环境检查，实际不使用）
- 状态: built

## 编译步骤

纯 Python noarch 包，无 configure/make：

1. `pip install setuptools wheel pytest`（构建 + 测试依赖）
2. `pip install --no-deps --prefix=<build>/staging <source>`（安装到 staging）
3. `package()`：把 `<staging>/lib/pythonX.Y/site-packages/xdg` 拷入
   `<package_folder>/lib/pythonX.Y/site-packages/`
4. `package_info()`：把该 site-packages 目录追加到 `PYTHONPATH`

与仓库既有 `soupsieve`/`acronym` 同款模式。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 解压后源码根只剩 `docs/` 内容，`setup.py`/`xdg/` 丢失 | `scripts/ohc/init_build.py` 的 `_BUILD_MARKERS` 只含 `configure/CMakeLists.txt/Makefile/meson.build`，**不含 `setup.py`**；pyxdg 根目录无这些标记，而 `docs/Makefile` 命中 → `_promote_nested_source` 误把 `docs/` 提升为源码根并**删除其余内容** | 用 tarball 重新解压并正确提升一层（框架缺陷，需框架侧修，见下） |
| 2 | `conan-init` 生成的是 autotools 模板 | 模板选择未识别纯 Python 包 | 按 `soupsieve` 范式手写配方 |
| 3 | 上游 `test/test_basedirectory.py` 无法导入 | 顶层 `from imp import reload`；`imp` 在 Python 3.12 已移除 | `--ignore=test/test_basedirectory.py`，并在本文件如实记录 |
| 4 | 上游 `test/test_mime.py` 8 项断言失败 | 依赖系统 MIME 数据库（shared-mime-info），本机无 | 列入 `ALLOWED_TEST_FAILURES`，日志显式列出（不静默放行） |
| 5 | pytest 无法启动 | `typeguard` 的 pytest 插件与 pytest 版本不兼容（`parser.addini("string")` 断言失败） | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` |
| 6 | pytest 断言重写抛 `TypeError: required field "lineno" missing from alias` | 本机 pytest 断言重写缺陷 | `--assert=plain` |

## 上游测试结果（R51 如实申报）

口径：`pytest test --assert=plain --ignore=test/test_basedirectory.py`
（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`）

- **41 passed / 8 failed**
- 8 项失败**全部**在 `test/test_mime.py`，原因：本机无系统 MIME 数据库
  （`shared-mime-info`），如 `get_type('text')` 期望值与空数据库不符 ——
  属**环境缺失**，非 pyxdg 缺陷。
- `test/test_basedirectory.py` **未执行**：顶层 `from imp import reload`，
  `imp` 在 Python 3.12 已移除（上游未适配 3.12）。此文件不计入 pass/fail。

## 依赖版本

无运行期依赖（纯 Python 自包含）。

## 框架缺陷（需框架侧处理，非本包可修）

`scripts/ohc/init_build.py` 的 `_find_source_subdir`/`_promote_nested_source`
会把「含 `docs/Makefile` 的纯 Python 包」的源码根误判为 `docs/`，且提升过程
**删除真实源码**。影响所有 `setup.py`/`pyproject.toml` 形态的包（本批 6 个包中
5 个纯 Python 包都会命中）。建议 `_BUILD_MARKERS` 增补 `setup.py`/`pyproject.toml`，
并让提升过程不删除未提升的内容。
---

**编译结束**: 2026-09-23 19:09
**最终状态**: built
