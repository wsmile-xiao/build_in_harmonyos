# robin-map 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | robin-map (Tessil's Hash Map) |
| 版本 | 1.4.1 |
| 官网 | https://github.com/Tessil/robin-map |
| 源码下载 | https://github.com/Tessil/robin-map/archive/refs/tags/v1.4.1.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

robin-map 是 C++ 快速哈希映射实现：
- Header-only 库，无需编译二进制
- 基于 Robin Hood 哈希算法
- 低内存占用
- 快速查找性能

## 安装步骤

### 1. 下载源码

```bash
curl -L -o robin-map-1.4.1.tar.gz "https://github.com/Tessil/robin-map/archive/refs/tags/v1.4.1.tar.gz"
tar -xzf robin-map-1.4.1.tar.gz
cd robin-map-1.4.1
```

### 2. 安装头文件

```bash
mkdir -p $HOME/usr/local/include/tsl
cp include/tsl/robin_map.h $HOME/usr/local/include/tsl/
cp include/tsl/robin_set.h $HOME/usr/local/include/tsl/
```

## 使用方法

```cpp
#include <tsl/robin_map.h>
#include <string>

// 哈希映射
tsl::robin_map<std::string, int> map;
map["Alice"] = 25;
map["Bob"] = 30;

auto it = map.find("Alice");
if (it != map.end()) {
    std::cout << it.value() << std::endl;  // 25
}

// 哈希集合
tsl::robin_set<std::string> set;
set.insert("Alice");
set.insert("Bob");
bool has = set.contains("Alice");  // true
```

## 性能特点

- 比 std::unordered_map 快 2-5x
- 内存占用更小
- 负载因子可达 0.9
- Robin Hood 哈希减少查找跳转

## 编译产物

```
$HOME/usr/local/include/tsl/
├── robin_map.h   # 哈希映射
├── robin_set.h   # 哈希集合
└── robin_hash.h  # 内部实现（可选）
```

## 参考链接

- [robin-map GitHub](https://github.com/Tessil/robin-map)
