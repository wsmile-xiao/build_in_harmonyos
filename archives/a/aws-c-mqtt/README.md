# AWS C MQTT — OpenHarmony 编译档案

## 软件简介
aws-c-mqtt 提供 MQTT 客户端库，支持 MQTT 3.1.1 和 MQTT 5 协议。

## 功能概述
- MQTT 3.1.1 完整支持
- MQTT 5 支持（v0.15.0+ 完整）
- QoS 0/1/2 消息
- 共享订阅、主题别名、流控制

## OHOS 适配要点
- CMake 标准构建，推荐 v0.15.2

## 依赖关系
- 编译依赖: aws-c-common, aws-c-io, aws-c-http
- 被依赖: aws-crt-cpp, AWS IoT SDK

## 版本差异
| 版本 | MQTT5 支持 |
|------|-----------|
| 0.14.0 | 部分 |
| 0.15.2 | 完整 |

## 参考资料
- [aws-c-mqtt GitHub](https://github.com/awslabs/aws-c-mqtt)
