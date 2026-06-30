# postgresql-hll

PostgreSQL extension adding HyperLogLog data structures as a native data type.

## 简介

postgresql-hll 是一个 PostgreSQL 扩展模块，实现了 HyperLogLog（HLL）数据结构，用于高效地进行基数估计（distinct value counting）。HLL 是一种固定大小的、类似集合的结构，可以在可调节的精度下估计数十亿个不同值的数量。

例如，在 1280 字节的空间内，HLL 可以估计数十亿个不同值的数量，误差仅为几个百分点。

## 主要特性

- **固定大小**: HLL 数据结构占用固定内存空间（默认 1280 字节）
- **高精度**: 可调节精度参数（log2m, regwidth）
- **快速插入**: 每秒可处理 200k-300k 次插入（EMPTY/EXPLICIT/SPARSE 模式），数百万次（FULL 模式）
- **可合并**: 支持多个 HLL 对象的合并操作
- **类型转换**: 支持 HLL 与文本之间的转换

## 算法层次

postgresql-hll 实现了四个层次的算法：

1. **EMPTY**: 表示空集的常量值
2. **EXPLICIT**: 显式存储唯一整数的有序列表（精确计数）
3. **SPARSE**: 基于 map 的 HyperLogLog 实现（仅存储非零寄存器）
4. **FULL**: 完全物化的列表式 HyperLogLog 实现

算法会根据基数自动从低层次升级到高层次。

## OHOS 编译状态

| 版本 | 状态 | 编译日期 | 构建系统 |
|------|------|----------|----------|
| 2.19 | built | 2026-06-09 | PGXS |

## 编译依赖

- PostgreSQL 16.4（构建依赖，需要 pg_config 和 PGXS）
- clang/clang++ (OpenHarmony NDK)
- libc.so（运行时依赖）

## 安装说明

### 方法1：使用预编译包（推荐）

```bash
# 下载预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- postgresql-hll 2.19

# 安装到 PostgreSQL
psql -c "CREATE EXTENSION hll;"
```

### 方法2：从源码编译

**前置条件**:
- PostgreSQL 16.4 已编译并安装（提供 pg_config）
- clang 编译器可用

```bash
# 下载源码
curl -kL https://github.com/citusdata/postgresql-hll/archive/refs/tags/v2.19.tar.gz -o postgresql-hll-2.19.tar.gz
tar xzf postgresql-hll-2.19.tar.gz
cd postgresql-hll-2.19

# 编译
export PATH=$HOME/usr/local/bin:$PATH  # 确保 pg_config 在 PATH 中
export SQLPP=clang-cpp  # 使用 clang 预处理器
make USE_PGXS=1

# 安装
make install USE_PGXS=1

# 在 PostgreSQL 中创建扩展
psql -c "CREATE EXTENSION hll;"
```

## 使用示例

### 基本用法

```sql
-- 创建空 HLL
SELECT hll_empty();

-- 添加哈希值
SELECT hll_add(hll_empty(), hll_hash_integer(12345));
SELECT hll_add(hll_empty(), hll_hash_text('hello world'));

-- 计算基数
SELECT hll_cardinality(hll_add(hll_empty(), hll_hash_integer(12345)));
```

### 实际应用：统计每日独立用户

```sql
-- 创建聚合表
CREATE TABLE daily_uniques (
  date            date UNIQUE,
  users           hll
);

-- 添加数据
INSERT INTO daily_uniques (date, users)
SELECT date, hll_agg(hll_hash_integer(user_id))
FROM facts
GROUP BY date;

-- 查询某日的独立用户数
SELECT date, hll_cardinality(users) FROM daily_uniques;

-- 合并多日的数据
SELECT hll_cardinality(hll_union_agg(users))
FROM daily_uniques
WHERE date BETWEEN '2024-01-01' AND '2024-01-31';
```

## OHOS 特殊说明

### 编译注意事项

1. **PGXS 构建系统**: postgresql-hll 使用 PGXS（PostgreSQL Extension Building Infrastructure）而非标准 autotools
2. **pg_config 依赖**: 必须先编译 PostgreSQL 16.4 以获取 pg_config 和 PGXS 构建文件
3. **预处理器**: 需要设置 `SQLPP=clang-cpp` 以处理 SQL 文件中的预处理器指令
4. **HMDFS 限制**: PostgreSQL make install 在 HMDFS 文件系统上会遇到硬链接权限问题，需手动复制关键文件

### 运行时要求

- PostgreSQL 服务器必须运行（扩展需加载到服务器进程）
- 建议与 PostgreSQL 16.4 配合使用

## 技术细节

- **License**: Apache-2.0
- **源码 URL**: https://github.com/citusdata/postgresql-hll
- **编译器**: clang (OpenHarmony NDK)
- **产物大小**: hll.so ~100KB, SQL 脚本 10 个

## 参考文档

- [HyperLogLog 论文](http://algo.inria.fr/flajolet/Publications/FlFuGaMe07.pdf)
- [postgresql-hll GitHub](https://github.com/citusdata/postgresql-hll)
- [PostgreSQL 扩展开发文档](https://www.postgresql.org/docs/current/extend.html)

---

**维护者**: OpenHarmonyPCDeveloper 团队
**编译归档**: archives/p/postgresql-hll/2.19/