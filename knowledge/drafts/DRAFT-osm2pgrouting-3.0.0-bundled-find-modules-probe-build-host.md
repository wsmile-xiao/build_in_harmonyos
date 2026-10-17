# DRAFT：上游自带的 `cmake/FindXxx.cmake` 探的是构建主机 —— 改 CONFIG 模式的 CMakeDeps 包，Boost 也要 CONFIG

> 状态：草稿（待知识库主编 promote）
> 来源：osm2pgrouting 3.0.0 适配，`archives/o/osm2pgrouting/3.0.0`
> 类别：conan / cmake / 交叉构建 / host-leak
> 配套草稿：`DRAFT-osm2pgrouting-3.0.0-cmakelists-cxx-standard-shadows-toolchain-cache`

## 错误特征

两种症状，同一个根因（以为 `find_package()` 看的是目标平台）：

**(a) worker 上什么都没装 —— configure 直接失败**

```
CMake Error at cmake/FindPQXX.cmake:... :
  libpqxx couldn't be found
CMake Error at CMakeLists.txt:18 (find_package):
  Could NOT find PostgreSQL (missing: POSTGRESQL_INCLUDE_DIR POSTGRESQL_LIBRARIES)
```

**(b) worker 上恰好装了 libpq-dev —— 更糟：编过了、链上了宿主的库**

```
/usr/bin/ld: undefined reference to `PQconnectdb@PQ_17'
/usr/bin/ld: undefined reference to `pqxx::connection::connection(...)'
```

(b) 才是真正的雷：产物在 CI 上"成功"，却在设备上跑不起来；而且同一个 commit
在 A worker 过、B worker 挂，看起来像**抖动**而不是配方 bug。

**关键识别信号**：源树里有 `cmake/Find*.cmake`，或配方里只靠 `*_DIR` / `*_ROOT`
去"告诉" `find_package` 位置 —— 先去 `grep CMAKE_MODULE_PATH`。

## 触发条件

上游 `CMakeLists.txt`：

```cmake
LIST(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")
...
find_package(PostgreSQL REQUIRED)
find_package(PQXX REQUIRED)
include_directories(${PQXX_INCLUDE_DIR})
find_package(EXPAT REQUIRED)
```

`CMAKE_MODULE_PATH` 里有自带的 `cmake/`，所以 `find_package` 走 **module 模式**
先命中 bundled 模块：

- `cmake/FindPostgreSQL.cmake`：`find_program(pg_config)` →
  `execute_process(pg_config --includedir/--libdir)` →
  `find_path(POSTGRESQL_INCLUDE_DIR libpq-fe.h ...)`，候选路径是
  `/usr/include/postgresql*`、`/usr/pgsql-*/include`、
  `$ENV{ProgramFiles}/PostgreSQL/*/include`；
- `cmake/FindPQXX.cmake`：`find_path(PQXX_INCLUDE_DIR NAMES pqxx/pqxx PATHS
  /usr/local/include /usr/include ...)` + `find_library(PQXX_LIBRARIES NAMES pqxx)`。

这些候选路径全部描述 **跑 cmake 的那台机器**。交叉构建到 OHOS 时它们与目标无关。

## 根因分析

### (1) module 模式先于 CONFIG 模式，且 bundled 模块整段描述宿主

CMake 的 `find_package()` 默认先走 module 模式（在 `CMAKE_MODULE_PATH` 里找
`Find<Name>.cmake`），找不到才走 config 模式。上游把自带的 `cmake/` 前插进
`CMAKE_MODULE_PATH`，等于把"怎么找库"的定义权交给了**随源码分发的主机探测脚本**。

于是两种结局：

- 宿主有 PostgreSQL → 拿到宿主的 `libpq-fe.h` 与 `libpq.so`，链接期或运行期 ABI 不匹配；
- 宿主没有 → `Could NOT find PostgreSQL`，configure 终止。

### (2) 更隐蔽的第三处：Boost

```cmake
find_package(Boost ${BOOST_MINIMUM_VERSION} REQUIRED COMPONENTS program_options)
```

**默认也是 module 模式**，会命中 CMake **内建**的 `FindBoost`（不是上游自带的，
所以 `grep cmake/` 查不出来），而那个模块同样在主机路径上搜索 —— 即便前三家都
改好了，Boost 仍会偷偷把宿主的 `libboost_program_options` 拉进来。

### (3) CMakeDeps 只给 target，不回填旧变量名

Conan 的 `CMakeDeps` 生成 config 包，是正确的事实来源，但它**只定义 imported
target**：既不填充 `${POSTGRESQL_INCLUDE_DIR}` 这类旧变量，也不能阻止 module
模式先行。

