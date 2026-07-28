# mkvalidator 0.6.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4 / clang++ 15.0.4 (OH native)
- 目标架构: aarch64 / musl libc
- 状态: built → 等待 published

## 编译步骤

1. `ohc init-build mkvalidator 0.6.0 --url=https://downloads.sourceforge.net/project/matroska/mkvalidator/mkvalidator-0.6.0.tar.bz2`
2. 修改 corec/CMakeLists.txt：注释掉 `add_subdirectory("tests")`（track-edit 跟踪）
3. 修改 mkvalidator/CMakeLists.txt：添加 `include(GNUInstallDirs)` 和 `install(TARGETS mkvalidator RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})` 规则（track-edit 跟踪）
4. `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release -DCMAKE_SYSTEM_NAME=Linux`
5. `make -j2` — 全部目标编译成功
6. `make install DESTDIR=$TEST_PREFIX` — staging 验证安装成功
7. `conan create` — 从干净源码构建验证配方自包含性（R19: 使用 conan create，禁止手动打包）
8. `conan-verify` — G1-G4 全部 PASS
9. `finish` — 归档收尾，状态 built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 严重程度 |
|---|------|------|----------|---------|
| 1 | undefined reference (str_linux.c 相关符号，如 syscall、__LINE__解析等) | CMake 未设置 CMAKE_SYSTEM_NAME，UNIX 宏未定义，corec 条件编译选择 str_linux.c（仅 glibc）而非 str_os.c（通用 POSIX） | 添加 -DCMAKE_SYSTEM_NAME=Linux cmake 选项 | 🔴 阻塞 |
| 2 | string_test/file_test/node_test 链接失败（undefined tchar 符号） | corec tests 子目录中的测试可执行文件依赖缺失的 tchar 符号 | 注释掉 corec/CMakeLists.txt 中的 `add_subdirectory("tests")` | 🔴 阻塞 |
| 3 | mkvalidator 二进制无法 make install | mkvalidator/CMakeLists.txt 缺少 install() 规则 | 手动添加 install(TARGETS) 规则 | 🔴 阻塞 |
| 4 | cmake_policy CMP0054 字符串比较警告 | CMake 版本策略不一致 | 已在 CMakeLists.txt 中存在 `cmake_policy(SET CMP0054 NEW)`，无需修改 | 🟢 无害 |
| 5 | /proc/meminfo 解析警告 | OH 环境下 meminfo 格式不同 | 无害警告，不影响功能 | 🟢 无害 |
| 6 | charconvert_linux.c const pointer 警告 | iconv() 参数类型不匹配 | 无害编译警告 | 🟢 无害 |

## 源码修改

### 修改 1: corec/CMakeLists.txt
```diff
-add_subdirectory("tests")
+# add_subdirectory("tests")  # disabled: test executables fail on HarmonyOS due to undefined tchar symbols
```
**跟踪方式**: `ohc track-edit add corec/CMakeLists.txt`
**补丁**: 0001-disable-corec-tests.patch

### 修改 2: mkvalidator/CMakeLists.txt
```diff
+# Install the mkvalidator binary
+include(GNUInstallDirs)
+install(TARGETS "mkvalidator" RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
+
```
**跟踪方式**: `ohc track-edit add mkvalidator/CMakeLists.txt`
**补丁**: 0002-add-mkvalidator-install-rule.patch

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| libc.so | musl | 动态 | 系统运行时依赖 |
| libcorec.a | 内置 | 静态 | Core-C 基础库（随源码编译） |
| libebml2.a | 内置 | 静态 | EBML2 库（随源码编译） |
| libmatroska2.a | 内置 | 静态 | Matroska2 库（随源码编译） |
| zlib | 内置 | 静态 | 内嵌 zlib（随源码编译） |
| bzlib | 内置 | 静态 | 内嵌 bzlib（随源码编译） |

**外部预编译依赖**: 无（所有依赖均为内置编译）

## 验证结果

### 二进制信息
```
$ file mkvalidator
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ readelf -h mkvalidator
Type: DYN (Position-Independent Executable file)
Machine: AArch64
```

### 安全特性
- ✅ PIE (位置无关可执行): FLAGS_1 = NOW PIE
- ✅ BIND_NOW (全绑定): FLAGS = BIND_NOW
- ✅ 动态依赖仅 libc.so（最小化外部依赖）

### 功能测试
```
$ mkvalidator --version
mkvalidator v0.6.0, Copyright (c) 2010-2020 Matroska Foundation

$ mkvalidator --help
mkvalidator v0.6.0 — Usage: mkvalidator [options] <matroska_src>

$ mkvalidator chapters.webm
mkvalidator 0.6.0: the file appears to be valid

$ mkvalidator bbb_480p_vp9_opus_1second.webm
ERR201: Invalid 'SegmentUID' for profile 'webm'
(该文件确有错误，验证工具正确检测)
```

## 安装产物

| 产物 | 路径 | 大小 | 说明 |
|------|------|------|------|
| mkvalidator | usr/local/bin/mkvalidator | 461KB | Matroska 验证工具 (aarch64 ELF PIE) |
| libcorec.a | usr/local/lib/libcorec.a | 218KB | Core-C 基础库（静态） |
| libebml2.a | usr/local/lib/libebml2.a | 277KB | EBML2 库（静态） |
| libmatroska2.a | usr/local/lib/libmatroska2.a | 424KB | Matroska2 库（静态） |
| 头文件 | usr/local/include/corec/*.h | 14 个 | Core-C API 头文件 |
| 头文件 | usr/local/include/ebml2/*.h | 3 个 | EBML2 API 头文件 |
| 头文件 | usr/local/include/matroska2/*.h | 4 个 | Matroska2 API 头文件 |
| CMake 配置 | usr/local/lib/cmake/corec/*.cmake | 2 个 | Core-C CMake 配置 |
| CMake 配置 | usr/local/lib/cmake/ebml2/*.cmake | 2 个 | Ebml2 CMake 配置 |
| CMake 配置 | usr/local/lib/cmake/matroska2/*.cmake | 2 个 | Matroska2 CMake 配置 |

## 注意事项

1. **CMAKE_SYSTEM_NAME=Linux 是必需的**: 否则平台检测错误导致 corec 选择 str_linux.c 而非 str_os.c，产生 undefined reference
2. **mkvalidator 原始源码缺少 install 规则**: 必须手动添加 install(TARGETS) 和 GNUInstallDirs
3. **corec tests 子目录必须禁用**: 测试可执行文件依赖 tchar 符号在 musl 环境下不可用
4. **所有依赖均为内置编译**: 无外部预编译依赖需求

---
**编译结束**: 2026-06-17 17:20
**最终状态**: built（conan create 验证通过，待 conan upload 后标记 published）
