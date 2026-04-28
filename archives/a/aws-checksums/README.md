# AWS Checksums — OpenHarmony 编译档案

## 软件简介
aws-checksums 提供高效校验和计算库，支持 CRC32/CRC32C（SIMD 优化）、CRC64、MD5 和 SHA 系列。

## 功能概述
- CRC32/CRC32C（NEON 加速）
- CRC64（S3 用）
- MD5, SHA-1/SHA-256

## 依赖关系
- 编译依赖: aws-c-common
- 被依赖: aws-c-s3, aws-c-event-stream

## 参考资料
- [aws-checksums GitHub](https://github.com/awslabs/aws-checksums)
