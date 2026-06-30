# pg_roaringbitmap

> Roaring bitmap extension for PostgreSQL — efficient compressed bitmap operations

## 简介

pg_roaringbitmap 是一个 PostgreSQL 扩展，提供了 Roaring Bitmap 数据类型和操作函数。Roaring Bitmap 是一种压缩的位图数据结构，在空间效率和计算速度之间取得了很好的平衡，特别适合大数据集合运算场景。

pg_roaringbitmap 支持位图的交集、并集、差集、异或等集合操作，以及基数统计（count）、包含检测等查询操作。它广泛应用于用户标签管理、广告投放筛选、实时分析等需要高效集合运算的场景。

该扩展由 ChenHuajun 开发，基于 CRoaring（Roaring Bitmap 的 C 实现），编译为 PostgreSQL 扩展后提供 `roaringbitmap` 数据类型。

## OHOS 适配要点

- PGXS 扩展使用 `make USE_PGXS=1` 编译 [E200]
- 内嵌 CRoaring 库，编译时无需额外安装 roaring bitmap 依赖

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| PostgreSQL | 17.10 | 核心数据库 |

## 功能验证

```sql
CREATE EXTENSION pg_roaringbitmap;

-- 创建 roaringbitmap 并计算基数
SELECT roaringbitmap('{1,2,3,100,1000}') & rb_cardinality();
```

## 参考

- [pg_roaringbitmap GitHub](https://github.com/ChenHuajun/pg_roaringbitmap)
- [Roaring Bitmap spec](https://roaringbitmap.org/)