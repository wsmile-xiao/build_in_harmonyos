# ca-certificates

Mozilla CA 证书捆绑包，提供 HTTPS/TLS 连接所需的受信任根证书。

## 功能概述

- 提供 Mozilla 维护的受信任根 CA 证书集合
- 包含 update-ca-certificates 工具管理证书信任链
- 供 OpenSSL、GnuTLS 等 TLS 库使用

## OHOS 适配

- 纯数据包，无需编译
- 从 Debian 预编译包提取证书文件（certdata2pem.py 需要 Python cryptography 模块）
- 安装 150 个 Mozilla CA 证书到 `$PREFIX/share/ca-certificates/mozilla/`

## 依赖关系

- 无编译依赖
- Python cryptography 模块（可选，用于从源码生成证书）

## 参考资料

- Debian: https://salsa.debian.org/debian/ca-certificates
- Mozilla: https://www.mozilla.org/en-US/about/governance/policies/security-group/certs/
