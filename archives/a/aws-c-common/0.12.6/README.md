# aws-c-common 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS C Common Library |
| 版本 | 0.12.6 |
| 官网 | https://github.com/awslabs/aws-c-common |
| 源码下载 | https://github.com/awslabs/aws-c-common/archive/refs/tags/v0.12.6.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
curl -L -o aws-c-common-0.12.6.tar.gz "https://github.com/awslabs/aws-c-common/archive/refs/tags/v0.12.6.tar.gz"
tar -xzf aws-c-common-0.12.6.tar.gz
cd aws-c-common-0.12.6
```

### 2. 配置

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_TESTING=OFF
```

### 3. 编译

```bash
cmake --build build -j$(nproc)
```

### 4. 安装

```bash
DESTDIR=$HOME/tmp/aws-c-common cmake --install build
```

## 功能说明

aws-c-common 是 AWS SDK for C 的核心基础库，提供：
- 跨平台抽象层（内存、字符串、列表、哈希表）
- 错误处理机制
- 日志系统
- 内存管理（aws_allocator）
- UTF-8 字符串处理
- 线程抽象

## 依赖关系

### 编译依赖
- CMake 3.9+

### 被依赖（核心依赖库）
- aws-c-cal
- aws-c-io
- aws-c-compression
- aws-c-http
- aws-c-auth
- aws-c-mqtt
- aws-c-s3
- aws-crt-cpp
- 所有 AWS SDK for C 组件

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libaws-c-common.a
│   └── cmake/aws-c-common/
└── include/
    └── aws/common/
        ├── allocator.h
        ├── array_list.h
        ├── byte_buf.h
        ├── error.h
        ├── hash_table.h
        ├── string.h
        └── thread.h
```

## 参考链接

- [aws-c-common GitHub](https://github.com/awslabs/aws-c-common)
