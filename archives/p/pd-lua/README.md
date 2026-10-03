# pd-lua

## 软件简介
pd-lua（pdlua）是 Pure Data（Pd）的 Lua 嵌入外部加载器，让开发者可以用 Lua 语言编写 Pd 外部（externals）。基于 Makefile.pdlibbuilder 构建，生成 `pdlua.pd_linux` 共享库，由 Pd 宿主通过 `pd -lib pdlua` 加载。

## 基本信息
- 官方网站: https://github.com/agraef/pd-lua
- 源码仓库: https://github.com/agraef/pd-lua
- 许可协议: GPL-2.0-or-later

## 特性
- Lua 编写 Pd 外部：无需 C 编译即可扩展 Pd
- 支持 Pd 各类对象（消息/信号/图形 GUI 外部）
- 支持多声道信号处理（PD_MULTICHANNEL）
- 附教程（pd-lua-intro）与大量示例外部

## 编译版本
- 0.12.23: ✅ 已编译（OHOS aarch64，clang，静态链接 lua/5.4.8.1，依赖 puredata/0.54.1）
