# xmake 3.0.5 编译笔记

## 编译概述
- **软件**: xmake 3.0.5 (基于 Lua 的跨平台构建工具)
- **日期**: 2026-05-26
- **状态**: 编译成功

## 编译过程
1. 使用 xmake.sh configure 脚本生成 build.ninja
2. HMDFS 文件系统导致 xmake.sh 生成的构建文件损坏（变量定义与 install 命令行交错）
3. 手动编译所有组件: lua, lua-cjson, lz4, sv, tbox, xmake
4. 手动创建 tbox.config.h (基于 linux 版本，针对 HarmonyOS 适配)
5. 手动创建 xmake.config.h
6. 使用 --allow-multiple-definition 链接最终二进制

## 关键发现
- xmake.sh configure 在 HMDFS 上生成损坏的 Makefile/ninja 文件（并发写入问题）
- 需要手动创建 harmonyos 版本的 tbox.config.h
- tbox 的 posix/socket.c 不应单独编译（由 platform/socket.c 条件包含引入）
- xmake winos/ 和 windows/ 源文件不应在 HarmonyOS 上编译
- xmake Lua 模块安装路径: share/xmake/ (不是 share/xmake/xmake/)

## 验证结果
- xmake --version 输出: v3.0.5+20260526
- 依赖: readline (预编译包提供)

**编译结束**: 2026-05-26
**最终状态**: published
---

**编译结束**: 2026-05-26 17:03
**最终状态**: built
