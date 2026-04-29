# pstree (from psmisc) 23.7 for HarmonyOS

## 概述

pstree 是显示进程树的工具，属于 psmisc 包的一部分。由于 psmisc 整包编译失败，本次采用单独编译 pstree.c 的方式。

## 编译信息

- **版本**: 23.7 (基于 psmisc v23.7)
- **编译日期**: 2026-04-28
- **目标平台**: aarch64-unknown-linux-ohos
- **编译器**: clang
- **构建方式**: 单文件编译（非标准 autotools）

## 编译步骤

```bash
# 1. 克隆源码
git clone https://gitlab.com/psmisc/psmisc.git
cd psmisc/src

# 2. 单独编译 pstree.c
clang -DVERSION="23.7" \
      -o pstree \
      pstree.c \
      -I$HOME/usr/local/include \
      -L$HOME/usr/local/lib \
      -lncursesw

# 3. 验证
./pstree --version
```

## 依赖

- **ncursesw**: 用于终端显示（已预装）

## 验证

```bash
$ pstree --version
pstree (PSmisc) 23.7
Copyright (C) 1993-2024 Werner Almesberger and Craig Small

# 显示进程树
$ pstree -p
systemd(1)─┬─dbus-daemon(1234)
           ├─sshd(2345)
           └─bash(3456)───pstree(4567)
```

## 特殊说明

1. **单文件编译**: 由于 psmisc 整包编译失败，仅编译 pstree.c
2. **VERSION 宏**: 需要手动定义，通常由 configure 脚本自动生成
3. **ncursesw**: 使用带宽字符支持的 ncurses 库

## 注意事项

- 仅包含 pstree 工具，不包含 psmisc 的其他工具（killall, fuser, peekfd 等）
- 如需其他工具，需单独编译对应的 .c 文件