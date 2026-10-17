# sqlite_orm

❤️ SQLite ORM light header only library for modern C++ (C++17, C++20).

sqlite_orm 是一个轻量级、仅头文件的 ORM 库，封装 SQLite3 的 C API，
提供类型安全的表映射、增删改查、语句构建与同步操作。

## 版本

- 1.9.1（2025-02-03 上游发布，标签 `v1.9.1` = `5f1a2ce84a3d72711b4f0a440fdaba977868ae67`）

## 适配信息

- 类型：header-only（CMake INTERFACE target）
- 依赖：`sqlite3/3.49.1`（已发布到 ohpcd 制品仓）
- 官方源码：https://github.com/fnc12/sqlite_orm
- 适配方法：`archives/s/sqlite_orm/1.9.1/`，Conan 配方 `package_type = "header-library"`，
  `package()` 拷贝 `include/` 头文件，`package_info()` 将 `sqlite3::sqlite3` 作为传递依赖暴露。

## 使用

```cpp
#include <sqlite_orm/sqlite_orm.h>
// 见 test_package/test.c（内存数据库建表/插入/查询示例）
```

详见 `archives/s/sqlite_orm/1.9.1/notes.md`。