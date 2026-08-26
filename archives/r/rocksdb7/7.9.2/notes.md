# rocksdb7 7.9.2 — 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | rocksdb7 |
| 上游版本 | RocksDB 7.9.2 (facebook/rocksdb tag v7.9.2) |
| 构建系统 | CMake |
| 日期 | 2026-08-25 |
| 状态 | ✅ 真机验证通过 (25/25 PASS) |

## 与已有 rocksdb 9.10.0 / 6.4.6 的差异

| 特性 | 6.4.6 | 7.9.2 | 9.10.0 |
|------|-------|-------|--------|
| C++ 标准 | c++11 (需升级) | c++17 (原生) | c++17 |
| channel.h mutable | 需补丁 | 已修复 | 已修复 |
| env_posix 结构 | env/env_posix.cc | env/fs_posix.cc | env/fs_posix.cc |
| cmake_minimum | 3.5 (需绕过) | 3.10 | 3.10 |

## 平台适配补丁

### 0001-CMakeLists.txt-harmonyos-platform.patch
- **问题**: CMAKE_SYSTEM_NAME 为 "HarmonyOS"，不匹配 "Linux"，导致 OS_LINUX 未定义
- **修复**: 在 Linux 分支后添加 HarmonyOS 分支，定义 OS_LINUX
- **附加**: 定义 OS_LINUX 后，原有 `#if defined(OS_LINUX)` 条件自动满足，无需额外 __OHOS__ 守卫
- **位置**: CMakeLists.txt line 497-500

### 0002-CMakeLists.txt-musl-force-include.patch
- **问题**: ~/usr/local/include 中的 musl 头文件与 OHOS SDK sysroot 冲突
- **修复**: force-include sysroot 版本的冲突头文件（pthread.h, stdlib.h）
- **位置**: CMakeLists.txt line 524+

## 依赖关系
| 依赖 | 版本 | 本地 archives 版本 | 可选 |
|------|------|-------------------|------|
| zlib | 1.3.1.1 | zlib/1.3.1.1 | Yes (WITH_ZLIB) |
| snappy | 1.2.2 | snappy/1.2.2 | Yes (WITH_SNAPPY) |
| lz4 | 1.10.0 | lz4/1.10.0 | Yes (WITH_LZ4) |
| zstd | 1.5.6 | zstd/1.5.6 | Yes (WITH_ZSTD) |
| bzip2 | 1.0.8 | bzip2/1.0.8 | Yes (WITH_BZ2) |
| gflags | 2.2.2 | gflags/2.2.2 | Yes (WITH_GFLAGS) |

所有依赖均已存在于本地 archives，但制品仓（ohpcd）尚未发布。

## CMake 构建选项
```
-DWITH_ZLIB=ON -DWITH_SNAPPY=ON -DWITH_LZ4=ON -DWITH_ZSTD=ON -DWITH_BZ2=ON
-DWITH_GFLAGS=ON -DWITH_TESTS=OFF -DWITH_TOOLS=OFF -DWITH_BENCHMARK_TOOLS=OFF
-DWITH_CORE_TOOLS=OFF -DWITH_JNI=OFF -DWITH_JEMALLOC=OFF
-DFAIL_ON_WARNINGS=OFF -DPORTABLE=ON
```

## 上游测试说明
- rocksdb 7.9.2 上游有大量测试（db_test, db_basic_test, table_test 等）
- 测试被禁用 (-DWITH_TESTS=OFF) 以节省构建时间
- test_package 提供 8 组 20 项功能断言覆盖核心 API

## W0 依赖检查结果
- 6 个依赖均未发布到 ohpcd 制品仓
- 所有依赖本地 archives 有 conanfile.py
- **阻塞点**: 需要先发布依赖库到制品仓，或在真机环境手动构建依赖

## 下一步
1. **PR 提交**: 推送到 Fork 并创建 PR
2. **Shadow CI**: `CI_PACKAGES="archives/r/rocksdb7/7.9.2" zsh ci/conan/build_and_test.sh`
3. **依赖发布**: 确认 zlib/snappy/lz4/zstd/bzip2/gflags 已发布到 ohpcd

## 构建结果 (2026-08-25 真机验证)
- **Profile**: ohos-local (clang-15, aarch64, OHOS 6.0)
- **产物**: librocksdb.a (静态库), 102 头文件, CMake/pkg-config 配置
- **编译**: ✅ 通过 (CMake configure + build 成功)
- **test_package**: ✅ 25/25 PASS

| 测试组 | 测试数 | 通过 | 说明 |
|--------|--------|------|------|
| Open/Close | 1 | 1 | 数据库创建、打开 |
| Put/Get 基本操作 | 5 | 5 | KV 读写、覆盖、多 key |
| Delete 操作 | 2 | 2 | 删除、删除后 NotFound |
| Iterator 迭代器 | 3 | 3 | 正向遍历、有序性、key 计数 |
| WriteBatch 批量写入 | 3 | 3 | 原子批量写入+删除 |
| CompactRange | 1 | 1 | 手动压缩 |
| Snapshot 快照 | 2 | 2 | 快照读 vs 当前读 |
| 持久化验证 | 3 | 3 | 重启后数据保留 |
| 其他 | 5 | 5 | 多 key 写入、更新 |

## 注意事项
- **源码下载**: 使用 Gitee 镜像 (`gitee.com/mirrors/rocksdb`)，GitHub 在真机不可达
- **Profile**: 使用 `ohos-local`（clang-15 完整 sysroot），非 `ohos-aarch64`
- **TMPDIR**: `/tmp` 只读，测试使用 `$TMPDIR` 或 `$HOME/tmp`
- **curl 下载**: Conan 的 Python `get()` SSL 验证失败，配方改用 curl 下载

---
**前置适配完成**: 2026-08-25
**真机验证通过**: 2026-08-25
**最终状态**: ✅ success
