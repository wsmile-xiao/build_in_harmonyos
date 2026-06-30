# E103: PostgreSQL 扩展 PGXS 构建系统

## 错误场景

编译 PostgreSQL 扩展时，G0 干净构建验证尝试运行 configure，但扩展项目没有 configure 脚本。

**典型日志**：
```
ℹ️ G0: 运行 configure...
❌ G0: configure 失败 (exit 127)
No rule to make target 'configure'. Stop.
```

**受影响软件**：
- postgresql-topn
- postgresql-pg_graphql
- postgresql-rum
- postgis
- 所有 PostgreSQL 扩展项目

## 根因分析

PostgreSQL 扩展使用 **PGXS (PostgreSQL Extension Building Infrastructure)** 构建系统：

1. **无 configure 步骤**: 扩展项目直接使用 Makefile，不需要 configure
2. **pg_config 依赖**: 使用 `pg_config` 命令获取 PostgreSQL 安装路径
3. **标准化流程**: `make` → `make install DESTDIR=...`

典型 Makefile 结构：
```makefile
MODULES = my_extension
EXTENSION = my_extension
PG_CONFIG ?= pg_config
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)
```

## 解决方案

### 直接编译（无需 configure）

```bash
# Step 1: 确认 pg_config 可用
pg_config --pgxs

# Step 2: 直接 make（无 configure）
make

# Step 3: 安装到 staging 目录
make install DESTDIR=$TEST_PREFIX

# Step 4: 验证产物
ls $TEST_PREFIX/$DEFAULT_PREFIX/lib/postgresql/*.so
ls $TEST_PREFIX/$DEFAULT_PREFIX/share/postgresql/extension/*.sql
```

### G0 验证适配

PostgreSQL 扩展的 G0 干净构建验证应：
- **跳过 configure 检查**: 直接解压源码后运行 make
- **验证 make 可重现**: 重复编译得到相同产物
- **检查产物完整性**: 确认 .so 和 .sql 文件正确生成

## 产物结构

PostgreSQL 扩展的标准产物布局：
```
lib/postgresql/
  └── my_extension.so      # 共享库

share/postgresql/extension/
  ├── my_extension.control  # 控制文件
  ├── my_extension--0.1.sql # 主 SQL 文件
  └── my_extension--*.sql   # 版本迁移文件
```

## 检查清单

编译 PostgreSQL 扩展时：
- ✅ PostgreSQL 已安装（pg_config 可用）
- ✅ 无需 configure，直接 make
- ✅ 使用 DESTDIR 模式安装
- ✅ 检查 .so 文件生成
- ✅ 检查 .control 和 .sql 文件生成
- ⚠️ G0 验证跳过 configure 步骤

## 知识层级

**L1 - 平台真理**: 所有 PostgreSQL 扩展都使用此模式

## 参考

- PostgreSQL 文档: https://www.postgresql.org/docs/current/extend-extensions.html
- PGXS 说明: https://www.postgresql.org/docs/current/extend-pgxs.html