# lpeg 1.1.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载 Lua 5.4.7 源码并编译（获取 Lua headers）
   ```bash
   curl -L -o lua-5.4.7.tar.gz "https://www.lua.org/ftp/lua-5.4.7.tar.gz"
   tar xzf lua-5.4.7.tar.gz
   cd lua-5.4.7 && make linux CC=clang MYCFLAGS="-fPIC -O2"
   ```

2. 编译 lpeg
   ```bash
   cd lpeg-1.1.0
   make linux CC=clang LUADIR=/path/to/lua-5.4.7/src/
   ```

3. 测试
   ```bash
   LUA_CPATH="./?.so" LUA_PATH="./?.lua" /path/to/lua test.lua
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Lua 不在 Conan 制品仓 | Lua 未作为 Conan 配方发布 | 在 conanfile.py 的 build() 中从源码构建 Lua 获取 headers |
| 2 | lpeg.so 加载失败 | 未设置 LUA_CPATH | 设置 LUA_CPATH 指向 lpeg.so 所在目录 |

## 依赖版本

- Lua 5.4.7（构建时依赖，从源码编译获取 headers）
- lpeg 源码: https://www.inf.puc-rio.br/~roberto/lpeg/lpeg-1.1.0.tar.gz

## 验证结果

```bash
$ make linux CC=clang LUADIR=/path/to/lua-5.4.7/src/
# 编译成功，生成 lpeg.so

$ LUA_CPATH="./?.so" LUA_PATH="./?.lua" lua test.lua
General tests for LPeg library
LPeg 1.1.0
OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| lpeg.so | Lua 扩展库，运行时由 Lua require("lpeg") 加载 |

## 注意事项

- lpeg 是 Lua 扩展库（.so），不是独立可执行文件
- 需要安装 Lua 才能使用 lpeg
- Lua 尚未作为 Conan 配方发布，conanfile.py 在 build() 中从源码构建 Lua
- 无需补丁，通过 make 变量 CC 和 LUADIR 即可完成编译
---

**编译结束**: 2026-07-15 23:26
**最终状态**: built
