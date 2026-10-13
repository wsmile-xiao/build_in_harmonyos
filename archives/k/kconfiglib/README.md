# kconfiglib

`kconfiglib` 是 Zephyr 项目维护的纯 Python Kconfig 解析库，实现了完整的
Kconfig 语言（含预处理、依赖求解、值计算），并附带一组命令行配置工具。

- Homepage: https://github.com/zephyrproject-rtos/Kconfiglib
- License: ISC
- Build system: setuptools
- Package type: pure Python library

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [14.1.0](./14.1.0/) | built | 2026-09-28 |

## 交付内容

13 个 Python 模块（`kconfiglib.py` 库本体 + 12 个 CLI 工具）：

| 模块 | 说明 |
|------|------|
| `kconfiglib.py` | 库本体，提供 `Kconfig` / `MenuNode` / `Symbol` 等 API |
| `menuconfig.py` | 基于 curses 的交互式配置界面 |
| `oldconfig.py` / `olddefconfig.py` | 按已有 .config 更新配置 |
| `savedefconfig.py` / `defconfig.py` | 最小配置导出 / 按默认值生成 |
| `allnoconfig.py` / `allyesconfig.py` / `allmodconfig.py` / `alldefconfig.py` | 批量配置生成 |
| `genconfig.py` | 由 Kconfig 反向生成 .config |
| `listnewconfig.py` | 列出新增符号 |
| `setconfig.py` | 命令行设置符号值 |

> **不交付 `guiconfig.py`** —— 它依赖 Tkinter，而 OHOS 的 Python 不带
> `_tkinter` 模块（`harmonybrew` 亦无 tcl/tk）。详见 `14.1.0/notes.md`。

## OHOS 适配要点

- 纯 Python 包，**无需编译**：适配工作为「源码 → site-packages 布局 → PYTHONPATH 暴露」
- 上游测试为自带 `testsuite.py`（非 pytest），本配方执行其中的 `run_selftests()`
- 源码取 GitHub tag 归档（PyPI sdist 不含测试套件，无法满足 R51）
