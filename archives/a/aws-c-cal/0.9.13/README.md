# aws-c-cal 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS Crypto Abstraction Layer |
| 版本 | 0.9.13 |
| 官网 | https://github.com/awslabs/aws-c-cal |
| 源码下载 | https://github.com/awslabs/aws-c-cal/archive/refs/tags/v0.9.13.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
curl -L -o aws-c-cal-0.9.13.tar.gz "https://github.com/awslabs/aws-c-cal/archive/refs/tags/v0.9.13.tar.gz"
tar -xzf aws-c-cal-0.9.13.tar.gz
cd aws-c-cal-0.9.13
```

### 2. 配置

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_PREFIX_PATH=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_TESTING=OFF \
  -DBYO_CRYPTO=ON
```

### 3. 编译

```bash
cmake --build build -j$(nproc)
```

### 4. 安装

```bash
DESTDIR=$HOME/tmp/aws-c-cal cmake --install build
```

## 功能说明

aws-c-cal 是 AWS 加密抽象层，提供：
- HMAC (SHA-256, SHA-384, SHA-512)
- 块加密 (AES-CBC, AES-GCM, AES-ECB)
- 哈希函数 (SHA-1, SHA-256, SHA-384, SHA-512)
- RSA 签名/验证
- ECDH 密钥交换
- 随机数生成

## 编译选项

| 参数 | 说明 |
|------|------|
| BYO_CRYPTO=ON | 使用平台自带加密库（禁用 s2n） |
| BUILD_TESTING=OFF | 禁用测试 |

## 依赖关系

### 编译依赖
- aws-c-common 0.12.x ✅
- aws-lc 或 OpenSSL（通过 BYO_CRYPTO）

### 被依赖
- aws-c-io
- aws-c-http
- aws-c-auth
- aws-c-s3

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libaws-c-cal.a
│   └── cmake/aws-c-cal/
└── include/
    └── aws/cal/
        ├── hmac.h
        ├── hash.h
        ├── cipher.h
        └── ecdh.h
```

## 参考链接

- [aws-c-cal GitHub](https://github.com/awslabs/aws-c-cal)
