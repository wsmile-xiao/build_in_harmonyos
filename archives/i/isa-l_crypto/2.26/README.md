# isa-l_crypto 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | ISA-L Crypto (Intel Storage Acceleration Library) |
| 版本 | 2.26 |
| 官网 | https://github.com/intel/isa-l_crypto |
| 源码下载 | https://github.com/intel/isa-l_crypto/archive/refs/tags/v2.26.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

ISA-L Crypto 提供 Intel 存储加密加速：
- 多缓冲区加密（Multi-buffer encryption）
- AES-GCM/XCBC/XTS
- SHA256/MD5 多缓冲区哈希
- SIMD 优化（SSE, AVX, AVX2, AVX512）

注意：ARM 平台主要使用 C 实现，SIMD 加速有限。

## 编译步骤

### 1. 下载源码

```bash
curl -L -o isa-l_crypto-2.26.tar.gz "https://github.com/intel/isa-l_crypto/archive/refs/tags/v2.26.tar.gz"
tar -xzf isa-l_crypto-2.26.tar.gz
cd isa-l_crypto-2.26
```

### 2. 配置

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF
```

### 3. 编译

```bash
cmake --build build -j$(nproc)
```

### 4. 安装

```bash
DESTDIR=$HOME/tmp/isa-l_crypto cmake --install build
```

## 使用方法

### AES-GCM 加密

```c
#include <isa-l_crypto.h>

// 多缓冲区 AES-GCM
uint8_t *keys[8];
uint8_t *plaintexts[8];
uint8_t *ciphertexts[8];
uint8_t *ivs[8];

// 批量加密（高性能）
aes_gcm_enc_multi(keys, ivs, plaintexts, ciphertexts, lengths, 8);
```

### SHA256 多缓冲区

```c
#include <sha256_mb.h>

SHA256_HASH_CTX ctx[8];
sha256_ctx_mgr_init(&mgr);

// 批量哈希计算
sha256_submit(&mgr, &ctx[0], data0, len0);
sha256_submit(&mgr, &ctx[1], data1, len1);
```

## 性能特点

| 功能 | x86 SIMD | ARM |
|------|---------|-----|
| AES-GCM | AVX/AVX2 | NEON (部分) |
| SHA256 | AVX | C 实现 |
| MD5 | SSE | C 实现 |

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libisa-l_crypto.a
│   └── cmake/isa-l_crypto/
└── include/
    └── isa-l_crypto.h
```

## 参考链接

- [ISA-L Crypto GitHub](https://github.com/intel/isa-l_crypto)
- [ISA-L 文档](https://intel.github.io/isa-l_crypto/)
