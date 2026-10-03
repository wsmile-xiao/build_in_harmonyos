# nanodbc 2.14.0 适配笔记（OHOS PC / aarch64）

**nanodbc — C++ ODBC 轻量封装库**（MIT），上游：https://github.com/nanodbc/nanodbc ，
tag v2.14.0（tarball sha256 `56228372042b689beccd96b0ac3476643ea85b3f57b3f23fb11ca4314e68b9a5`）。

## 交付形态

- `lib/libnanodbc.a`（静态，默认 shared=False）
- `include/nanodbc/nanodbc.h`
- `licenses/LICENSE`（MIT，顶层拷贝）
- `lib/cmake/nanodbc/nanodbc-config.cmake`（install EXPORT，消费者 `find_package(nanodbc CONFIG)`）
- 依赖：`unixodbc/2.3.12`（ODBC 驱动管理器；sql.h/sqlext.h + libodbc.so）

## 核心适配点（0001 patch，4 hunks）

上游 ODBC 探测链是**宿主专用三连**：`find_program(odbc_config)` →
`find_path(uodbc_stats.h)` → `find_program(iodbc-config)`。交叉构建
（CMAKE_SYSTEM_NAME=HarmonyOS）下三者必然落空 → FATAL_ERROR "can not find a
suitable odbc driver manager"；且 HarmonyOS 平台**连 UNIX 变量都不定义**，
探测块本体都不会进入。改造：

1. `cmake_minimum_required` 3.0.0 → 3.10（CMake 4.x 拒绝 <3.5，本次适配实测必需）
2. 探测链前插 `if(ODBC_INCLUDE_DIR AND ODBC_LIBRARY)` 显式分支：直接采用
   conan CMakeToolchain 注入的两个路径（unixodbc 包的 include/ 与 libodbc.so
   全路径），`set(ODBC_CONFIG 1)` 使后续 `if(NOT ODBC_CONFIG)` 守卫不触发
3. 链接库选择守卫 `if(UNIX)` → `if(UNIX OR (ODBC_INCLUDE_DIR AND ODBC_LIBRARY))`
4. 目标属性守卫同上扩展（COMPILE_FLAGS/LIBRARY_OUTPUT_DIRECTORY）

## 上游测试（真跑与排除，如实记录）

上游测试双形态（test/CMakeLists.txt）：

| 套件 | 注册数 | 形态 | 处置 |
|------|--------|------|------|
| utility_test | 1 TEST_CASE（7 断言） | 纯离线（`#include nanodbc.cpp` 直访私有 convert，无 DB） | **真跑通过** |
| mssql_test | 60 TEST_CASE_METHOD | base_test_fixture 构造即 REQUIRE 连接 | 环境排除 |
| mysql_test | 34 | 同上 | 环境排除 |
| postgresql_test | 36 | 同上 | 环境排除 |
| sqlite_test | 38 | 同上 | 环境排除 |
| vertica_test | 30 | 同上 | 环境排除 |
| odbc_test | 27 | 上游自注 dummy（test_list 不含，从不构建） | 不计入注册数 |

**上游注册数 N=199**（1+60+34+36+38+30；odbc_test 的 27 个 dummy 剔除）。

- 环境排除原因：五套 DB 测试经 `base_test_fixture` 构造函数
  `connection_string_ = get_env("TEST_NANODBC_CONNSTR")` 取连接串后首个用例即
  `REQUIRE` 真连接（mssql/mysql/postgresql/vertica 需对应 DB 服务器；sqlite 需
  SQLite ODBC 驱动——沙箱无 ODBC 数据源、无驱动注册表），OHOS PC CI 沙箱无法
  提供真实数据库服务，属环境排除而非测试缺陷。
- 真跑方法（本机 OHOS 原生复现，已在 CI 同款环境验证）：
  源码树打 0001 patch 后独立构建：
  ```
  cmake .. -DCMAKE_BUILD_TYPE=Release \
    -DODBC_INCLUDE_DIR=<unixodbc 包>/include \
    -DODBC_LIBRARY=<unixodbc 包>/lib/libodbc.so \
    -DNANODBC_DISABLE_EXAMPLES=ON -DNANODBC_DISABLE_INSTALL=ON
  make utility_tests
  LD_LIBRARY_PATH="<unixodbc>/lib:<SDK llvm>/lib:<SDK llvm>/lib/aarch64-linux-ohos:/system/lib64" \
    ctest -R utility_tests --output-on-failure
  ```
  结果：`All tests passed (7 assertions in 1 test case)`（断言明细：identity
  conversion ×4、widening ×1、narrowing ×2——非 MSVC 分支下 std::string↔u16string
  与 SQLWCHAR 经 wide_char_t 的转换）。

## test_package（消费者冒烟，9 断言）

`test.cpp` 用交付包（find_package(nanodbc CONFIG) + 链接 libnanodbc.a），
纯离线 API 面（均为库内实现、无驱动交互）：
connection/statement/result 默认构造语义（connected()==false、operator
bool==false、transactions()==0）、未连接 disconnect() no-op、statement 空态
close() no-op、date/time/timestamp POD（timestamp 字段名 **fract**）、
database_error(nullptr,0,info) 离线构造。CI 的 L1e 会移走 lib/include 后重跑
conan test → find_package/链接必失败，真依赖被测包。

## 踩坑记录

- statement **无 reset()**，上游语义是 close()；timestamp 字段是 **fract** 非
  fraction（test.cpp 初版笔误，编译期即被揪出）。
- 本机 OHOS 原生跑动态链接产物需补 LD_LIBRARY_PATH：unixodbc 包 lib/ + OHOS
  SDK llvm/lib（lld 依赖）+ /system/lib64（libc++_shared.so 真身在系统分区，
  SDK 的同名文件是链接器脚本）。
- make jobserver 在沙箱 HMDFS 上 mkfifo 报 Operation not permitted（无害，
  构建照常）。
- conan create 走 `--build=missing` + `-c tools.build:jobs=2`；/tmp 只读，
  需 `export TMPDIR=~/huawei/tmp`。
