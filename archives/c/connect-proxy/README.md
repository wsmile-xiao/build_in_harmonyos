# connect-proxy

`connect-proxy`（上游项目名 ssh-connect / connect）是一个单文件 C 程序，通过 SOCKS4、SOCKS4a、SOCKS5、HTTP CONNECT
隧道或 telnet 代理中继 TCP 连接。它最常见的用途是作为 OpenSSH 的 `ProxyCommand`，让 ssh 穿过代理访问外网：

```
Host github.com
    ProxyCommand connect-proxy -H proxy.example.com:8080 %h %p
```

- 上游仓库：https://github.com/gotoh/ssh-connect
- 包名说明：Debian/Termux 等以 connect-proxy 之名分发同一程序（避免与其他 connect(1) 工具重名），
  本归档遵循该命名，安装的二进制亦为 `connect-proxy`。
- 许可证：GPL-2.0-or-later
- 构建系统：裸 Makefile（无 configure，无 install 目标）
- 类型：命令行工具（无库产物）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.105 | built | 首次适配 HarmonyOS PC (aarch64) |
