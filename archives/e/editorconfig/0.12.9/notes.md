# editorconfig 0.12.9 编译笔记

## 编译信息
- **软件**: editorconfig-core-c
- **版本**: 0.12.9
- **构建系统**: cmake
- **产物类型**: 可执行文件 + 静态库
- **编译日期**: 2026-05-26

## 编译过程

### 问题1: PCRE2依赖缺失
- **错误**: CMake配置时找不到PCRE2库
- **根因**: editorconfig依赖PCRE2正则表达式库
- **解决**: 安装预编译包pcre2/10.40，并显式指定路径参数
```bash
-DPCRE2_INCLUDE_DIR=$DEFAULT_PREFIX/include
-DPCRE2_LIBRARY_RELEASE=$DEFAULT_PREFIX/lib/libpcre2-8.a
```

### 问题2: 平台识别编译错误
- **错误**: misc.c编译失败，错误 "Either UNIX or WIN32 must be defined"
- **根因**: 源码缺少HarmonyOS平台支持（src/lib/misc.c第27行）
- **解决**: 修改源码添加__OHOS__宏定义（视为UNIX系统）
- **补丁**: 0001-src-lib-misc.c.patch

### 问题3: 动态库RPATH错误
- **错误**: 二进制文件依赖相对路径../../lib/libeditorconfig.so
- **根因**: CMake的link_directories导致相对路径问题
- **解决**: 使用静态链接选项 `-DBUILD_STATICALLY_LINKED_EXE=ON`

### 问题4: clean_verify不支持CMake
- **错误**: G0干净构建验证失败（clean_verify.py只支持autotools）
- **根因**: clean_verify.py只支持configure/make流程，不支持CMake
- **解决**: 创建configure和Makefile wrapper补丁，桥接CMake到autotools流程
- **补丁**: 0002-cmake-configure-wrapper.patch

## CMake配置选项
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_BUILD_TYPE=Release \
         -DBUILD_STATICALLY_LINKED_EXE=ON \
         -DPCRE2_INCLUDE_DIR=$DEFAULT_PREFIX/include \
         -DPCRE2_LIBRARY_RELEASE=$DEFAULT_PREFIX/lib/libpcre2-8.a
```

## 补丁文件
1. **0001-src-lib-misc.c.patch**: 添加__OHOS__平台识别宏
2. **0002-cmake-configure-wrapper.patch**: 创建configure/Makefile wrapper桥接G0验证

## 编译产物
- **可执行文件**: editorconfig-0.12.9 (静态链接)
- **静态库**: libeditorconfig_static.a
- **头文件**: editorconfig/editorconfig.h, editorconfig/editorconfig_handle.h
- **预编译包**: 无（子任务未执行package步骤）

## 安装验证
- 版本检查: `$HOME/usr/local/bin/editorconfig --version` 返回 "EditorConfig C Core Version 0.12.9"

## 知识图谱草稿
- 草稿ID: E081
- 内容: CMake项目依赖路径显式指定 + clean_verify wrapper桥接方案

编译状态: built
