# duckdb 1.5.5 — HarmonyOS PC 适配笔记

## 概要

| 项 | 值 |
|----|----|
| 上游 | https://github.com/duckdb/duckdb |
| tag | `v1.5.5` |
| 源码 sha256 | `f33155ff962e6e1e08fd1e9caffa487d4325aa60999e2eabc76feff534d6558b` |
| 构建系统 | CMake（Ninja generator） |
| 目标 | OHOS / armv8 / clang 15 / libc++ / Release |
| 依赖 | 全部内置（third_party/），无外部 Conan requires |
| 补丁 | 无 |
| 上一适配版本 | 1.2.0（本版本为**新版本重新适配**，非复制） |

## 1. 与 1.2.0 的关键差异（必须重新处理）

### 1.1 新增跨编译硬阻塞：`duckdb_platform_binary`

1.5.5 的 `CMakeLists.txt:872-895`：

```cmake
if(NOT DUCKDB_EXPLICIT_PLATFORM)
  add_executable(duckdb_platform_binary ${VERSION_SOURCES})
  add_custom_command(
    OUTPUT ${PROJECT_BINARY_DIR}/duckdb_platform_out
    DEPENDS duckdb_platform_binary
    COMMAND $<TARGET_FILE:duckdb_platform_binary> > ...   # ← 运行目标二进制
    ...)
else()
  add_custom_command(... COMMAND ${CMAKE_COMMAND} -E echo_append
                       "${DUCKDB_EXPLICIT_PLATFORM}" > ...) # ← 仅 echo
endif()
```

`duckdb_platform_binary` 是 **aarch64 目标二进制**，构建主机无法执行，
因此不设置 `DUCKDB_EXPLICIT_PLATFORM` 时交叉编译必然失败。

该目标不是孤立的：`extension/extension_build_tools.cmake:88-94` 的
`duckdb_local_extension_repo`（`ALL` 目标）以及每个 loadable extension
（`extension_build_tools.cmake:214`）都 `add_dependencies(... duckdb_platform)`，
即默认 `all` 路径上就会被触发。

**修复**：`tc.variables["DUCKDB_EXPLICIT_PLATFORM"] = "linux_arm64"`

选择 `linux_arm64` 的依据：`src/include/duckdb/common/platform.hpp:37-88`
在 aarch64 Linux 上会自行算出 `linux_arm64`。该变量同时经
`CMakeLists.txt:143-145` 定义为 `DUCKDB_CUSTOM_PLATFORM`，命中
`platform.hpp:38-39` 的 `#if defined(DUCKDB_CUSTOM_PLATFORM)` 分支，
从而**绕过** `platform.hpp:70-74` 的 legacy C++ ABI `#error`——该
`#error` 对 OHOS（musl 系）尤其重要，因为 OHOS 的 libc++ 走的是
`_LIBCPP_ABI_NAMESPACE` 旧/新命名空间判定，不能依赖 glibc 的
`__GLIBCXX__` 探测。

### 1.2 shared / static 变为无条件构建

1.5.5 的 `src/CMakeLists.txt:96`（`duckdb_static`）与 `:107`（`duckdb`）
是**无条件**的，没有 `BUILD_SHARED_LIBS` / recipe `shared` 开关。
1.2.0 recipe 里的 `options = {"shared": [True, False]}` 实际是空转，
本版本配方**移除了该选项**，如实安装两个库。

### 1.3 CMake 包配置

`DuckDBConfig.cmake.in` / `DuckDBConfigVersion.cmake.in` 位于仓库根，
经 `CMakeLists.txt:924-943` 安装到 `lib/cmake/DuckDB/`。
导出集名 `DuckDBExports`（`CMakeLists.txt:106`），
`install(EXPORT ...)`（`CMakeLists.txt:911`）**不带 NAMESPACE**，
所以上游导出目标名是裸 `duckdb` / `duckdb_static`；
`duckdb::duckdb` 只存在于 Conan CMakeDeps 生成的 config 中
（test_package 正是走这条路，且 package_info 保持 `libs = ["duckdb"]`）。

### 1.4 依赖仍然全部内置（已重新核验，非沿用旧结论）

`third_party/`（30 项）包含 zstd / snappy / lz4 / brotli / thrift /
parquet / mbedtls / re2 / fmt / utf8proc / miniz / yyjson / libpg_query 等，
经 `add_third_party(...)`（`CMakeLists.txt:860-871`）或直接源文件列表编译。
默认扩展集只有 `core_functions` + `parquet`（`extension/extension_config.cmake`），
均在源码树内。全树唯一的 `FetchContent` 出现在
`extension_build_tools.cmake:322-342`（`register_external_extension`），
只用于**树外**扩展，默认不触发；configure 阶段无网络下载。
全树外部 `find_package` 只有 `Python3`（非 REQUIRED）、`Threads`（REQUIRED）、
`Git`（可选，缺失时回退 dummy 版本 `v0.0.1`）。

## 1.5 Conan 校验：`package_type` 必须与声明的 options 一致

