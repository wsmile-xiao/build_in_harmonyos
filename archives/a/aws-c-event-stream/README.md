# AWS C Event Stream — OpenHarmony 编译档案

## 软件简介

aws-c-event-stream 提供 AWS event-stream 协议的编解码支持，用于二进制消息分帧和 CRC 校验。主要服务于 S3 Select、Kinesis、DynamoDB Streams 等 AWS 服务。

## 功能概述

- 二进制编码/解码
- 消息分帧
- CRC 校验
- 流式处理

## OHOS 适配要点

- CMake 标准构建，无特殊平台适配需求
- 依赖链较深：aws-c-common → aws-c-io → aws-c-http → aws-checksums
- 使用 `-DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF` 编译静态库

## 依赖关系

- 编译依赖: aws-c-common, aws-c-io, aws-c-http, aws-checksums
- 被依赖: aws-c-s3（S3 Select）

## 参考资料

- [aws-c-event-stream GitHub](https://github.com/awslabs/aws-c-event-stream)
