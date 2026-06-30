# fakesteak

ASCII Matrix-like steak demo program. Renders a matrix-style rain effect using ANSI escape codes and ASCII characters in the terminal.

- **URL**: https://github.com/domsson/fakesteak
- **Category**: entertainment
- **Language**: C
- **Build System**: Makefile (plain, no autotools, no configure script)
- **Version**: 0.2.4
- **Dependencies**: none (only libc + libm)

## 鸿蒙适配说明

- 需修改 Makefile 添加 DESTDIR 支持（R20 铁律）
- 需传递 CC=clang（鸿蒙无 cc 命令）
- CFLAGS 需添加 -fPIC（PIE 格式要求）
- HMDFS 文件系统: cp 不能覆盖已存在文件，需先 rm -f
- 无 make check 目标
