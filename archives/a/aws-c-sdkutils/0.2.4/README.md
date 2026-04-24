# aws-c-sdkutils 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS C SDK Utilities |
| 版本 | 0.2.4 |
| 官网 | https://github.com/awslabs/aws-c-sdkutils |
| 源码下载 | https://github.com/awslabs/aws-c-sdkutils/archive/refs/tags/v0.2.4.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
curl -L -o aws-c-sdkutils-0.2.4.tar.gz "https://github.com/awslabs/aws-c-sdkutils/archive/refs/tags/v0.2.4.tar.gz"
tar -xzf aws-c-sdkutils-0.2.4.tar.gz
cd aws-c-sdkutils-0.2.4
```

### 2. 配置

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_PREFIX_PATH=$HOME/usr/local \
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
DESTDIR=$HOME/tmp/aws-c-sdkutils cmake --install build
```

## 功能说明

aws-c-sdkutils 提供 AWS SDK 实用工具：
- AWS 端点解析（endpoint resolver）
- SDK 配置管理
- 环境变量解析
- 配置文件解析

## 依赖关系

### 编译依赖
- aws-c-common ✅

### 被依赖
- aws-c-auth（用于区域解析）
- aws-c-s3（端点配置）

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libaws-c-sdkutils.a
│   └── cmake/aws-c-sdkutils/
└── include/
    └── aws/sdkutils/
        ├── endpoint.h
        └── config.h
```

## 参考链接

- [aws-c-sdkutils GitHub](https://github.com/awslabs/aws-c-sdkutils)
