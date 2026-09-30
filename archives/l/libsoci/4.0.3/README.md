# libsoci

**SOCI — Simple Open-source C++ database access library**（C++ 数据库访问层），
上游：<https://github.com/SOCI/soci>，许可证 BSL-1.0。

SOCI 用类型安全的语法把 C++ 与 SQL 接起来：

```cpp
soci::session sql(soci::sqlite3, "file:app.db");
int count; double total;
sql << "select count(*), sum(value) from measurement",
    soci::into(count), soci::into(total);
sql << "insert into measurement(name, value) values(:name, :value)",
    soci::use(name), soci::use(value);
```

## OHOS（鸿蒙 PC / aarch64）适配状态

| 版本 | 状态 | 后端范围 | 依赖 |
|------|------|----------|------|
| 4.0.3 | 已适配（消费者用例 14/14，上游 ctest 2/2） | SQLite3 + empty | `sqlite3/3.49.1` |

- 交付：`libsoci_core`、`libsoci_sqlite3`、`libsoci_empty` 三个库 + 全部公开头文件
  + 上游 `SOCIConfig.cmake` + `licenses/LICENSE_1_0.txt`。
- 其余后端（MySQL/PostgreSQL/ODBC/Firebird/DB2/Oracle）需要各自的客户端库，
  OHOS 上暂无对应 Conan 包，因此本包只启用 SQLite3 与零依赖的 empty 后端。

## 使用（Conan 2）

```ini
[requires]
libsoci/4.0.3
```

CMake：`find_package(SOCI CONFIG REQUIRED)` + `target_link_libraries(app PRIVATE SOCI::SOCI)`
（上游自带的 `SOCIConfig.cmake` 也提供 `SOCI::soci_core`/`SOCI::soci_sqlite3` 分目标）。

## 适配要点

详见 `4.0.3/notes.md`：CMake 最低版本、`FindSQLite3` 的缓存变量接线、`SOCI_CXX11=ON`
的必要性、shared/static 只出一份、`<sqlite3.h>` 的头文件传递。
