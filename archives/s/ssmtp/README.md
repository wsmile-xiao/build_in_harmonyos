# ssmtp

## 简介

ssmtp 是一个仅发送邮件的 sendmail 模拟器，适用于从集中式邮件枢纽
（mailhub）收取邮件的机器。它把标准输入的邮件投递到配置的 SMTP 服务器，
不支持本地收件箱。

## OHOS 适配

- **构建系统**: autotools（autoconf 2.13 时代脚本，无 config.guess/config.sub）
- **SSL/TLS**: 默认启用（`--enable-ssl`），静态链接 openssl/1.1.1w，
  运行时仅依赖 libc.so
- **老 Makefile 适配**: 链接行只用 `@LIBS@`（无 LDFLAGS），openssl 的
  `-L`/`-lcrypto` 通过 LIBS 环境变量在 configure 时注入
- **命令行工具**: 产物为 `sbin/ssmtp`

## 依赖

- openssl/1.1.1w（Conan 制品仓）

## 功能验证

```bash
ssmtp -V                      # sSMTP 2.64 (Not sendmail at all)
tr -d '\0' < ssmtp | grep -a STARTTLS   # SSL 编译进二进制的标记
```

## 参考

- 官网: https://packages.debian.org/source/ssmtp
