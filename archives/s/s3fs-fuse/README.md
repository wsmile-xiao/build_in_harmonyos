# s3fs-fuse

## 简介
s3fs-fuse 是一个基于 FUSE 的文件系统，允许将 Amazon S3 或兼容的对象存储桶挂载为本地文件系统，提供 POSIX 文件系统接口。

## 功能概述
- 将 S3 桶挂载为本地目录
- 支持标准文件操作（读、写、删除、重命名）
- 兼容多种 S3 存储服务（AWS S3、阿里云 OSS、MinIO 等）
- 支持多线程并发上传
- 支持 CDN 集成

## OHOS 适配要点

### 已解决问题
1. **pthread_cancel 缺失**：鸿蒙 musl 未实现 pthread_cancel，通过 stub 函数解决
2. **configure 脚本生成**：GitHub archive 无预生成 configure，需要 autoreconf -iv
3. **HMDFS 临时目录限制**：config.status 在 HMDFS 上创建临时目录受限，需修改 TMPDIR
4. **FUSE 静态链接**：必须静态链接 libfuse.a 以避免动态库的 pthread 问题

### 使用限制
- 需要 FUSE 内核支持（/dev/fuse 设备）
- 需要 root 权限进行挂载
- 需要用户自行配置 S3 访问凭证（~/.passwd-s3fs 或环境变量）

## 依赖关系

### 编译依赖
- **fuse** 2.9.9：FUSE 库（必须静态链接）
- **libcurl**：HTTP 客户端库（系统预装）
- **libxml2**：XML 解析库（系统预装）
- **openssl**：SSL/TLS 库（已编译）
- **pkg-config** 0.29.2：依赖检测工具

### 运行依赖
- FUSE 内核模块支持
- fusermount 工具（通常来自 fuse 包）

## 参考资料
- **官网**：https://github.com/s3fs-fuse/s3fs-fuse
- **文档**：https://github.com/s3fs-fuse/s3fs-fuse/wiki
- **源码**：https://github.com/s3fs-fuse/s3fs-fuse