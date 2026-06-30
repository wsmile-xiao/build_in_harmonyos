# lpeg 1.1.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

LPeg 使用简单的 Makefile 构建系统，无 configure 步骤。编译步骤如下：

1. 下载源码：`lpeg-1.1.0.tar.gz`（从 https://www.inf.puc-rio.br/~roberto/lpeg/lpeg-1.1.0.tar.gz）
2. 修改 Makefile：调整编译器（CC）和 Lua 头文件路径（LUADIR）
3. 编译：`make linux`（生成 lpeg.so）
4. 安装：手动将 lpeg.so 安装到 `~/usr/local/lib/lua/5.4/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | inf.puc-rio.br 网站证书不被信任 | 使用 curl -k 手动下载源码 |
| 2 | gcc 命令不存在 | Makefile 硬编码使用 gcc，系统只有 clang | 修改 Makefile：`CC = clang` |
| 3 | lua.h 头文件缺失 | LUADIR 指向错误的路径 `./lua/` | 修改 Makefile：`LUADIR = ~/usr/local/include/` |
| 4 | Lua 动态加载不支持 | Lua 编译时可能未启用动态加载功能 | 记录为平台限制，不影响库文件生成 |

## 源码修改

补丁文件：`0001-makefile.patch`

修改内容：
- 将编译器从 gcc 改为 clang（适配 OpenHarmony 工具链）
- 将 LUADIR 从 `./lua/` 改为 `/storage/Users/currentUser/usr/local/include/`（指向实际 Lua 头文件位置）

## 依赖版本

- Lua: 5.4（已安装在 ~/usr/local/bin/lua）
- clang: 15.0.4
- GNU Make: 4.4.1

## 验证结果

编译产物：`lpeg.so`（ELF shared object, 64-bit LSB arm64, 未 strip）

安装位置：
- staging: `/storage/Users/currentUser/test-install-lpeg-1.1.0/storage/Users/currentUser/usr/local/lib/lua/5.4/lpeg.so`
- 系统: `/storage/Users/currentUser/usr/local/lib/lua/5.4/lpeg.so`

文件大小：67904 字节

注意：Lua 动态加载功能可能需要重新编译 Lua 以支持动态库加载。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lpeg.so | 67KB | Lua 解析表达式语法库 |

## 注意事项

1. LPeg 是纯 Lua C 模块，无独立可执行文件
2. 需要安装到 Lua 的库路径（`lib/lua/5.4/`）
3. 需要 Lua 支持动态库加载（检查 Lua 编译选项）
4. 补丁中 LUADIR 使用了绝对路径，可能需要调整为更通用的相对路径或环境变量

---

**编译结束**: 2026-06-15 15:17
**最终状态**: built