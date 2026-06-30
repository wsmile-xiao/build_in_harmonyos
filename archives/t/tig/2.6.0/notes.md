# tig 2.6.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 从 GitHub 下载源码包
   - URL: https://github.com/jonas/tig/releases/download/tig-2.6.0/tig-2.6.0.tar.gz

2. 初始化编译环境
   - 使用 ohc-run.py init-build 创建工作目录

3. 安装依赖 ncurses
   - 尝试预编译包但头文件不完整
   - 从源码编译 ncurses 6.4（静态库，--without-shared）
   - 手动复制头文件到 ~/usr/local/include

4. 修复平台问题
   - 更新 config.guess/config.sub（支持 ohos）
   - 修改 configure 中的 umask 077 为 umask 022（E011）

5. 执行编译
   - configure --prefix=/storage/Users/currentUser/usr/local
   - CFLAGS="-I/storage/Users/currentUser/usr/local/include"
   - LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"
   - make -j4

6. 手动安装（因 tools/install.sh 有问题）
   - cp src/tig ~/usr/local/bin/
   - cp doc/tig.1 ~/usr/local/share/man/man1/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ncurses not found | 预编译包缺少头文件 | 从源码编译 ncurses 6.4 |
| 2 | config.guess无法识别系统 | 旧版本不支持 ohos | 更新为支持 ohos 的版本 |
| 3 | config.status临时目录权限失败 | HMDFS umask 077 限制 | 修改 configure 中 umask（E011） |
| 4 | curses.h找不到 | ncurses 头文件未安装 | 手动复制 curses.h/term.h/termcap.h |
| 5 | ncurses_dll.h找不到 | 缺少dll头文件 | 复制 ncurses_dll.h |
| 6 | tools/install.sh失败 | install命令路径问题 | 手动cp安装 |

## 源码修改

应用了 1 个补丁文件：
- configure.patch：修改 umask 077 为 umask 022

## 依赖版本

- ncurses 6.4（静态库，--without-shared）
- clang 15.0.4
- GNU Make 4.4.1

## 验证结果

```bash
# 版本验证
/storage/Users/currentUser/usr/local/bin/tig --version
tig version 2.6.0
ncurses version 6.4.20221231

# 二进制文件检查
ls -lh /storage/Users/currentUser/usr/local/bin/tig
-rwxrwx--- 1 20001006 file_manager 1.0M 2026-05-25 18:00 tig

# 预编译包
tig-2.6.0-ohos-aarch64.tar.gz (1.0M)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tig-2.6.0-ohos-aarch64.tar.gz | 1.0M | 预编译包 |
| configure.patch | ~1K | umask 修改补丁 |

## 注意事项

1. tig 需要 ncurses 库支持，必须编译静态库版本
2. HMDFS 文件系统的 umask 077 限制会导致 autotools configure 失败
3. ncurses 头文件必须完整安装（包括 curses.h、term.h、termcap.h、ncurses_dll.h）
4. tools/install.sh 在鸿蒙系统上可能失败，需要手动安装

---
**编译结束**: 2026-05-26
**最终状态**: published
---

**编译结束**: 2026-05-26 09:54
**最终状态**: built
