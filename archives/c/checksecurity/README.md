# checksecurity

Debian 系统安全检查脚本集（2.0.18）。

## 简介

checksecurity 是一组由 cron 周期性调用的安全检查脚本：主脚本
`bin/checksecurity`（Perl）读取 `/etc/checksecurity.conf` 配置，驱动
`/usr/share/checksecurity/check-*` 插件逐项检查系统安全状态：

- `check-diskfree`：磁盘剩余空间告警
- `check-iptables-logs`：分析 iptables 日志中被过滤的 IP
- `check-passwd`：空口令 / UID 0 账号检查
- `check-setuid`：SUID 文件变化检查
- `check-sockets`：TCP/UDP 监听 socket 变化检查

上游为纯 Perl/shell 脚本，**无 C/C++ 编译过程**（Makefile 仅做安装布局）。
源码官方托管：https://salsa.debian.org/debian/checksecurity

## OHOS 适配说明

1. **shebang 修复**：`#!/usr/bin/perl` → `#!/usr/bin/env perl`（OHOS 无
   `/usr/bin/perl`，perl 5.42 由制品仓提供，经 PATH 解析）。见
   `2.0.18/patches/`。
2. **运行时依赖**：perl/5.42.2（制品仓已发布）+ 系统基础命令（df/awk/find/mount 等）。
3. **权限说明**：主脚本运行需 root 权限（非 root 输出 "Sorry, only root can
   run checksecurity" 后退出）；test_package 采用 perl -c 语法校验 +
   打包完整性断言做消费者验证。

## 使用

```bash
conan install checksecurity/2.0.18
# 安装后：bin/checksecurity、share/checksecurity/check-*（插件）、
# etc/checksecurity/*.conf（配置样例）、share/man/man8/*.8
```

## 版本

| 版本 | 状态 | 日期 | 源码 |
|------|------|------|------|
| 2.0.18 | built | 2026-09-07 | [salsa.debian.org](https://salsa.debian.org/debian/checksecurity/-/archive/debian/2.0.18/checksecurity-2.0.18.tar.gz) |