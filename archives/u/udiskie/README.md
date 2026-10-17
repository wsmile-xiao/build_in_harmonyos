# udiskie

基于 [udisks2](https://www.freedesktop.org/wiki/Software/udisks/) 的可移动介质自动挂载器。
udiskie 监听 udisks2 的 D-Bus 信号，可在设备插入/拔出时自动挂载/卸载，并提供 LUKS
解锁、桌面通知与系统托盘图标。

上游为**纯 Python 3 应用**（PEP 517 / setuptools），源码树不含任何 C/C++ 源文件，
因此没有原生编译步骤。`pyproject.toml` 声明四个命令行入口（`[project.scripts]`）：

| 命令 | 入口点 | 说明 |
|------|--------|------|
| `udiskie` | `udiskie.cli:Daemon.main` | 常驻守护进程，自动挂载 + 通知 + 托盘 |
| `udiskie-mount` | `udiskie.cli:Mount.main` | 手动挂载 |
| `udiskie-umount` | `udiskie.cli:Umount.main` | 手动卸载 |
| `udiskie-info` | `udiskie.cli:Info.main` | 列出设备信息 |

## HarmonyOS PC (aarch64) 适配

- **启动器自包含**：上游 setuptools entry point 会把脚本装进解释器 system site-packages
  并在 shebang 写死构建解释器路径；OHOS 上 conan 包不得改动共享解释器，因此四个启动器
  被重新生成为可移植形式：`#!/usr/bin/env python3` + **包相对 site-packages 引导**，
  可脱离 conan runenv 独立运行（`udiskie --version` 实测通过）。
- **依赖**：原生绑定 `PyGObject`（`gi`）以 conan 依赖 `pygobject/3.58.0` 提供；
  纯 Python 依赖 `docopt`、`PyYAML` 以 **vendor** 方式随包发布，使启动器自包含。
- **OHOS 补丁（2 个，见 `patches/`）**：
  1. `0001-defer-gi-runtime-ohos.patch`：gi(PyGObject) 运行时导入惰性化 —— OHOS 沙箱无法
     加载 `_gi.*.so`（`PyType_Ready` 重定位失败）且无 GLib/Gio typelib，否则连
     `--version`/`--help` 都无法运行。
  2. `0002-cache-optional-keyutils-ohos.patch`：`python-keyutils` 变为可选，OHOS 无
     libkeyutils/内核 keyring 时以进程内缓存按相同语义回退。
     > 安全性权衡：该回退不再由内核 keyring 托管，密码缓存仅存活于当前进程。

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 2.6.2   | built  | 纯 Python 3（setuptools）；启动器 OHOS 可移植化 + 自包含（内嵌 docopt/PyYAML）；2 个可移植性补丁；上游 unittest 6/6 通过；test_package 40/40 |
