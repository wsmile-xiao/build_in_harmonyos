# cppdb for HarmonyOS

## 概述

CppDB 是 CppCMS 项目的 SQL 连接库，提供与数据库无关的统一 API（类似 JDBC 的设计思想），支持 Sqlite3、PostgreSQL、MySQL 以及经 ODBC 桥接的各类关系数据库。2013 年发布 0.3.1 后上游迁移至 GitHub（artyom-beilis/cppdb）继续维护。

本次适配仅启用 serverless 的 sqlite3 后端：mysql/postgresql/odbc 后端需要在线数据库服务，在 HarmonyOS 环境中不可用。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | cppdb |
| 版本 | 0.3.1 |
| 许可证 | BSL-1.0 或 MIT（任选） |
| 上游仓库 | https://github.com/artyom-beilis/cppdb（原始发布见 SourceForge CppCMS 项目页） |
| 依赖 | sqlite3/3.49.1（制品仓已发布） |
| 构建系统 | CMake |

## 鸿蒙适配要点

- sqlite3 头文件/库路径通过 `-DSQLITE3_PATH/-DSQLITE3_LIB` 直接覆盖上游裸 `find_path/find_library` 变量（find 对已定义变量跳过搜索，无需改源码）。
- 默认静态库（`shared=False`）把 sqlite 后端直接编进 `libcppdb.a`（`SQLITE_BACKEND_INTERNAL=ON`），运行时无需 dlopen；`shared=True` 时走上游默认的模块布局（`libcppdb_sqlite3.so` 运行时加载）。
- 补丁仅做两处可移植调整：`cmake_minimum_required` 2.6 → 3.5，固定 `CMAKE_CXX_STANDARD=14`（上游使用 C++17 已移除的 `std::auto_ptr`）。

## 验证

```bash
conan create . --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

构建中运行上游 sqlite 测试子集（`test_basic`/`test_backend` 各 4 种连接串变体 + `test_caching`，对应 `test/run_test_linux_a.sh` 的 sqlite 部分）；test_package 另做消费者 CRUD 与上游回放验证。

## 参考

- http://cppcms.com/sql/cppdb/
- https://github.com/artyom-beilis/cppdb
- https://sourceforge.net/projects/cppcms/files/cppdb/
