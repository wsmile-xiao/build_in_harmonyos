# libcuckoo

## 简介
libcuckoo 是高性能并发哈希表库，基于 Cuckoo 哈希算法，支持无锁查找和细粒度锁写入。

## OHOS 适配
- Header-only 库，安装只需复制头文件
- CMake 仅用于安装步骤，无需编译

## 依赖
- C++11 或更高版本编译器

## 功能验证
```cpp
#include <libcuckoo/cuckoohash_map.hh>
// 编译测试程序验证头文件可用
```

## 参考
- 主页: https://github.com/efficient/libcuckoo
