# aws-lc 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS LibCrypto (AWS-LC) |
| 版本 | 1.72.0 |
| 官网 | https://github.com/aws/aws-lc |
| 源码下载 | https://github.com/aws/aws-lc/archive/refs/tags/v1.72.0.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
curl -L -o aws-lc-1.72.0.tar.gz "https://github.com/aws/aws-lc/archive/refs/tags/v1.72.0.tar.gz"
tar -xzf aws-lc-1.72.0.tar.gz
cd aws-lc-1.72.0
```

### 2. 配置

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_TESTING=OFF
```

### 3. 编译

```bash
cmake --build build -j$(nproc)
```

### 4. 安装

```bash
DESTDIR=$HOME/tmp/aws-lc cmake --install build
```

### 5. 测试（可选）

```bash
cmake -B build -DBUILD_TESTING=ON
ctest --test-dir build
```

## 功能说明

AWS-LC 是基于 BoringSSL 的通用加密库，提供：
- TLS 1.0/1.1/1.2/1.3 协议支持
- 常用加密算法：AES, RSA, ECDSA, ECDH, SHA-2, SHA-3
- AWS 特定优化：AWS-KMS 集成、s2n 兼容
- FIPS 140-3 认证路径（可选）

## 编译选项

### 关键 CMake 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| BUILD_SHARED_LIBS | 构建共享库 | OFF |
| BUILD_TESTING | 启用测试 | OFF |
| FIPS | 启用 FIPS 模式 | OFF |
| AWSLC_FIPS | AWS FIPS 认证 | OFF |

## 依赖关系

### 编译依赖
- CMake 3.10+
- Clang/GCC

### 被依赖
- aws-c-cal
- aws-c-io
- s2n-tls
- AWS SDK for C++

## 编译产物

安装后生成以下文件：

```
$HOME/usr/local/
├── lib/
│   ├── libcrypto.a     # 核心加密库
│   ├── libssl.a        # TLS 库
│   └── cmake/aws-lc/   # CMake 配置
└── include/
    └── openssl/        # OpenSSL API 头文件
```

## 参考链接

- [AWS-LC GitHub](https://github.com/aws/aws-lc)
- [AWS-LC 文档](https://aws.github.io/aws-lc/)
