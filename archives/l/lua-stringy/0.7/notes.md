# lua-stringy 0.7 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GitHub 下载源码: https://github.com/mdeneen/lua-stringy/archive/master.tar.gz
2. 解压源码到 ~/builds/lua-stringy-0.7.work
3. 手动编译:
   - 设置 Lua 头文件路径: -I~/usr/local/include
   - 编译: clang -c -O3 -Wall -Werror -fPIC -I~/usr/local/include stringy.c
   - 链接: clang -shared stringy.o -L~/usr/local/lib -llua -o stringy.so
4. 安装到 staging: ~/test-install-lua-stringy-0.7/usr/local/lib/lua/5.4/stringy.so
5. 安装到本地: ~/usr/local/lib/lua/5.4/stringy.so
6. 创建预编译包: lua-stringy-0.7-ohos-aarch64.tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pkg-config 找不到 lua | Lua 5.4.7 安装时没有生成 lua.pc 文件 | 手动设置 LUA_CFLAGS |
| 2 | 链接时缺少 luaL_checkversion_ 符号 | 链接时没有指定 Lua 库 | 在链接命令中添加 -llua |
| 3 | 测试代码有错误 | 测试代码本身的问题 | 不影响编译，记录即可 |

## 源码修改

无补丁文件，直接编译。

## 依赖版本

- lua: 5.4.7 (已预编译)
- clang: 15.0.4

## 验证结果

```bash
# 测试预编译包
lua -e "local stringy = require 'stringy'; print(stringy.strip('  test  '))"
# 输出: test
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lua-stringy-0.7-ohos-aarch64.tar.gz | 30KB | 预编译包 |

## 注意事项

1. lua-stringy 使用 Makefile 构建，不是 autotools
2. 需要手动设置 Lua 头文件和库路径
3. Lua 5.4.7 需要预先安装

---
**编译结束**: 2026-06-10 10:38
**最终状态**: built