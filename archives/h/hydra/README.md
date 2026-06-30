# hydra

**描述**: THC hydra - 快速网络登录破解工具，支持多种协议

**版本**: 9.6-r1

**主页**: https://github.com/vanhauser-thc/thc-hydra

**编译状态**: built ✅

## 支持的协议

hydra 支持超过 50 种协议的密码破解，包括：
- FTP, HTTP(S), SMTP, POP3, IMAP
- SSH (需要 libssh), Telnet
- SMB, RDP, VNC
- MySQL, PostgreSQL, Oracle
- 以及更多...

## 编译依赖

- openssl (必需)
- zlib (必需)
- libssh (可选，用于 SSH 模块)
- libidn (可选，用于国际化登录)
- ncurses (可选，用于彩色输出)

## HarmonyOS 编译说明

1. configure 自动检测依赖，缺少可选依赖会禁用相应模块
2. 核心功能仅需 openssl 和 zlib
3. 使用 `--disable-xhydra` 禁用 GUI

## 安装

```bash
tar xzf hydra-9.6-r1-ohos-aarch64.tar.gz
cd hydra-9.6-r1
./install.sh
```

## 使用示例

```bash
# FTP 密码破解
hydra -l user -P passwords.txt ftp://target

# HTTP 基本认证
hydra -l admin -P passwords.txt http-get://target/admin

# 查看支持的模块
hydra -U
```
