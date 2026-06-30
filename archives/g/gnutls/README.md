# GnuTLS

## 简介

GnuTLS 是一个安全的通信库，实现了 SSL、TLS 和 DTLS 协议。 提供了用于实现安全通信的应用程序接口。

## 功能概述

- **协议支持**：TLS 1.0-1.3、DTLS、SSL 3.0
- **加密算法**：RSA、DSA、ECDSA、ECDH、AES、Camellia
- **证书处理**：X.509 证书解析、验证、生成
- **工具**：gnutls-cli、certtool、ocsptool

## OHOS 适配

### 依赖链
```
libgpg-error → libgcrypt → libtasn1 → nettle → gnutls
```

### 关键适配点
1. **修复 E007 平台识别**：更新 config.guess/config.sub
2. **需要 libintl**：链接 libintl 库以支持国际化
3. **psktool 编译问题**：需要 libintl_bindtextdomain 函数

### 已知问题
- psktool 编译失败，- gnutls-serv 需要额外依赖

## 依赖
### 编译依赖
| 软件 | 版本 | 说明 |
|------|------|------|
| nettle | >= 3.10 | 低级加密库 |
| libtasn1 | >= 4.21 | ASN.1 编码库 |
| libgcrypt | >= 1.11 | 加密库 |
| libgpg-error | >= 1.55 | 错误处理库 |

## 功能验证
```bash
gnutls-cli --version
pkg-config --modversion gnutls
```

## 参考
- 官网：https://www.gnutls.org/
- 源码：https://github.com/gnutls/gnutls