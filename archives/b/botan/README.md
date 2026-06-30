# Botan 加密库

## 软件描述

Botan是一个现代化的、开源的C++加密库，提供了广泛的加密算法和协议实现。它支持：

- 对称加密：AES、ChaCha20、Serpent等
- 公钥加密：RSA、ECC、DH等
- 哈希函数：SHA-2、SHA-3、BLAKE2等
- MAC算法：HMAC、CMAC等
- 数字签名：RSA、ECDSA、EdDSA等
- TLS协议：支持TLS 1.2和TLS 1.3
- 其他：随机数生成、密码哈希等

## 官方网站

- 项目主页：https://botan.randombits.net/
- GitHub：https://github.com/randombit/botan

## 特性

- C++实现，性能优异
- 模块化设计，可按需启用功能
- 支持静态库和共享库
- 提供CLI工具用于加密操作
- 跨平台支持

## HarmonyOS适配说明

本预编译版本针对HarmonyOS进行了适配：

1. **静态库可用**：libbotan-3.a（推荐使用静态链接）
2. **后量子加密模块禁用**：Kyber/Dilithium模块因C++20特性不完整被禁用
3. **explicit_bzero缺失**：使用volatile memset替代

## 使用建议

- 推荐使用静态库 `libbotan-3.a` 进行链接
- 头文件位于 `include/botan-3/botan/`
- CLI工具 `botan` 可用于测试和操作