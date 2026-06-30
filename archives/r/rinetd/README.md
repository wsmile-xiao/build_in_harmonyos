# rinetd

## 简介

rinetd 是一个 Internet TCP 重定向服务器，将 TCP 连接从一个地址/端口透明转发到另一个地址/端口，常用于网络地址转换（NAT）和端口映射场景。

## 功能概述

- TCP 端口转发：将指定绑定地址和端口的连接转发到目标地址和端口
- 访问控制：支持基于 IP 地址的 allow/deny 规则，支持通配符（* 和 ?）
- IPv6 支持：支持 IPv4 和 IPv6 地址
- 配置文件驱动：通过简单的配置文件管理所有转发规则
- 后台守护进程：默认以守护进程模式运行，支持前台模式（-f）

## OHOS 适配

### 已知问题

1. **umask 077 兼容性问题**：configure 脚本使用 `umask 077` 创建临时目录，在 HMDFS 文件系统上会导致目录权限异常（`drwx--S---`），所有者也无法写入，导致 config.status 执行失败。解决方案：将 configure 脚本中的 `umask 077` 改为 `umask 022`。

2. **安装路径**：rinetd 二进制安装到 `sbin/` 而非 `bin/`，自动化验证工具（如 G2 功能验证）若仅在 `bin/` 目录查找二进制文件会报警告，属正常现象。

### 与 Linux 的差异

- 在 HMDFS 文件系统上需修补 configure 的 umask 设置
- 其余编译和运行行为与 Linux 一致

## 排除与替代

无。rinetd 功能独立，无需要排除或替代的组件。

## 依赖

- **编译依赖**：无（仅依赖标准 C 库和 POSIX 系统调用）
- **运行依赖**：无

## 功能验证

```bash
# 版本验证
$ rinetd --version
rinetd 0.73

# 端口转发测试
$ rinetd -f -c rinetd.conf
rinetd: starting redirections...
# 配置: 0.0.0.0 38081 127.0.0.1 38080
# 通过 38081 发送数据，38080 收到并回显
```

## 参考

- 官网: https://github.com/samhocevar/rinetd
- 源码: https://github.com/samhocevar/rinetd/releases
- 许可证: GPL-2.0-or-later
