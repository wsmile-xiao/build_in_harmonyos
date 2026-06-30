# poster

## 简介

poster 是一个将 PostScript 文件缩放打印为大尺寸海报的工具。它可以将一个单页的 PostScript 文件缩放并分割为多个页面，以便在普通打印机上打印后拼接成大尺寸海报。

## 功能概述

- 支持指定缩放倍数 (-s) 或目标海报尺寸 (-p)
- 支持指定纸张尺寸 (-m)，如 A4、Letter 等
- 支持设置裁切边距 (-c) 和白边 (-w)
- 支持 verbose 模式 (-v) 输出缩放决策信息
- 支持输出重定向到文件 (-o)
- 自动生成裁切标记和页面标签

## OHOS 适配要点

- 原始 Makefile 硬编码 gcc 和 /usr/local，需补丁 (0001-Makefile.patch) 添加 CC/CFLAGS/PREFIX/DESTDIR 变量
- poster.c 使用已弃用的 gets() 函数，在 C99+ 标准下仅产生编译警告，不影响运行
- 无 configure 脚本，直接使用 make 编译
- poster 不支持 --version 参数，功能验证需通过运行确认

## 依赖关系

- **编译依赖**: 无外部依赖，仅需标准 C 库和数学库 (-lm)
- **运行依赖**: libc.so (musl libc)

## 参考资料

- 源码仓库: https://github.com/schrfr/poster
- 许可证: GPL-2.0-or-later
