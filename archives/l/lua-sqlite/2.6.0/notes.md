# lua-sqlite 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 通过 Conan 安装依赖: `conan install --requires=lua/5.4.8 --requires=sqlite3/3.49.1 -r=ohpcd`
2. 使用 make 变量覆盖 config 配置:
   ```bash
   make sqlite3 CC=clang LUA_INC=<lua_include> DRIVER_INCS_sqlite3=-I<sqlite3_inc> DRIVER_LIBS_sqlite3="-L<sqlite3_lib> -lsqlite3" LIB_OPTION=-shared
   ```
3. 无需补丁 — 所有路径通过 make 命令行变量传递，覆盖 config 默认值

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 历史补丁包含硬编码路径 | 历史手动构建使用 /storage/Users/currentUser/usr/local 等路径 | Conan 配方不使用补丁，通过 make 变量传递 Conan 依赖路径 |
| 2 | Lua 符号重复定义 | 历史补丁链接 -llua 导致 Lua 符号静态链接进 .so | 不链接 -llua，Lua 符号在运行时由宿主解释器解析 |
| 3 | require("luasql.sqlite3") 找不到模块 | .so 需放在 luasql/ 子目录 | package() 安装到 lib/luasql/sqlite3.so |

## 源码修改

无补丁。Conan 配方通过 make 变量覆盖 config 文件的默认路径:
- LUA_INC: Lua 头文件路径 (来自 Conan lua/5.4.8)
- DRIVER_INCS_sqlite3: SQLite3 头文件路径 (来自 Conan sqlite3/3.49.1)
- DRIVER_LIBS_sqlite3: SQLite3 库路径 (来自 Conan sqlite3/3.49.1)

## 依赖版本

- lua/5.4.8 (Conan 制品仓)
- sqlite3/3.49.1 (Conan 制品仓)

## 验证结果

```bash
# 编译验证
conan create . --build=missing

# 测试验证
# test_package 编译最小 Lua 解释器，加载 luasql.sqlite3 模块，
# 执行建表、插入、查询、关闭等操作
```

## 注意事项

- Lua 扩展模块 (.so) 不应链接 -llua，Lua 符号在运行时解析
- .so 文件必须安装到 lib/luasql/ 子目录以匹配 Lua require 路径
- test_package 使用 Conan lua 依赖编译最小解释器，无需从外部下载 Lua 源码
---

**编译结束**: 2026-08-07 02:10
**最终状态**: published
