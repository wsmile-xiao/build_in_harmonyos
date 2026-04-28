# AWS C IO — OpenHarmony 编译档案

## 软件简介
aws-c-io 处理所有 IO 和 TLS 工作，提供事件循环、Socket 通道和异步 IO 操作。是 AWS C SDK 的 IO 基础层。

## 功能概述
- 事件循环（基于 Linux epoll）
- Socket 通道（TCP/UDP）
- TLS 通道（BYO_CRYPTO 模式）
- 异步 IO 操作

## OHOS 适配要点
- **关键**: 使用 `-DBYO_CRYPTO=ON` 禁用 s2n TLS 依赖
- CMake 不识别 HarmonyOS，使用 `-DCMAKE_SYSTEM_NAME=Linux`

## 依赖关系
- 编译依赖: aws-c-common, aws-c-cal, aws-c-compression
- 被依赖: aws-c-http, aws-c-mqtt, aws-c-s3, aws-crt-cpp

## 参考资料
- [aws-c-io GitHub](https://github.com/awslabs/aws-c-io)
