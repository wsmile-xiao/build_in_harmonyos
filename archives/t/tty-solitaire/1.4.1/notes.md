# tty-solitaire 1.4.1 编译笔记

**日期**: 2026-06-11
**状态**: ✅ published

---

## 编译上下文

- **软件**: tty-solitaire 1.4.1 — 终端 ncurses 纸牌游戏（Klondike Solitaire）
- **源码**: https://github.com/mpereira/tty-solitaire/archive/refs/tags/v1.4.1.tar.gz
- **SHA256**: 8eb536a87f0586e1f057a3aa05256df34cbd92a3e22545d1df2f945e27d89db2
- **许可证**: MIT
- **语言**: C (ansi/c99)
- **构建系统**: plain Makefile（⚠️ 不是 autotools，无 configure 脚本）

---

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init-build | ✅ | init-build 成功，环境检查通过 |
| Step 2 编译 | ✅ | plain Makefile 直接 make，无 configure |
| Step 3 安装 | ✅ | DESTDIR 模式安装成功，产物: bin/ttysolitaire |
| Step 4 测试 | ✅ | ttysolitaire_test 执行退出码 0 |
| Step 5 staging | ✅ | staging 产物验证通过 |
| Step 6 package | ✅ | 预编译包 313KB 制作成功 |
| Step 7 finish | ✅ | G1-G4 全 PASS，状态 published |

---

## 编译命令

tty-solitaire 是纯 Makefile 项目（不是 autotools），无 configure 脚本，直接使用 make 编译：

```bash
make CC=clang \
  CFLAGS="-fPIC -O2 -I$DEFAULT_PREFIX/include -W -Wall -pedantic -ansi -std=c99 -DVERSION=\"1.4.1\"" \
  LDFLAGS="-lncursesw -L$DEFAULT_PREFIX/lib"
```

安装命令：
```bash
make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
```

---

## 对话记录

### 问题1: 构建系统识别错误

**现象**: init-build 自动检测为 autotools，但实际是 plain Makefile
**诊断**: tty-solitaire 源码目录只有 Makefile，没有 configure/configure.ac
**解决**: 修正 manifest.yaml 中 `build_system: makefile`，直接 make 编译
**知识级别**: L2 模式经验 → E091

### 问题2: ncurses.h 头文件缺失

**现象**: 编译时报 `fatal error: 'ncurses.h' file not found`
**诊断**: ncurses 6.4 预编译包 (ncurses-6.4-ohos-aarch64.tar.gz) 只包含 bin/、lib/libncursesw.a 和 share/terminfo，不包含开发头文件 (curses.h, term.h)
**解决**: 从 ncurses 6.4 源码手动生成 curses.h：
  1. 提取 ncurses 源码 (ncurses-6.4.tar.gz)
  2. 用 sed 替换 curses.h.in 中所有 @placeholder@ 生成 curses.head
  3. 运行 MKkey_defs.sh 生成按键定义
  4. 拼接 curses.head + MKkey_defs输出 + curses.wide + curses.tail → 完整 curses.h
  5. 安装到 ~/usr/local/include/curses.h 和 ncurses.h（符号链接）
  6. 同步生成 unctrl.h, ncurses_dll.h
**知识级别**: L1 平台真理 → E090

### 问题3: ncurses configure 在 HMDFS 上失败

**现象**: ncurses configure 运行时 config.status 无法创建临时文件 (Permission denied)
**诊断**: HMDFS 文件系统限制了 config.status 脚本在源目录创建随机临时子目录 (csXXXX/out)
**解决**: 改用手动从模板生成头文件方式，绕过 configure
**知识级别**: L1 平台真理 → E010

### 问题4: VERSION 宏浮点常量错误

**现象**: 编译报 `invalid suffix '.1' on floating constant`
**诊断**: Make 命令行 `-DVERSION="1.4.1"` 被 shell 吃掉引号，变为 `-DVERSION=1.4.1`
**解决**: 使用 `DVERSION=\"1.4.1\"` 或在 CFLAGS 中显式传递引号包裹的版本字符串
**知识级别**: L2 模式经验 → E091

---

## 知识沉淀

### L1 平台真理（不可绕过，必须记录） ✅
- ✅ **E090**: ncurses 预编译包不含开发头文件 (curses.h)，依赖 ncurses 的软件必须从源码手动生成头文件
- ✅ **E010**: HMDFS 文件系统限制 config.status 创建临时文件，导致 autoconf 类项目 configure 可能失败

### L2 模式经验（可复用方法论） ✅
- ✅ **E091**: plain Makefile 项目无需 configure 步骤，直接 `make CC=clang` 编译
- ✅ VERSION 宏定义必须引号包裹 `-DVERSION=\"x.y.z\"`，否则 C99 编译报浮点常量错误
- ✅ ncursesw 链接需 `-L$DEFAULT_PREFIX/lib -lncursesw`（静态库路径）

### L3 项目特定（仅本项目） ✅
- ✅ tty-solitaire 4个 -Wreturn-type 警告 (cursor.c:112, cursor.c:144, game.c:34, game.c:57) 属上游代码缺陷
- ✅ 游戏运行需要真实终端环境 (xterm/VT100)，无终端时报 "Error opening terminal" 并退出---

**编译结束**: 2026-06-12 10:32
**最终状态**: published
---

**编译结束**: 2026-06-12 10:33
**最终状态**: published
