# pgexporter 0.8.0 — HarmonyOS/OpenHarmony aarch64 构建

## 简介
pgexporter 是一个 PostgreSQL 指标导出器，用于 Prometheus 监控。本项目为 HarmonyOS/OpenHarmony aarch64 平台的移植构建。

## 补丁说明
- **0001-CMakeLists.txt.patch**: 跳过测试子目录 (HarmonyOS 平台不包含 libev test include path)
- **0002-src-CMakeLists.txt.patch**: 添加 HarmonyOS 平台检测段 (HAVE_HARMONY, -D_POSIX_C_SOURCE, 静态库允许, PIE/RELRO 支持)
- **0003-src-admin.c.patch**: secure_getenv → getenv 条件宏 (HarmonyOS/musl 无 secure_getenv)
- **0004-src-libpgexporter-utils.c.patch**: GET_ENV macro 添加 __OHOS__ 条件 fallback

## 遇到的问题
1. **secure_getenv 不可用**: HarmonyOS/musl libc 不提供 secure_getenv 函数，需添加条件编译宏 fallback 到 getenv
2. **依赖库只有静态版本**: HarmonyOS 上 libev、libyaml、libz、liblz4 等只提供 .a 静态库，需修改 CMake 检测逻辑允许静态库
3. **libatomic 缺失**: 创建 stub libatomic.a 提供空函数实现
4. **pthread.h 路径**: symlink 到 OHOS SDK sysroot
5. **测试子目录编译失败**: test 目标缺少 libev include path，跳过测试构建

## 构建产物
- `pgexporter-0.8.0-ohos-aarch64.tar.gz`: Release 构建包 (~10MB)
- `pgexporter-0.8.0-ohos-aarch64-debug.tar.gz`: Debug 符号包 (~4MB)

## 依赖
- libev 4.33, libyaml 0.2.5, OpenSSL 3.5.6, zlib 1.3.1, bzip2 1.0.8, lz4, zstd, libatomic (stub), pthread (OHOS SDK)
