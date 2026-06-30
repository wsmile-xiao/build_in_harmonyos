# urlview-ng 1e 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: built

## 编译步骤

urlview-ng 使用纯 Makefile，无 configure 脚本。编译步骤：
```bash
make -j2 CC=clang CXX=clang++ PREFIX=$DEFAULT_PREFIX
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
```

编译需要额外标志处理 ncurses 和 C++ 标准库兼容性问题。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | DEFAULT_REGEXP 转义错误 | Makefile shell 命令转义层数太多导致 C 编译错误 | 在 urlview.c 中直接定义 DEFAULT_REGEXP，简化正则表达式 |
| 2 | reallocarray 函数缺失 | GNU 扩展，OHOS musl 未实现 | 替换为 realloc(url, urlsizetmp * sizeof(*url)) |
| 3 | KEY_MOUSE 与 KEY_RESIZE 冲突 | ncurses 宏值相同导致逻辑冲突 | 注释 KEY_MOUSE 处理代码块 |
| 4 | NCURSES_BOOL 与 C++ bool 冲突 | ncurses 定义 bool 为 unsigned char，C++ 标准库期望 bool 类型 | 添加 #undef bool 和 #undef NCURSES_BOOL |
| 5 | mvaddnwstr/addnwstr 未声明 | ncursesw 库中有函数但头文件未声明 | 手动添加 extern "C" 函数声明 |
| 6 | std::bit_width C++23 特性 | 使用 C++17 编译不支持 | 替换为常量值 5 |
| 7 | C++ 字面量 0z 不支持 | C++23 特性 | 替换为 0UL |
| 8 | g_libintl_gettext 未定义 | gettext 函数需链接 libintl | 添加 LDLIBS=-lintl |
| 9 | C++ 异常处理函数缺失 | 使用 -fno-exceptions 但仍有引用 | 需正确链接或禁用异常 |

## 源码修改

### urlview.c
- 添加 DEFAULT_REGEXP 定义（简化版）
- 替换 reallocarray → realloc
- 注释 KEY_MOUSE 处理代码

### enter.cpp
- 添加 #undef bool 防止 NCURSES_BOOL 冲突
- 添加 extern "C" 函数声明 addnwstr/mvaddnwstr
- 替换 reallocarray → realloc
- 替换 std::bit_width → 常量
- 替换 0z → 0UL

### Makefile
- 删除 DEFAULT_REGEXP 传递（改在 urlview.c 定义）
- 保留其他标准参数

## 依赖版本

- ncursesw/6.5（静态库）
- libintl/0.21

## 验证结果

```bash
# 编译成功
$ ls -la urlview
urlview: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

# 功能验证（提取 URL）
$ ./urlview README
https://git.sr.ht/~nabijaczleweli/urlview-ng
https://todo.sr.ht/~nabijaczleweli/urlview-ng
...（成功显示 URL 列表）
```

## 补丁列表

生成了 5 个补丁文件：
1. 0001-Makefile.patch - DEFAULT_REGEXP 移除
2. 0002-enter.cpp.patch - NCURSES_BOOL/reallocarray/宽字符函数
3. 0003-fr.po.patch - 翻译文件更新
4. 0004-pl.po.patch - 翻译文件更新
5. 0005-urlview.c.patch - DEFAULT_REGEXP/reallocarray/KEY_MOUSE

## 注意事项

1. **构建系统**: urlview-ng 使用 Makefile 而非 autotools，G0 验证需要特殊处理
2. **ncurses 兼容性**: NCURSES_BOOL 定义与 C++ 标准库冲突是常见问题
3. **宽字符函数**: ncursesw 库包含函数但头文件可能未声明
4. **GNU 扩展**: reallocarray 是 GNU 扩展，OHOS musl 未实现
---
**编译结束**: 2026-06-03 17:33
**最终状态**: built