# E082 — HMDFS文件系统mktemp临时目录权限限制

## 问题概述

HMDFS（鸿蒙分布式文件系统）对`mktemp`创建的临时目录有特殊权限限制，导致autotools构建系统的`config.status`脚本无法在当前目录创建临时文件。

## 错误特征

```
./config.status[810]: can't create ./confiJElPG/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

## 根本原因

1. `mktemp -d "./confXXXXXX"`创建的目录权限为`drwx--S---`（仅owner权限+setgid位）
2. config.status脚本无法在其中创建subs1.awk等临时文件
3. chmod命令无法修改HMDFS文件系统上的目录权限（平台限制）

## 解决方案

**方案一：修改config.status使用固定目录**
```bash
mkdir -p tmp_work
sed -i 's/mktemp -d "./confXXXXXX"/mkdir -p "tmp_work"/' config.status
```

**方案二：使用简单Makefile编译方式**
- 避开autotools的configure阶段
- 直接执行make编译

**方案三：在非HMDFS目录编译**
- 在`~/tmp`目录执行configure（TMPDIR已设置）

## 受影响软件

tmux, zsh, hwloc, procps 等使用autotools构建系统的软件

## 发现时间

2026-04-27，机器E编译任务
