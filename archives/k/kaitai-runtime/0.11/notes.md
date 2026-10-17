# kaitai-runtime 0.11 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang/clang++ (Clang 15.0.4, aarch64)
- 状态: published

## 编译步骤

```bash
# 源码: GitHub tag 0.11 (codeload 通道, sha256 见 manifest)
# 依赖: zlib/1.3.2 (conan ohpcd), gtest 1.17.0 (conan cache, 仅上游测试用)
cmake -S . -B build-dir -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DGTest_DIR=~/.conan2/p/gtest*/p/lib/cmake/GTest \
  -DZLIB_INCLUDE_DIR=~/.conan2/p/zlib*/p/include \
  -DZLIB_LIBRARY=~/.conan2/p/zlib*/p/lib/libz.a
cmake --build build-dir -j4
# 上游测试
(cd build-dir/tests && ./unittest)   # 53/53 PASSED
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 主站 443 超时, init-build 下载失败 | 网络仅 codeload/gitcode 可达 | 用 codeload.github.com tar.gz 通道下载 tag 0.11, 放入 ~/tmp/builds 后重跑 init-build |
| 2 | tests/unittest.cpp 编译失败: no member 'process_zlib' | CMake 未找到 ZLIB → KS_ZLIB 未定义, 但测试无条件调用 process_zlib | 安装 zlib/1.3.2 (conan ohpcd, CI profile), CMake 传入 ZLIB_INCLUDE_DIR/LIBRARY |
| 3 | 上游测试 2/53 失败: bytes_to_str_ibm437 / bytes_to_str_big_dest | HarmonyOS/musl iconv 不识别 IBM437/IBM-437 别名 (只认 CP437/CP-437) | 补丁 0001: iconv_open EINVAL 时回退到平台别名 CP437 重试; 复测 53/53 通过 |

## 源码修改

- patches/0001-ibm437-iconv-alias-fallback.patch — kaitai/kaitaistream.cpp bytes_to_str: EINVAL 时 IBM437/IBM-437 → CP437 别名重试。

## 依赖版本

- zlib/1.3.2 (conan ohpcd 预编译, 静态 libz.a)
- gtest/1.17.0 (conan cache, 仅上游测试构建用, 非配方依赖)

## 验证结果

- 上游测试: 53/53 PASSED (含 IBM437 编码与 10MB big_dest 用例)
- test_package: 消费者 smoke test (kstream 读取 + IBM437 编码转换) 通过
- R26 检查: 包内 libkaitai_struct_cpp_stl_runtime 与系统库无同名冲突
- HarmonyOS 专项: ELF64 AArch64; 动态依赖仅 libc++_shared.so + libc.so; 无 SONAME (上游 CMake 未设 SOVERSION, 属上游默认行为, 不阻断)
---

**编译结束**: 2026-09-03 10:24
**最终状态**: built
