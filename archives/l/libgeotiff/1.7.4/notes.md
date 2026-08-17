# libgeotiff 1.7.4 适配笔记（HarmonyOS PC · Conan cmake）

## 定位
- 产出动态库 libgeotiff.so.5.2.4，供 dlopen 及作依赖。

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-23
- 编译器: clang/clang++ 15.0.4
- 状态: built（conan create + test_package 通过）

## 关键适配

### 1. OHOS 工具链发现
使用 `_ohos_toolchain()` 方法自发现 ohos.toolchain.cmake（glob /data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/）。

### 2. 传递依赖链接
libgeotiff (C 共享库) 依赖 libproj.a (C++ 静态库)，传递依赖 sqlite3/lzma/zstd 等。
使用 `CMAKE_C_STANDARD_LIBRARIES` 将所有传递依赖库路径和 -l 标志追加到链接命令末尾。

### 3. C++ 运行时链接
libproj.a 是 C++ 静态库，需要 `-lc++_shared` 和 `-fuse-ld=bfd` 链接器（bfd 自动解析 C++ 运行时符号）。

### 4. 依赖接线
libgeotiff 使用 find_package(PROJ) 和 find_package(TIFF)，通过预设 cmake cache 变量绕过搜索：
- PROJ_INCLUDE_DIR / PROJ_LIBRARY
- TIFF_INCLUDE_DIR / TIFF_LIBRARY

### 5. ELF 签名
所有 .so 文件用 llvm-objcopy + binary-sign-tool 签名，确保可在 OHOS 设备上运行。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libtiff | 4.7.2 | 共享库 libtiff.so |
| proj | 9.3.1.1 | 静态库 libproj.a (禁用 curl, 制品仓已发布) |
| zlib | 1.3.1.1 | 压缩库 |
| libjpeg-turbo | 3.2.0 | JPEG 库 |

## 构建产物
- libgeotiff.so.5.2.4 (5.7MB, ELF aarch64)
- 12 个头文件 (.h) + 11 个 .inc 文件
- 4 个 CMake config 文件
- 1 个 pkg-config 文件 (libgeotiff.pc)

## 验证结果
- conan create: 通过
- test_package (ctest): 1/1 通过
- 功能测试: GTIFNew/GTIFKeySet/GTIFWriteKeys/GTIFKeyGet/GTIFFree 全部验证通过
- CI 质量门 L0-L5: 全部通过
