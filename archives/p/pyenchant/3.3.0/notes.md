# pyenchant 3.3.0 适配笔记

## 编译环境
- 构建系统: custom（纯 Python，无编译器）
- 编译日期: 2026-09-23
- 编译器: clang/clang++（仅环境检查，实际不使用）
- 状态: built

## 编译步骤

纯 Python noarch：

1. `pip install setuptools wheel pytest`
2. `pip install --no-deps --prefix=<源码树外>/_staging_pyenchant <source>`
3. 运行上游套件（`pytest tests`），并把 `enchant/2.8.2` 的 `lib/` 经
   `PYENCHANT_LIBRARY_PATH` + `LD_LIBRARY_PATH` 暴露
4. `package()`：拷 `<staging>/lib/pythonX.Y/site-packages/enchant` 到 package folder

## 依赖

| 依赖 | 版本 | 来源 | 说明 |
|---|---|---|---|
| enchant | 2.8.2 | ohpcd 已发布 | 提供 `libenchant-2`，pyenchant 经 ctypes 在运行期加载 |

**运行时接入点**：`enchant/_enchant.py` 的查找顺序为
`PYENCHANT_LIBRARY_PATH` 环境变量 → `PYENCHANT_ENCHANT_PREFIX` →
`ctypes.util.find_library("libenchant-2" / "libenchant" / "libenchant-1")`。
配方用前者显式指向 conan 依赖的 `lib/`，最稳。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | staging 可能被纳入包发现 | `setup.cfg` 用 `packages = find:`（自动发现），而 conan 下 source_folder 与 build_folder 相同 | staging 落在**源码树之外**（source_folder 的父目录） |
| 2 | pytest 无法启动 | `typeguard` 的 pytest 插件与 pytest 版本不兼容（`parser.addini("string")` 断言失败） | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` |
| 3 | pytest 断言重写抛 `TypeError: required field "lineno" missing from alias` | 本机 pytest 断言重写缺陷 | `--assert=plain` |

## 上游测试结果（R51 如实申报）

口径：`pytest tests --assert=plain`（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，
`PYENCHANT_LIBRARY_PATH` 指向 enchant/2.8.2 的 lib）。

上游测试 9 个文件（test_broker / test_checker / test_dict / test_docstrings /
test_misc / test_multiprocessing / test_pwl / test_tokenize / test_utils）。
实测结果见 test_package/MANIFEST.yml。

## 备注

- pyenchant 无 `docs/` 目录，`scripts/ohc/init_build.py` 的嵌套源码提升缺陷
  （见 pyxdg notes.md）**未命中本包**。
- 上游测试中的词典相关用例可能依赖系统已安装的拼写词典；若缺词典导致失败，
  会据实列入允许清单并在日志告警，不静默放行。
---

**编译结束**: 2026-09-23 19:17
**最终状态**: built
