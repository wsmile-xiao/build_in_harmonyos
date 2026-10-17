# OpenConnect

OpenConnect 是开源的 SSL VPN 客户端，支持 Cisco AnyConnect / Juniper / GlobalProtect / Pulse / F5 / Fortinet / Array 等主流 VPN 网关协议，同时提供 `libopenconnect` 库与 `openconnect` 命令行工具。

## HarmonyOS PC (aarch64) 适配

- 版本: 9.12 (2023-05-20 upstream)
- 构建系统: autotools
- SSL 后端: GnuTLS (openconnect 默认)
- 依赖: gnutls/3.8.10, libxml2/2.15.3, zlib/1.3.1 (均发布于 ohpcd 制品仓)
- 产物: `openconnect` CLI + `libopenconnect.so.5` + 头文件 + openconnect.pc

## 说明

- 由于 VPN 隧道需要网络与系统特权，`openconnect` 的联网能力取决于运行环境（沙箱/权限），本仓库交付编译与打包适配，不承诺内核隧道能力。
- 详细适配过程见 `9.12/notes.md`。

## 版本索引

| 版本 | 状态 | 构建日期 |
|------|------|---------|
| 9.12 | built | 2026-09-02 |
