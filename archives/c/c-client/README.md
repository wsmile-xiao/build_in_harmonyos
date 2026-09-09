# c-client

## 简介
c-client 是 University of Washington IMAP toolkit 的核心库，提供 IMAP、POP3、NNTP 等邮件协议的客户端实现。

## OHOS 适配
- **构建系统**: 顶层 Makefile，目标 slx (Linux) 在 HarmonyOS 上原生编译
- **依赖链**: 需要 openssl/3.5.6 提供 SSL 支持
- **编译选项**: 使用 IP=6 -j1，EXTRACFLAGS=-fPIC

## 依赖
- openssl/3.5.6

## 功能验证
```bash
pkg-config --modversion c-client  # 期望输出: 2007f
```

## 参考
- 官网: https://www.washington.edu/imap/
- 源码: https://github.com/uw-imap/imap
