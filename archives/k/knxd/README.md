# knxd

knxd 是 KNX / EIB（安装总线）网关守护进程，eibd 的后继。它把 KNX 双绞线总线上的
电报在不同接口（串口 TPUART/NCN5120、USB 接口、IP 组播、IP 隧道、FT1.2、dummy）之间
路由，并向客户端提供 `libeibclient`（C API）与 `knxtool` 命令行工具。

- 上游：<https://github.com/knxd/knxd>
- 构建系统：autotools（`configure.ac`；上游发布件不含生成物，需自举）
- 语言：C/C++（本版本主程序为 C++，客户端库 `libeibclient` 为 C）
- 许可：GPL-2.0-or-later

## 已适配版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.14.73 | 见 `0.14.73/manifest.yaml` | HarmonyOS PC (OHOS aarch64) |

## 产物

- `bin/knxd` —— 路由守护进程（argp 命令行解析）
- `bin/knxtool` —— 客户端命令行工具（安装时会在 `libexec/knxd/` 生成数十个功能别名软链接）
- `bin/findknxusb` —— USB 接口探测工具（启用 USB 后端时）
- `libexec/knxd_args` —— 参数展开辅助程序
- `lib/libeibclient.{so,a}` + `include/eibclient.h`、`include/eibtypes.h`、`include/eibloadresult.h`

## HarmonyOS PC 上的已知限制

见 `0.14.73/notes.md` 的「已知限制 / 能力墙」节：串口与 USB 设备节点、组播/隧道网络面
在真机上的可达性需要按运行期逐项取证，编译与安装面不代表运行时可用。
