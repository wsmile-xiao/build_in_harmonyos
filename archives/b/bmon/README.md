# bmon

可移植的网络带宽监控与速率估算命令行工具。

- 上游：https://github.com/tgraf/bmon
- 许可证：MIT / BSD-2-Clause
- 类型：命令行工具（tool）

## HarmonyOS PC 适配要点
- libconfuse 以源码静态编入（无外部 Conan 依赖）。
- 移除 libnl/netlink，默认通过 `/proc/net/dev`（in_proc 输入模块）读取接口统计。
- 禁用 ncurses UI，保留 `ascii`/`format` 文本输出模块。
- 产物 `bin/bmon` 仅动态依赖 `libc.so`。

详见各版本目录下的 `notes.md`。

## 版本
- `4.0` — 首次适配（built）
