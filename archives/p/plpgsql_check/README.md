# plpgsql_check

## 简介

plpgsql_check 是 PostgreSQL 的 PL/pgSQL 代码检查器和性能分析工具。它可以在编译时检查 PL/pgSQL 函数中的错误，并提供详细的性能分析报告。

## OHOS 适配

### 适配要点

1. 使用 PGXS 构建系统，需要设置 `USE_PGXS=1`
2. 依赖 PostgreSQL 服务器端开发文件（pg_config）
3. 编译时需要正确的 PostgreSQL 版本匹配

### 已知问题

- 安装 target 可能缺失（install-binPROGRAMS），需要使用 DESTDIR 手动安装

## 依赖

### 编译依赖
- PostgreSQL 17.0（或对应版本）
- clang/clang++ 编译器

### 运行依赖
- PostgreSQL 服务器

## 功能验证

```sql
-- 安装扩展
CREATE EXTENSION plpgsql_check;

-- 检查函数
SELECT plpgsql_check_function('my_function()');

-- 性能分析
SELECT plpgsql_profiler_function_tb('my_function()');
```

## 参考

- GitHub: https://github.com/okbob/plpgsql_check
- 文档: https://github.com/okbob/plpgsql_check#readme