# rocksdb 6.4.6 — OpenHarmony 编译版本

## 版本信息
- **版本**: 6.4.6
- **状态**: published
- **编译日期**: 2026-06-23
- **构建系统**: cmake
- **编译器**: OHOS SDK clang 15.0.4
- **架构**: aarch64-linux-ohos

## 源码
- **URL**: https://github.com/facebook/rocksdb/archive/refs/tags/v6.4.6.tar.gz
- **SHA256**: 3efeb3fb39e3bad444e63c49c1099d22fa07312f3cb9a8a546e551618f8c69b8
- **实际下载**: Gitee 镜像（GitHub 直连失败）

## 编译依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| zlib | 1.3.1 | 预编译包 |
| bzip2 | 1.0.8 | 预编译包 |
| lz4 | r131 | 预编译包 |
| zstd | 1.5.6 | 预编译包 |
| gflags | 2.2.2 | 预编译包 |
| snappy | 1.2.2 | 预编译包 |

## 平台适配补丁 (4 个)

| # | 补丁文件 | 修改文件 | 说明 |
|---|---------|---------|------|
| 1 | 0001-CMakeLists.txt.patch | CMakeLists.txt | HarmonyOS 平台检测 + C++17 升级 + force-include 头文件冲突修复 |
| 2 | 0002-env-env_posix.cc.patch | env/env_posix.cc | `__OHOS__` 守卫，包含 POSIX 头文件 |
| 3 | 0003-env-io_posix.cc.patch | env/io_posix.cc | `__OHOS__` 守卫，包含 POSIX 头文件 |
| 4 | 0004-util-channel.h.patch | util/channel.h | `mutable std::mutex` 修复 C++17 const 方法兼容性 |

## 编译产物
- librocksdb.a: 17,505,734 bytes (静态库)
- librocksdb.so: 7,571,968 bytes (动态库, ELF 64-bit LSB arm64)
- 79 个头文件
- CMake 配置文件

## 功能测试
- **结果**: 44/44 PASS (100%)
- **测试日期**: 2026-06-23
- **覆盖范围**: Open/Close, Put/Get/Delete, Iterator, WriteBatch, 持久化, CompactRange, Snapshot

## 预编译包
- rocksdb-6.4.6-ohos-aarch64.tar.gz (26MB)
- rocksdb-6.4.6-ohos-aarch64-debug.tar.gz (2.6MB)

## 已知限制
1. **链接需 `--allow-shlib-undefined`**: librocksdb.so 引用 `pthread_cond_clockwait`，OHOS sysroot libc 未导出但运行时可用
2. **需 force-include**: 编译链接 rocksdb 的程序需使用 `ohos_sysroot_force_include.h` 解决 musl/sysroot 头文件冲突
3. **C++17 最低标准**: OHOS SDK libc++ 头文件要求 C++17

## 与 9.10.0 的差异
- 6.4.6 有 `env_posix.cc` 而非 `env/fs_posix.cc`（9.10.0 结构）
- 6.4.6 的 io_posix.cc 使用 `#ifdef OS_LINUX` 而非 `#if defined(OS_LINUX) || defined(OS_ANDROID)`
- 6.4.6 强制 c++11，需要升级到 c++17
- 6.4.6 的 channel.h 有 const 方法锁定问题（9.10.0 已修复）

## 参考
- 官网: https://rocksdb.org/
- 源码: https://github.com/facebook/rocksdb
- 版本标签: v6.4.6
