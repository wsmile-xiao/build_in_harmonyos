# lua-resty-lrucache

## 简介

lua-resty-lrucache 是一个基于 LuaJIT FFI 的 LRU（最近最少使用）缓存库，专为 OpenResty 设计。它提供了高效的内存缓存功能，支持普通模式和 pure FFI 模式。

## 功能特性

- **LRU 缓存**: 自动淘汰最少使用的缓存项
- **两种实现模式**:
  - 普通模式（基于 Lua 表）
  - Pure FFI 模式（基于 C 结构，更高性能）
- **容量管理**: 支持设置最大缓存容量
- **计数器**: 支持获取当前缓存项数量
- **键管理**: 支持获取所有缓存键

## 版本信息

- 当前版本: 0.15
- 发布日期: 2024-10-10
- 官方仓库: https://github.com/openresty/lua-resty-lrucache

## 编译状态

- 编译日期: 2026-06-11
- 编译器: 不适用（纯 Lua 库）
- 编译状态: built
- 预编译包: lua-resty-lrucache-0.15-ohos-aarch64.tar.gz

## 运行要求

- **LuaJIT**: 需要 LuaJIT 的 FFI 功能
- **OpenResty**: 推荐在 OpenResty 环境中使用
- 标准 Lua 5.1/5.2/5.3/5.4 **不支持**此库（缺少 FFI）

## 安装方法

### 方法 1: 使用预编译包

```bash
# 下载预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lua-resty-lrucache 0.15

# 文件将安装到: /usr/local/lib/lua/5.1/resty/lrucache.lua
#               /usr/local/lib/lua/5.1/resty/lrucache/pureffi.lua
```

### 方法 2: 手动安装

```bash
# 解压预编译包
tar xzf lua-resty-lrucache-0.15-ohos-aarch64.tar.gz -C /

# 或从源码安装
cd lua-resty-lrucache-0.15
make install PREFIX=/usr/local LUA_LIB_DIR=/usr/local/lib/lua/5.1
```

## 使用示例

### 普通模式

```lua
local lrucache = require "resty.lrucache"

-- 创建缓存（最大容量 1000）
local cache, err = lrucache.new(1000)
if not cache then
    return nil, err
end

-- 设置缓存
cache:set("key1", "value1", 3600)  -- 3600秒过期时间

-- 获取缓存
local value = cache:get("key1")

-- 删除缓存
cache:delete("key1")

-- 获取所有键
local keys = cache:get_keys()

-- 获取当前数量
local count = cache:count()
```

### Pure FFI 模式

```lua
local lrucache_pureffi = require "resty.lrucache.pureffi"

-- 创建缓存（最大容量 1000）
local cache, err = lrucache_pureffi.new(1000)

-- 其他操作与普通模式相同
cache:set("key1", "value1", 3600)
local value = cache:get("key1")
```

## API 文档

### `new(max_items)`

创建新的 LRU 缓存实例。

- `max_items`: 最大缓存项数量
- 返回: 缓存实例或 nil + 错误信息

### `set(key, value, ttl)`

设置缓存项。

- `key`: 缓存键
- `value`: 缓存值
- `ttl`: 过期时间（秒，可选）

### `get(key)`

获取缓存项。

- `key`: 缓存键
- 返回: 缓存值或 nil

### `delete(key)`

删除缓存项。

- `key`: 缓存键

### `get_keys(max_items)`

获取所有缓存键。

- `max_items`: 最大返回数量（可选）
- 返回: 键数组

### `count()`

获取当前缓存项数量。

- 返回: 数量

### `flush_all()`

清空所有缓存项。

## 依赖关系

- **运行时依赖**: LuaJIT（FFI）
- **测试依赖**: OpenResty, Test::Nginx::Socket::Lua

## 注意事项

1. **LuaJIT 必需**: 此库依赖 LuaJIT 的 FFI 功能，标准 Lua 不支持
2. **OpenResty 环境**: 推荐在 OpenResty 中使用，测试也需要 OpenResty 环境
3. **内存管理**: LRU 缓存会自动管理内存，淘汰最少使用的项
4. **并发安全**: 在 OpenResty 中使用时，注意 worker 进程间的缓存隔离

## 已知版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.15 | built | 最新版本，修复 FreeBSD bash 问题 |
| 0.14 | - | - |
| 0.13 | - | - |

## 相关库

- lua-resty-core
- lua-resty-http
- lua-resty-dns

## 参考资料

- [官方文档](https://github.com/openresty/lua-resty-lrucache)
- [OpenResty 文档](https://openresty.org/)
- [LuaJIT FFI 文档](https://luajit.org/ext_ffi.html)

## 更新历史

- 2026-06-11: 编译版本 0.15，创建预编译包
- 2024-10-10: 发布版本 0.15