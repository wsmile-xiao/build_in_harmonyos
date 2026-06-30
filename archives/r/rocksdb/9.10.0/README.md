# rocksdb 9.10.0 — OpenHarmony 编译版本

## 版本信息
- **版本**: 9.10.0
- **状态**: built
- **编译日期**: 2026-04-27
- **构建系统**: cmake
- **编译器**: clang (OHOS SDK)
- **架构**: aarch64-linux-ohos

## 源码
- **URL**: https://github.com/facebook/rocksdb/archive/refs/tags/v9.10.0.tar.gz

## 平台适配补丁 (2 个)

| # | 补丁文件 | 修改文件 | 说明 |
|---|---------|---------|------|
| 1 | 0001-env-fs_posix.cc.patch | env/fs_posix.cc | 添加 `\|\| defined(__OHOS__)` 到 `#if defined(OS_LINUX) \|\| defined(OS_SOLARIS) \|\| defined(OS_ANDROID)` |
| 2 | 0002-env-io_posix.cc.patch | env/io_posix.cc | 添加 `\|\| defined(__OHOS__)` 到 `#if defined(OS_LINUX) \|\| defined(OS_ANDROID)` |

## 与 6.4.6 的差异
- 9.10.0 有 `env/fs_posix.cc`（6.4.6 为 `env/env_posix.cc`）
- 9.10.0 的 io_posix.cc 使用 `#if defined(OS_LINUX) || defined(OS_ANDROID)`（6.4.6 为 `#ifdef OS_LINUX`）
- 9.10.0 不需要 C++17 升级（已使用更高标准）
- 9.10.0 不需要 channel.h mutable mutex 修复（已在上游修复）
- 9.10.0 不需要 force-include 机制（未遇到 musl 头文件冲突）

## 参考
- 官网: https://rocksdb.org/
- 源码: https://github.com/facebook/rocksdb
- 版本标签: v9.10.0
