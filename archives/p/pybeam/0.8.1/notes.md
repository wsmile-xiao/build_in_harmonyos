# pybeam 0.8.1 适配笔记

## 编译环境
- 构建系统: custom（纯 Python，无编译器）
- 编译日期: 2026-09-23
- 编译器: clang/clang++（仅环境检查，实际不使用）
- 状态: built

## 编译步骤

纯 Python noarch（`pyproject.toml` / setuptools 后端）：

1. `pip install setuptools wheel pytest`
2. `pip install --no-deps --prefix=<build>/staging <source>`
   （`--no-deps`：`construct` 由 conan 依赖提供，不走 pip）
3. 运行上游套件（`pytest test`），PYTHONPATH 注入 construct 的 site-packages
4. `package()`：拷 `<staging>/lib/pythonX.Y/site-packages/pybeam` 到 package folder

## 依赖

| 依赖 | 版本 | 来源 | 说明 |
|---|---|---|---|
| construct | 2.10.70 | 本仓已适配（ohpcd 待发布） | PyPI `requires_dist: construct>=2.9,<2.11`，2.10.70 落在区间内 |

**拓扑序提示**：pybeam 依赖 construct，故 construct 必须先适配并**发布到 ohpcd**，
pybeam 的 CI L0i（依赖可用性）才能通过。本地已用 conan 缓存中的
`construct/2.10.70` 完成构建验证。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 直接跑上游测试全部收集失败 | 测试需 `import construct`，而 construct 由 conan 依赖提供、不在环境 PATH 上 | 构建期把 `dependencies["construct"]` 的 site-packages 注入 PYTHONPATH |
| 2 | pytest 无法启动 | `typeguard` 的 pytest 插件与 pytest 版本不兼容（`parser.addini("string")` 断言失败） | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` |
| 3 | pytest 断言重写抛 `TypeError: required field "lineno" missing from alias` | 本机 pytest 断言重写缺陷 | `--assert=plain` |

## 上游测试结果（R51 如实申报）

口径：`pytest test --assert=plain`（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，
PYTHONPATH 注入 construct）。

上游测试 3 个文件（test_beam_file / test_schema_beam / test_schema_eetf）均使用
**内联合成 BEAM 数据**，无需外部 fixture。实测结果见 test_package/MANIFEST.yml。

## 备注

- pybeam 无 `docs/` 目录，`scripts/ohc/init_build.py` 的嵌套源码提升缺陷
  （见 pyxdg notes.md）**未命中本包**。
- 本包**不**在 test_package 放任何二进制数据 —— 仓库既有教训：test_package 内
  二进制测试数据在 CI（`git apply` 应用 PR diff）会报 "missing binary patch data"。
---

**编译结束**: 2026-09-27 15:52
**最终状态**: built
