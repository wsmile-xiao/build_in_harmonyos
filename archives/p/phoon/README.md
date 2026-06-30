# phoon — 月相显示工具

phoon 是一个用 ASCII 图形显示月球当前或指定日期相位的小型命令行工具。不同于其他只报告数值的程序，phoon用直观的ASCII图形"展示"月球的外观。

## 功能特点
- 用 ASCII 图形直观展示月球相位（新月、上弦月、满月等）
- 支持指定日期查询月相（格式: "DD Mon YYYY"，如 "15 Jun 2026"）
- 支持 `-l` 参数调整月相图大小
- 无外部依赖，纯 C 实现，仅需 -lm 数学库
- 输出附带月相详细信息（新月天数、上弦月时间等）

## 构建信息
- 构建系统: Makefile（无 configure 脚本，需手动适配）
- 编译器: clang
- 许可证: BSD-2-Clause
- 作者: Jef Poskanzer（月相计算来自 John Walker 的 "moontool.c"）

## 注意事项
- 系统无 cc 命令，Makefile 需将 CC 改为 clang
- 原版 Makefile 无 DESTDIR 支持，需添加以适配预编译打包
- 仅支持 "DD Mon YYYY" 格式的日期参数，ISO格式（YYYY-MM-DD）不被接受
