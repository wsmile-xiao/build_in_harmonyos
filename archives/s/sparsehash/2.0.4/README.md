# sparsehash 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | sparsehash (Google Hash Maps) |
| 版本 | 2.0.4 |
| 官网 | https://github.com/sparsehash/sparsehash |
| 源码下载 | https://github.com/sparsehash/sparsehash/archive/refs/tags/sparsehash-2.0.4.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

sparsehash 是 Google 的 C++ 哈希映射库：
- Header-only 库，无需编译
- 提供 sparse_hash_map 和 dense_hash_map
- 内存高效的稀疏哈希表
- 高性能密集哈希表

## 安装步骤

### 1. 下载源码

```bash
curl -L -o sparsehash-2.0.4.tar.gz "https://github.com/sparsehash/sparsehash/archive/refs/tags/sparsehash-2.0.4.tar.gz"
tar -xzf sparsehash-2.0.4.tar.gz
cd sparsehash-sparsehash-2.0.4
```

### 2. 手动安装头文件（推荐）

由于 HMDFS 文件系统限制，autotools 配置可能失败。使用手动安装：

```bash
mkdir -p $HOME/usr/local/include/google
mkdir -p $HOME/usr/local/include/sparsehash

cp -r src/google/* $HOME/usr/local/include/google/
cp -r src/sparsehash/* $HOME/usr/local/include/sparsehash/
```

## 使用方法

### sparse_hash_map（内存高效）

```cpp
#include <google/sparse_hash_map>
#include <string>

using google::sparse_hash_map;

sparse_hash_map<std::string, int> ages;
ages["Alice"] = 25;
ages["Bob"] = 30;

// 可设置 deleted key 支持删除
ages.set_deleted_key("");  // 空字符串作为删除标记
ages.erase("Alice");
```

### dense_hash_map（高性能）

```cpp
#include <google/dense_hash_map>
#include <string>

using google::dense_hash_map;

dense_hash_map<std::string, int> scores;
scores.set_empty_key("");     // 必须设置空键
scores.set_deleted_key("\0"); // 必须设置删除键
scores["Alice"] = 100;
scores.erase("Alice");
```

## 性能对比

| 类型 | 内存使用 | 查找速度 | 适用场景 |
|------|---------|---------|---------|
| sparse_hash_map | 低 | 中等 | 大表、稀疏数据 |
| dense_hash_map | 高 | 快 | 小表、密集数据 |

## 已知限制

HMDFS 文件系统上 autotools 的 config.status 可能失败，需手动安装头文件。

## 编译产物

```
$HOME/usr/local/include/
├── google/
│   ├── sparse_hash_map
│   ├── dense_hash_map
│   ├── sparse_hash_set
│   └── dense_hash_set
└── sparsehash/
    ├── template_util.h
    └── type_traits.h
```

## 参考链接

- [sparsehash GitHub](https://github.com/sparsehash/sparsehash)
- [sparsehash 文档](https://sparsehash.github.io/sparsehash/)
