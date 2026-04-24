# xxhash 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | xxHash |
| 版本 | 0.8.3 |
| 官网 | https://xxhash.com/ |
| 源码下载 | https://github.com/Cyan4973/xxHash/archive/refs/tags/v0.8.3.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

xxHash 是超高速非加密哈希算法：
- XXH32: 32位哈希，5.4 GB/s
- XXH64: 64位哈希，11.8 GB/s
- XXH3: 128位哈希，加速 SIMD

## 编译步骤

### 1. 下载源码

```bash
curl -L -o xxhash-0.8.3.tar.gz "https://github.com/Cyan4973/xxHash/archive/refs/tags/v0.8.3.tar.gz"
tar -xzf xxhash-0.8.3.tar.gz
cd xxHash-0.8.3
```

### 2. 编译

```bash
make -j$(nproc)
```

### 3. 安装

```bash
PREFIX=$HOME/usr/local make install
```

### 4. 测试

```bash
make test
# 49,948 sanity tests passed
```

## 使用方法

### 命令行

```bash
# 计算文件哈希
xxhsum file.txt
# 输出: a5c4e6d8  file.txt

# 指定算法
xxhsum -H64 file.txt   # XXH64
xxhsum -H128 file.txt  # XXH3 128位

# 批量校验
xxhsum -c checksums.txt
```

### C API

```c
#include <xxhash.h>

// XXH64
XXH64_hash_t hash = XXH64(data, len, seed);

// XXH3（流式）
XXH3_state_t* state = XXH3_createState();
XXH3_128bits_reset(state);
XXH3_128bits_update(state, data1, len1);
XXH3_128bits_update(state, data2, len2);
XXH128_hash_t hash = XXH3_128bits_digest(state);
XXH3_freeState(state);
```

## 性能

| 算法 | 速度 (GB/s) | 哈希长度 |
|------|------------|---------|
| XXH32 | 5.4 | 32-bit |
| XXH64 | 11.8 | 64-bit |
| XXH3-64 | 12.6 | 64-bit |
| XXH3-128 | 11.8 | 128-bit |

## 编译产物

```
$HOME/usr/local/
├── bin/
│   └── xxhsum          # 命令行工具
├── lib/
│   ├── libxxhash.a     # 静态库
│   └── libxxhash.so    # 共享库
└── include/
    └── xxhash.h        # 头文件
```

## 参考链接

- [xxHash 官网](https://xxhash.com/)
- [xxHash GitHub](https://github.com/Cyan4973/xxHash)