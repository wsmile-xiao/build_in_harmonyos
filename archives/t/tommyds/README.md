# TommyDS

TommyDS 是一个 C 语言的高性能数据结构和容器库，提供数组、哈希表、树、trie 等
容器，专为高性能设计，接口易用。

- 官方主页: https://www.tommyds.it
- 上游源码: https://github.com/amadvance/tommyds
- 许可证: BSD-2-Clause

## 功能概述

- `tommy_list` — 双向链表
- `tommy_array` / `tommy_arrayblk` — 线性数组（不碎片化堆内存）
- `tommy_hashtable` — 固定大小链式哈希表
- `tommy_hashdyn` — 动态链式哈希表
- `tommy_hashlin` — 线性链式哈希表（无扩容延迟、不碎片化堆）
- `tommy_trie` / `tommy_trie_inplace` — 针对缓存优化的 trie
- `tommy_hash` — 哈希函数（inthash、inthash_u32、fnv_hash 等）

## OHOS 适配

- 上游无 configure、无 install 目标，仅普通 Makefile；库本质是
  `tommyds/tommy.c`（内联全部实现）+ `tommyds/*.h` 头文件。
- 配方以静态库 `libtommy.a` 交付：`build()` 直接用 Conan Toolchain 编译器
  编译 `tommyds/tommy.c`，`package()` 安装头文件到 `include/tommyds/`。
- 上游 `make check` 自检（tommycheck 程序）可作为测试集。

## 依赖关系

- 编译依赖：无（纯 C，仅依赖 C 标准库）
- 运行依赖：无

## 参考资料

- https://www.tommyds.it
- https://github.com/amadvance/tommyds
