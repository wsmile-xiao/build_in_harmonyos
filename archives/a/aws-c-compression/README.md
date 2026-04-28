# AWS C Compression — OpenHarmony 编译档案

## 软件简介

aws-c-compression 是 AWS C SDK 中的压缩库，提供 Huffman 编码/解码功能。主要用于 HTTP/2 HPACK 头部压缩，是 aws-c-http 的编译依赖。

## 功能概述

- Huffman 编码表构建
- Huffman 编码（符号→比特流）
- Huffman 解码（比特流→符号）
- 流式处理支持

## OHOS 适配要点

- CMake 标准构建，无特殊平台适配需求
- 需先编译安装 aws-c-common
- 使用 `-DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF` 编译静态库

## 依赖关系

- 编译依赖: aws-c-common
- 被依赖: aws-c-http（HTTP/2 HPACK）、aws-c-s3

## 参考资料

- [aws-c-compression GitHub](https://github.com/awslabs/aws-c-compression)
