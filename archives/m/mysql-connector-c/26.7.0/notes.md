# mysql-connector-c 26.7.0 编译笔记

## 编译状态
状态: draft（首轮待编译）

## 项目身份

Conan package name `mysql-connector-c` 对应 MySQL Connector/C++ 26.7.0
（Oracle 官方 source distribution）。任务名沿用 "mysql-connector-c"，但
实际指代 Connector/C++ 提供的 X DevAPI for C（plain C API，头文件
`<mysqlx/xapi.h>`）。MySQL 历史上有独立的 Connector/C 6.x（6.1.11 即最后版本，
2017 年停更），与本任务无关。

## 库名（源码实际产物）

| 类型 | 库名 | SONAME |
|---|---|---|
| 静态 | `libmysqlcppconnx-static.a` | — |
| 动态 | `libmysqlcppconnx.so` | `2.26.7.0`（即 `${ABI_VERSION_MAJOR}.${CONCPP_VERSION}`） |

源码 `install_layout.cmake` 第 218 行：
```cmake
set(LIB_NAME_BASE "mysqlcppconnx")
set(LIB_NAME_STATIC "${LIB_NAME_BASE}-static")
```

## 真实依赖（基于 26.7.0 源码 DepFind*.cmake）

| 依赖 | 类型 | 启用方式 |
|---|---|---|
| OpenSSL | 必需，system | `WITH_SSL=system`（cdk/cmake/DepFindSSL.cmake 默认）|
| lz4 | 必需，bundled | cdk/extra/lz4/ |
| zstd | 必需，bundled | cdk/extra/zstd/ |
| zlib | 必需，bundled | cdk/extra/zlib/ |
| protobuf-3.19.6 | 必需，bundled | cdk/extra/protobuf/protobuf-3.19.6/ |
| RapidJSON | 必需，bundled（header-only） | cdk/extra/rapidjson/include/ |
| JDBC（libmysqlclient） | 可选 | `WITH_JDBC=OFF` 跳过 |
| GoogleTest | 测试 | `WITH_TESTS=OFF` 跳过 |

## CMake 选项（已确认存在）

顶层 `CMakeLists.txt`：
- `add_config_option(BUILD_STATIC BOOLEAN DEFAULT OFF)` （第 215 行）
- `add_config_option(WITH_TESTS BOOL ADVANCED DEFAULT OFF)` （第 358 行）
- `add_config_option(WITH_JDBC DEFAULT OFF)` （第 389 行）
- `add_config_option(BUNDLE_DEPENDENCIES BOOL DEFAULT OFF)` （第 141 行）
- `add_config_option(STATIC_MSVCRT BOOL DEFAULT OFF)` （第 159 行）

cdk/cmake/DepFindSSL.cmake：
- `add_config_option(WITH_SSL STRING DEFAULT system)`

## 关键技术点

### 1. OpenSSL 集成

`cdk/cmake/DepFindSSL.cmake` 在 cmake>=3.8 时调用 `find_package(OpenSSL)`，
但 Conan CMakeDeps 生成的 `OpenSSLConfig.cmake` 不会出现在 build tree 的
`CMAKE_PREFIX_PATH` 中（upstream cmake 路径里用了模块模式）。解决：
通过 `CMakeToolchain` 直接传 `OPENSSL_ROOT_DIR` / `OPENSSL_INCLUDE_DIR` /
`OPENSSL_SSL_LIBRARY` / `OPENSSL_CRYPTO_LIBRARY` / `OPENSSL_FOUND` /
`OPENSSL_USE_STATIC_LIBS`，让 cmake 内置的 FindOpenSSL 模块在模块模式下
直接拿到路径，绕开 CMakeDeps 不可见的问题。cpr 1.14.2 配方用的是同
一种模式。

### 2. 静态库与 PIC

源码 `enable_pic()`（cdk/cmake/platform.cmake 第 159 行）会在所有 target
上自动加 `-fPIC`，所以不需要手动设置。`BUILD_STATIC=ON` 时
`BUILD_SHARED_LIBS=OFF`，生成 `libmysqlcppconnx-static.a`。这是首轮目标。

### 3. C API 头文件

`include/mysqlx/xapi.h` 是 plain C API。`include/mysqlx/xdevapi.h` 是 C++ API。
任务目标使用 `<mysqlx/xapi.h>`，对应 `mysqlx_*` 系列 C 函数（mysqlx_session、
mysqlx_result、mysqlx_stmt 等）。

## 待解决问题（编译时再分析）

- bundled protobuf 3.19.6 编译时间长，是否在 OHOS 工具链上无问题
- bundled zlib 是否有 PIC 问题
- X18 寄存器问题：grep 验证源码无 X18 显式使用（cdk 内部有 #elif defined(__aarch64__)
  但都是 platform macros，不直接使用 X18）
- cdk/foundation 的 pthread 使用：OHOS 工具链应支持

## 预编译包

（首轮编译后再补充）

---
首轮开始: 2026-09-03
最终状态: draft
