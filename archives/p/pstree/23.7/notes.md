# pstree 23.7 — OHOS 适配笔记

## 背景

pstree 是 psmisc 工具包的一部分，用于以树状结构显示运行中的进程。
源码来自 GitLab: https://gitlab.com/psmisc/psmisc

## 构建方式

由于 psmisc 的 autotools 构建系统需要 automake（鸿蒙环境不可用），
采用单文件编译方式：

```bash
clang -DVERSION='"23.7"' -I<ncurses_inc> -o pstree src/pstree.c -L<ncurses_lib> -lncursesw
```

## 适配关键点

1. **跳过 config.h**: 不定义 `HAVE_CONFIG_H`，跳过 `#include <config.h>`
2. **VERSION 宏**: 手动定义 `-DVERSION='"23.7"'`，通常由 configure 脚本生成
3. **ncursesw 依赖**: 使用 OHPCD 制品仓中的 `ncurses/6.6`，提供 `libncursesw.a` + 头文件
4. **SELinux/AppArmor**: 默认关闭，不影响编译
5. **statx**: 代码中有 statx 检测，但未定义 `WITH_STATX`，会使用 stat() 回退

## 验证

```bash
$ pstree --version
pstree (PSmisc) 23.7
Copyright (C) 1993-2024 Werner Almesberger and Craig Small
```

```bash
$ pstree -p 1
init(1)───...
```

## 已知限制

- 仅包含 pstree 工具，不包含 psmisc 的其他工具（killall, fuser, peekfd 等）
- 如需其他工具，需单独编译对应的 .c 文件
---

**编译结束**: 2026-08-08 02:24
**最终状态**: built
