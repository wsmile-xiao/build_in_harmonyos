# aws-c-mqtt 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS C MQTT Library |
| 版本 | 0.15.2 |
| 官网 | https://github.com/awslabs/aws-c-mqtt |
| 源码下载 | https://github.com/awslabs/aws-c-mqtt/archive/refs/tags/v0.15.2.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

aws-c-mqtt 提供 MQTT5 客户端：
- MQTT5 协议支持（v0.15.0+）
- MQTT3.1.1 支持
- QoS 0/1/2 消息
- 发布确认（Publish Acknowledgement）
- 订阅管理
- 连接池

## 编译步骤

### 1. 下载源码

```bash
curl -L -o aws-c-mqtt-0.15.2.tar.gz "https://github.com/awslabs/aws-c-mqtt/archive/refs/tags/v0.15.2.tar.gz"
tar -xzf aws-c-mqtt-0.15.2.tar.gz
cd aws-c-mqtt-0.15.2
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
DESTDIR=$HOME/tmp/aws-c-mqtt cmake --install build
```

## MQTT5 新功能（v0.15.0+）

| 功能 | API |
|------|-----|
| 发布确认 | `aws_mqtt5_client_acquire_publish_acknowledgement` |
| 共享订阅 | `$share/<group>/<topic>` |
| 主题别名 | 减少带宽 |
| 用户属性 | 键值对元数据 |
| 流控制 | 发布速率限制 |

## 依赖关系

### 编译依赖
- aws-c-common ✅
- aws-c-io ✅
- aws-c-http ✅

### 被依赖
- aws-crt-cpp（C++ MQTT API）
- AWS IoT SDK

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libaws-c-mqtt.a
│   └── cmake/aws-c-mqtt/
└── include/
    └── aws/mqtt/
        ├── mqtt.h
        ├── mqtt5_client.h
        └── mqtt_subscription.h
```

## 参考链接

- [aws-c-mqtt GitHub](https://github.com/awslabs/aws-c-mqtt)
- [MQTT5 规范](https://docs.oasis-open.org/mqtt/mqtt5/v5.0/mqtt5-v5.0.html)
