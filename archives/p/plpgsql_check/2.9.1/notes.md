# plpgsql_check 2.9.1 适配笔记

## 编译环境
- 构建系统: makefile (PGXS)
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- PostgreSQL: 17.0
- 状态: built

## 编译步骤

```bash
# 使用 PGXS 构建系统
make USE_PGXS=1
make install USE_PGXS=1 DESTDIR=~/test-install-plpgsql_check-2.9.1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | install-binPROGRAMS target缺失 | PGXS Makefile结构差异 | 使用DESTDIR手动安装 |

## 验证结果

```bash
ls -lh ~/test-install-plpgsql_check-2.9.1/
# lib/postgresql/plpgsql_check.so      1.2MB
# share/postgresql/extension/*.sql     14KB
# share/postgresql/extension/*.control 182B
```

## 交付物

制品目录: `/storage/Users/currentUser/xuejiachen/xuejiachen0603/plpgsql_check-2.9.1-ohos-aarch64/`

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/postgresql/plpgsql_check.so | 1.2MB | 扩展模块 |
| share/postgresql/extension/plpgsql_check--2.9.sql | 14KB | SQL定义 |
| share/postgresql/extension/plpgsql_check.control | 182B | 控制文件 |

## 注意事项

- 依赖 PostgreSQL 17.0 的 PGXS 构建系统
- 安装时需使用 `USE_PGXS=1` 参数
