# AWS C HTTP — OpenHarmony 编译档案

## 软件简介

aws-c-http 提供 HTTP/1.1 和 HTTP/2 客户端库，支持连接池、HPACK 压缩、流式处理和 WebSocket。是 AWS C SDK 的核心网络层。

## 功能概述

- HTTP/1.1 连接管理
- HTTP/2 多路复用（HPACK 压缩）
- 请求/响应流式处理
- 连接池
- WebSocket 支持

## OHOS 适配要点

- CMake 标准构建，无特殊平台适配需求
- 需先编译 aws-c-common, aws-c-io, aws-c-compression
- 使用 `-DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF`

## 依赖关系

- 编译依赖: aws-c-common, aws-c-io, aws-c-compression
- 被依赖: aws-c-auth, aws-c-s3, aws-c-event-stream

## 参考资料

- [aws-c-http GitHub](https://github.com/awslabs/aws-c-http)
