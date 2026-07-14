# connect

`connect`（上游项目名 ssh-connect）是一个单文件 C 程序，通过 SOCKS4、SOCKS4a、SOCKS5、HTTP CONNECT
隧道或 telnet 代理中继 TCP 连接。它最常见的用途是作为 OpenSSH 的 `ProxyCommand`，让 ssh 穿过代理访问外网：

```
Host github.com
    ProxyCommand connect -H proxy.example.com:8080 %h %p
```

- 上游仓库：https://github.com/gotoh/ssh-connect
- 许可证：GPL-2.0-or-later
- 构建系统：裸 Makefile（无 configure，无 install 目标）
- 类型：命令行工具（无库产物）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.106 | built | 首次适配 HarmonyOS PC (aarch64) |

## 鸿蒙适配要点

- 上游 Makefile 硬编码 `CC=gcc`，配方从 Conan profile 注入 clang（R33）。
- 鸿蒙 libc（musl）已内置 resolver 与 socket 实现，`LDLIBS` 必须置空，不能链接 `-lresolv`/`-lsocket`/`-lnsl`。
- Makefile 无 `install` 目标，由 `package()` 手动安装 `bin/connect`。
- `-R <nameserver-ip>` 依赖 glibc 的 `_res` 全局解析器状态，musl 无此结构（编译报 `use of undeclared identifier '_res'`）。
  补丁 `0001-connect.c.patch` 在 musl/OHOS 上改为直接向指定 nameserver 发 UDP DNS 查询，功能等价保留（详见 1.106/notes.md）。
