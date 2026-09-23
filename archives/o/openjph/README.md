# OpenJPH for HarmonyOS

## 概述

OpenJPH 是 JPEG2000 Part-15（HTJ2K / JPH，ISO/IEC 15444-15）标准的开源实现，
包含编解码库和命令行工具。与传统 JPEG2000（openjpeg）是不同的项目。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | openjph |
| 版本 | 0.31.0 |
| 官方仓库 | https://github.com/aous72/OpenJPH |
| 许可证 | BSD-2-Clause |
| 构建系统 | CMake (C/C++) |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS PC（OHOS 6.0） |
| 架构 | aarch64 |
| 编译器 | clang (LLVM 15) |

## 构建产物

- `libopenjph.so` — HTJ2K 编解码共享库
- `ojph_compress` — HTJ2K 编码器（PPM/YUV → .j2c/.jph）
- `ojph_expand` — HTJ2K 解码器（.j2c/.jph → PPM/YUV）
- `include/openjph/*.h` — 公开头文件
- `openjph-config.cmake`、`openjph.pc` — 构建集成文件

## 适配要点

1. CMake 构建系统，库本体零补丁即可在 OHOS 上编译（target_arch 通过编译器宏检测架构，交叉编译安全）；
   仅 1 个测试集成补丁（`patches/0001-tests-use-conan-gtest-and-local-codestreams.patch`）
2. 需要设置 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG="-Wl,-soname,"` 以修复 OHOS 上的 SONAME 缺失问题
3. 裁剪 TIFF 支持（`OJPH_ENABLE_TIFF_SUPPORT=OFF`），PPM/YUV I/O 不受影响，运行时零外部依赖
4. 0.31.0 上游已无 TBB 依赖，核心编解码自包含
5. 上游 gtest 套件（`tests/`，86 用例）已纳入 Conan 构建并真实执行：
   googletest 用制品仓已发布的 `gtest/1.17.0`（test_requires），测试码流
   `jp2k_test_codestreams` 作为 `conandata.yml` 的 `test_codestreams` 源随配方下载（commit 固定），
   补丁 0001 将上游 `tests/CMakeLists.txt` 的 FetchContent 联网下载替换为上述本地来源；
   `conanfile.py` 的 `build()` 末尾调用 `ctest`，86/86 用例随构建真实执行（失败即构建失败）。
   test_package 另提供消费者视角的编解码闭环 + 库级 API 冒烟（5/5）