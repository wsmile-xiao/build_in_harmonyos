# soci 4.1.4 — HarmonyOS PC (aarch64) 适配笔记

- 上游：SOCI（Simple Oracle Call Interface）—— C++ 数据库访问层
- 仓库：https://github.com/SOCI/soci
- 版本：4.1.4（tag `v4.1.4`，该仓库最新稳定 release）
- 许可证：**BSL-1.0**（Boost Software License 1.0，见 LICENSE_1_0.txt）
- 构建系统：CMake
- 依赖：**sqlite3/3.53.4**（SQLite3 后端）、**fmt/11.1.3**（上游把 fmt 作为
  git submodule 放在 3rdparty/，归档 tarball 不含）
- 包形态：纯库 —— `libsoci_core.a` + 每个启用后端一个库
  （`libsoci_sqlite3.a`、`libsoci_empty.a`）+ `include/soci/`；**无 bin/**，
  故不需要 commands.json（R38）
- 状态：**READY_FOR_HARMONY** —— 本地直接构建上游已验证，conan 侧待真机

## 1. 后端取舍

后端由 `SOCI_<NAME>` 缓存变量控制（ON/OFF/**AUTO**，默认 AUTO = 依赖满足即启用）。
本配方：

| 后端 | 设置 | 原因 |
|---|---|---|
| SQLite3 | **ON** | 无服务器，`:memory:` 即可测试 |
| Empty | **ON** | 空实现后端，用于验证 core 本身 |
| DB2 / Firebird / MySQL / ODBC / Oracle / PostgreSQL | **OFF** | 需要专有客户端库或活数据库服务器 |

## 2. ⚠️ fmt 是 git submodule，归档里没有

soci 在 `3rdparty/fmt` 放了一个 submodule；**GitHub 的 archive tarball 不含 submodule**，
直接构建会：

```
CMake Error at CMakeLists.txt:148 (message):
  fmt library submodule not found.
```

上游支持外部 fmt（`find_package(fmt)` 成功即用）。配方 `requires("fmt/11.1.3")`
并设 `SOCI_FMT_BUILTIN=OFF` —— 宁可显式失败也不静默回退到不存在的副本。

## 3. ⚠️ 用例总数必须取 Catch2 运行时自报（112 ≠ 84）

- 源码里 `TEST_CASE` 行：common + sqlite3 合计 **112**；
- 实际编译进 `soci_sqlite3_test` 并执行的：**84**。

差额来自条件编译，最典型的是 `tests/common/test-boost.cpp` **整个文件**包在
`#ifdef SOCI_HAVE_BOOST` 内（本配置没有 Boost，4 条全部不参与）。

判定依据取 Catch2 自己的总结行：

```
All tests passed (2242 assertions in 84 test cases)
```

**把源码声明数（112）当 case total 会虚报 33%** —— 这正是 R51 要防的那类失真。

## 4. 其它 API 注意点

- `soci::use()` **显式删除了右值重载**（`use(T&&, ...) = delete`），必须传左值变量：
  `soci::use(1)` 编译失败，要写成 `int id = 1; soci::use(id);`
- soci 自带 `soci-config.cmake`，导出 `SOCI::Core` / `SOCI::Empty` / `SOCI::SQLite3`；
  Conan 侧由 `cpp_info.components` 生成 `soci::core` / `soci::sqlite3` / `soci::empty`。
  test_package 用 `find_package(soci)` + `soci::sqlite3`，会自动带出 core 与
  `sqlite3::sqlite3`。

## 5. 本地实测（直接构建上游 + 自建 sqlite3/fmt）

```
$ cmake -S soci-4.1.4 -B b -DCMAKE_PREFIX_PATH=<sqlite3+fmt 前缀> \
        -DSOCI_SHARED=OFF -DSOCI_TESTS=ON -DSOCI_FMT_BUILTIN=OFF \
        -DSOCI_SQLITE3=ON -DSOCI_EMPTY=ON -DSOCI_DB2=OFF -DSOCI_FIREBIRD=OFF \
        -DSOCI_MYSQL=OFF -DSOCI_ODBC=OFF -DSOCI_ORACLE=OFF -DSOCI_POSTGRESQL=OFF
  -- Using system fmt library 11.1.3
  -- Enabled SOCI backends are: Empty;SQLite3
$ make -j4 && ctest
100% tests passed, 0 tests failed out of 2
$ ./bin/soci_sqlite3_test ":memory:"
All tests passed (2242 assertions in 84 test cases)
$ ./test_soci
ok × 9  (all soci consumer checks passed)
```

（本地依赖同样是自己构建的：sqlite 3.50 合并源码 + fmt 11.1.3；
制品仓里的 sqlite3/3.53.4 与 fmt/11.1.3 均为 OHOS 预编译二进制，真机直接用。）

## 6. 待真机验证内容（READY_FOR_HARMONY 清单）

1. `conan create`（clang 15 / aarch64-ohos）：sqlite3/3.53.4 与 fmt/11.1.3
   预编译二进制的链接
2. 真机 ctest 2/2；sqlite3 后端的 84 个 Catch2 用例 / 2242 断言是否全过
   （重点：soci 依赖 sqlite3 的动态加载与文件/内存数据库行为）
3. test_package 9 项断言（含 2 项负向）
4. 库包无 bin/ → 确认不需要 commands.json

---

## 7. BLOCKED — 真机 conan create 未通过（2026-09-22 01:5x）

**状态：BLOCKED（不是 recipe 逻辑缺陷；本地直接构建上游全绿）。**
分支 `feat/soci-4.1.4` 未推送、无 PR。

### 7.1 首轮失败：generate() 漏了 CMakeDeps（**已修，已提交**）
```
System fmt library not found and using built-in version was disabled.
CMake Error at CMakeLists.txt:134 (message)
```
根因：soci 自己在 CMakeLists 里 `find_package(fmt)`，而我第一版 `generate()`
只建了 `CMakeToolchain`、没有 `CMakeDeps` → generators 目录里没有任何
`<pkg>-config.cmake`。补上 `CMakeDeps(self).generate()` 后该错误消失
（commit 2c64cf394a）。

### 7.2 第二轮失败：CMake target 命名不匹配（**未解决**）
```
Conan: Target declared 'sqlite3::sqlite3'
CMake Error at cmake/soci_define_backend_target.cmake:130 (message):
  Expected successful find_package call with 'SQLite3' to define target 'SQLite::SQLite3'
Call Stack: src/backends/sqlite3/CMakeLists.txt:22 (soci_define_backend_target)
```

**根因**：两边对同一个库用了不同的 CMake 目标名。

| 来源 | 配置文件名 | 声明的 target |
|---|---|---|
| Conan 的 `sqlite3/3.53.4` 配方 | `sqlite3-config.cmake` | `sqlite3::sqlite3` |
| CMake 内置 `FindSQLite3`（soci 的预期） | — | `SQLite::SQLite3`（CMake <4.3）/ `SQLite3::SQLite3`（≥4.3） |

soci 走**配置模式**先命中 Conan 的 `sqlite3-config.cmake`（CMake 的
`find_package(X)` 会匹配小写 `x-config.cmake`），于是 `sqlite3::sqlite3` 存在、
而 soci 期望的 `SQLite::SQLite3` 不存在 → `soci_define_backend_target` 第 130 行
直接 FATAL。soci 那段逻辑要求 `YIELDS` 里的**所有**目标都存在（不是任一），
所以没法用「候选列表」绕。

### 7.3 已排除的绕法（供后续接手）
- **内置 sqlite3**（`SOCI_SQLITE3_BUILTIN=ON`）：需要
  `${SOCI_SQLITE3_DIRECTORY}/sqlite3.c`，而该源码同样是 submodule，
  **GitHub 归档里没有** → 不可行。
- **给 YIELDS 传候选列表**：`soci_define_backend_target` 第 90/128 行要求
  列表中**每个**目标都存在，传两个必然 FATAL → 不可行。
- **首选方案（未实施）**：在 soci 的 `project()` 之后、backends 之前注入一个
  小 shim，让它先 `find_package(sqlite3)` 再把 `SQLite::SQLite3` 定义成指向
  `sqlite3::sqlite3` 的 IMPORTED INTERFACE 目标。soci 检测到目标已存在会走
  `SKIP_DEP_SEARCH` 分支直接链接，不再自己 find_package。
  注入点可用 `CMAKE_PROJECT_soci_INCLUDE`（CMake ≥3.10），由
  `tc.cache_variables` 指定 shim 路径、shim 由 recipe 在 generate() 里写出。
  注意目标名随 CMake 版本变化（<4.3 是 `SQLite::SQLite3`，≥4.3 是
  `SQLite3::SQLite3`），shim 里两个都定义更稳。
- **备选方案**：把 sqlite3 从 Conan 依赖里去掉，改为让 CMake 内置
  `FindSQLite3` 通过 `SQLITE3_INCLUDE_DIR`/`SQLITE3_LIBRARY` 直接指向包路径；
  但那样就失去了 Conan 的依赖链管理，需要自己处理 include/lib 路径。

### 7.4 本地验证结论（证明不是 recipe 逻辑问题）
同一份配方逻辑在本地（自建 sqlite3 + fmt）完整跑通：
ctest 2/2 通过、sqlite3 后端 2242 断言/84 用例全过、消费者 9/9。
因此本 blocker 属于 **Conan 包与上游 CMake 的目标命名对接问题**，
不是编译或测试本身的问题。
