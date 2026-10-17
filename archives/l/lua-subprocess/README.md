# lua-subprocess

## 简介

lua-subprocess 是一个 Lua C 扩展模块，提供子进程创建和管理功能。它允许 Lua 程序启动外部命令、管理进程输入输出、等待进程完成等。API 基于 Python 的 subprocess 模块。

## 版本信息

- **当前版本**: 0.02
- **源码仓库**: https://github.com/xlq/lua-subprocess
- **构建系统**: Makefile (raw make)
- **构建依赖**: lua/5.4.8

## 构建信息

- **编译器**: clang 15.0.4
- **平台**: OpenHarmony / HarmonyOS PC (aarch64)
- **产物**: subprocess.so (shared Lua C module)

## 功能特性

- 创建子进程并管理输入输出 (subprocess.popen)
- 管道和重定向支持 (subprocess.PIPE)
- 进程状态查询和控制 (proc:poll, proc:wait, proc:kill)
- 捕获子进程输出 (subprocess.call_capture)
- POSIX 平台支持

## 安装路径

- **模块路径**: `lib/lua/5.4/subprocess.so`
- **Lua 版本**: Lua 5.4

## 使用方法

```lua
local subprocess = require("subprocess")

-- 创建子进程
local p = subprocess.popen {"echo", "hello", stdout = subprocess.PIPE}

-- 读取输出
local stdout = p.stdout:read("*a")

-- 等待进程完成
local exitcode = p:wait()

print("Exit code:", exitcode)
print("Output:", stdout)
```

## 编译历史

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 0.02 | published | 2026-08-07 | Conan 适配完成，conan-verify 通过 |
