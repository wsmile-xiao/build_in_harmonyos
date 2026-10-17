# owfs

> 1-Wire filesystem — access Dallas/Maxim 1-wire devices as a virtual filesystem or via network

| 项目 | 值 |
|------|-----|
| 软件 | owfs |
| 版本 | 3.2p4 |
| 上游 | https://github.com/owfs/owfs |
| 主页 | https://owfs.org/ |
| 许可证 | GPL-2.0-only AND LGPL-2.0-only |
| 构建系统 | autotools |
| 适配状态 | 🔄 pending |

## 简介

OWFS 是 Dallas/Maxim 1-wire 总线设备的文件系统接口。它提供：

- **owserver** — 1-wire 网络服务器，支持远程访问
- **owhttpd** — 基于 HTTP 的设备浏览界面
- **owftpd** — FTP 接口
- **owshell** — 命令行工具集（owdir, owread, owwrite, owget 等）
- **libowcapi** — C 语言 API 库
- **ownet/ownetlib** — 网络客户端库

## HarmonyOS 适配说明

初始适配聚焦**网络模式**组件（owserver/owhttpd/owftpd/owshell/owcapi），
禁用所有硬件总线主机适配器（USB/i2c/W1/parport/FTDI）。

### 已知限制

- `daemon()` 在 OHOS 沙箱中不可用，需使用 `--foreground` 模式
- FUSE 文件系统挂载需要内核 FUSE 支持
- 硬件适配器需要后续逐步启用并验证

## 版本历史

| 版本 | 日期 | 状态 | 备注 |
|------|------|------|------|
| 3.2p4 | 2026-09-08 | 🔄 pending | 初始适配 |
