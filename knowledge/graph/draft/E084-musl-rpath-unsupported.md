# E084 — musl动态链接器不支持$ORIGIN RPATH

## 问题概述

鸿蒙系统使用musl libc，其动态链接器不支持`$ORIGIN` RPATH扩展，导致依赖RPATH定位共享库的程序运行失败。

## 错误特征

```
error while loading shared libraries: libfoo.so: cannot open shared object file
```

## 根本原因

1. musl动态链接器不支持DT_RPATH和DT_RUNPATH中的`$ORIGIN`扩展
2. 设置`-Wl,-rpath,'$ORIGIN/../lib'`后程序无法找到相对路径的共享库

## 解决方案

**方案一：静态链接（推荐）**
```bash
clang -static -o program program.c libdep.a
```

**方案二：绝对路径RPATH**
```bash
clang -Wl,-rpath,$HOME/usr/local/lib -o program program.c
```

**方案三：LD_LIBRARY_PATH**
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
```

## 受影响软件

lm-sensors 等需要加载共享库的程序

## 发现时间

2026-04-27，机器E编译任务
