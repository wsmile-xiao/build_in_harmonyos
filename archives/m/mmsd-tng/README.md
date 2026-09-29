# mmsd-tng

Multimedia Messaging Service Daemon - The Next Generation（MMS 守护进程 TNG）。

- 上游：https://gitlab.com/kop316/mmsd
- 描述：底层 MMS 收发守护进程，与 ModemManager 电话栈配合工作（运行期通过 D-Bus
  与 ModemManager 通信）。附带 `mmsctl` 控制工具。
- 许可证：GPL-2.0-or-later
- 构建系统：meson

## 版本

| 版本 | 状态 | 产物 | 备注 |
|---|---|---|---|
| 2.6.4 | built | `bin/mmsdtng`（MMS 守护进程）、`bin/mmsctl`（D-Bus 控制工具） | HarmonyOS PC aarch64 适配；3 个可移植性补丁，见 2.6.4/notes.md |

## 产物形态

本软件只产出**可执行文件**（无对外 `.so`/`.a`，内部 `libmms.a`/`libplugins.a` 不安装），
`package_type = application`；命令行工具声明见 [`commands.json`](commands.json)。

## 运行期依赖

`mmsdtng` 运行需要：ModemManager 服务（D-Bus）、
`mobile-broadband-provider-info` 的 `serviceproviders.xml` 数据库、可写的 `$HOME/.mms`。
