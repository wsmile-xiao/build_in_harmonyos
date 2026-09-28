# libbigwig 0.4.9 适配笔记

## 上游信息
- 仓库: https://github.com/dpryan79/libBigWig
- 版本: 0.4.9 (官方 tag 0.4.9 tarball)
- 语言: C (CMakeLists.txt project(libBigWig LANGUAGES C))
- License: MIT
- 构建系统: CMake (>=3.8), 同时附带一个 Makefile (非主构建入口)

## 关键决策
1. **WITH_CURL=OFF**: curl 在 ohpcd 制品仓未发布（conan download 探测全部版本返回
   "system acceleration policy not enabled" = 配方未发布），且 curl 是上游**可选**依赖
   （CMakeLists option WITH_CURL 默认 ON，关闭后定义 NOCURL，源码 io.c/bwRead.c 全部
   curl 路径均有 `#ifndef NOCURL` 守卫）。关掉 curl 是上游支持的合法配置，远端测试
   （testRemote/testRemoteManyContigs，需 curl）不适用，本地测试不受影响。
2. **zlib/1.3.1 依赖**: 上游 `find_package(ZLIB REQUIRED)`，zlib 已在 ohpcd 发布（探测确认）。
   WITH_ZLIBNG=OFF 使用标准 zlib。
3. **ZLIB::ZLIB 桥接**: 上游 CMakeLists 用 find_package(ZLIB)/ZLIB::ZLIB（大写），
   Conan CMakeDeps 生成小写 zlib-config.cmake + zlib::zlib 目标；在大小写敏感 Linux 上
   find_package(ZLIB) 找不到大写配置。conanfile generate() 用 CMAKE_PROJECT_INCLUDE
   桥接片段：写 ZLIBConfig.cmake + `add_library(ZLIB::ZLIB ALIAS zlib::zlib)`（同 libcurl 配方模式）。
4. **静态库**: 上游 BUILD_SHARED_LIBS 默认 OFF，配方默认 shared=False。

## 构建与测试实测
- 环境: clang 15.0.4 (OHOS 适配版 conan 2.29.1, profile ohos-aarch64)
- cmake configure + make: 通过，产物 libBigWig.a
- 本地测试（WITH_CURL=OFF 后 test/CMakeLists.txt 只构建本地测试）:
  - exampleWrite: exit 0 ✅
  - testIterator (test/test.bw 1 1000): exit 0 ✅
  - testLocal (test/test.bw): exit 0 ✅
  - testWrite (test/test.bw test/out.bw): exit 0 ✅
  - testBigBed: 需要上游未附带的 .bb 输入文件（bigBed 格式），用 .bw 输入属误用
    （测试程序读文件头后因格式不符退出），二进制本身构建正常，无法以现有数据运行。
- 远端测试 testRemote/testRemoteManyContigs 需 curl，配方 WITH_CURL=OFF 不构建（上游设计如此）。

## 知识要点
- lang-preflight 会把源码包内 docs/html/ 的 Doxygen 生成物（.js/.html）计入源码统计，
  导致纯 C 库被误判为 mixed/nodejs → env_unsupported 误报。真实判定应以
  manifest（CMakeLists project LANGUAGES C）+ 排除 docs 后的源码统计为准。
- CMake 4.x 默认 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，Find<Name>.cmake 模块 shim
  不会先于 CMakeDeps config 生效；CMake 4 下桥接需用 CMAKE_PROJECT_INCLUDE 或
  直接写大写 Config.cmake。
---

**编译结束**: 2026-09-23 00:35
**最终状态**: built
