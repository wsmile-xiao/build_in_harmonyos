# libcuckoo 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | libcuckoo (Cuckoo Hashing Map) |
| 版本 | 0.3.1 |
| 官网 | https://github.com/efficient/libcuckoo |
| 源码下载 | https://github.com/efficient/libcuckoo/archive/refs/tags/v0.3.1.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

libcuckoo 是高性能并发哈希表：
- Header-only 库，无需编译
- 基于 Cuckoo 哈希算法
- 支持多线程并发操作
- O(1) 查找、插入、删除

## 安装步骤

### 1. 下载源码

```bash
curl -L -o libcuckoo-0.3.1.tar.gz "https://github.com/efficient/libcuckoo/archive/refs/tags/v0.3.1.tar.gz"
tar -xzf libcuckoo-0.3.1.tar.gz
cd libcuckoo-0.3.1
```

### 2. 安装头文件

```bash
mkdir -p $HOME/usr/local/include
cp -r libcuckoo/libcuckoo.h $HOME/usr/local/include/
```

## 使用方法

```cpp
#include <libcuckoo/cuckoohash_map.hh>
#include <string>

// 并发哈希表
cuckoohash_map<std::string, int> map;

// 锁粒度操作
map.insert("Alice", 25);
map.update("Alice", 26);

// 快速查找
int value;
if (map.find("Alice", value)) {
    std::cout << value << std::endl;
}

// 删除
map.erase("Alice");

// 批量操作（快照）
auto snapshot = map.snapshot_table();
for (auto &item : snapshot) {
    std::cout << item.first << ": " << item.second << std::endl;
}
```

## 并发特性

- 无锁查找（lock-free read）
- 细粒度锁写入
- 支持多线程高并发
- 线程安全的迭代器

## 性能

- 单线程查找：~100ns
- 多线程并发：线性扩展
- 负载因子：~95%

## 编译产物

```
$HOME/usr/local/include/
└── libcuckoo.h   # Header-only
```

## 参考链接

- [libcuckoo GitHub](https://github.com/efficient/libcuckoo)
- [Cuckoo Hashing 论文](https://www.cs.princeton.edu/research/techreps/TR-032-00)
