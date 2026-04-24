# aws-checksums 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | AWS Checksums Library |
| 版本 | 0.2.10 |
| 官网 | https://github.com/awslabs/aws-checksums |
| 源码下载 | https://github.com/awslabs/aws-checksums/archive/refs/tags/v0.2.10.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
curl -L -o aws-checksums-0.2.10.tar.gz "https://github.com/awslabs/aws-checksums/archive/refs/tags/v0.2.10.tar.gz"
tar -xzf aws-checksums-0.2.10.tar.gz
cd aws-checksums-0.2.10
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
DESTDIR=$HOME/tmp/aws-checksums cmake --install build
```

## 功能说明

aws-checksums 提供高效校验和计算：
- CRC32/CRC32C（SIMD 优化）
- CRC64（用于 S3）
- MD5
- SHA-1/SHA-256

支持硬件加速：
- x86: SSE4.2 CRC32, AVX512
- ARM: NEON CRC32 (ARMv8)

## 依赖关系

### 编译依赖
- aws-c-common ✅

### 被依赖
- aws-c-s3（CRC64 校验）
- aws-c-event-stream

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libaws-checksums.a
│   └── cmake/aws-checksums/
└── include/
    └── aws/checksums/
        ├── crc.h
        └── crc32.h
```

## 参考链接

- [aws-checksums GitHub](https://github.com/awslabs/aws-checksums)
