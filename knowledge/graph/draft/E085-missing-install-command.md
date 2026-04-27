# E085 — 鸙蒙系统缺少install命令需手动替代

## 问题概述

鸿蒙系统使用toybox提供基础命令，toybox不包含`install`命令，导致Makefile中的install目标执行失败。

## 错误特征

```
install: command not found
sh: install: inaccessible or not found
```

## 根本原因

toybox命令集不包括GNU coreutils的install命令。

## 解决方案

**手动替代方案**
```bash
# install -m 755 program $PREFIX/bin/program 等价于：
mkdir -p $PREFIX/bin
cp program $PREFIX/bin/program
chmod 755 $PREFIX/bin/program
```

**安装GNU coreutils预编译包**
```bash
curl -fsSL https://gitcode.com/.../install.sh | sh -s -- coreutils 9.10
```

## 受影响软件

sysfsutils, lm-sensors 等使用简单Makefile的软件

## 发现时间

2026-04-27，机器E编译任务
