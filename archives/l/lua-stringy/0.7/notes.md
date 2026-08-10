# lua-stringy 0.7 适配笔记

## 编译环境
- 构建系统: custom (direct compiler invocation)
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GitHub 下载 v0.7-0 tag 源码: https://github.com/mdeneen/lua-stringy/archive/v0.7-0.tar.gz
2. 源码结构: 解压后源码在 stringy/ 子目录
3. 使用 conan 依赖 lua/5.4.8 (提供 liblua.a 带 -fPIC 和头文件)
4. 下载 lua 5.4.8 源码, 编译 lua 解释器 (lua.c 链接 conan liblua.a)
5. 编译 stringy.c: clang -c -O3 -Wall -Werror -fPIC -I<lua_inc> -o stringy.o stringy/stringy.c
6. 链接 stringy.so: clang -shared stringy.o -L<lua_lib> -llua -lm -ldl -o stringy.so
7. ELF 签名 (OHOS)
8. 打包: lib/lua/5.4/stringy.so + bin/lua (测试用)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lua/5.4.8 conan 包没有解释器二进制 | conan 配方只打包 liblua.a 和头文件 | 从源码编译 lua 解释器 (lua.c) |
| 2 | lua/5.5.0 liblua.a 没有 -fPIC | lua/5.5.0 conan 配方未添加 -fPIC | 改用 lua/5.4.8 (有 -fPIC) |
| 3 | stringy.so 链接需要 liblua.a | lld 不允许未定义符号 | 链接 conan liblua.a |
| 4 | join() 在 Lua 5.4 下失败 | luaL_buffinit 压入 userdata, lua_gettop 多算 1 | 补丁: 将 lua_gettop 移到 luaL_buffinit 之前 |

## 补丁

- 0001-fix-join-lua54-buffinit-stack.patch: 修复 join() 在 Lua 5.4 下的兼容性问题

## 依赖版本

- lua: 5.4.8 (conan 制品仓)
- clang: 15.0.4

## 验证结果

- conan create: ✅ 通过
- test_package: ✅ 全部测试通过 (37 个断言, 7 个函数)
- W3 本地 CI 模拟: ✅ 通过

---
**编译结束**: 2026-08-07
**最终状态**: built
