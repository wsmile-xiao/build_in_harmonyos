# aws-c-mqtt 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS C MQTT Library |
| 版本 | 0.11.0 |
| 官网 | https://github.com/awslabs/aws-c-mqtt |
| 源码下载 | https://github.com/awslabs/aws-c-mqtt/archive/refs/tags/v0.11.0.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

aws-c-mqtt 0.11.0 提供 MQTT3.1.1 客户端：
- MQTT3.1.1 完整支持
- MQTT5 基础功能（不完整）
- QoS 0/1/2 消息

**注意**: 建议使用 0.15.2 版本以获得完整 MQTT5 支持。

## 编译步骤

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF

cmake --build build -j$(nproc)
DESTDIR=$HOME/tmp/aws-c-mqtt cmake --install build
```

## 参考链接

- [aws-c-mqtt GitHub](https://github.com/awslabs/aws-c-mqtt)