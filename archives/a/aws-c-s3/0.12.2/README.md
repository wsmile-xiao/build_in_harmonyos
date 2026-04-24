# aws-c-s3 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS C S3 Library |
| 版本 | 0.12.2 |
| 官网 | https://github.com/awslabs/aws-c-s3 |
| 源码下载 | https://github.com/awslabs/aws-c-s3/archive/refs/tags/v0.12.2.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
curl -L -o aws-c-s3-0.12.2.tar.gz "https://github.com/awslabs/aws-c-s3/archive/refs/tags/v0.12.2.tar.gz"
tar -xzf aws-c-s3-0.12.2.tar.gz
cd aws-c-s3-0.12.2
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
DESTDIR=$HOME/tmp/aws-c-s3 cmake --install build
```

## 功能说明

aws-c-s3 提供 Amazon S3 API 客户端：
- S3 对象操作（PUT/GET/DELETE）
- 分片上传（multipart upload）
- S3 Select（SQL 查询）
- S3 Express One Zone
- 元数据管理
- ACL 和权限控制

## 依赖关系

### 编译依赖
- aws-c-common ✅
- aws-c-io ✅
- aws-c-http ✅
- aws-c-auth ✅
- aws-c-event-stream ✅
- aws-checksums ✅

### 被依赖
- aws-crt-cpp
- AWS SDK for C++

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libaws-c-s3.a
│   └── cmake/aws-c-s3/
└── include/
    └── aws/s3/
        ├── s3.h
        ├── s3_client.h
        └── s3_multipart_upload.h
```

## 参考链接

- [aws-c-s3 GitHub](https://github.com/awslabs/aws-c-s3)
