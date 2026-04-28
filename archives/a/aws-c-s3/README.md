# AWS C S3 — OpenHarmony 编译档案

## 软件简介
aws-c-s3 提供 Amazon S3 API 客户端库，支持对象操作、分片上传和 S3 Select。

## 功能概述
- S3 对象操作（PUT/GET/DELETE）
- 分片上传（multipart upload）
- S3 Select（SQL 查询）
- 元数据管理

## OHOS 适配要点
- CMake 标准构建，无特殊适配需求

## 依赖关系
- 编译依赖: aws-c-common, aws-c-io, aws-c-http, aws-c-auth, aws-c-event-stream, aws-checksums
- 被依赖: aws-crt-cpp, AWS SDK for C++

## 参考资料
- [aws-c-s3 GitHub](https://github.com/awslabs/aws-c-s3)
