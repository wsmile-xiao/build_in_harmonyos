# db — Berkeley DB classic (6.x line)

Berkeley DB 经典线（Sleepycat 血统，Oracle 收购后 6.x 系列采用 AGPL-3.0 许可）。嵌入式键/值数据库，提供 C API（`db.h` / `libdb-6.2`）与 C++ API（`db_cxx.h` / `libdb_cxx-6.2`）。

## 与仓内其他 Berkeley DB 条目的关系

| 条目 | 版本线 | 许可 | 关系 |
|------|--------|------|------|
| **db**（本条目） | 6.2.32（经典 6.x） | AGPL-3.0 | 独立软件条目，包名取自上游 tarball（db-6.2.32.tar.gz） |
| berkeley-db4 | 4.8.30 | Sleepycat | 4.x 线，独立条目 |
| berkeley-db5 | 5.3.28 | Sleepycat | 5.x 线，独立条目 |
| Oracle Berkeley DB 12c/18c/19c | — | — | 不同包名线 |

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 6.2.32 | built | 首次适配 OHOS aarch64（HarmonyOS PC） |

## 构建说明

autoconf 项目，BDB 特有构建形态：configure 位于 `dist/`，需在 `build_unix/` 子目录中调用。详见各版本目录下 `notes.md`。

## 上游

- Homepage: https://www.oracle.com/database/technologies/related/berkeleydb.html
- Source: https://download.oracle.com/berkeley-db/db-6.2.32.tar.gz
