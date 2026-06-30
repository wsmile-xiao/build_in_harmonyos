# scip 10.0.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-10
- 编译器: Clang 15.0.4 (harmonybrew)
- 目标平台: HarmonyOS (aarch64)
- 状态: built

## 编译步骤

1. 源码下载: `curl -kL -o scip-10.0.2.tar.gz https://github.com/scipopt/scip/archive/refs/tags/v10.0.2.tar.gz` (SSL证书问题需使用 -k 参数)
2. 初始化构建: `python3 ohc-run.py init-build scip --no-download` (自动下载失败因SSL问题，改为手动下载)
3. 嵌套目录提升: 解压后scip-10.0.2/scip-10.0.2 → scip-10.0.2 (消除嵌套)
4. cmake配置:
   ```bash
   cmake .. \
     -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
     -DAUTOBUILD=ON \
     -DSHARED=OFF \
     -DREADLINE=OFF \
     -DGMP=OFF \
     -DPAPILO=OFF \
     -DZIMPL=OFF \
     -DAMPL=OFF \
     -DIPOPT=OFF \
     -DTPI=tny \
     -DEXPRINT=none \
     -DSYM=none \
     -DTHREADSAFE=ON \
     -DLPS=none \
     -DZLIB=ON \
     -DZLIB_LIBRARY=/storage/Users/currentUser/usr/local/lib/libz.a \
     -DZLIB_INCLUDE_DIR=/storage/Users/currentUser/usr/local/include
   ```
5. 编译: `make -j1` (耗时约53分钟, 420个目标文件)
6. 安装: `make install DESTDIR=$TEST_PREFIX`
7. 打包: `python3 ohc-run.py package scip 10.0.2`
8. 验证: `python3 ohc-run.py verify-build scip 10.0.2 --install-prefix=$TEST_PREFIX/$DEFAULT_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | HarmonyOS环境中Python urllib SSL证书路径配置问题 | 创建symlink: `ln -sf /usr/local/ssl/cert.pem /usr/local/etc/ssl/cert.pem`; curl使用 -k 参数 |
| 2 | ohc-run.py自动下载失败 | SSL证书问题导致HTTPS下载中断 | 手动curl -kL下载后使用 --no-download 参数初始化 |
| 3 | cmake将HarmonyOS识别为unknown platform | CMake缺少Platform/HarmonyOS模块 | 不影响编译，cmake仍可正常工作 |
| 4 | ohc-run.py误判构建系统为autotools | SCIP同时包含CMakeLists.txt和Makefile | 手动修正manifest.yaml中build_system为cmake |
| 5 | 无可用LP solver | SoPlex/HiGHS/GLPK均未预编译 | 使用LPS=none配置，SCIP仍可编译但无LP求解能力 |
| 6 | verify-build找不到bin文件 | DESTDIR模式导致安装路径嵌套 | 使用 --install-prefix 指向正确路径 |
| 7 | manifest缺少build_system字段 | manifest.yaml使用嵌套格式而非顶层字段 | 添加 `build_system: cmake` 顶层字段 |

## 源码修改

无补丁，无源码修改。SCIP原始代码在HarmonyOS上编译无兼容性问题。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| zlib | 1.3.1 | 静态库 libz.a, 来自预编译包 |
| TinyCThread | 1.2 | SCIP内置, 线程支持 |

## 验证结果

```bash
$ scip --version
SCIP version 10.0.2 [precision: 8 byte] [memory: block] [mode: optimized] [LP solver: NONE] [GitHash: NoGitInfo]
Copyright (c) 2002-2026 Zuse Institute Berlin (ZIB)

External libraries:
  ZLIB 1.3.1           General purpose compression library
  TinyCThread 1.2      small portable implementation of the C11 threads API

Compiler: clang 15.0.4
Build options:
 OSTYPE=HarmonyOS-HongMeng Kernel 1.12.0
 COMP=Clang 15.0.4
 BUILD=Release
 LPS=none
 THREADSAFE=ON;FORCE
 SHARED=OFF
 VERSION=10.0.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| scip-10.0.2-ohos-aarch64.tar.gz | 27692KB | 预编译包 (含bin/scip, lib/libscip.a, headers, cmake configs) |
| scip-10.0.2-ohos-aarch64-debug.tar.gz | 675KB | 调试符号包 |

## 注意事项

1. SCIP编译无LP solver支持(LPS=none)，因此无法求解LP/MIP问题。如需完整功能需安装SoPlex或HiGHS
2. 静态库 libscip.a (13.4MB) 含所有SCIP核心功能
3. 编译耗时约53分钟(cmake配置247秒 + make 3197秒)，单线程编译
4. DESTDIR安装路径需注意嵌套问题: `DESTDIR/storage/Users/currentUser/usr/local/bin/scip`

---

**编译结束**: 2026-06-10 17:33
**最终状态**: built