## 与相邻条目的关系

- **E456（Windows→OHOS Qt5，目标侧 Qt 与宿主 moc/rcc/uic 必须分开）**：同属
  "native 侧工具/库不该进交叉产物"，本条是它在 `find_package` 发现路径上的形态。
- **E487（qt6linguisttools tool_require + 钉死 `*_DIR`）**：同一族的"find_package
  找错地方"，那条靠钉 `_DIR`，本条靠换模式。
- **E393（`CMAKE_MODULE_PATH` 相关的 CMakeAutoGen 路径修复）**：都涉及这个变量。
- **E296（在 Windows 构建主机上补全 OHOS meson cross file）**：跨平台的"构建主机
  描述 ≠ 目标描述"。
- **petsc-complex（`--with-x` 自动探测宿主 X11、`--with-petsc-arch` 由
  `sys.platform` 推导构建树名）**：同源 —— **通则**是：交叉构建前，逐条列出
  "哪些决定是由 native probe 做的"，并显式钉死。

## 修复清单（照抄即可）

```cmake
# CONFIG 关键字顺带跳过 CMAKE_MODULE_PATH 里的同名模块
find_package(libpq CONFIG REQUIRED)
find_package(libpqxx CONFIG REQUIRED)
find_package(EXPAT CONFIG REQUIRED)
find_package(Boost CONFIG REQUIRED COMPONENTS program_options)   # ← 别漏这行

# 文件后半段仍在用这些旧变量名做 TARGET_LINK_LIBRARIES，
# 把 imported target 映射回去 —— CMake 允许把 target 当库名传
set(POSTGRESQL_LIBRARIES libpq::libpq)
set(PQXX_LIBRARIES libpqxx::pqxx)
set(EXPAT_LIBRARIES expat::expat)
```

要点：

1. **config 包名 = 依赖的 `cmake_file_name`**（默认就是包名）：
   `libpq/18.1` → `libpq-config.cmake` + `libpq::libpq`；
   `libpqxx/8.0.1`（设了 `cmake_file_name=libpqxx`）→ `libpqxx::pqxx`；
   `expat/2.8.2.1`（`cmake_file_name=expat`）→ `expat::expat`。
2. `find_package(EXPAT CONFIG)` 能命中 `expat-config.cmake`，因为 CMake 在 config
   模式下同时找 `<Name>Config.cmake` 与 `<lowercase-name>-config.cmake`。
3. Conan 的 `CMakeToolchain` 会把 generators 目录前插到 `CMAKE_PREFIX_PATH`
   （`list(PREPEND CMAKE_PREFIX_PATH ${CMAKE_CURRENT_LIST_DIR})`），所以不需要额外
   传 `*_DIR`。
4. 传递性 include 目录随 target 走，`INCLUDE_DIRECTORIES(... ${POSTGRESQL_INCLUDE_DIR}
   ...)` 里那几个空变量无害。

不想打补丁时的替代做法（`osm2pgsql/2.3.1` 用的就是这条）：在 `generate()` 里把
`{EXPAT,BZIP2,ZLIB,LUA}_INCLUDE_DIR(_S)`、`{X}_LIBRARY(_RELEASE/_DEBUG)/{X}_LIBRARIES`
以 cache variable 的形式钉成**具体文件路径**，`libpq` 则用 `PostgreSQL_ROOT`。
缺点是路径拼装（`.so` vs `.a`、子目录）很脆；而且如果依赖还要求 C++20，见配套条目，
补丁终究躲不掉。

## 反例（不要做）

| 反例 | 后果 |
|------|------|
| 只靠 `-DPostgreSQL_ROOT=` / `-DXXX_DIR=` 让 bundled 模块"找对地方" | 模块照跑、照扫 `/usr/include` 与 `$ENV{ProgramFiles}`，宿主有同名库就抢先命中，跨 worker 行为不一致 |
| 删掉上游 `cmake/Find*.cmake` 或 `export CMAKE_MODULE_PATH=""` | 上游 CMakeLists 自己会 `APPEND` 回去；删除只是让 module 模式失败，并没有切到 config 模式 |
| 前三处加 `CONFIG`，`find_package(Boost ...)` 不加 | 内建 `FindBoost` 按主机路径搜索，宿主的 `libboost_program_options` 仍被链进来 |
| 拿 `INCLUDE_DIRECTORIES(${POSTGRESQL_INCLUDE_DIR})` 为空去判断"没生效" | config 包的 include 目录随 target 传递，这个变量为空是预期的，不是故障 |
