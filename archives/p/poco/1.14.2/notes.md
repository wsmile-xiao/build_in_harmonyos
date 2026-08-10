# poco 1.14.2 编译笔记

## 编译信息
- 软件名: poco
- 版本: 1.14.2
- 构建系统: cmake
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 编译日期: 2026-05-26

## 构建选项
- CMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
- CMAKE_BUILD_TYPE=Release
- 共享库模式 (无静态库)

## 编译依赖
- openssl 3.5.6 (本地预编译)
- zlib 1.3.1 (内嵌版由 poco 自动使用)

## 源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| Foundation/src/Thread_POSIX.cpp | musl 缺 pthread_setaffinity_np/pthread_getaffinity_np | #ifdef __OHOS__ 使用 sched_setaffinity/sched_getaffinity + syscall(SYS_gettid) | 待 refresh-patch |

## 预编译风险扫描
- critical: 1 (PSCAN-MUSL-002: mremap in SQLite - 已有 fallback)
- medium: 4 (chmod/HMDFS, /tmp hardcoded, gettext/NLS, backtrace)
- info: 1 (Linux/glibc dependency docs)

## 遇到的问题
1. **pthread_setaffinity_np/pthread_getaffinity_np 缺失**: musl/OHOS 不提供这些 glibc 扩展函数。修复: 在 setAffinityImpl/getAffinityImpl 中用 `#ifdef __OHOS__` 分支使用 sched_setaffinity/sched_getaffinity 配合 syscall(SYS_gettid) 获取线程 tid。

2. **SSL证书问题**: HTTPS下载失败 (SSL: CERTIFICATE_VERIFY_FAILED)，手动用 curl -k 下载源码后复制到预期位置，init-build --no-download 继续。

3. **PKG_CONFIG_PATH**: 初始为空，需手动设置以让 cmake 找到 zlib/openssl 的 .pc 文件。

## 编译模块列表
- Foundation (核心库)
- Encodings
- XML
- JSON
- Util
- Net
- NetSSL (OpenSSL)
- Crypto
- Data + SQLite + MySQL
- ActiveRecord + ActiveRecordCompiler
- MongoDB
- Redis
- Prometheus
- JWT
- Zip
- PageCompiler + File2Page

## 验证结果
- .so 文件: 17 个共享库 (全部版本号 112)
- 头文件: 15 个模块目录
- 可执行文件: cpspc, f2cpsp, poco-arc
- cmake config: 完整 (PocoConfig.cmake 等)

## 预编译包
- poco-1.14.2-ohos-aarch64.tar.gz: 52MB
- poco-1.14.2-ohos-aarch64-debug.tar.gz: 15MB

**编译结束**: 2026-05-26
**最终状态**: published知识图谱草稿: E105 (musl pthread_setaffinity_np compat)
---

**编译结束**: 2026-08-08 01:05
**最终状态**: built
