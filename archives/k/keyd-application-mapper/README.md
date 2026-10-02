# keyd-application-mapper

> keyd 的应用级按键重映射客户端：窗口焦点切换时，把当前窗口对应的按键绑定下发给 keyd 守护进程。

## Overview

`keyd-application-mapper` 是 [keyd](https://github.com/rvaiya/keyd) 随树发布的应用级重映射客户端。
它读取 `~/.config/keyd/app.conf`（按窗口 class/title 分段），监听窗口焦点变化，
并在每次焦点切换时执行 `keyd bind reset <bindings>`，把对应应用的绑定推给 keyd 守护进程。
上游把它作为 `scripts/keyd-application-mapper`（单文件 Python 3 脚本）随 tarball 发布，
`Makefile:37` 只用 `cp` 生成命令，没有任何编译或链接步骤。

支持的窗口监视后端（脚本内按序探测，全部失败则退出）：

| 后端 | 依赖 | 说明 |
|------|------|------|
| KDE / Plasma | `dbus-python` + PyGObject (`gi.repository.GLib`) | 通过 D-Bus 注入 KWin 脚本监听窗口切换 |
| wlroots ( sway 等 ) | 仅标准库 | 直接实现 `zwlr_foreign_toplevel_manager_v1` 协议 |
| COSMIC | 仅标准库 | 直接实现 `zcosmic_toplevel_info_v1` 协议 |
| GNOME | 仅标准库 + gnome-shell 扩展 | 经 `$XDG_RUNTIME_DIR/keyd.fifo` 接收扩展上报 |
| X11 | `python-xlib` | 通过 Xlib 轮询 `_NET_WM_NAME` / WM_CLASS |

## OHOS Adaptation

- **构建动作**：上游 `Makefile:37` 的 `cp scripts/keyd-application-mapper bin/`（无编译产物）。本包不做任何源码级功能改动。
- **解释器行**：上游硬编码 `#!/usr/bin/python3`，OHOS 无 `/usr/bin/python3`；补丁 `0001-scripts-keyd-application-mapper.patch`
  改为 `#!/usr/bin/env python3`，由依赖 `python/3.12.9` 提供解释器（Conan run 环境把其 `bin/` 前置进 `PATH`）。
- **文档**：安装上游预生成的 `data/keyd-application-mapper.1.gz` 到 `share/man/man1/`（仓库内已含 scdoc 产物，不需要 scdoc）。
- **可选后端**：`dbus-python` 与 `python-xlib` 在制品仓不存在，二者在脚本内都是**延迟 import**：
  缺失时只有对应后端不可用，`get_monitor()` 会继续尝试其余后端并最终以
  `Could not detect app environment :(.` 退出。因此本包不声明这两个依赖。
- **运行期对端**：本命令必须与 keyd 守护进程同机部署并运行（经 `/var/run/keyd.socket`，
  用户需在 `keyd` 组）。守护进程属 keyd 包，不属本包。

## Dependencies

| Dependency | Type | Purpose |
|---|---|---|
| `python/3.12.9` | 运行时强制 | 解释器（补丁后 shebang 为 `/usr/bin/env python3`），脚本核心路径仅用标准库 |
| `dbus-python` / `python-xlib` | 可选（未发布，不声明） | KDE / X11 后端；延迟 import，缺失时仅该后端不可用 |
| keyd 守护进程 | 运行期对端（同上游树，另一包） | 实际执行绑定（`keyd bind reset`），经 `/var/run/keyd.socket` |

## Upstream tests

上游 `t/` 共 94 个 `.t` 用例，**没有一个覆盖本命令**（`grep -rn 'application-mapper|app.conf' t/` 无命中）。
可在无 root、无 `/dev/uinput` 的环境运行的入口是 `make test-io`：本次在 OHOS aarch64 实测
**94/94 PASSED、0 FAILED、0 SKIPPED**（覆盖对象为 keyd 守护进程的 keymap 引擎）。
上游主入口 `t/run.sh` 需要 root + `/dev/uinput`，在本环境实测 rc=255（Toybox 无 `whoami`、设备权限拒绝、
`-linotify` 链接失败）；详见 `2.6.0/reports/`。
