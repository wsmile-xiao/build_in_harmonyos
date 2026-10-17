# pstree (from psmisc) 23.7 for HarmonyOS

## 概述

pstree 是显示进程树的命令行工具，属于 psmisc 包的一部分。由于 psmisc 的
autotools 构建系统需要 automake（鸿蒙环境不可用），采用单文件编译 pstree.c。

## 编译信息

- **版本**: 23.7 (基于 psmisc v23.7)
- **构建方式**: 单文件编译（clang 直接编译 src/pstree.c）
- **依赖**: ncurses/6.6 (from OHPCD 制品仓, 静态链接 libncursesw.a)

## 构建方式

```bash
# Conan 驱动构建
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 适配说明

1. **单文件编译**: autotools 不可用，直接编译 pstree.c
2. **VERSION 宏**: 手动定义 `-DVERSION='"23.7"'`
3. **跳过 config.h**: 不定义 `HAVE_CONFIG_H`
4. **ncurses 依赖**: 使用 conan 制品仓的 ncurses/6.6

## 验证

```bash
$ pstree --version
pstree (PSmisc) 23.7
Copyright (C) 1993-2024 Werner Almesberger and Craig Small
```
