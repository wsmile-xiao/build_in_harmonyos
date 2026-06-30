# lavat

Lavat 是一个终端 lava lamp 模拟程序，使用 metaballs 算法和 unicode 块字符在终端中创建动态视觉效果。它是一个轻量级的终端图形演示软件。

## 功能概述

- 在终端中模拟 lava lamp 动画效果
- 使用 metaballs 算法生成动态图形
- 支持多种颜色和效果参数
- 基于 termbox 库实现终端渲染

## OHOS 适配要点

- **构建系统**: 简单 Makefile（非 autotools），无 configure 脚本
- **DESTDIR 支持**: 需要补丁修改 Makefile install 目标，添加 `$(DESTDIR)` 前缀，符合 R20 DESTDIR 模式铁律
- **许可证**: MIT（不是 GPL-2.0-or-later）
- **仓库**: 实际仓库为 `AngelJumbo/lavat`（不是 `angel-pazos/lavat`）
- **测试**: 无 make check 目标（demo 类软件，不包含测试套件）
- **版本参数**: 不支持 `--version` 参数

## 依赖关系

- **编译依赖**: 无（纯 C 程序，仅依赖系统 musl libc）
- **运行依赖**: musl libc（系统自带）

## 源码结构

| 文件 | 大小 | 说明 |
|------|------|------|
| lavat.c | 18KB | 主程序源码 |
| makefile | 244B | 简单 Makefile |
| termbox.h | 117KB | 内嵌 termbox 头文件 |
| LICENSE | 1KB | MIT 许可证 |

## 参考资料

- 官方仓库: https://github.com/AngelJumbo/lavat
- 许可证: MIT License
