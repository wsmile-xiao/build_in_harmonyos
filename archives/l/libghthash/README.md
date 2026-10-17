# libghthash

[![License](https://img.shields.io/badge/license-LGPL--2.0--or--later-blue.svg)](https://github.com/SimonKagstrom/libghthash)

**libghthash** (Generic Hash Table) is a generic, extensible hash table library
for C, by Simon Kågström. It can store arbitrary data and supports pluggable
hash functions and access-order heuristics (move-to-front / transpose).

## 描述

libghthash 提供一个通用、可扩展的 C 哈希表实现，支持：

- 任意类型 key/value 存储（key 由指针 + 大小描述）
- 可插拔哈希函数（`ght_one_at_a_time_hash` / `ght_rotating_hash` / `ght_crc_hash`）
- 访问顺序启发式（`GHT_HEURISTICS_MOVE_TO_FRONT` / `GHT_HEURISTICS_TRANSPOSE`）
- 自动 rehash 与有界 bucket（bounded buckets）
- 迭代器遍历（`ght_first` / `ght_next`）

## 已编译版本

- 0.6.2 (2026-08-24)

## 依赖

- 无外部依赖（仅依赖标准 C 头文件：stdlib.h / stdio.h / errno.h / string.h / assert.h）

## 构建说明

上游 0.6.2 tarball 附带旧式 autotools（`configure.in` 使用已弃用的
`AM_INIT_AUTOMAKE` / `AM_PROG_LIBTOOL`）。CI 环境的 automake 1.17 因
`Automake::Config.pm` 缺失无法运行 `autoreconf`，因此 Conan 配方不使用
autotools，而是直接用 OHOS clang 工具链编译两个 C 源文件，并通过对
`ght_hash_table.h.in` 做 `@INT32_T@ → int` 替换生成公共头文件
（`int` 在 aarch64 上为 4 字节，与 configure 的尺寸检测结果一致）。

产物为静态库 `libghthash.a`。

## 使用方法

```c
#include <ght_hash_table.h>

ght_hash_table_t *p_table = ght_create(128);
int *p_val = malloc(sizeof(int));
*p_val = 42;
ght_insert(p_table, p_val, strlen("key") + 1, "key");

int *p_get = ght_get(p_table, strlen("key") + 1, "key");
/* *p_get == 42 */

ght_finalize(p_table);
```

链接：`-lghthash`

## License

LGPL-2.0-or-later（源码 COPYING 为 GNU Library General Public License v2，
源文件头部声明 "version 2 or any later version"）。
