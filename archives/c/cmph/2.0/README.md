# cmph 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | CMPH (C Minimal Perfect Hashing Library) |
| 版本 | 2.0 |
| 官网 | https://cmph.sourceforge.net/ |
| 源码下载 | https://github.com/zvelo/cmph/archive/refs/tags/v2.0.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

CMPH 提供最小完美哈希函数生成：
- 无碰撞哈希表（完美哈希）
- O(1) 查找时间
- 内存高效
- 支持多种算法

### 支持的算法

| 算法 | 特点 |
|------|------|
| CHD | 最通用，空间效率高 |
| CHM | 简单，经典算法 |
| BMZ | 快速生成 |
| BMZ8 | 8位键优化 |
| FCH | 稀疏数据 |
| BRZ | 外部存储支持 |

## 编译步骤

### 1. 下载源码

```bash
curl -L -o cmph-2.0.tar.gz "https://github.com/zvelo/cmph/archive/refs/tags/v2.0.tar.gz"
tar -xzf cmph-2.0.tar.gz
cd cmph-2.0
```

### 2. 配置

```bash
./configure --prefix=$HOME/usr/local
```

### 3. 编译

```bash
make -j$(nproc)
```

### 4. 安装

```bash
make install
```

## 使用方法

### 命令行工具

```bash
# 创建完美哈希
cmph -g keys.txt

# 查找
cmph -m keys.mph -k "key1"
```

### C API

```c
#include <cmph.h>

// 创建哈希函数
cmph_t *hash = cmph_new(keys, nkeys);
unsigned int id = cmph_search(hash, "key", strlen("key"));
cmph_destroy(hash);
```

## 已知限制

HMDFS 文件系统上 autotools config.status 可能失败，需手动处理。

## 编译产物

```
$HOME/usr/local/
├── bin/
│   └── cmph          # 命令行工具
├── lib/
│   ├── libcmph.a     # 静态库
│   └── libcmph.so    # 共享库
└── include/
    └── cmph.h        # 头文件
```

## 参考链接

- [CMPH 官网](https://cmph.sourceforge.net/)
- [CMPH GitHub](https://github.com/zvelo/cmph)
