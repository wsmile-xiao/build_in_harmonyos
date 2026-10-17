# luasql 2.4.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4
- 状态: published

## 源码信息
- 仓库: https://github.com/lunarmodules/luasql
- 版本: v2.4.0
- SHA256: db2458a8c8c5f3bc717e4030fe2878f1ad8d71e437ec6149c381eebad5d525c5

## 编译步骤

### 1. 构建 Lua 5.4.7（从源码）
- 下载: https://www.lua.org/ftp/lua-5.4.7.tar.gz
- 构建: `make linux MYCFLAGS="-fPIC" CC=clang`
- 安装到本地前缀

### 2. 构建 SQLite3（从 amalgamation 源码）
- 下载: https://www.sqlite.org/2024/sqlite-autoconf-3460000.tar.gz
- 直接编译 sqlite3.c（不使用 configure，因 OHOS 不识别平台）
- `clang -c -O2 -fPIC -DSQLITE_THREADSAFE=1 sqlite3.c -o sqlite3.o`
- `llvm-ar rcu libsqlite3.a sqlite3.o`

### 3. 构建 LuaSQL SQLite3 驱动
- 修改 config 文件:
  - PREFIX → 本地安装路径
  - LUA_SYS_VER → 5.4
  - LUA_INC → $(PREFIX)/include
  - DRIVER_LIBS_sqlite3 → -L$(PREFIX)/lib -lsqlite3 -llua -lm -ldl
  - DRIVER_INCS_sqlite3 → -I$(PREFIX)/include
  - CC → clang
- 编译: `make sqlite3`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Lua 不在 conan 制品仓 | 依赖未发布 | conanfile.py 中从源码构建 Lua |
| 2 | SQLite3 不在 conan 制品仓 | 依赖未发布 | conanfile.py 中从源码构建 SQLite3 |
| 3 | SQLite3 configure 失败 | config.guess 不识别 OHOS | 直接编译 amalgamation 源码 |
| 4 | Lua 扩展模块链接失败 | OHOS 不支持动态符号导出 | 显式链接 -llua |
| 5 | Lua make guess 失败 | uname 返回 HarmonyOS | 使用 make linux 目标 |

## 验证结果

```bash
# 编译产物
lib/lua/5.4/luasql/sqlite3.so

# 功能验证（成功）
- 模块加载: require('luasql.sqlite3') ✅
- 创建环境: luasql.sqlite3() ✅
- 连接数据库: env:connect(':memory:') ✅
- 创建表: conn:execute('CREATE TABLE...') ✅
- 插入数据: conn:execute('INSERT...') ✅
- 查询数据: cursor:fetch() ✅
- 更新数据: conn:execute('UPDATE...') ✅
- 删除数据: conn:execute('DELETE...') ✅
```

## 依赖说明

由于 lua 和 sqlite3 尚未发布到 conan 制品仓，conanfile.py 采用自包含方式：
- 在 build() 方法中从源码构建 Lua 5.4.7 和 SQLite3
- 不声明外部 conan 依赖
- 产物包含 lua 二进制（用于测试）和 luasql .so 模块

## 注意事项

1. LuaSQL 使用 Makefile 系统，不支持 configure 脚本
2. 需要手动修改 config 文件适配 OpenHarmony 环境
3. OHOS 上 Lua 扩展模块必须显式链接 -llua
4. SQLite3 configure 在 OHOS 上失败，使用 amalgamation 直接编译
5. 仅编译了 SQLite3 驱动，其他数据库驱动需要对应的依赖库

---

**编译结束**: 2026-07-15
**最终状态**: published
