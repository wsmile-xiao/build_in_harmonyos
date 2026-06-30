# lua-subprocess

## 简介

lua-subprocess 是一个 Lua 库模块，提供子进程创建和管理功能。它允许 Lua 程序启动外部命令、管理进程输入输出、等待进程完成等。

## 版本信息

- **当前版本**: 0.02
- **发布日期**: 2016-04-22
- **源码仓库**: https://github.com/kernelsmith/lua-subprocess

## 构建信息

- **构建系统**: makefile
- **构建依赖**: lua/5.4.7
- **编译器**: clang

## 功能特性

- 创建子进程并管理输入输出
- 支持管道和重定向
- 提供进程状态查询和控制
- 跨平台支持（POSIX 系统）

## 安装路径

- **模块路径**: `/usr/local/lib/lua/5.4/subprocess.so`
- **Lua 版本**: Lua 5.4

## 使用方法

```lua
local subprocess = require("subprocess")

-- 创建子进程
local proc = subprocess.spawn({"ls", "-la"}, {
    stdout = subprocess.PIPE,
    stderr = subprocess.PIPE
})

-- 读取输出
local stdout = proc.stdout:read("*a")
local stderr = proc.stderr:read("*a")

-- 等待进程完成
local exit_code = proc:wait()

print("Exit code:", exit_code)
print("Output:", stdout)
```

## 注意事项

- 需要设置 `LUA_CPATH` 环境变量以包含正确的模块路径
- 遵循 Lua 5.4 的模块加载机制

## 编译历史

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 0.02 | built | 2026-06-09 | 成功编译并打包 |