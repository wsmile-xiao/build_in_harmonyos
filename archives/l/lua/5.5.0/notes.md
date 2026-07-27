# Lua 5.5.0 编译笔记

## 编译环境
- 源码路径: /storage/Users/currentUser/tmp/builds/lua-5.5.0.work
- 归档路径: /storage/Users/currentUser/opt/ai-worker/repo/archives/l/lua/5.5.0
- 编译日期: 2026-07-16

## 构建系统分析
Lua 5.5.0 使用简单的 Makefile，没有 configure 脚本。
- 主 Makefile: 定义安装目标和平台选择
- src/Makefile: 定义编译规则和平台特定选项
- 支持自定义变量: MYCFLAGS, MYLDFLAGS, MYLIBS

## 平台选择
- 默认平台: guess
- 可用平台: guess aix bsd c89 freebsd generic ios linux macosx mingw posix solaris
- 选择: linux（使用 -DLUA_USE_LINUX，链接 -ldl，不需要 readline）
- 注意: Lua 5.5.0 的 PLATS 列表中不再有 linux-readline 目标

## 编译参数
```bash
make linux CC="clang" -j1
```

## 遇到的问题

### 无问题
Lua 5.5.0 在鸿蒙系统上编译顺利，无任何错误。

## 依赖信息
- 无 conan 依赖
- 系统库: libm, libdl（由 libc 提供）

## 测试结果
```bash
./lua -v
Lua 5.5.0  Copyright (C) 1994-2025 Lua.org, PUC-Rio
```
```bash
./lua -e 'print("Hello from Lua " .. _VERSION)'
Hello from Lua Lua 5.5
```
```bash
make test
Lua 5.5.0  Copyright (C) 1994-2025 Lua.org, PUC-Rio
```

## 编译产物
- lua: Lua 解释器
- luac: Lua 编译器
- liblua.a: Lua 静态库

## 安装方式
Lua Makefile 不支持 DESTDIR，使用 INSTALL_TOP 指定安装目录：
```bash
make install INSTALL_TOP=<prefix>
```

## Conan 配方要点
- package_type: library
- 构建命令: make linux CC=<cc from conan conf> -j1
- 安装命令: make install INSTALL_TOP=<package_folder>
- cpp_info.libs: ["lua"]
- cpp_info.system_libs: ["m", "dl"]
- 无 conan 依赖（readline 不在制品仓，使用 linux 平台目标避免依赖）
---

**编译结束**: 2026-07-16 00:51
**最终状态**: built
