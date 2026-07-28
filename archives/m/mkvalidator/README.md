# mkvalidator

## 简介

mkvalidator 是 Matroska Foundation 开发的容器格式验证工具，用于检查 MKV/WebM 文件的结构完整性。它能检测 EBML 头部错误、段 UID 无效、轨道信息缺失等常见 Matroska 格式问题。

## OHOS 适配

- **CMAKE_SYSTEM_NAME=Linux**：必须设置此 CMake 变量。否则 UNIX 宏未定义，corec 条件编译选择 str_linux.c（仅 glibc）而非 str_os.c（通用 POSIX），产生 undefined reference 错误。在 conanfile.py 的 `generate()` 中通过 `tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"` 设置。
- **corec 测试禁用**：corec/tests 子目录中的测试可执行文件依赖 tchar 符号，在 musl 环境下不可用。通过补丁 0001 注释掉 `add_subdirectory("tests")` 禁用。
- **install 规则补全**：原始 mkvalidator/CMakeLists.txt 缺少 install() 规则。通过补丁 0002 添加 `include(GNUInstallDirs)` 和 `install(TARGETS mkvalidator RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})`。
- **内置依赖**：所有依赖（corec/ebml2/matroska2/zlib/bzlib）均为源码内置编译为静态库，无外部 Conan 依赖。

## 依赖

无外部 Conan 依赖。所有库（corec/ebml2/matroska2/zlib/bzlib）均为源码内置静态编译。

## 功能验证

```bash
$ mkvalidator --version
mkvalidator v0.6.0, Copyright (c) 2010-2020 Matroska Foundation

$ mkvalidator --help
mkvalidator v0.6.0 — Usage: mkvalidator [options] <matroska_src>

$ readelf -h mkvalidator | grep Type
 Type: DYN (Position-Independent Executable file)
# PIE + BIND_NOW 安全特性
```

## 参考

- 官网: https://www.matroska.org/downloads/mkvalidator.html
- 源码: https://downloads.sourceforge.net/project/matroska/mkvalidator/mkvalidator-0.6.0.tar.bz2
