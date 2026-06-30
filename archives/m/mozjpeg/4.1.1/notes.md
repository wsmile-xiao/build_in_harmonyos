# mozjpeg 4.1.1 适配笔记

## 编译环境
- 构建系统: cmake (with Ninja generator)
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. `init-build mozjpeg 4.1.1` — 初始化构建环境
2. 源码下载通过镜像 ghfast.top 完成（GitHub直连HTTPS超时）
3. cmake 配置（关键：使用Ninja生成器，避免GNU Make jobserver mkfifo问题）:
```bash
/data/service/hnp/bin/cmake -G Ninja \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DWITH_SIMD=0 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_MAKE_PROGRAM=ninja \
  -DCMAKE_COMMAND=/data/service/hnp/bin/cmake \
  ..
```
4. `ninja -j2` — 编译（295/295 目标完成）
5. `DESTDIR=$TEST_PREFIX cmake --install .` — staging 安装
6. ELF签名 + 安全弹窗验证 → cjpeg/djpeg/jpegtran 均输出 mozjpeg version 4.1.1
7. `ctest --output-on-failure` — 216/216 测试全部通过
8. `ohc-run.py package mozjpeg 4.1.1` — 打包预编译包
9. `cmake --install .`（不带DESTDIR）→ 本地安装到 $DEFAULT_PREFIX
10. 用户验证 → cjpeg/djpeg/jpegtran -version 均正常

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub HTTPS下载超时 | 网络连接受限 | 使用 ghfast.top 镜像下载 |
| 2 | cmake -G "Unix Makefiles" try-compile失败 "permission denied" | GNU Make 4.4.1 jobserver使用mkfifo，HMDFS不支持mkfifo | 改用Ninja生成器（无mkfifo需求） |
| 3 | cmake版本兼容性警告 | mozjpeg cmake_minimum_required(VERSION 2.5)低于cmake 4.1要求 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 4 | ~/usr/local/bin/cmake无法执行(ELF未签名) | cmd-pkgs安装的cmake缺少ELF签名 | 使用系统cmake /data/service/hnp/bin/cmake + -DCMAKE_COMMAND设置 |
| 5 | 缺少nasm汇编器 | nasm不可用且cmd-pkgs无预编译包 | 使用 -DWITH_SIMD=0 禁用SIMD优化 |
| 6 | staging目录中binaries无法直接运行(RPATH缺失) | cmake安装未设置RPATH | 打包脚本(ohc-run.py package)自动处理RPATH；运行时用LD_LIBRARY_PATH |

## 依赖版本

- zlib/1.3.1 (libz.so, libz.a)
- libpng/1.6.43 (libpng.so, liblibpng16_static.a)

## 验证结果

```bash
$ cjpeg -version
mozjpeg version 4.1.1 (build 20260526)
$ djpeg -version
mozjpeg version 4.1.1 (build 20260526)
$ jpegtran -version
mozjpeg version 4.1.1 (build 20260526)
$ ctest --output-on-failure
100% tests passed, 0 tests failed out of 216
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mozjpeg-4.1.1-ohos-aarch64.tar.gz | 3610KB | Release预编译包(含strip+ELF签名+RPATH) |
| mozjpeg-4.1.1-ohos-aarch64-debug.tar.gz | 420KB | Debug预编译包 |

## 注意事项

- mozjpeg必须用Ninja生成器编译（HMDFS不支持mkfifo，GNU Make jobserver会失败）
- 需要指定 -DCMAKE_COMMAND=/data/service/hnp/bin/cmake 避免使用未签名的cmd-pkgs cmake
- -DWITH_SIMD=0 禁用SIMD（nasm不可用），性能会略低但功能完整
- cmake --install 用于安装（非 ninja install），因为DESTDIR参数需通过cmake传递---

**编译结束**: 2026-05-26 11:45
**最终状态**: built
---

**编译结束**: 2026-05-26 11:48
**最终状态**: built
