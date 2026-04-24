# aws-c-compression 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS C Compression Library |
| 版本 | 0.3.2 |
| 官网 | https://github.com/awslabs/aws-c-compression |
| 源码下载 | https://github.com/awslabs/aws-c-compression/archive/refs/tags/v0.3.2.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
curl -L -o aws-c-compression-0.3.2.tar.gz "https://github.com/awslabs/aws-c-compression/archive/refs/tags/v0.3.2.tar.gz"
tar -xzf aws-c-compression-0.3.2.tar.gz
cd aws-c-compression-0.3.2
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
DESTDIR=$HOME/tmp/aws-c-compression cmake --install build
```

### 5. 测试

```bash
# 启用测试重新配置
cmake -B build -DBUILD_TESTING=ON
ctest --test-dir build
```

## 功能说明

aws-c-compression 提供 Huffman 编码/解码功能：
- Huffman 编码表构建
- Huffman 编码（符号→比特流）
- Huffman 解码（比特流→符号）
- 流式处理支持

## 依赖关系

### 编译依赖
- aws-c-common ✅

### 被依赖
- aws-c-http（HTTP/2 压缩）
- aws-c-s3

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libaws-c-compression.a
│   └── cmake/aws-c-compression/
└── include/
    └── aws/compression/
        ├── huffman.h
        └── huffman_encoding.h
```

## 参考链接

- [aws-c-compression GitHub](https://github.com/awslabs/aws-c-compression)
