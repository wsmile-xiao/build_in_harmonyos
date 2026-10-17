# rocksdb 11.1.2 — HarmonyOS PC 适配笔记

## 概要

| 项 | 值 |
|----|----|
| 上游 | https://github.com/facebook/rocksdb |
| tag | `v11.1.2` |
| 源码 sha256 | `3aba946031d27734eeea68ced7dd6f46629ba23a7b49945eb29aea68d1595311` |
| 构建系统 | CMake（Ninja generator） |
| 目标 | OHOS / armv8 / clang 15 / libc++ / Release / C++20 |
| 依赖 | zlib/1.3.1、snappy/1.2.2、lz4/1.10.0、bzip2/1.0.8（均为制品仓静态包） |
| 补丁 | 0001（fs_posix.cc）、0002（io_posix.cc） |
| 上一适配版本 | 8.7.3（已发布）与 9.10.0（**仅有 manifest/notes/patches，从未有 conanfile.py**） |

> ⚠ 本版本是**从零编写配方**，不是复制旧版本目录。仓库里
> `archives/r/rocksdb/9.10.0/` 只有 `README.md`、`manifest.yaml`、`notes.md`、
> `patches/`——没有 `conanfile.py`、`conandata.yml`、`test_package/`。
> 可复用的只有那 2 个补丁（已逐一重新验证）。

## 1. 新增的关键约束（相对 8.7.3 recipe）

### 1.1 C++20

`CMakeLists.txt:103-105`：

```cmake
if(NOT DEFINED CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 20)
endif()
```

farm profile 默认 `compiler.cppstd=17`。构建时由 CMake 自行提升到 20；
`test_package` 侧显式设置 `self.settings.compiler.cppstd = "20"`，因为
RocksDB 的公共头在 C++17 下无法编译。

### 1.2 `WITH_TESTS` 默认只在 Debug 打开 —— 且测试会**运行**目标二进制

`CMakeLists.txt:1234`：

```cmake
CMAKE_DEPENDENT_OPTION(WITH_TESTS ... ON "CMAKE_BUILD_TYPE STREQUAL Debug" OFF)
```

Release 交叉编译下本已 OFF，但配方**显式**再设一次 `WITH_TESTS=OFF`
（连同 `WITH_ALL_TESTS=OFF`），因为一旦打开，
`CMakeLists.txt:1604` 的 `gtest_discover_tests()` 会在构建期**执行**
刚链接出来的 aarch64 测试二进制来枚举用例——交叉编译必然失败。
测试框架是内置的 gtest 1.8.1（`third-party/gtest-1.8.1/fused-src`），
不依赖外部 gtest。

### 1.3 压缩编解码器全部依赖外部包

RocksDB **没有**内置压缩库（`third_party/` 里没有 snappy/zlib/zstd/lz4/bz2），
与 DuckDB 相反。CMake 侧的发现方式与目标名（`CMakeLists.txt`）：

| 库 | 发现方式 | 链接目标 | 行 |
|----|----------|----------|-----|
| zlib | `find_package(ZLIB REQUIRED)`（CMake 内置 MODULE） | `ZLIB::ZLIB` | 172-174 |
| snappy | `find_package(Snappy CONFIG)` → 回退 MODULE | **`Snappy::snappy`**（大写 S） | 163-168 |
| lz4 | `find_package(lz4 REQUIRED)`（CONFIG） | `lz4::lz4` | 190-192 |
| zstd | `find_package(zstd REQUIRED)`（CONFIG） | `zstd::zstd` | 195-199 |
| bzip2 | `find_package(BZip2 REQUIRED)`（CMake 内置 MODULE） | `${BZIP2_LIBRARIES}` | 179-186 |

### 1.4 zstd 被有意关闭（诚实说明）

制品仓上唯一的 zstd（`zstd/1.5.7.1`）是 **shared-only** 包。OHOS 的动态
加载器拒绝从用户可写路径加载共享库，这会让 test_package 无法运行。
因此本配方 `WITH_ZSTD=OFF`，改为启用 zlib/snappy/lz4/bzip2 四个**静态**
编解码器——RocksDB 仍然具备真实压缩能力，只是不含 zstd。

