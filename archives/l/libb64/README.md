# libb64

libb64 是用 ANSI C 编写的快速 Base64 编码/解码库，附带 C++ 包装器及独立的编码/解码可执行程序。源码由 V4 of the Base64 流式编解码算法实现，已进入公有领域（CC-PDDC）。

## 功能概述

- 流式（分块）Base64 编码与解码，可处理任意长度数据
- 纯 ANSI C 实现，仅依赖 libc
- 提供 C++ 包装类（encode.h / decode.h）
- 附带独立 base64 编码/解码命令行工具

## OHOS 适配要点

- **构建系统**: 简单 Makefile（非 autotools，无 configure 脚本）
- **交叉编译**: 上游 Makefile 硬编码 `gcc`/`ar` 且带 `-Werror -pedantic`，不适合交叉编译。conanfile.py 不打补丁、不修改上游源码，直接用 OHOS toolchain（`tools.build:compiler_executables`）编译 `src/cencode.c` 与 `src/cdecode.c` 两个真实源文件，并用 `llvm-ar` 归档为 `libb64.a`
- **产物**: 静态库 `lib/libb64.a` + 公共头文件 `include/b64/{cencode.h,cdecode.h}`
- **许可证**: CC-PDDC（公有领域）
- **无系统同名库**: 纯静态库，不向系统路径输出 `.so`，无同名库冲突
- **公开 C API**（从源码头文件确认）:
  - `base64_init_encodestate(base64_encodestate*)`
  - `base64_encode_block(const char*, int, char*, base64_encodestate*)`
  - `base64_encode_blockend(char*, base64_encodestate*)`
  - `base64_init_decodestate(base64_decodestate*)`
  - `base64_decode_block(const char*, int, char*, base64_decodestate*)`
- **测试**: test_package 为真实功能测试（链接库、编码固定字符串并校验、解码并校验恢复原文），非 include-only 测试
