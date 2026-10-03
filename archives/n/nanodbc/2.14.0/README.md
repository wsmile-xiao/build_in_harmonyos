# nanodbc

**nanodbc — C++ ODBC 轻量封装库**（header + 单 cpp，MIT），
上游：<https://github.com/nanodbc/nanodbc>。

```cpp
#include <nanodbc/nanodbc.h>

nanodbc::connection conn;
conn.connect("Driver=SQLite3;Database=test.db");  // 沙箱内无数据源时离线 API 亦可安全使用
nanodbc::result row = nanodbc::execute(conn, "SELECT 1");
```

本包交付：`lib/libnanodbc.a` + `include/nanodbc/nanodbc.h` +
`lib/cmake/nanodbc/`（find_package(nanodbc CONFIG) 导出）+ `licenses/LICENSE`，
唯一依赖是已发布的 `unixodbc/2.3.12`。

测试：上游 utility_test（1 TEST_CASE "convert"，7 断言，纯离线）在源码树
独立构建真跑通过；五套 DB 型测试（mssql/mysql/postgresql/sqlite/vertica 共
198 例）需 TEST_NANODBC_CONNSTR 真数据库，沙箱环境排除如实记录；消费者
离线冒烟 9 断言见 `test_package/`。详见 `notes.md`。