这是"依赖可用性约束下的取舍"，不是"为了省事关掉核心功能"：压缩是可选
特性，四个编解码器已足够验证压缩路径。

### 1.5 `WITH_LIBURING` 默认 ON

`CMakeLists.txt:92` 默认 `WITH_LIBURING=ON`。`find_package(uring)`
（`:349-355`）不是 REQUIRED，缺失时不会报错，但配方显式 `OFF`
以避免探测，并确保 `-DROCKSDB_IOURING_PRESENT` 不被定义。

### 1.6 `PORTABLE=1` 防御性设置

`CMakeLists.txt:303-316` 在 `PORTABLE=0`（默认）且
`-march=armv8-a+crc+crypto` 探测失败（`:268-275`）时会注入
`-march=native`——交叉编译下 clang 会拒绝。设 `PORTABLE=1` 可避免。

## 2. 补丁（2 个，均已对 11.1.2 重新验证）

两个补丁都来自 9.10.0 目录，但已针对 11.1.2 源码**实测**应用：

| 补丁 | 文件 | 变更 | 11.1.2 应用结果 |
|------|------|------|-----------------|
| 0001 | `env/fs_posix.cc` | `#if defined(OS_LINUX) \|\| defined(OS_SOLARIS) \|\| defined(OS_ANDROID)` → 追加 `\|\| defined(__OHOS__)` | 干净应用，无 fuzz |
| 0002 | `env/io_posix.cc` | `#if defined(OS_LINUX) \|\| defined(OS_ANDROID)` → 追加 `\|\| defined(__OHOS__)` | 干净应用，无 fuzz |

**根因**：这两处守卫 `<sys/statfs.h>` / `<sys/sysmacros.h>` 的包含。
RocksDB 的 `OS_LINUX` 由 `CMakeLists.txt:516-517` 的
`CMAKE_SYSTEM_NAME MATCHES "Linux"` 推导，而 OHOS 工具链下
`CMAKE_SYSTEM_NAME=OHOS`，两个条件都不成立 → `OS_LINUX` 未定义 →
头文件从未被包含。`__OHOS__` 是编译器内置宏，用它补齐守卫。

其余 OHOS 相关的符号在 11.1.2 中均**无硬依赖**（已逐一核查）：
`std::filesystem` 零命中；`eventfd`/`epoll`/`SO_REUSEPORT`/`pthread_cancel`
零命中；`execinfo.h`/`backtrace`、`sys/syscall.h`、`gettid` 全部在
`#ifdef OS_LINUX` 分支内（OHOS 下整段不编译）；`getauxval(AT_HWCAP)`
（`util/crc32c_arm64.cc:58,87`）经 `check_cxx_symbol_exists` 软探测，
缺失时 CRC32C 静默回退软件实现，构建仍成功。

## 3. 构建配置

```
-G Ninja
-DCMAKE_BUILD_TYPE=Release
-DWITH_ZLIB=ON -DWITH_SNAPPY=ON -DWITH_LZ4=ON -DWITH_BZ2=ON -DWITH_ZSTD=OFF
-DWITH_GFLAGS=OFF -DWITH_LIBURING=OFF -DWITH_JEMALLOC=OFF
-DWITH_TESTS=OFF -DWITH_ALL_TESTS=OFF
-DWITH_TOOLS=OFF -DWITH_CORE_TOOLS=OFF -DWITH_BENCHMARK_TOOLS=OFF
-DWITH_EXAMPLES=OFF -DWITH_BENCHMARK=OFF -DWITH_JNI=OFF
-DFAIL_ON_WARNINGS=OFF
-DPORTABLE=1
```

## 4. 测试：诚实申报

### 4.1 上游测试（未运行，如实申报）

