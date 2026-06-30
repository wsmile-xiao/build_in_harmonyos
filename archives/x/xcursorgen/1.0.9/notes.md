# xcursorgen 1.0.9 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `autoreconf -fvi` — 从GitLab archive源码生成configure脚本（需先运行libtoolize --copy --force）
2. `./configure --prefix=$DEFAULT_PREFIX HELP2MAN=/bin/true MAKEINFO=/bin/true` — 配置编译
3. 修复config.status的umask 077 → umask 002（HMDFS SGID兼容性）
4. `./config.status` — 重新生成配置文件
5. `make -j1` — 编译成功
6. `make install DESTDIR=$TEST_PREFIX` — staging安装
7. `make install` — 安装到$DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status创建临时目录失败（Permission denied） | HMDFS上umask 077+SGID导致`drwx--S---`目录无法写入 | 修改config.status：`umask 077` → `umask 002` |
| 2 | C compiler cannot create executables | lld链接器找不到libxml2.so.16 | 添加ohos-sdk llvm/lib到LD_LIBRARY_PATH最前面 |
| 3 | autoreconf需要libtoolize但bash/sed路径问题 | libtoolize脚本引用~/usr/local/bin/bash和sed | 创建~/usr/local/bin/bash和sed符号链接 |

## 源码修改

无源码修改，仅修改生成的config.status（umask修复）

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libXcursor | 1.2.3 | 手动编译 |
| libpng | 1.6.44 | 预编译 |
| x11 | 1.8.12 | 预编译 |
| xproto | 7.0.31 | 预编译 |
| xrender | 0.9.12 | 预编译 |

## 验证结果

```bash
$DEFAULT_PREFIX/bin/xcursorgen --version
xcursorgen version 1.0.9
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/xcursorgen | ~30KB | X光标生成工具 |
| share/man/man1/xcursorgen.1 | ~1KB | man page |

## 注意事项

- HMDFS上umask 077与SGID冲突是系统性问题，所有autotools项目的config.status都需要此修复
- xcursorgen依赖libXcursor，必须先编译安装libXcursor
---

**编译结束**: 2026-06-05 16:58
**最终状态**: built
