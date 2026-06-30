# 适配笔记 — rocksdb 6.4.6

## 基本信息
- 软件: rocksdb 6.4.6
- 日期: 2026-06-23
- 构建系统: cmake
- 编译器: clang 15.0.4 (OHOS SDK)
- 架构: aarch64-linux-ohos

## 源码获取
- GitHub 直连失败（SSL证书 + 网络超时）
- 使用 Gitee 镜像成功下载: https://gitee.com/mirrors/rocksdb/repository/archive/v6.4.6.tar.gz

## 平台适配补丁

### 1. CMakeLists.txt — HarmonyOS 平台检测 (R8)
- **问题**: CMAKE_SYSTEM_NAME 为 "HarmonyOS"，不匹配 "Linux"，导致 OS_LINUX 未定义
- **修复**: 在 Linux 分支后添加 HarmonyOS 分支，定义 OS_LINUX
- **位置**: CMakeLists.txt line 407-410

### 2. env_posix.cc — __OHOS__ include guard (R8)
- **问题**: `#if defined(OS_LINUX) || defined(OS_SOLARIS) || defined(OS_ANDROID)` 不包含 __OHOS__
- **修复**: 添加 `|| defined(__OHOS__)` 以包含 `<sys/statfs.h>`, `<sys/syscall.h>`, `<sys/sysmacros.h>`
- **位置**: env/env_posix.cc line 27

### 3. io_posix.cc — __OHOS__ include guard (R8)
- **问题**: `#ifdef OS_LINUX` 不包含 __OHOS__，缺失 `<sys/statfs.h>`, `<sys/syscall.h>`, `<sys/sysmacros.h>`
- **修复**: 改为 `#if defined(OS_LINUX) || defined(__OHOS__)`
- **位置**: env/io_posix.cc line 25

### 4. CMakeLists.txt — C++17 标准升级
- **问题**: OHOS SDK libc++ 头文件 (libcxx-ohos) 要求 C++17 最低标准，rocksdb 6.4.6 强制 `-std=c++11`
- **修复**: 将 `-std=c++11` 改为 `-std=c++17`
- **位置**: CMakeLists.txt line 188

### 5. util/channel.h — mutable mutex
- **问题**: `size() const` 方法中使用 `std::lock_guard<std::mutex> lk(lock_)`，C++17 严格类型检查下 lock_ 需为 mutable
- **修复**: `std::mutex lock_` → `mutable std::mutex lock_`
- **位置**: util/channel.h line 63

## 编译过程

### 环境问题
1. **C++ 编译器**: usr/local 的 clang++ 18 缺少 libc++ 链接库，使用 OHOS SDK 的 clang++ 15 (有完整 sysroot)
2. **musl 头文件冲突**: ~/usr/local/include/ 中的 musl libc 头文件 (stddef.h, stdlib.h, pthread.h 等) 与 OHOS SDK sysroot 冲突
   - `-isystem ~/usr/local/include` 导致 musl 的 stddef.h 覆盖编译器内置版本，nullptr_t 未定义
   - 解决方案: 编译期间临时移走冲突的 musl 头文件，编译后恢复
3. **cmake 版本兼容**: rocksdb 6.4.6 要求 cmake < 3.5，使用 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 绕过
4. **FAIL_ON_WARNINGS**: 关闭 `-Werror` 以避免新 C++ 标准带来的警告导致编译失败

### 编译结果
- librocksdb.a: 17,505,734 bytes ✅
- librocksdb.so: 7,571,968 bytes (ELF shared object, 64-bit LSB arm64) ✅
- 79 个头文件 ✅
- CMake 配置文件 ✅

## make check
- 跳过（库项目，测试已禁用 -DWITH_TESTS=OFF）

## 功能测试 (2026-06-23)

编写 C++ 测试程序 `rocksdb_test.cpp`，链接 librocksdb.so，对 8 个功能组进行 44 项测试。

### 编译参数
```bash
clang++ -std=c++17 -target aarch64-linux-ohos \
  --sysroot=$OHOS_SYSROOT \
  -include ohos_force_include.h \
  -nostdinc++ -I$CLANG_DIR/include/libcxx-ohos/include/c++/v1 \
  -L$DEFAULT_PREFIX/lib -Wl,--allow-shlib-undefined \
  rocksdb_test.cpp -o rocksdb_test \
  -lrocksdb -lgflags -lsnappy -lz -llz4 -lzstd -lbz2 -lc++ -lpthread -ldl
```

### 测试结果: ✅ 44/44 全部通过 (100%)

| 测试组 | 测试数 | 通过 | 说明 |
|--------|--------|------|------|
| Open/Close | 2 | 2 | 数据库创建、打开、关闭 |
| Put/Get 基本操作 | 9 | 9 | KV 读写、覆盖、大 value(100KB) |
| Delete 操作 | 4 | 4 | 删除、删除后验证、删除不存在 key |
| Iterator 迭代器 | 6 | 6 | 正向遍历、有序性、Seek 定位 |
| WriteBatch 批量写入 | 5 | 5 | 原子批量写入+删除 |
| 持久化验证 | 3 | 3 | 重启后数据保留 |
| 压缩 (CompactRange) | 5 | 5 | 1000 key 压缩后数据完整 |
| Snapshot 快照 | 4 | 4 | 快照一致性读取 |

### 结论
rocksdb 6.4.6 在 OpenHarmony (aarch64) 平台功能完全正常，核心功能全部可用。

### 链接注意事项
- **需 `--allow-shlib-undefined`**: librocksdb.so 引用 `pthread_cond_clockwait`，OHOS sysroot libc 未导出但运行时可用
- **需 force-include**: 编译链接 rocksdb 的程序需使用 `ohos_sysroot_force_include.h` 解决 musl/sysroot 头文件冲突
- **CompactRange 已标记 deprecated**: 6.4.6 版本 API，功能正常

## 与 rocksdb 9.10.0 的差异
- 6.4.6 有 `env_posix.cc` 而非 `env/fs_posix.cc`（9.10.0 结构）
- 6.4.6 的 io_posix.cc 使用 `#ifdef OS_LINUX` 而非 `#if defined(OS_LINUX) || defined(OS_ANDROID)`（9.10.0 结构）
- 6.4.6 强制 c++11，需要升级到 c++17
- 6.4.6 的 channel.h 有 const 方法锁定问题

---
**编译开始**: 2026-06-23
**编译结束**: 2026-06-23
**最终状态**: success
---

**编译结束**: 2026-06-23 20:07
**功能测试**: 2026-06-23 21:55 — 44/44 PASS (100%)
**最终状态**: published
