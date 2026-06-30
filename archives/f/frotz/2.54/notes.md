# Frotz 2.54 编译笔记

## 编译信息

- **软件**: frotz
- **版本**: 2.54
- **状态**: published
- **日期**: 2026-06-04
- **构建系统**: Makefile

## 源码获取

从清华镜像获取 Debian 源码包：
```bash
curl -k -L -o frotz_2.54.orig.tar.xz \
  "https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/f/frotz/frotz_2.54+dfsg.orig.tar.xz"
```

## 编译过程

### 1. 初始化

```bash
ohc-run.py init-build frotz 2.54 --url=file://$HOME/builds/frotz-2.54.tar.xz --no-download
```

### 2. 编译

frotz 使用 Makefile 构建系统，无 configure 脚本：

```bash
cd ~/builds/frotz-2.54.work
make PREFIX=/storage/Users/currentUser/usr/local \
     SOUND_TYPE=none \
     CC=clang \
     CFLAGS="-Wall -std=c99 -O3 -g -D_DEFAULT_SOURCE -D_XOPEN_SOURCE=600" \
     CURSES_CFLAGS="-I/storage/Users/currentUser/usr/local/include -D_XOPEN_SOURCE_EXTENDED" \
     CURSES_LDFLAGS="-L/storage/Users/currentUser/usr/local/lib -lncursesw"
```

### 3. 安装

OpenHarmony 缺少 install 命令，手动安装：
```bash
mkdir -p ~/tmp/test-install-frotz-2.54/usr/local/bin
mkdir -p ~/tmp/test-install-frotz-2.54/usr/local/share/man/man6
cp frotz ~/tmp/test-install-frotz-2.54/usr/local/bin/
chmod 755 ~/tmp/test-install-frotz-2.54/usr/local/bin/frotz
```

### 4. 打包验证

```bash
ohc-run.py package frotz 2.54
make install  # 安装到本地
~/usr/local/bin/frotz -v  # 验证
```

## 遇到的问题

### 问题 1: cc 命令不存在

**根因**: Makefile 默认使用 cc，系统只有 clang

**解决**: 设置 `CC=clang`

### 问题 2: strdup 未声明

**根因**: C99 模式需要 feature test macro

**解决**: 添加 `-D_DEFAULT_SOURCE -D_XOPEN_SOURCE=600`

### 问题 3: true/false 未定义

**根因**: ux_input.c 缺少 stdbool.h

**解决**: 补丁添加 `#include <stdbool.h>` 到 src/curses/ux_input.c

### 问题 4: KEY_MOUSE 未定义

**根因**: ncursesw 静态编译时缺失鼠标定义

**解决**: 补丁手动定义 `KEY_MOUSE = 0631`

### 问题 5: ncurses.h 未找到

**根因**: ncursesw 在非标准路径

**解决**: 设置 `CURSES_CFLAGS=-I~/usr/local/include`

### 问题 6: install 命令不存在

**根因**: OpenHarmony 缺少 install 工具

**解决**: 手动 cp + chmod

## 补丁说明

### 0001-src-curses-ux_input.c.patch

修复 ncursesw 静态编译问题：
- 添加 `#include <stdbool.h>`
- 定义 `KEY_MOUSE = 0631`

## 验证结果

```
FROTZ V2.54 - Curses interface. Audio output disabled.
Git commit: 5a86de2f0799bde12699a0189ea12be8c96194a5
```

## 质量门禁

- G0 干净构建: N/A（无 configure）
- G1 二进制完整性: PASS
- G2 功能可用性: PASS
- G3 可移植性: PASS
- G4 档案完整性: PASS

## 编译结束

**最终状态**: published
**产物**: frotz-2.54-ohos-aarch64.tar.gz (395KB)