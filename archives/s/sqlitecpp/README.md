# sqlitecpp

SQLiteCpp is a smart and easy to use C++ SQLite3 wrapper.

- **上游仓库**: https://github.com/SRombauts/SQLiteCpp
- **License**: MIT
- **构建系统**: CMake（内部自带 sqlite3 源码，`SQLITECPP_INTERNAL_SQLITE=ON` 为上游默认）
- **类型**: C++ 库（静态 `libSQLiteCpp.a` + 内部 `libsqlite3.a`）
- **外部依赖**: 无（sqlite3 内嵌编译，无需外部 provision）
- **公开头文件**: `include/SQLiteCpp/*.hpp`、`include/sqlite3.h`

## 可用版本

| 版本 | 状态 |
|------|------|
| 3.3.3 | built |
