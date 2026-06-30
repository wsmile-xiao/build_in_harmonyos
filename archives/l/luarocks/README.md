# LuaRocks

> Lua package manager for installing Lua modules as self-contained packages

## 简介

LuaRocks 是 Lua 编程语言的包管理系统，允许用户创建、安装和管理 Lua 模块（称为"rocks"）。它支持本地和远程仓库，以及多个本地 rocks 树。

LuaRocks 本身是纯 Lua 脚本，无需编译 native 代码，仅需 Lua 解释器即可运行。在 HarmonyOS 上，它使用预装的 LuaJIT 作为 Lua 5.1 兼容解释器。

## OHOS 适配要点

- 纯 Lua 脚本包，无 native 代码编译
- 需要预装 Lua/LuaJIT 解释器（已在系统中预装）
- configure 时自动检测 LuaJIT 作为 Lua 5.1 解释器
- 无测试套件（make check 不存在）
- 无需补丁，直接 configure + make + install 即可

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Lua/LuaJIT | 系统预装 | Lua 解释器和库文件 |

## 功能验证

```bash
luarocks --version
/storage/Users/currentUser/usr/local/bin/luarocks 3.12.2
LuaRocks main command-line interface
```

## 参考

- [官方网站](https://luarocks.org)
- [GitHub 仓库](https://github.com/luarocks/luarocks)