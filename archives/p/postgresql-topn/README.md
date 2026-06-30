# postgresql-topn

## 软件描述

postgresql-topn 是一个开源的 PostgreSQL 扩展，用于高效返回数据库中根据某些条件排名的 Top-N 值。

### 主要特性

- **近似算法**: 使用近似算法快速计算 Top-N，消耗较少的计算和内存资源
- **实时分析**: 适用于实时仪表板和亚秒级响应的分析查询
- **增量更新**: 支持增量更新 Top 值和跨时间间隔合并
- **JSONB 类型**: 使用 PostgreSQL 的 JSONB 类型存储频繁项及其频率

### 典型应用场景

- 客户仪表板实时展示
- 分析查询的亚秒级响应
- 按维度排名事件、用户或产品
- 处理 TB 数据的实时分析

## 编译版本

### 当前版本

- **版本**: 2.7.0
- **状态**: built
- **日期**: 2026-06-03

### 编译信息

- **构建系统**: Makefile (PGXS)
- **依赖**: PostgreSQL 17.0
- **编译器**: clang
- **平台**: OpenHarmony aarch64

### 可用版本

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 2.7.0 | built | 2026-06-03 | 最新稳定版 |

## 使用方法

### 安装预编译包

```bash
# 通过 cmd-pkgs 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- postgresql-topn 2.7.0

# 或直接解压预编译包
tar -xzf postgresql-topn-2.7.0-ohos-aarch64.tar.gz -C ~/usr/local
```

### PostgreSQL 中加载扩展

```sql
-- 连接到 PostgreSQL
psql -U postgres

-- 创建扩展
CREATE EXTENSION topn;

-- 验证安装
SELECT * FROM pg_extension WHERE extname = 'topn';
```

### 示例用法

```sql
-- 创建聚合表捕获最流行的产品
CREATE TABLE popular_products
(
  review_date date UNIQUE,
  agg_data jsonb
);

-- 物化每天的 Top 产品
INSERT INTO popular_products
    SELECT review_date, topn_add_agg(product_id)
    FROM customer_reviews
    GROUP BY review_date;

-- 查询某天的 Top 10 产品
SELECT (topn(agg_data, 10)).*
FROM popular_products
WHERE review_date = '2000-01-15';

-- 合并多天的 Top 产品
SELECT (topn(topn_union_agg(agg_data), 10)).*
FROM popular_products
WHERE review_date >= '2000-01-01' AND review_date < '2000-02-01';
```

## 兼容性

- PostgreSQL 版本: 9.6, 10, 11, 12, 13, 14, 15, 16, 17
- Citus 版本: 所有支持的版本 (6.x, 7.x, 8.x, 9.x)

## 提供的函数

### 聚合函数

- `topn_add_agg(textColumnName)` - 添加聚合
- `topn_union_agg(topnTypeColumn)` - 合并聚合

### 普通函数

- `topn(jsonb, n)` - 获取 Top-N 元素
- `topn_add(jsonb, text)` - 添加元素到 JSONB
- `topn_union(jsonb, jsonb)` - 合并两个 JSONB

### 配置参数

- `topn.number_of_counters` - 设置跟踪的计数器数量（默认 1000）

## 源码信息

- **官方仓库**: https://github.com/citusdata/postgresql-topn
- **下载地址**: https://api.github.com/repos/citusdata/postgresql-topn/tarball/v2.7.0
- **License**: PostgreSQL License (开源)

## 维护者

由 Citus 数据库团队创建和维护（现为 Microsoft 的一部分）