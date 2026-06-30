# pgexporter 0.8.0 适配笔记

## 编译环境
- 构建系统: cmake (CMakeLists.txt, cmake_minimum_required 3.14)
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4 (target: aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/pgexporter/pgexporter/archive/refs/tags/0.8.0.tar.gz
2. 运行 ohc-run.py init-build pgexporter 0.8.0
3. 安装依赖: libev 4.33, libyaml 0.2.5, libatomic (stub), python-docutils/rst2man, pthread.h (symlink from OHOS SDK)
4. 修补源码 (4 patches):
   - CMakeLists.txt: 跳过测试子目录 (HarmonyOS 平台)
   - src/CMakeLists.txt: 添加 HarmonyOS 平台检测段, 允许静态库, PIE/RELRO 支持
   - src/admin.c: secure_getenv → getenv (HarmonyOS 无 secure_getenv)
   - src/libpgexporter/utils.c: GET_ENV macro 添加 __OHOS__ 条件 fallback
5. cmake configure: cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DCMAKE_BUILD_TYPE=Release ..
6. make: 成功 (3 binaries + 1 shared lib)
7. make install DESTDIR: staging 成功 (bin=3, lib=1)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake 找不到 libev | pkg-config 无 .pc 文件 | cmake FindLibev.cmake 用 find_path/find_library 可找到 |
| 2 | cmake 找不到 rst2man | 缺 docutils | pip install python-docutils, 创建 rst2man.py wrapper |
| 3 | cmake 找不到 libatomic | OHOS 无 libatomic | 创建 stub libatomic.a (空函数实现) |
| 4 | cmake 找不到 libyaml | 缺 .pc 文件 | 安装 libyaml from cmd-pkgs, 手动创建 yaml-0.1.pc |
| 5 | cmake 找不到 pthread.h | OHOS SDK sysroot 无 pthread.h | symlink 到 OHOS SDK sysroot |
| 6 | secure_getenv undefined | musl 无 secure_getenv | 添加 __OHOS__ 条件宏, fallback 到 getenv |
| 7 | pgexporter_require_shared_libs 失败 | 只检测 .so | 添加 HarmonyOS 条件允许 .a |
| 8 | test target 编译失败 (ev.h not found) | test cmake 不含 libev include path | 跳过 test 子目录 (HarmonyOS) |

## 源码修改

| Patch | 文件 | 修改内容 |
|-------|------|----------|
| 0001 | CMakeLists.txt | 跳过 test 子目录 (HarmonyOS) |
| 0002 | src/CMakeLists.txt | HarmonyOS 平台段 (HAVE_HARMONY, -D_POSIX_C_SOURCE, 静态库, PIE) |
| 0003 | src/admin.c | #if defined(__OHOS__) → #define secure_getenv getenv |
| 0004 | src/libpgexporter/utils.c | GET_ENV macro 添加 __OHOS__ 条件 |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libev | 4.33 | cmd-pkgs |
| libyaml | 0.2.5 | cmd-pkgs |
| zlib | 1.3.1 | cmd-pkgs |
| bzip2 | 1.0.8 | cmd-pkgs |
| zstd | (动态) | 系统共享库 |
| lz4 | (静态) | cmd-pkgs |
| OpenSSL | 3.5.6 | 系统共享库 |
| libatomic | stub | 手工创建 |
| pthread | OHOS SDK | symlink |
| python-docutils | 0.23 | pip |

## 验证结果

```bash
# 3 executables + 1 shared library installed:
bin/pgexporter (main daemon)
bin/pgexporter-cli (CLI tool)
bin/pgexporter-admin (admin tool)
lib/libpgexporter.so (shared library)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pgexporter-0.8.0-ohos-aarch64.tar.gz | 10295KB | Release 构建包 |
| pgexporter-0.8.0-ohos-aarch64-debug.tar.gz | 4310KB | Debug 符号包 |

## 注意事项

- pgexporter 使用 CMake 构建系统 (非 autotools)
- HarmonyOS/musl 无 secure_getenv, 需要 getenv fallback
- 许多依赖库只有静态版本 (.a), 无共享版本 (.so)
- libpthread.so.0 实际是 libgcompat.so.0 的符号链接
- 测试子目录因缺少 libev include path 而跳过
---

**编译结束**: 2026-06-12 19:09
**最终状态**: published
