# dhcp-helper

`dhcp-helper` 是 Simon Kelley（dnsmasq 作者）编写的小型 DHCP 中继代理（RFC 2131/1542）。
它监听指定接口上的 DHCP 请求，单播转发给远端 DHCP 服务器，并把应答送回客户端网段，
用于 DHCP 服务器与客户端被路由分隔、无法直连的网段。

- 上游仓库：https://www.thekelleys.org.uk/dhcp-helper/
- 许可证：GPL-2.0-or-later
- 构建系统：裸 Makefile（无 configure，无测试目标）
- 类型：命令行工具/守护进程（无库产物，安装于 sbin/）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.2 | built | 首次适配 HarmonyOS PC (aarch64) |
