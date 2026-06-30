# libpg_query

C library for accessing the PostgreSQL parser outside of the server environment.

## 软件简介

libpg_query 使用 PostgreSQL 服务器的实际源码来解析 SQL 查询，返回 PostgreSQL 内部解析树。主要用于 pg_query（Ruby）、pg_query.go（Go）、pg_query.rs（Rust）等绑定库的基础。

## 关键功能

- **pg_query_parse**: 解析 SQL 返回 JSON 格式解析树
- **pg_query_normalize**: 参数化查询（如 `SELECT 1` → `SELECT $1`）
- **pg_query_fingerprint**: 计算查询指纹哈希
- **pg_query_scan**: 扫描 SQL 返回 Protobuf token 序列
- **pg_query_split**: 分割多条 SQL 语句
- **pg_query_parse_plpgsql**: 解析 PL/pgSQL 存储过程

## 编译信息

| 项目 | 值 |
|------|------|
| 构建系统 | makefile（纯 Makefile，非 autotools） |
| 编译器 | clang 15.0.4 |
| 平台 | OpenHarmony aarch64 |
| 产物类型 | 静态库（libpg_query.a） |
| 无依赖 | 纯 C 库，无外部依赖 |

## 已知限制

1. **lld 链接器问题**: OHOS SDK 的 lld 缺少 libxml2.so.16，无法链接 examples/test 可执行文件
   - 解决方案: 使用 `-fuse-ld=bfd` 链接，或只构建静态库 `make build`
2. **上游测试套**: 因链接器限制，无法运行 make test（但核心功能已通过手动测试验证）
3. **HMDFS 内存**: 程序体积较大时 init/exit 循环可能段错误（与 HMDFS 内存管理相关）

## 安装文件

- `lib/libpg_query.a` — 静态库
- `include/pg_query.h` — 主头文件
- `include/postgres_deparse.h` — 反解析头文件
- `include/libpg_query/pg_query.proto` — Protobuf 定义（可选）

## 使用示例

```c
#include <pg_query.h>
#include <stdio.h>

int main() {
    PgQueryParseResult result = pg_query_parse("SELECT 1");
    printf("%s\n", result.parse_tree);
    pg_query_free_parse_result(result);
    return 0;
}
```

编译: `clang -I$PREFIX/include -L$PREFIX/lib -fuse-ld=bfd your_program.c -lpg_query -pthread`