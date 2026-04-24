# aws-c-auth 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS C Auth Library |
| 版本 | 0.10.1 |
| 官网 | https://github.com/awslabs/aws-c-auth |
| 源码下载 | https://github.com/awslabs/aws-c-auth/archive/refs/tags/v0.10.1.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

aws-c-auth 提供 AWS 认证机制：
- AWS 凭证管理（Access Key + Secret Key）
- IAM 角色（Role-based credentials）
- 签名版本 4（SigV4）
- 临时凭证（STS）
- 实例元数据服务（IMDS）

## 编译步骤

### 1. 下载源码

```bash
curl -L -o aws-c-auth-0.10.1.tar.gz "https://github.com/awslabs/aws-c-auth/archive/refs/tags/v0.10.1.tar.gz"
tar -xzf aws-c-auth-0.10.1.tar.gz
cd aws-c-auth-0.10.1
```

### 2. 配置

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_PREFIX_PATH=$HOME/usr/local \
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
DESTDIR=$HOME/tmp/aws-c-auth cmake --install build
```

## 使用方法

### C API

```c
#include <aws/auth/auth.h>

// 创建凭证
aws_credentials *creds = aws_credentials_new(
    allocator,
    "ACCESS_KEY",
    "SECRET_KEY",
    NULL,  // session token
    0      // expiration
);

// 创建凭证提供者
aws_credentials_provider *provider = aws_credentials_provider_static_new(
    allocator,
    creds
);

// 签名请求
aws_auth_signing_config config;
config.credentials = creds;
config.algorithm = AWS_AUTH_SIGNING_ALGORITHM_V4;
config.service = "s3";
config.region = "us-east-1";
```

## 认证方式

| 认证类型 | 说明 |
|---------|------|
| Static | 直接使用 Access Key/Secret Key |
| Environment | 从环境变量读取 |
| Profile | 从 ~/.aws/credentials 读取 |
| IMDS | EC2 实例元数据服务 |
| STS | 临时凭证（AssumeRole） |

## 依赖关系

### 编译依赖
- aws-c-common ✅
- aws-c-io ✅
- aws-c-http ✅
- aws-c-cal ✅
- aws-c-sdkutils ✅

### 被依赖
- aws-c-s3
- aws-crt-cpp

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libaws-c-auth.a
│   └── cmake/aws-c-auth/
└── include/
    └── aws/auth/
        ├── auth.h
        ├── credentials.h
        └── signing.h
```

## 参考链接

- [aws-c-auth GitHub](https://github.com/awslabs/aws-c-auth)
- [AWS SigV4 规范](https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html)