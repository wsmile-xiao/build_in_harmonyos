# aws-c-io 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS C IO Library |
| 版本 | 0.26.3 |
| 官网 | https://github.com/awslabs/aws-c-io |
| 源码下载 | https://github.com/awslabs/aws-c-io/archive/refs/tags/v0.26.3.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
curl -L -o aws-c-io-0.26.3.tar.gz "https://github.com/awslabs/aws-c-io/archive/refs/tags/v0.26.3.tar.gz"
tar -xzf aws-c-io-0.26.3.tar.gz
cd aws-c-io-0.26.3
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

**注意**: `BYO_CRYPTO=ON` 禁用 s2n TLS 依赖，使用平台自带加密库。

### 3. 编译

```bash
cmake --build build -j$(nproc)
```

### 4. 安装

```bash
DESTDIR=$HOME/tmp/aws-c-io cmake --install build
```

## 功能说明

aws-c-io 处理所有 IO 和 TLS 工作：
- 事件循环（event-loop）
- Socket 通道（TCP/UDP）
- TLS 通道（通过 aws-c-cal）
- 异步 IO 操作
- 通道 bootstrap
- 统计监控

## 编译选项

| 参数 | 说明 |
|------|------|
| BYO_CRYPTO=ON | 禁用 s2n TLS，使用平台加密库 |
| BUILD_TESTING=OFF | 禁用测试 |

## 依赖关系

### 编译依赖
- aws-c-common 0.12.x ✅
- aws-c-cal 0.9.x ✅
- aws-c-compression 0.3.x ✅

### 被依赖
- aws-c-http
- aws-c-mqtt
- aws-c-s3
- aws-crt-cpp

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libaws-c-io.a
│   └── cmake/aws-c-io/
└── include/
    └── aws/io/
        ├── channel.h
        ├── event_loop.h
        ├── socket.h
        └── tls_channel_bootstrap.h
```

## 参考链接

- [aws-c-io GitHub](https://github.com/awslabs/aws-c-io)
