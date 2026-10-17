# stb_ds

stb_ds 是 Sean Barrett 的**单头文件** C/C++ 数据结构库（stb 系列之一），提供：

- 动态数组（arrput/arrlen/arrfree/arrins/arrdel/arrdelswap）
- 哈希表（hmput/hmget/hmgeti/hmdel，支持结构体 key/value、数组 key）
- 字符串哈希映射（shput/shget，支持 strdup/arena 内存模式）
- 排序（hmsort/arrsort）、insthash、sets

## 适配版本

- **0.67**（上游 commit `2c980bb59875b0d32144a71867fbdebb2f77cd20`，2023-04-22）
- 平台: 鸿蒙 PC (OHOS / aarch64)
- 状态: built（本地 W3 验证通过，CI 待发布）

## 特性

- 纯 C/C++ 单头文件，零依赖
- 使用前需在**一个**编译单元中 `#define STB_DS_IMPLEMENTATION` 再 `#include <stb_ds.h>`
- 可选 `STBDS_UNIT_TESTS`（内嵌单元测试）、`STBDS_STATISTICS`（探针统计）等宏

## 使用

```c
#define STB_DS_IMPLEMENTATION
#include <stb_ds.h>

/* 动态数组 */
int *arr = NULL;
arrput(arr, 1);
arrlen(arr) == 1;

/* 哈希表 */
struct { int key, value; } *map = NULL;
hmput(map, 42, 7);
hmget(map, 42) == 7;

/* 字符串映射 */
struct { char *key; int value; } *smap = NULL;
shput(smap, "hello", 1);
shget(smap, "hello") == 1;
```

## 参考

- 上游: https://github.com/nothings/stb （`stb_ds.h`）
- 文档: stb_ds.h 头部注释（API 全表 + 说明）
