# sl — Steam Locomotive

## 简介
sl (Steam Locomotive) 是一个经典的终端动画命令行玩具程序。
当用户误输入 `sl` (而非 `ls`) 时，会在终端显示一个动画火车。

## 版本历史
- 5.02-r1: 编译成功 (2026-06-04)

## 特点
- 简单 C 项目，单文件 Makefile 构建系统
- 依赖 ncurses (使用 ncursesw wide-char 版本)
- 无 configure 脚本，直接 make 编译

## 用法
```bash
sl        # 显示普通火车
sl -l     # 显示小火车
sl -a     # 显示事故场景
sl -F     # 火车飞行
sl -c     # 显示 C51 车型
```
