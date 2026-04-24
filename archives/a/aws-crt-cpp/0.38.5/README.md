# aws-crt-cpp 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS CRT for C++ |
| 版本 | 0.38.5 |
| 官网 | https://github.com/awslabs/aws-crt-cpp |
| 源码下载 | https://github.com/awslabs/aws-crt-cpp/archive/refs/tags/v0.38.5.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
curl -L -o aws-crt-cpp-0.38.5.tar.gz "https://github.com/awslabs/aws-crt-cpp/archive/refs/tags/v0.38.5.tar.gz"
tar -xzf aws-crt-cpp-0.38.5.tar.gz
cd aws-crt-cpp-0.38.5
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
DESTDIR=$HOME/tmp/aws-crt-cpp cmake --install build
```

## 功能说明

aws-crt-cpp 是 AWS C 运行时的 C++ 包装：
- C++ API 封装所有 aws-c-* 库
- RAII 内存管理
- 异步操作（C++ 协程支持）
- 跨平台 IO 抽象
- MQTT5 客户端（C++ API）
- S3 客户端（C++ API）

## 依赖关系

### 编译依赖（全部 AWS C 组件）
- aws-c-common ✅
- aws-c-cal ✅
- aws-c-io ✅
- aws-c-compression ✅
- aws-c-http ✅
- aws-c-auth ✅
- aws-c-mqtt ✅
- aws-c-s3 ✅
- aws-c-event-stream ✅
- aws-checksums ✅
- aws-c-sdkutils ✅

### 被依赖
- AWS SDK for C++ v2

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libaws-crt-cpp.a
│   └── cmake/aws-crt-cpp/
└── include/
    └── aws/crt/
        ├── Auth.h
        ├── HttpClient.h
        ├── MqttClient.h
        ├── S3Client.h
        └── Io.h
```

## 参考链接

- [aws-crt-cpp GitHub](https://github.com/awslabs/aws-crt-cpp)
- [AWS SDK for C++](https://github.com/aws/aws-sdk-cpp)
