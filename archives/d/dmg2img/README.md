# dmg2img

dmg2img 是一个将 Apple DMG（Disk Image）格式转换为 IMG/raw 格式的命令行工具。

## 功能概述
- 将 DMG 格式转换为 raw/IMG 格式
- 支持加密 DMG 解密（通过 vfdecrypt）
- 支持压缩 DMG 转换
- 依赖 zlib 和 bzip2 进行解压

## OHOS 适配
- 纯 Makefile 项目，无 configure 脚本
- 需要修改 Makefile 添加交叉编译支持（CC、CFLAGS、LDFLAGS）
- vfdecrypt.c 使用了 OpenSSL 1.1.1 已废弃的 API（EVP_CIPHER_CTX、HMAC_CTX），需要适配
- 编译和安装过程简单直接

## 依赖关系
- **编译依赖**: zlib, bzip2, openssl
- **运行依赖**: zlib, bzip2, openssl（共享库）

## 参考资料
- 官网: http://vu1tur.eu.org/tools/
