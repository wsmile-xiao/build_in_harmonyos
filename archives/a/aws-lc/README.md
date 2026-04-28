# AWS LibCrypto (AWS-LC) — OpenHarmony 编译档案

## 软件简介
AWS-LC 是基于 BoringSSL 的通用加密库，提供完整 TLS 协议支持和 OpenSSL API 兼容。

## 功能概述
- TLS 1.0/1.1/1.2/1.3 支持
- ML-KEM (Kyber) 后量子密码学
- ML-DSA 签名算法
- AES-GCM-SIV
- OpenSSL 1.1.1 API 兼容
- FIPS 140-3 路径

## OHOS 适配要点
- **关键**: `-DDISABLE_GO=ON` 禁用 Go 依赖
- **关键**: `-DOPENSSL_NO_ASM=1` 禁用汇编
- 无汇编优化性能下降约 20-30%

## 依赖关系
- 编译依赖: CMake 3.10+, Clang
- 被依赖: aws-c-cal, aws-c-io, s2n-tls

## 参考资料
- [AWS-LC GitHub](https://github.com/aws/aws-lc)
