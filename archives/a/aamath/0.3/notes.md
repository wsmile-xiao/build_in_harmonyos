# aamath 0.3 适配笔记

## 编译环境
- 构建系统: makefile (无 configure 脚本)
- 编译日期: 2026-06-16
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码 tarball 并解压
2. 源码中无 configure 脚本，仅有 Makefile / Makefile.good
3. 修改 Makefile.good 适配 OpenHarmony：
   - CXX/LD: g++ → clang++
   - CXXFLAGS: 增加 -fPIC，增加 -I$DEFAULT_PREFIX/include（readline 头文件路径）
   - LIBS: -ltermcap → -lncurses（ncurses 提供 termcap 功能）
   - LFLAGS: 增加 -L$DEFAULT_PREFIX/lib（readline 库路径）
   - PREFIX/DESTDIR: 增加 install target 支持 DESTDIR 模式（R20）
4. bison/flex 重新生成 parser.cc/lexer.cc/parser.h
   - bison 3.8.2 生成 parser.tab.c/parser.tab.h，需重命名为 parser.cc/parser.h
   - parser.cc 中 #include "parser.tab.h" 需修改为 #include "parser.h"
5. make -f Makefile.good → 编译成功（仅有 warning，无 error）
6. make -f Makefile.good install DESTDIR=$TEST_PREFIX → 安装到 staging
7. Staging 验证 → 通过
8. ohc-run.py package → 打包成功
9. make install（不带 DESTDIR）→ 安装到 $DEFAULT_PREFIX
10. 用户验证 → aamath 可正常运行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | parser.cc:120 fatal error: 'parser.hh' file not found | bison 3.8.2 生成 C++ 输出时使用 .hh 扩展名 | 重新用 bison -d 生成 parser.tab.h，重命名为 parser.h；修改 parser.cc 中 #include "parser.tab.h" → #include "parser.h" |
| 2 | aamath.cc:19 fatal error: 'readline/readline.h' file not found | readline 头文件在 $DEFAULT_PREFIX/include 下，不在默认搜索路径 | CXXFLAGS 增加 -I$DEFAULT_PREFIX/include |
| 3 | -ltermcap 不可用 | OpenHarmony 无独立 termcap 库 | 替换为 -lncurses（ncurses 提供 termcap 兼容功能） |

## 源码修改

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| Makefile.good | 适配 OpenHarmony 工具链和库 | 修改编译器、CXXFLAGS、LIBS、增加 install target | ✅ 0001-Makefile.good.patch |
| parser.cc | bison 3.8.2 生成代码引用 parser.tab.h | sed 替换 #include "parser.tab.h" → #include "parser.h" | ✅ 0002-parser.cc.patch |
| parser.h (重命名) | bison 输出文件名与源码不匹配 | 从 parser.tab.h 复制为 parser.h | ✅ 0003-parser.h.patch |
| lexer.cc (重新生成) | flex 重新生成 lexer 代码 | flex lexer.l → lexer.cc | 生成文件无需补丁 |

## 依赖版本

- readline 8.2（预编译包）
- ncurses 6.5（预编译包，静态编译 --without-shared）
- bison 3.8.2（构建工具）
- flex 2.6.4（构建工具）
- clang 15.0.4（编译器）

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/aamath -q < testcases
# 输出 ASCII 数学表达式，正常工作
$ file /storage/Users/currentUser/usr/local/bin/aamath
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| aamath-0.3-ohos-aarch64.tar.gz | 649KB | 预编译包 |

## 注意事项

- aamath 不支持 --version 参数，只通过 -h 显示版本信息
- 该项目无 configure 脚本，是纯 Makefile 项目
- parser.cc 和 lexer.cc 需从 .y/.l 源文件生成（bison/flex）
---

**编译结束**: 2026-06-16 23:27
**最终状态**: published

## 知识图谱草稿

- E052-draft-B9A8: bison 3.8+ 输出文件名与旧 Makefile 不兼容
