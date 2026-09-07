# sqlitecpp 3.3.3 — 上游测试枚举台账（HarmonyOS PC / aarch64）

任务: sqlitecpp-3.3.3-r01-pc1-31-20260903T014443Z
worktree: （worktree: worktrees/pc1-31-sqlitecpp-3.3.3）
源码: （构建源目录，见回报证据日志）
分支: feat/sqlitecpp-3.3.3  HEAD: 2f60a10778991c6e9a06341cc419280c3d778d49
构建目录: （构建源目录，见回报证据日志）/build-ohos（OHOS clang 工具链 /data/service/hnp/bin）

## 统计口径
- 全量口径: 用户测试源 tests/*.cpp 中独立 TEST/TEST_F 用例总数 = 49
- 全量通过率: 49/49 = 100%（49 个全部实际运行并 PASSED）
- 实际执行口径: 49/49 = 100%（无未运行项）

## 逐项枚举台账

| 入口 | 类型 | 是否独立上游用例 | 分类理由 | 是否实际运行 | 结果 / 不能运行原因 |
|---|---|---|---|---|---|
| tests/Column_test.cpp | 用户测试源 | 是（Column 套件 5 用例） | 上游独立 TEST | 是 | PASSED（basis/basis16/getName/stream/shared_ptr） |
| tests/Database_test.cpp | 用户测试源 | 是（Database+SQLiteCpp 套件 16 用例） | 上游独立 TEST | 是 | PASSED（ctorExecCreateDropExist/moveConstructor/createCloseReopen/inMemory/backup/busyTimeout/exec/tryExec/execAndGet/execException/tryExecError/createFunction/loadExtension/getHeaderInfo/encryptAndDecrypt + SQLiteCpp.version） |
| tests/Statement_test.cpp | 用户测试源 | 是（Statement 套件 16 用例） | 上游独立 TEST | 是 | PASSED（invalid/moveConstructor/executeStep/tryExecuteStep/bindings/bindNoCopy/bindByName/bindByNameString/bindNoCopyByName/isColumnNull/isColumnNullByName/getColumnByName/getName/getColumnDeclaredType/getColumns/getBindParameterCount） |
| tests/Backup_test.cpp | 用户测试源 | 是（Backup 套件 4 用例） | 上游独立 TEST | 是 | PASSED（initException/executeStepOne/executeStepAll/executeStepException） |
| tests/Exception_test.cpp | 用户测试源 | 是（Exception 套件 4 用例） | 上游独立 TEST | 是 | PASSED（copy/assignment/throw_catch/constructor） |
| tests/ExecuteMany_test.cpp | 用户测试源 | 是（ExecuteMany 1 用例） | 上游独立 TEST | 是 | PASSED（invalid） |
| tests/Savepoint_test.cpp | 用户测试源 | 是（Savepoint 1 用例） | 上游独立 TEST | 是 | PASSED（commitRollback） |
| tests/Transaction_test.cpp | 用户测试源 | 是（Transaction 1 用例） | 上游独立 TEST | 是 | PASSED（commitRollback） |
| tests/VariadicBind_test.cpp | 用户测试源 | 是（VariadicBind 1 用例） | 上游独立 TEST | 是 | PASSED（invalid） |
| googletest/ | 框架 | 否 | GoogleTest 单测框架（gtest 宏与 runner），非用户用例 | 是 | 框架头/静态库编译并链接进 SQLiteCpp_tests |
| src/*.cpp | 库源码 | 否 | SQLiteCpp 库实现，非测试 | 是 | 编译进 libSQLiteCpp.a |
| sqlite3/sqlite3.c | 内嵌依赖源码 | 否 | 内嵌 sqlite3 C 库源码，非测试 | 是 | 编译进 libsqlite3.a |
| examples/example1/example2 | 样例/demo | 否 | 上游示例程序（example1 命令行演示/example2 子目录集成示例），非自动化测试用例 | 否（未构建） | 样例非门禁用例，CMake SQLITECPP_BUILD_EXAMPLES 默认 OFF |
| CMakeLists.txt (SQLITECPP_BUILD_TESTS) | 构建目标 | 否 | 测试构建目标定义（add_executable SQLiteCpp_tests + add_test UnitTests） | 是 | 目标编译链接成功，ctest 注册 UnitTests |

## 独立用例计数汇总
- 发现独立上游用例总数: 49（tests/ 用户测试源）
- 实际运行: 49
- 通过: 49（100%）
- 失败: 0
- 未运行 / 不可运行: 0
- 硬阻塞: 0

## 运行命令与结果
- 构建: `cmake -B build-ohos -DSQLITECPP_INTERNAL_SQLITE=ON -DSQLITECPP_RUN_CPPLINT=OFF -DSQLITECPP_RUN_DOXYGEN=OFF && make -C build-ohos -j2` → exit 0
- 运行: `./build-ohos/bin/SQLiteCpp_tests` → `[==========] 49 tests from 10 test suites ran. [  PASSED  ] 49 tests.` exit 0
- 完整输出: reports/sqlitecpp-r01-upstream-tests.log

## Conan 消费者验证（test_package）
- conan create（ohos-aarch64 profile）→ test_package 构建 + ctest：`1/1 Test #1: test_sqlitecpp ... Passed`（见 reports/conan-create.log）
