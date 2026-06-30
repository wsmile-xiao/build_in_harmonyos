# lua-alt-getopt

Lua module for parsing command line options similar to getopt_long.

## 特点

- **纯 Lua 模块**：无需编译，直接安装 Lua 文件
- **getopt_long 风格**：支持短选项和长选项解析
- **兼容 Lua 5.1+**：支持 Lua 5.1, 5.2, 5.3, 5.4

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 0.8.0 | built | 2026-06-17 |

## 安装说明

lua-alt-getopt 是纯 Lua 模块，安装方式：

```bash
# 安装 Lua 模块
cp alt_getopt.lua $PREFIX/share/lua/5.4/

# 安装演示脚本
cp alt_getopt $PREFIX/bin/
```

安装产物：
- `share/lua/5.4/alt_getopt.lua` - 核心模块
- `bin/alt_getopt` - 演示脚本

## 使用说明

需要设置 LUA_PATH 环境变量：

```bash
export LUA_PATH="$HOME/usr/local/share/lua/5.4/?.lua;;"
```

示例：
```lua
local alt_getopt = require 'alt_getopt'
local opts, optind, optarg = alt_getopt.get_ordered_opts({'-h', '--help'}, 'hv', {help='h', verbose='v'})
```

## 源码信息

- **项目主页**: https://github.com/LuaDist-alt-getopt/lua-alt-getopt
- **许可证**: MIT/X11

## 依赖

- Lua >= 5.1