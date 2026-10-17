# Lua

## 软件简介
Lua 是一种轻量级、高效的脚本语言，设计目的是为了嵌入到其他程序中，从而提供灵活的扩展和定制功能。

## 基本信息
- 官方网站: https://www.lua.org/
- 源码仓库: https://www.lua.org/ftp/
- 许可协议: MIT License

## 特性
- 轻量级：完整的 Lua 解释器仅约 200KB
- 高效：使用寄存器式虚拟机，执行速度快
- 可嵌入：设计用于嵌入到 C/C++ 程序中
- 简洁：语法简单，易于学习
- 可扩展：可通过 C 函数扩展功能

## 编译版本
- 5.4.8: ✅ 已编译（使用 clang + readline）
- 5.4.8.1: ✅ 已编译（使用 generic，无 readline，包含 liblua.a、headers、lua/luac CLI）

## 编译要点
1. **构建系统**: 使用简单 Makefile，无 configure
2. **平台选择**: 5.4.8 使用 linux-readline；5.4.8.1 使用 generic，避免额外 readline 依赖
3. **编译器**: 必须使用 clang（鸿蒙系统无 gcc）
4. **依赖**: readline 仅 linux-readline 变体需要；5.4.8.1 无第三方构建依赖
5. **安装**: 直接设置 INSTALL_TOP，不支持 DESTDIR
6. **测试框架复用**: 5.4.8.1 包修订打包 lua/luac，并通过 Conan runenv 暴露 PATH，可作为 Busted/Vusted 等 Lua 上游测试框架的基础解释器。

## 使用场景
- 嵌入式脚本引擎（游戏、应用程序）
- 快速原型开发
- 配置文件处理
- 自动化脚本