第一版配方沿用了旧版本的 `package_type = "library"`，但 1.5.5 已移除 `shared`
选项（见 §1.2），Conan 在校验阶段直接拒绝：

```
ERROR: duckdb/1.5.5: Package type is 'library', but no 'shared' option declared
```

改为 `package_type = "static-library"`——这与实际交付一致：`cpp_info.libs`
指向默认链接的静态库 `libduckdb_static.a`（`libduckdb.so` 同时安装，
需要动态库的消费方可直接使用上游的 `lib/cmake/DuckDB/DuckDBConfig.cmake`）。

## 2. 构建配置

```
-G Ninja
-DCMAKE_BUILD_TYPE=Release
-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
-DDUCKDB_EXPLICIT_PLATFORM=linux_arm64
-DBUILD_SHELL=OFF          # 只要库，不要 shell CLI / plan_serializer
-DBUILD_UNITTESTS=OFF      # 跨编译不构建测试运行器
-DBUILD_BENCHMARKS=OFF
-DEXTENSION_STATIC_BUILD=OFF
```

## 3. 测试：诚实申报

### 3.1 上游测试（未运行，如实申报）

| 项 | 值 |
|----|----|
| 框架 | Catch2（`third_party/catch`，随源码内置） |
| 目标 | `unittest`（`test/CMakeLists.txt:50`），由 `BUILD_UNITTESTS` 控制 |
| 规模 | **4087** 个 `*.test`（sqllogictest 脚本）+ **73** 个 `test/api/*.cpp` |
| 上游调用 | `./build/release/test/unittest` |
| 本次执行 | **未执行（NOT_RUN）** |

未执行的技术原因（非"环境不支持"式敷衍）：

1. 本次 `conan create` 采用 `BUILD_UNITTESTS=OFF`：`unittest` 会复用
   `duckdb_static` 的全部对象文件（`test/CMakeLists.txt:57`），在
   单线程（profile `tools.build:jobs=1` + `CMAKE_BUILD_PARALLEL_LEVEL=1`）
   的构建约束下，构建该运行器本身即数十分钟量级，且它不产生任何
   对外交付产物。
2. 更关键的是**运行期布局约束**：`DUCKDB_ROOT_DIRECTORY` 在
   `test/CMakeLists.txt:44-48` 被编译期固定为构建时的源码根绝对路径，
   运行 unittest 时该路径下必须仍存在完整源码树（`test/sql/**/*.test`、
   `data/`、`test/schema.sql`、`test/load.sql`）。Conan 的
   `conan create` 会把源码与构建树放在临时目录中，构建结束后不保证保留，
   因此**即使构建了 unittest 也无法在 test/ 阶段直接运行**。
   要真跑需要额外的"构建 → 打包源码树 → 设备侧还原路径 → 运行"流程。

因此本版本如实标记上游套件 `executed: false`，并在
`test_package/MANIFEST.yml` 中给出 `not_run_reason`，不把未运行的测试
计为 PASS。

### 3.2 test_package（已执行，消费者视角）

`test_package/test.c` 通过 **C API** 真实调用被测库，6 个断言：

| # | 动作 | 断言 |
|---|------|------|
| 1 | `duckdb_open(NULL, &db)` | 返回 `DuckDBSuccess` |
| 2 | `duckdb_connect(db, &con)` | 返回 `DuckDBSuccess` |
| 3 | `SELECT 1 + 1` | 值 == 2 |
| 4 | `CREATE TABLE t(id INTEGER, name VARCHAR)` | 返回 `DuckDBSuccess` |
| 5 | `INSERT INTO t VALUES (1,'hello'),(2,'world')` | 返回 `DuckDBSuccess` |
| 6 | `SELECT COUNT(*) FROM t` / `SELECT name WHERE id=2` | count == 2 且 name == "world" |

由 `test_package/CMakeLists.txt` 的 `add_test` + conanfile `test()` 的
`cmake.test()` 自动执行，任一断言失败即非零退出并打印 DuckDB 错误串。
测试二进制为 aarch64，在 OHOS PC 上原生运行。

## 4. 产物

| 文件 | 说明 |
|------|------|
| `lib/libduckdb.so` | 共享库（目标 `duckdb`） |
| `lib/libduckdb_static.a` | 静态库（目标 `duckdb_static`） |
| `include/duckdb.h`、`duckdb.hpp`、`duckdb_extension.h` | C / C++ 公共头 |
| `include/duckdb/**/*.hpp` | C++ 内部头（供扩展开发） |
| `lib/cmake/DuckDB/DuckDBConfig.cmake` 等 | 上游 CMake 包配置 |

`bin/duckdb`（shell CLI）因 `BUILD_SHELL=OFF` 未构建——本包定位为
嵌入式库，CLI 不属于核心交付面。

## 5. 参考

- 上一版本配方：`archives/d/duckdb/1.2.0/`（仅作参考，本版本全部重新核验）
- 上游构建文档：https://duckdb.org/docs/stable/dev/building/overview
