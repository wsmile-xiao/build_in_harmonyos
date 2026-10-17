# lua-pty 1.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 状态: built

## 编译步骤

lua-pty 是一个 Lua PTY（伪终端）绑定库，使用 C++ 编写，需要编译成 Lua 模块 (core.so)。

1. 下载源码：从 GitHub AshleighAdams/lua-pty v1.1 tag 获取
2. 修改 include 路径：`src/main.cpp` 中 `#include <lua5.2/lua.hpp>` 改为 `#include <lua.hpp>`
3. 修改 config 文件：适配 Lua 5.4 安装路径
4. 编译 core.o：`clang++ -o core.o -c -fPIC -O3 -Wall -Werror --std=c++11 -I$HOME/usr/local/include src/main.cpp`
5. 编译 core.so：`clang++ -o core.so -shared -lutil -L$HOME/usr/local/lib -Wl,--whole-archive -llua-pic -Wl,--no-whole-archive -lm core.o`
   - 注意：需要使用 PIC 编译的 liblua-pic.a（Lua 需用 -fPIC 编译）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah URL 404 | lua-pty 在 Savannah 上不存在或已移除 | 使用 GitHub 仓库 URL |
| 2 | SSL 证书验证失败 | Python urllib SSL 问题 | 使用 curl -k 手动下载 |
| 3 | `#include <lua5.2/lua.hpp>` 找不到 | 源码硬编码 Lua 5.2 路径 | 修改为 `<lua.hpp>` |
| 4 | liblua.a 非 PIC 编译 | 静态库无 -fPIC，无法链接到 .so | 重新编译 Lua 带 -fPIC |
| 5 | Lua 二进制未签名 | HMDFS 限制，未签名 ELF 不可执行 | 使用 sign-elf 工具签名 |

## 源码修改

1. **config** - 修改安装路径适配 Lua 5.4
   - PREFIX = $(DESTDIR)/usr → $(DESTDIR)/usr/local
   - LUA_LIBDIR/LUA_DIR: lua/5.2 → lua/5.4

2. **src/main.cpp** - 修改 include 路径
   - `#include <lua5.2/lua.hpp>` → `#include <lua.hpp>`

## 依赖版本

- Lua 5.4.7（需要 PIC 编译的静态库）
- clang 15.0.4

## 验证结果

```bash
# 编译产物
ls ~/builds/lua-pty-1.1.work/core.so
# -rwxrwx--- 334272 2026-06-12 core.so

# 本地安装
ls ~/usr/local/lib/lua/5.4/pty/core.so
ls ~/usr/local/share/lua/5.4/pty.lua
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lua-pty-1.1-ohos-aarch64.tar.gz | 330K | 预编译包（含 core.so + pty.lua） |
| 0001-config.patch | - | 配置文件补丁 |
| 0002-src-main.cpp.patch | - | 源码 include 路径补丁 |

## 注意事项

1. lua-pty 是 Lua C 模块，需要 Lua 提供 PIC 编译的静态库或动态库才能编译
2. 当前 Lua 预编译包只有静态库，需要手动重新编译 Lua 带 -fPIC 生成 liblua-pic.a
3. 此模块无法独立运行验证（需要 Lua 运行时加载），但编译产物已签名

---
**编译结束**: 2026-06-12 15:28
**最终状态**: built
---

**编译结束**: 2026-07-16 00:03
**最终状态**: built
