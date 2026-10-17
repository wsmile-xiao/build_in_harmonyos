# ASMotor

ASMotor is a portable and generic assembler engine and development system written in ANSI C and
licensed under the GNU General Public License v3. The package consists of the assembler
(`motor68k`/`motor6502`/`motorz80`/`motordcpu16`/`motormips`/`motorschip`), the librarian
(`xlib`) and the linker (`xlink`).

- 上游主页: https://github.com/asmotor/asmotor
- 版本: 1.0.0
- 构建系统: CMake (C99)

## 组件

| 二进制 | 用途 |
|---|---|
| motor68k | 680x0 家族交叉汇编器 |
| motor6502 | 6502 交叉汇编器 |
| motorz80 | Z80 / Game Boy (SM83) 汇编器 |
| motordcpu16 | DCPU-16 汇编器 |
| motormips | MIPS32 汇编器 |
| motorschip | CHIP-8 / SCHIP 汇编器 |
| xlib | 库管理器 |
| xlink | 链接器 |

## 版本索引

| 版本 | 状态 | 构建系统 |
|---|---|---|
| 1.0.0 | published | cmake |
