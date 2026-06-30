# pcalc

程序员计算器 — 支持多进制、多尺寸、贴近底层位的计算工具。

pcalc 是一个面向程序员的双进制（Decimal + Hex）计算器，支持位运算（AND/OR/XOR/移位）、
算术运算（加减乘除取模）、输入格式（0x十六进制/0b二进制/0o八进制）等特性。

## 基本信息

- **主页**: https://github.com/alt-romes/programmer-calculator
- **许可证**: GPL-3.0-or-later
- **语言**: C
- **构建系统**: makefile（简单 Makefile，无 configure/autotools）
- **依赖**: ncurses（交互界面）

## 鸿蒙适配要点

1. **编译器**: 使用 clang（默认 Makefile 为 gcc），需通过补丁修改
2. **链接器**: 使用 bfd（lld 缺失 libxml2.so.16），需 `-fuse-ld=bfd`
3. **ncurses**: 头文件和库路径不在默认搜索路径，需显式指定
4. **ELF签名**: 鸿蒙平台二进制需要签名才能执行
5. **无 install 目标**: 需手动安装到 DESTDIR staging 目录

## 可用版本

| 版本 | 状态 | 日期 | 补丁 |
|------|------|------|------|
| 3.0 | published | 2026-06-03 | 0001-Makefile.patch（CC/CFLAGS/LFLAGS鸿蒙适配） |