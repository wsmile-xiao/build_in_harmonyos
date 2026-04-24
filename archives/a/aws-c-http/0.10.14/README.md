# aws-c-http 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS C HTTP Library |
| 版本 | 0.10.14 |
| 官网 | https://github.com/awslabs/aws-c-http |
| 源码下载 | https://github.com/awslabs/aws-c-http/archive/refs/tags/v0.10.14.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
curl -L -o aws-c-http-0.10.14.tar.gz "https://github.com/awslabs/aws-c-http/archive/refs/tags/v0.10.14.tar.gz"
tar -xzf aws-c-http-0.10.14.tar.gz
cd aws-c-http-0.10.14
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
DESTDIR=$HOME/tmp/aws-c-http cmake --install build
```

## 功能说明

aws-c-http 提供 HTTP/1.1 和 HTTP/2 客户端：
- HTTP/1.1 连接管理
- HTTP/2 多路复用（HPACK 压缩）
- 请求/响应流式处理
- 连接池
- WebSocket 支持

## 依赖关系

### 编译依赖
- aws-c-common ✅
- aws-c-io ✅
- aws-c-compression ✅（HTTP/2 HPACK）

### 被依赖
- aws-c-auth（API 请求）
- aws-c-s3（S3 API）
- aws-c-event-stream

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libaws-c-http.a
│   └── cmake/aws-c-http/
└── include/
    └── aws/http/
        ├── http.h
        ├── http_connection.h
        ├── http_request_response.h
        └── h2_stream.h
```

## 参考链接

- [aws-c-http GitHub](https://github.com/awslabs/aws-c-http)
