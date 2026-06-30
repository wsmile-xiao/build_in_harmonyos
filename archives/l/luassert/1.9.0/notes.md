# luassert 1.9.0 适配笔记

## 编译环境
- 构建系统: lua-builtin (纯 Lua 库)
- 编译日期: 2026-06-15
- 编译器: 无需编译器（纯 Lua）
- 状态: published

## 编译步骤

### 1. 获取源码
由于 GitHub 连接失败，使用 LuaRocks 官方服务器获取 .rock 文件：
```bash
curl -k -L -o luassert-1.9.0-1.src.rock https://luarocks.org/luassert-1.9.0-1.src.rock
unzip luassert-1.9.0-1.src.rock
```

### 2. 安装依赖 say
```bash
curl -k -L -o say-1.4.1-3.src.rock https://luarocks.org/say-1.4.1-3.src.rock
unzip say-1.4.1-3.src.rock
mkdir -p ~/usr/local/share/lua/5.4/say
cp ~/tmp/say/src/say/init.lua ~/usr/local/share/lua/5.4/say/init.lua
```

### 3. 安装 luassert 模块
```bash
cd ~/tmp/luassert
mkdir -p ~/usr/local/share/lua/5.4/luassert
mkdir -p ~/usr/local/share/lua/5.4/luassert/matchers
mkdir -p ~/usr/local/share/lua/5.4/luassert/formatters
mkdir -p ~/usr/local/share/lua/5.4/luassert/languages
cp src/*.lua ~/usr/local/share/lua/5.4/luassert/
cp src/matchers/*.lua ~/usr/local/share/lua/5.4/luassert/matchers/
cp src/formatters/*.lua ~/usr/local/share/lua/5.4/luassert/formatters/
cp src/languages/*.lua ~/usr/local/share/lua/5.4/luassert/languages/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 连接超时 | 网络防火墙或路由限制 | 使用 LuaRocks 官方服务器下载 .rock 文件 |
| 2 | Savannah URL 404 | URL 是假的或不存在 | 使用 LuaRocks 服务器替代 |
| 3 | Lua 无法加载模块 | Lua 编译时路径为绝对路径 `/usr/local`，系统路径不存在且无权限创建 | 使用 `LUA_PATH` 环境变量添加用户路径 |
| 4 | 缺少依赖 say | lua-luassert 依赖 say 库 | 先下载并安装 say |

## 源码修改

无补丁，源码直接安装。

## 依赖版本

- lua 5.4.7
- say 1.4.1-3

## 验证结果

```bash
export LUA_PATH="$HOME/usr/local/share/lua/5.4/?.lua;$HOME/usr/local/share/lua/5.4/?/init.lua;;"
lua -e "require('luassert'); print('luassert module installed successfully')"
# 输出: luassert module installed successfully

lua -e "
local assert = require('luassert')
assert.True(true)
assert.are.equal(1, 1)
print('All tests passed!')
"
# 输出: All tests passed!
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| luassert-1.9.0-ohos-aarch64.tar.gz | 113K | 预编译包（包含所有 Lua 模块文件） |
| luassert-1.9.0.tar.gz | 248K | 源码包 |

## 注意事项

1. **平台路径限制**：OpenHarmony 平台上 Lua 的 `package.path` 使用绝对路径 `/usr/local`，系统路径不存在且无权限创建。需要使用 `LUA_PATH` 环境变量或重新编译 Lua。

2. **依赖链**：luassert 依赖 say，安装顺序应为：say → luassert。

3. **网络问题**：GitHub 连接可能失败，建议使用 LuaRocks 官方服务器作为备用下载源。

---

**编译结束**: 2026-06-15 15:24
**最终状态**: published
---

**编译结束**: 2026-06-15 15:25
**最终状态**: built
