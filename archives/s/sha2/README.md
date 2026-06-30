# sha2 - SHA-2 Hash Utility

## 软件描述

sha2 是一个轻量级的 SHA-2 哈希计算工具，用于计算文件的 SHA-256、SHA-384 和 SHA-512 哈希值。该工具使用 OpenSSL 的 EVP API 进行哈希计算，与 Aaron Gifford 的原始 sha2 工具功能兼容。

## 功能说明

- 计算 SHA-256、SHA-384、SHA-512 三种哈希算法
- 支持文件哈希计算
- 支持标准输入哈希计算
- 输出格式兼容标准 sha256sum/sha384sum/sha512sum 格式

## 使用方法

```bash
# 计算文件的 SHA-256 哈希
sha2 myfile.txt

# 计算文件的 SHA-384 哈希
sha2 -a 384 myfile.txt

# 计算文件的 SHA-512 哈希
sha2 -a 512 myfile.txt

# 计算标准输入的哈希
echo "test" | sha2
```

## 支持的哈希算法

| 算法 | 输出长度 | 命令选项 |
|------|---------|----------|
| SHA-256 | 256 bits (64 hex chars) | `-a 256` 或默认 |
| SHA-384 | 384 bits (96 hex chars) | `-a 384` |
| SHA-512 | 512 bits (128 hex chars) | `-a 512` |

## 编译版本

- **当前版本**: 1.0.1
- **编译状态**: built
- **编译日期**: 2026-06-11
- **编译器**: clang 15.0.4

## 依赖

- OpenSSL 1.1.1w (libcrypto)

## 官方资源

- 官方网站: https://aarongifford.com/computers/sha.html
- 原始实现: Aaron Gifford 的 sha2 工具

## 注意事项

1. 本实现使用 OpenSSL EVP API，需要系统安装 OpenSSL 库
2. 运行时依赖 libcrypto.so，通过 RPATH 自动定位
3. OpenSSL 1.1.0+ 不需要手动初始化/清理（已自动处理）

## 已编译版本

| 版本 | 状态 | 补丁数 | 备注 |
|------|------|--------|------|
| 1.0.1 | built | 2 | OpenSSL 1.1.0+ API 适配 + RPATH 支持 |