| 项 | 值 |
|----|----|
| 框架 | 内置 gtest 1.8.1（`third-party/gtest-1.8.1/fused-src`） |
| 目标 | 每文件一个可执行文件（`CMakeLists.txt:1593-1595`），非单一 `rocksdb_test` |
| 规模 | `*_test.cc` **222** 个；CMake `TESTS` 列表 **213** 项（`CMakeLists.txt:1567`） |
| 启用条件 | `WITH_TESTS`（**仅 Debug 默认 ON**）+ `WITH_ALL_TESTS` |
| 聚合目标 | `rocksdb_check` = `add_custom_target(... ctest)`（`CMakeLists.txt:1580`） |
| 本次执行 | **未执行（NOT_RUN）** |

未执行的技术原因：

1. `CMakeLists.txt:1604` 的 `gtest_discover_tests(${exename} DISCOVERY_TIMEOUT 120)`
   在**构建期执行**每个刚链接的测试二进制来枚举用例。交叉编译场景下
   这些是 aarch64 目标二进制，无法在构建主机上执行——开启 `WITH_TESTS`
   会直接让构建失败，而不是"跳过测试"。
2. 因此上游套件在本配方中**结构性不可用**，如实申报 NOT_RUN，
   不把未运行的测试计为 PASS。

### 4.2 test_package（已执行，消费者视角）

`test_package/test_rocksdb.cpp` 通过 **C++ API** 真实调用被测库，
共 14 个断言，逐个打印 ok/FAIL：

| # | 动作 | 断言 |
|---|------|------|
| 1 | `DB::Open(options, path, &db)` | 返回 ok 且句柄非空 |
| 2-4 | `Put key1/key2/key3` | 三次均 ok |
| 5-6 | `Get key1` / `Get key3` | 值分别为 `value1` / `value3` |
| 7 | `Get no_such_key` | `IsNotFound()` |
| 8 | `Delete key2` | ok |
| 9 | `Get key2` | `IsNotFound()` |
| 10 | 迭代全键空间 | 迭代器状态 ok |
| 11 | 迭代计数 | 恰好 2 个存活键 |
| 12 | `Flush()` | ok |
| 13 | `Close()` | ok |

数据库目录使用 `$TMPDIR`（回退到当前工作目录）——OHOS 设备上 `/tmp`
是只读 tmpfs，不能作为数据库目录。

## 4.3 test_package 的 API 变更（11.x 实测踩到）

第一次 test_package 编译失败（库本体已 718/718 全部构建成功）：

```
test_rocksdb.cpp:56:28: error: no matching function for call to 'Open'
  rocksdb::Status status = rocksdb::DB::Open(options, path, &db);
include/rocksdb/db.h:139: note: candidate function not viable:
  no known conversion from 'rocksdb::DB **' to 'std::unique_ptr<DB> *'
```

11.x 的 `include/rocksdb/db.h:138-140` 只保留

```cpp
static Status Open(const Options& options, const std::string& name,
                   std::unique_ptr<DB>* dbptr);
```

**原始的 `DB**` 重载已被移除**，且没有 `Close()` 成员——句柄由
`unique_ptr` 析构时关闭。测试改为：

```cpp
std::unique_ptr<rocksdb::DB> db;
rocksdb::DB::Open(options, path, &db);
...
status = db->Flush(rocksdb::FlushOptions());
db.reset();                       // 析构即关闭（无 Close()）
```

## 5. 产物

`lib/librocksdb.a`（静态，默认）或 `lib/librocksdb.so`（`shared=True`）、
`include/rocksdb/**` 公共头、上游 CMake 包配置。
不构建 `db_bench` / `ldb` / `sst_dump` 等工具（`WITH_TOOLS=OFF`）——
本包定位为嵌入式库。

## 6. 参考

- 旧版本适配记录：`archives/r/rocksdb/8.7.3/`（制品仓已发布）、
  `archives/r/rocksdb/9.10.0/`（仅元数据）
- 上游：https://github.com/facebook/rocksdb
