# sqlite3pp

SQLite3++ - C++ wrapper of SQLite3 API

## 简介

sqlite3pp 是一个 header-only 的 C++ SQLite3 wrapper 库，提供更友好的 C++ API 来操作 SQLite3 数据库。

## 特性

- Header-only 库，无需编译
- 支持几乎所有 SQLite3 功能
- 提供数据库、命令、查询、事务等 C++ 类
- 支持迭代器概念
- 支持扩展函数和聚合

## 安装

预编译包安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- sqlite3pp 1.0.8
```

安装后头文件位置：`$PREFIX/include/sqlite3pp/`

## 使用

```cpp
#include "sqlite3pp/sqlite3pp.h"

sqlite3pp::database db("test.db");
db.execute("CREATE TABLE test (id INTEGER, name TEXT)");

sqlite3pp::command cmd(db, "INSERT INTO test VALUES (?, ?)");
cmd.binder() << 1 << "Hello";
cmd.execute();

sqlite3pp::query qry(db, "SELECT * FROM test");
for (auto row : qry) {
    int id;
    std::string name;
    row.getter() >> id >> name;
}
```

编译时需要：
- `-I$PREFIX/include`
- `-lsqlite3`

## 依赖

- sqlite3 (>= 3.46.0)

## 版本

- 1.0.8: 现代化和重大 bug 修复（header-only 实现）
- 1.0.10: 最新版本

## 许可证

MIT License

## 来源

https://github.com/iwongu/sqlite3pp
