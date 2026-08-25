# miniz 3.1.2 适配笔记

## 上游调查（3.1.2 tag, commit 77d0dce, 2026-07-01）

- 仓库：https://github.com/richgel999/miniz
- 源码 tarball：`https://github.com/richgel999/miniz/archive/refs/tags/3.1.2.tar.gz`
- sha256：`98468f8924934b723276680f85238b6c78bf1f8b49b4459cc9b7214a20e2e9fb`
- 许可：MIT
- 语言：纯 C（C90）
- 外部依赖：无（仅 libc；miniz_zip.c 非 Windows 路径用 ftello/fseeko/stat）

### 源码结构

```
miniz.c / miniz.h            zlib-compat API (mz_compress/uncompress/adler32/crc32/...)
miniz_tinfl.c/.h             单函数 inflate 解码器
miniz_tdef.c/.h              deflate 压缩器
miniz_zip.c/.h               ZIP 归档读写
miniz_common.h               公共类型 (mz_uint8/mz_bool/mz_uint32 ...)
CMakeLists.txt               上游原生 CMake
Config.cmake.in / miniz.pc.in  cmake package config / pkg-config 模板
examples/ example1..6.c      示例（关闭）
tests/  catch_amalgamated.*  上游 Catch2 单测 + fuzzers（关闭）
```

### 上游 CMake option（实际 3.1.2 CMakeLists.txt 声明）

| option | 默认（独立构建） | 本配方 |
|--------|------------------|--------|
| `BUILD_EXAMPLES` | ON | OFF（关闭示例） |
| `BUILD_FUZZERS` | OFF | OFF（关闭 fuzz） |
| `BUILD_TESTS` | ON | OFF（关闭上游 Catch2 测试，需 C++20） |
| `AMALGAMATE_SOURCES` | OFF | OFF（用原生多文件构建） |
| `BUILD_HEADER_ONLY` | OFF | OFF |
| `BUILD_SHARED_LIBS` | OFF | OFF（R26：与宿主 zlib 同名，强制静态） |
| `BUILD_NO_STDIO` | OFF | OFF（保留 stdio） |
| `INSTALL_PROJECT` | ON | ON（安装 lib/头/cmake config/pkg-config） |

非 amalgamation 路径编译 `miniz.c miniz_zip.c miniz_tinfl.c miniz_tdef.c`，并对共享库
`set_target_properties(... VERSION 3.1.2 SOVERSION 3)`。静态构建不产生 .so，无 SONAME
质量门负担。`generate_export_header(miniz)` 生成 `miniz_export.h`，静态消费方需定义
`MINIZ_STATIC_DEFINE`（本配方在 `cpp_info.defines` 声明）。

## 编译环境

- 构建系统：cmake（上游原生 CMakeLists.txt）
- 编译日期：2026-08-24
- 编译器：clang 15 / 目标 aarch64-linux-ohos
- profile：ci/conan/profiles/ohos-aarch64
- 状态：built

## 编译步骤

```bash
# conan create 走 CMake 构建：
#   cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake \
#         -DBUILD_SHARED_LIBS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_FUZZERS=OFF \
#         -DBUILD_TESTS=OFF -DBUILD_NO_STDIO=OFF -DINSTALL_PROJECT=ON <src>
#   cmake --build . -- -j
#   cmake --install . --prefix <pkg>
# 产物：libminiz.a + include/miniz/{miniz.h,miniz_common.h,miniz_tdef.h,
#        miniz_tinfl.h,miniz_zip.h,miniz_export.h} + lib/cmake/miniz/ +
#        lib/pkgconfig/miniz.pc
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | miniz 与宿主 zlib 同名 | miniz 提供 zlib-compat 符号，宿主 /lib/libz.so 同名 | `BUILD_SHARED_LIBS=OFF` 强制静态库 (R26)，避免系统同名库冲突；不产出 .so |
| 2 | 静态消费方链接报未定义 MINIZ_EXPORT | `generate_export_header` 在静态构建下设 `MINIZ_STATIC_DEFINE` 才能将 `MINIZ_EXPORT` 展开为空 | `package_info` 中 `cpp_info.defines = ["MINIZ_STATIC_DEFINE"]`，自动传递给消费者 |
| 3 | 上游 BUILD_TESTS 需 C++20 + Catch2 | tests/main.cpp + catch_amalgamated.cpp，CMake 强制 `CMAKE_CXX_STANDARD 20` | 关闭 `BUILD_TESTS`（option 真实存在），改用 test_package 消费者测试验证压缩能力 |

## 源码修改

无补丁。上游原生 CMake 非 amalgamation 路径在 OHOS aarch64 交叉编译下可直接构建。

## 依赖版本

- 无外部依赖（纯 C，仅 libc）

## test_package 验证内容

消费者测试 `test.c` 实质验证 miniz 压缩能力：
1. 准备一段重复字符串（含可压缩模式）
2. `mz_compressBound` 计算压缩缓冲上界
3. `mz_compress` 压缩
4. `mz_uncompress` 解压
5. `memcmp` 验证解压结果与原数据**完全一致**
6. 额外验证 `mz_adler32`/`mz_crc32` 校验和与 `mz_version`

链接 Conan 包内 `libminiz.a`（非宿主 zlib）—— `CMakeDeps` 生成 `miniz::miniz` 目标。

## 验证结果

```bash
# ci/conan/build_and_test.sh archives/m/miniz/3.1.2
# L0: quality gate pass（test_package 结构 + MANIFEST + 配方规范）
# L1: test_package 执行 + 破坏性反向验证 (R34) — 真依赖 miniz
# L2: skip（library package，无 bin/）
# L4: pass（无补丁，无危险函数）
# L5: lib/ 有内容 pass（静态库，无 .so → SONAME 门禁不适用）
```

## 交付物

| 文件 | 说明 |
|------|------|
| libminiz.a | 静态库（含 zip/tdef/tinfl 全部符号） |
| include/miniz/{miniz.h,miniz_common.h,miniz_tdef.h,miniz_tinfl.h,miniz_zip.h,miniz_export.h} | 公共头文件 |
| lib/cmake/miniz/ | CMake package config（miniz::miniz） |
| lib/pkgconfig/miniz.pc | pkg-config 文件 |
