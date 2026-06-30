# gsasl (GNU SASL)

GNU SASL 是一个实现 SASL (Simple Authentication and Security Layer) 协议的库，提供多种认证机制。

## 版本

- **1.8.1** (2026-05-25) - 首次在 OpenHarmony 上编译

## 描述

gsasl 提供 SASL 认证框架，支持多种机制：
- CRAM-MD5
- DIGEST-MD5
- GS2
- GSSAPI
- SCRAM
- SAML20
- OPENID20
- SECURID
- EXTERNAL
- ANONYMOUS
- PLAIN
- LOGIN

## 编译说明

使用 autotools 构建系统。主要依赖：libgcrypt。

## 鸿蒙适配

- E011: 修改 configure 中的 umask 077 → 022 解决 HMDFS 权限问题
- E007: 更新 config.guess/config.sub 支持 HarmonyOS 平台识别

