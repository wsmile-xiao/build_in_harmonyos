# lua-penlight

Penlight 是一组纯 Lua 库，提供类似 Python 标准库的功能，包括路径/文件操作、配置文件读取、函数式编程等。

## 基本信息

- **项目主页**: https://lunarmodules.github.io/Penlight/
- **GitHub**: https://github.com/lunarmodules/Penlight
- **许可证**: MIT/X11
- **构建系统**: lua（纯 Lua 库）

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.15.0 | built | 2026-06-12 |

## 依赖

- **必需**: Lua 5.4+
- **可选**: luafilesystem（pl.path 和 pl.dir 模块需要）

## 安装方式

```bash
# 使用预编译包安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lua-penlight 1.15.0
```

## OHOS 适配要点

1. 纯 Lua 库，无需 C 编译
2. 模块安装路径: `$PREFIX/share/lua/5.4/pl/`
3. 需要设置 `LUA_PATH` 环境变量才能加载
4. pl.path 和 pl.dir 模块依赖 luafilesystem

## 模块列表

| 模块 | 功能 | 依赖 lfs |
|------|------|---------|
| pl.path | 路径操作 | ✅ 需要 |
| pl.dir | 目录操作 | ✅ 需要 |
| pl.file | 文件操作 | ❌ 不需要 |
| pl.utils | 工具函数 | ❌ 不需要 |
| pl.stringx | 字符串扩展 | ❌ 不需要 |
| pl.tablex | 表操作扩展 | ❌ 不需要 |
| pl.pretty | 格式化输出 | ❌ 不需要 |
| pl.config | 配置文件 | ❌ 不需要 |
| pl.lexer | 词法分析 | ❌ 不需要 |
| pl.template | 模板引擎 | ❌ 不需要 |