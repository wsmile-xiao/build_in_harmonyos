# Lua 5.4.8 编译笔记

## 编译环境
- 源码路径: /storage/Users/currentUser/builds/lua-5.4.8.work
- 归档路径: /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/l/lua/5.4.8
- 编译日期: 2026-05-26

## 构建系统分析
Lua 使用简单的 Makefile，没有 configure 脚本。
- 主 Makefile: 定义安装目标和平台选择
- src/Makefile: 定义编译规则和平台特定选项
- 支持自定义变量: MYCFLAGS, MYLDFLAGS, MYLIBS

## 平台选择
- 默认平台: guess
- 可用平台: aix, bsd, c89, freebsd, generic, ios, linux, linux-readline, macosx, mingw, posix, solaris
- 选择: linux-readline（提供交互式命令行编辑功能）

## 编译参数
```bash
make linux-readline CC="clang" \
  MYCFLAGS="-I/storage/Users/currentUser/usr/local/include" \
  MYLDFLAGS="-L/storage/Users/currentUser/usr/local/lib -Wl,-rpath,/storage/Users/currentUser/usr/local/lib"
```

## 遇到的问题

### 问题 1: 缺少 gcc 编译器
- 错误: `gcc: No such file or directory`
- 解决: 使用 `CC=clang` 参数指定 clang 编译器
- 原因: 鸿蒙系统默认使用 clang，没有 gcc

### 问题 2: Lua Makefile 不支持 DESTDIR
- Lua 的 Makefile 不支持 DESTDIR 变量
- 解决: 直接设置 INSTALL_TOP 指向 staging 目录完整路径
- 实际命令: `make install INSTALL_TOP=/storage/Users/currentUser/test-install-lua-5.4.8/storage/Users/currentUser/usr/local`

## 依赖信息
- readline 8.2: 已预编译安装，提供交互式命令行编辑功能
- 位置: /storage/Users/currentUser/usr/local

## 测试结果
```bash
./lua -v
Lua 5.4.8  Copyright (C) 1994-2025 Lua.org, PUC-Rio
```

## 编译产物
- lua: Lua 解释器（297KB）
- luac: Lua 编译器（220KB）
- liblua.a: Lua 静态库（454KB）
- 头文件: lua.h, luaconf.h, lualib.h, lauxlib.h, lua.hpp
- man 文档: lua.1, luac.1

## 安装位置（staging）
- 二进制文件: /storage/Users/currentUser/test-install-lua-5.4.8/storage/Users/currentUser/usr/local/bin/
- 库文件: /storage/Users/currentUser/test-install-lua-5.4.8/storage/Users/currentUser/usr/local/lib/
- 头文件: /storage/Users/currentUser/test-install-lua-5.4.8/storage/Users/currentUser/usr/local/include/
- man 文档: /storage/Users/currentUser/test-install-lua-5.4.8/storage/Users/currentUser/usr/local/man/man1/

## 知识提取
1. **Lua 编译器选择**: 鸿蒙系统没有 gcc，必须使用 clang
   - 解决方案: `make linux-readline CC="clang"`
   - 适用范围: 所有使用 Makefile 的软件

2. **Lua DESTDIR 问题**: Lua Makefile 不支持标准 DESTDIR 模式
   - 解决方案: 直接设置 INSTALL_TOP 为完整 staging 路径
   - 适用范围: Lua 及类似简单 Makefile 软件

---
**编译结束**: 2026-05-26 14:50
**最终状态**: built
---

**编译结束**: 2026-05-26 14:51
**最终状态**: built
