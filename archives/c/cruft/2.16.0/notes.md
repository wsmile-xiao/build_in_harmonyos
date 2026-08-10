# cruft 2.16.0 适配笔记

## 编译环境
- 构建系统: pip (Python 包, hatchling 后端)
- 编译日期: 2026-08-08
- 编译器: N/A (pure Python package)
- 状态: built

## 软件概述

cruft 是用于维护 Cookiecutter 模板项目的纯 Python CLI 工具。它可以帮助用户：
- 从模板创建新项目 (`cruft create`)
- 检查项目是否与模板同步 (`cruft check`)
- 查看项目与模板的差异 (`cruft diff`)
- 更新项目以匹配最新模板 (`cruft update`)

## 构建步骤

1. 从 PyPI 下载源码: `https://files.pythonhosted.org/packages/source/c/cruft/cruft-2.16.0.tar.gz`
2. 安装运行时依赖到系统 Python (使用 `pip install --break-system-packages`)
3. 安装 cruft 本身到 staging 目录 (使用 `pip install --no-deps --prefix`)
4. 复制 staging 到 Conan 包目录
5. 复制 sitecustomize.py 到 site-packages 目录

## 依赖版本

依赖版本固定为上游 uv.lock 中的版本，避免新版 Typer/Click 交互行为在 OHOS 上导致阻塞：

| Dependency | Version |
|------------|---------|
| cookiecutter | 2.6.0 |
| GitPython | 3.1.43 |
| typer | 0.15.1 |
| click | 8.1.8 |
| toml | 0.10.2 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS Python 子进程无法按 PATH 查找 git | OHOS Python 使用 `posix_spawn()` 执行裸命令，不搜索 PATH | 附带 `sitecustomize.py`，仅在 OHOS 生效，将裸命令解析为绝对路径 |
| 2 | pip install 在 Conan 构建环境中失败 | Conan 环境中 `pip` 不在 PATH | 使用 `sys.executable -m pip` 代替 `pip` |
| 3 | 依赖版本冲突 | 新版 Typer/Click 在 OHOS 上交互行为不同 | 固定依赖版本到 uv.lock 中的版本 |
| 4 | `cruft --version` 不存在 | cruft 2.16.0 CLI 无 `--version` 选项 | 使用 `cruft --help` 和 `cruft.__version__` 验证 |

## 源码修改

- 不修改上游 cruft 源码。
- 新增 `sitecustomize.py`：仅在 OHOS 生效，修复 Python 子进程执行裸命令时的 PATH 解析。

## 验证

- Conan `create`：通过
- Conan `test_package`：3/3 通过 (import, CLI help, functional create/check/diff)
- 上游 pytest：186/187 通过（1 个失败，原因是 pytest 9.x 移除了 `pytest.warns(None)`，非适配问题）
- 真机环境：HarmonyOS aarch64, Python 3.12.8, Conan 2.29.1, pytest 9.1.1
- pytest 命令：`PYTHONPATH=$PKG python3 -m pytest -q tests --basetemp=~/pytest-basetemp`

## 注意事项

- cruft 是 pure Python 包，无 C 扩展需要编译
- 使用 hatchling 作为构建后端
- 运行时依赖通过 pip 安装到系统 Python，不打包进 Conan 包
- sitecustomize.py 仅在 OHOS 平台激活
