# Serf (Apache Serf)

Apache Serf 是一个基于 Apache Portable Runtime（APR）的高性能 C 语言 HTTP 客户端库，是 Subversion 等软件的底层依赖。

## 版本信息
- 当前版本: 1.3.10
- 上游仓库: https://github.com/apache/serf
- 官网: https://serf.apache.org/

## 描述

主要功能：
- 基于 APR 的异步 HTTP 客户端
- SSL/TLS 支持（OpenSSL）
- 压缩传输（zlib）
- 连接复用与请求流水线

## 编译状态
- 鸿蒙难度: 🟡 (中等，SCons 构建)
- 构建系统: scons
- 编译器: clang

## 依赖
- apr/1.7.6
- apr-util/1.6.3
- zlib/1.3.1
- openssl/3.5.6

## 使用方式
```bash
# 链接 serf
gcc myapp.c -I/path/to/include/serf-1 -L/path/to/lib -lserf-1
```
