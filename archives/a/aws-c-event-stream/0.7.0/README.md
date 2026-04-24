# aws-c-event-stream 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS C Event Stream Library |
| 版本 | 0.7.0 |
| 官网 | https://github.com/awslabs/aws-c-event-stream |
| 源码下载 | https://github.com/awslabs/aws-c-event-stream/archive/refs/tags/v0.7.0.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
curl -L -o aws-c-event-stream-0.7.0.tar.gz "https://github.com/awslabs/aws-c-event-stream/archive/refs/tags/v0.7.0.tar.gz"
tar -xzf aws-c-event-stream-0.7.0.tar.gz
cd aws-c-event-stream-0.7.0
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
DESTDIR=$HOME/tmp/aws-c-event-stream cmake --install build
```

## 功能说明

aws-c-event-stream 提供 AWS event-stream 协议支持：
- 二进制编码/解码
- 消息分帧
- CRC 校验
- 流式处理

用于 AWS 服务：
- S3 Select（事件流响应）
- Kinesis（数据流）
- DynamoDB Streams

## 依赖关系

### 编译依赖
- aws-c-common ✅
- aws-c-io ✅
- aws-c-http ✅
- aws-checksums ✅

### 被依赖
- aws-c-s3（S3 Select）

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libaws-c-event-stream.a
│   └── cmake/aws-c-event-stream/
└── include/
    └── aws/event-stream/
        ├── event_stream.h
        └── event_stream_channel.h
```

## 参考链接

- [aws-c-event-stream GitHub](https://github.com/awslabs/aws-c-event-stream)
