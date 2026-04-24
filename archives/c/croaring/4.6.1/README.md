# croaring 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | CRoaring (Roaring Bitmaps in C) |
| 版本 | 4.6.1 |
| 官网 | https://roaringbitmap.org/ |
| 源码下载 | https://github.com/RoaringBitmap/CRoaring/archive/refs/tags/v4.6.1.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

CRoaring 是 C 语言实现的 Roaring Bitmaps：
- 压缩位图（bitset）库
- SIMD 优化（AVX2, AVX-512, NEON）
- 快速集合操作：交集、并集、差集
- 内存高效，适合稀疏数据

## 编译步骤

### 1. 下载源码

```bash
curl -L -o croaring-4.6.1.tar.gz "https://github.com/RoaringBitmap/CRoaring/archive/refs/tags/v4.6.1.tar.gz"
tar -xzf croaring-4.6.1.tar.gz
cd CRoaring-4.6.1
```

### 2. 配置

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_ROARING_TESTS=OFF
```

### 3. 编译

```bash
cmake --build build -j$(nproc)
```

### 4. 安装

```bash
DESTDIR=$HOME/tmp/croaring cmake --install build
```

## 使用方法

```c
#include <roaring/roaring.h>

// 创建位图
roaring_bitmap_t *r1 = roaring_bitmap_create();
roaring_bitmap_add(r1, 100);
roaring_bitmap_add(r1, 200);

// 批量添加
roaring_bitmap_add_many(r1, 3, (uint32_t[]){300, 400, 500});

// 集合操作
roaring_bitmap_t *r2 = roaring_bitmap_create();
roaring_bitmap_add(r2, 200);
roaring_bitmap_add(r2, 300);

roaring_bitmap_t *intersection = roaring_bitmap_and(r1, r2);
roaring_bitmap_t *union_result = roaring_bitmap_or(r1, r2);

// 查询
bool contains = roaring_bitmap_contains(r1, 100);  // true
uint64_t count = roaring_bitmap_get_cardinality(r1);

// 清理
roaring_bitmap_free(r1);
roaring_bitmap_free(r2);
```

## 性能

- ARM NEON SIMD 加速
- 比 std::set 和 std::unordered_set 快 5-10x
- 内存占用比 std::bitset 小 10-100x

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libroaring.a
│   └── cmake/roaring/
└── include/
    └── roaring/
        ├── roaring.h
        ├── roaring_array.h
        └── roaring_bitmap.h
```

## 参考链接

- [Roaring Bitmaps 官网](https://roaringbitmap.org/)
- [CRoaring GitHub](https://github.com/RoaringBitmap/CRoaring)
