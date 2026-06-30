# xmake

xmake 是一个基于 Lua 的跨平台构建工具，使用 C/Lua 编写，自带构建系统。

## 特点
- 跨平台支持 (Linux, macOS, Windows, HarmonyOS 等)
- 内置 Lua 脚本引擎，灵活配置
- 自带构建系统 (xmake.sh bootstrap)
- 支持 C/C++, Rust, Go, Swift 等多种语言

## 当前版本
- **3.0.5** (2026-05-26) - 编译成功，状态: built

## 编译要点
- 构建系统: custom (xmake.sh)
- 需要手动创建 harmonyos 版本的 tbox.config.h
- xmake.sh 在 HMDFS 上生成损坏的构建文件，需要手动编译
- Lua 模块安装路径: share/xmake/ (不是 share/xmake/xmake/)
