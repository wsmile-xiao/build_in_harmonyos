# bamtools 2.5.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

### 1. 初始化编译环境
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build bamtools 2.5.3 --url=file:///path/to/bamtools-2.5.3.tar.gz
```

### 2. CMake 配置
```bash
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
export CMAKE_PREFIX_PATH="$HOME/usr/local"
cd ~/builds/bamtools-2.5.3.work/build
cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF ..
```

### 3. 编译
```bash
make -j2
```

### 4. 安装
```bash
# Staging 安装（DESTDIR 模式）
make install DESTDIR=$HOME/tmp/test-install-bamtools-2.5.3

# 本地安装（验证）
make install
```

### 5. 制作预编译包
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package bamtools 2.5.3 --prefix=$TEST_PREFIX/$HOME/usr/local
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 找不到 ZLIB | PKG_CONFIG_PATH 未包含 zlib.pc 目录 | 设置 `PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH` |
| 2 | 链接错误：缺少 libc++ 符号 | 鸿蒙系统需要显式链接 libc++ | 修改 src/CMakeLists.txt，添加对 c++ 和 c++abi 的链接 |
| 3 | verify-build G4 FAIL | manifest.yaml 缺少 build_system 字段 | 在版本级 manifest.yaml 添加 `build_system: cmake` |

## 源码修改

### src/CMakeLists.txt
在 bamtools_cmd 的 target_link_libraries 之后添加：

```cmake
# HarmonyOS/link libc++ explicitly for static linking
find_library(HAVE_LIBCXX c++ PATHS /system/lib /system/lib64 NO_DEFAULT_PATH)
find_library(HAVE_LIBCXXABI c++abi PATHS /system/lib /system/lib64 NO_DEFAULT_PATH)
if(HAVE_LIBCXX AND HAVE_LIBCXXABI)
    target_link_libraries(BamTools PRIVATE c++ c++abi)
    target_link_libraries(BamTools-utils PRIVATE c++ c++abi)
    target_link_libraries(bamtools_cmd PRIVATE c++ c++abi)
    message(STATUS "Found libc++ in system/lib, linking c++ and c++abi")
elseif(EXISTS "$ENV{HOME}/usr/local/lib/libc++.a")
    target_link_libraries(BamTools PRIVATE "$ENV{HOME}/usr/local/lib/libc++.a" "$ENV{HOME}/usr/local/lib/libc++abi.a")
    target_link_libraries(BamTools-utils PRIVATE "$ENV{HOME}/usr/local/lib/libc++.a" "$ENV{HOME}/usr/local/lib/libc++abi.a")
    target_link_libraries(bamtools_cmd PRIVATE "$ENV{HOME}/usr/local/lib/libc++.a" "$ENV{HOME}/usr/local/lib/libc++abi.a")
    message(STATUS "Found libc++ in user local directory, linking statically")
else()
    target_link_libraries(BamTools PRIVATE c++ c++abi)
    target_link_libraries(BamTools-utils PRIVATE c++ c++abi)
    target_link_libraries(bamtools_cmd PRIVATE c++ c++abi)
    message(STATUS "Attempting to link c++ and c++abi as fallback")
endif()
```

## 依赖版本

- zlib 1.3.1 (静态链接)
- libc++ (LLVM C++ 标准库)
- libc++abi (C++ ABI 库)
- 捆绑 jsoncpp (使用源码内嵌版本)

## 验证结果

```bash
$ ~/usr/local/bin/bamtools --version
bamtools 2.5.3
Part of BamTools API and toolkit
Primary authors: Derek Barnett, Erik Garrison, Michael Stromberg
(c) 2009-2012 Marth Lab, Biology Dept., Boston College
```

✅ 功能验证通过

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bamtools-2.5.3-ohos-aarch64.tar.gz | 2.7M | 预编译包（含二进制、库、头文件） |
| bamtools-2.5.3-ohos-aarch64-debug.tar.gz | 326K | 调试符号包 |
| libbamtools.a | 1.1M | 静态库 |
| bamtools | 1.1M | 命令行工具 |

## 注意事项

1. **必须设置 PKG_CONFIG_PATH**: 编译前必须设置 PKG_CONFIG_PATH 以找到 zlib
2. **libc++ 链接**: 鸆蒙系统使用 LLVM clang 编译器，需要显式链接 libc++ 和 libc++abi
3. **静态编译**: bamtools 默认编译为静态库（BUILD_SHARED_LIBS=OFF）
4. **CMake 平台警告**: CMake 会提示 "System is unknown to cmake"，但不影响编译
**归档路径**: archives/b/bamtools/2.5.3/
---

**编译结束**: 2026-06-17 14:25
**最终状态**: built
