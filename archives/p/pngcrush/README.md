# pngcrush

PNG 图片无损优化（重压缩）命令行工具，可减小 PNG 文件体积并修正部分格式问题。

## 可用版本

| 版本 | 状态 | 构建系统 |
|------|------|----------|
| 1.8.13 | built | makefile |

## 注意事项

- pngcrush 为纯 Makefile 项目（无 configure/autotools/cmake），源码自带 libpng-1.6.32 与 zlib-1.2.11，编译为单一静态可执行文件，无外部动态库依赖（仅 libc/libm）。
- 默认 Makefile 同时启用 INTEL SSE / MIPS MSA / POWERPC VSX / ARM NEON 指令集；统一构建会把对应 `filter_*.c` 直接 `#include` 进来，其中 x86/MIPS/POWERPC 的内联汇编在 aarch64 上无法编译，故补丁仅保留 ARM NEON。
- HarmonyOS 平台执行二进制需进行 ELF 签名（sign-elf）。
